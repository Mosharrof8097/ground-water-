"""
STAGE 3.3 — HOW MUCH DOES DL/2 SUBSTITUTION COST?
=================================================
Substituting half the detection limit for censored values is the default in
applied hydrogeochemistry and has been criticised for decades (Helsel 2005,
2012) without the practice changing much. This stage measures what it actually
does to the conclusions, on data where censoring ranges from 0 % to 34 % among
the modellable targets.

Input  : 00_data/interim/02_features.csv, 01_clean.csv, 02_design.json
Output : 04_results/metrics/33_censoring.json
         04_results/tables/T4_censoring_comparison.csv

Four ways of handling a value reported as "< DL" are compared on identical
cross-validation folds:

  substitute_half   y = DL / 2          the common default
  substitute_dl     y = DL              upper bound
  substitute_zero   y = 0               lower bound
  ros               regression on order statistics — censored values are
                    imputed from a lognormal fitted to the observed values,
                    preserving the distribution rather than stacking every
                    censored sample on one number

The spread across these four is the honest uncertainty that the usual single
choice hides. Where it is wide, any result based on DL/2 alone is fragile.

A separate check reports how far the fitted model's predictions move between
substitution rules, since a difference in R2 is easy to wave away but a
difference in the predicted concentration at a given well is not.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_FEATURES = ROOT / "00_data" / "interim" / "02_features.csv"
IN_CLEAN = ROOT / "00_data" / "interim" / "01_clean.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "33_censoring.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T4_censoring_comparison.csv"

N_SPLITS, N_REPEATS, SEED = 5, 5, 42
N_JOBS = 4
TIER = "E4_plus_well_record"      # the tier carried forward for this comparison

# Same search space as stage 3.1, so the only thing that varies between runs
# here is how censored values were filled in.
PARAM_GRID = [
    {"model": [Ridge()], "model__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
    {"model": [ElasticNet(max_iter=5000)],
     "model__alpha": [0.01, 0.1, 1.0], "model__l1_ratio": [0.2, 0.5, 0.8]},
    {"model": [HuberRegressor(max_iter=500)],
     "model__alpha": [1e-4, 1e-2], "model__epsilon": [1.35, 1.75]},
    {"model": [SVR(kernel="rbf")],
     "model__C": [1.0, 10.0], "model__gamma": ["scale", 0.1]},
    {"model": [RandomForestRegressor(n_estimators=150, random_state=SEED, n_jobs=1)],
     "model__max_depth": [3, 5], "model__min_samples_leaf": [2, 5]},
]


def ros_impute(values, censored, seed=SEED):
    """
    Regression on order statistics.

    Fit a lognormal to the uncensored observations, then draw each censored
    value from that distribution truncated above at its own detection limit.
    Unlike substitution this keeps the shape of the lower tail instead of
    collapsing it onto a single point, and it respects a column that carries
    more than one detection limit.
    """
    rng = np.random.default_rng(seed)
    out = values.astype(float).copy()
    obs = values[~censored & np.isfinite(values) & (values > 0)]
    if len(obs) < 10:
        return np.where(censored, values / 2.0, values)

    log_obs = np.log(obs)
    mu, sigma = log_obs.mean(), log_obs.std(ddof=1)
    if not np.isfinite(sigma) or sigma <= 0:
        return np.where(censored, values / 2.0, values)

    idx = np.where(censored)[0]
    for i in idx:
        dl = values[i]
        if not np.isfinite(dl) or dl <= 0:
            continue
        # Draw from the lognormal conditioned on being below this sample's DL
        u_max = stats.norm.cdf((np.log(dl) - mu) / sigma)
        u = rng.uniform(1e-6, max(u_max, 1e-5))
        out[i] = float(np.exp(mu + sigma * stats.norm.ppf(u)))
    return out


def cv_r2(X, y, grid):
    """
    5x5 repeated CV R2 on log1p(y), scored on the original scale.

    The model is searched inside each training fold, exactly as in stage 3.1.
    An earlier version fixed Ridge for every target, which confounded the
    comparison: targets that need a non-linear model scored badly regardless of
    the censoring rule, and the spread between rules then reflected an
    ill-fitting model rather than the substitution choice.
    """
    cv = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
    scores, preds = [], np.zeros(len(y))
    for tr, te in cv.split(X):
        base = Pipeline([("i", SimpleImputer(strategy="median")),
                         ("s", StandardScaler()),
                         ("model", Ridge())])
        search = GridSearchCV(base, grid, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X[tr], np.log1p(y[tr]))
        p = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)
        scores.append(r2_score(y[te], p))
        preds[te] = p
    return np.array(scores), preds


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)

    feats_df = pd.read_csv(IN_FEATURES)
    clean = pd.read_csv(IN_CLEAN)
    design = json.loads(IN_DESIGN.read_text())
    targets = design["targets_modellable"]
    feats = [f for f in design["tiers"][TIER]["features"] if f in feats_df.columns]

    print("=" * 76)
    print("  STAGE 3.3 — COST OF DL/2 SUBSTITUTION")
    print("=" * 76)
    print(f"  Tier: {TIER}  ({len(feats)} features)\n")

    rows, detail = [], {}
    for target in targets:
        cens_col = f"{target}_censored"
        if cens_col not in clean.columns:
            continue

        mask = clean[target].notna().to_numpy()
        y_dl = clean.loc[mask, target].to_numpy(dtype=float)
        cens = clean.loc[mask, cens_col].to_numpy(dtype=bool)
        X = feats_df.loc[mask, feats].to_numpy(dtype=float)
        pct = 100.0 * cens.mean()

        variants = {
            "substitute_half": np.where(cens, y_dl / 2.0, y_dl),
            "substitute_dl": y_dl.copy(),
            "substitute_zero": np.where(cens, 0.0, y_dl),
            "ros": ros_impute(y_dl, cens),
        }

        scores, preds = {}, {}
        for name, y in variants.items():
            s, p = cv_r2(X, y, PARAM_GRID)
            scores[name] = s
            preds[name] = p

        r2s = {k: float(v.mean()) for k, v in scores.items()}
        spread = max(r2s.values()) - min(r2s.values())

        # How far predictions move between the common default and ROS
        shift = float(np.median(np.abs(preds["substitute_half"] - preds["ros"])))
        med = float(np.median(y_dl))
        shift_rel = 100.0 * shift / med if med > 0 else np.nan

        detail[target] = {
            "pct_censored": round(pct, 1),
            "r2_by_rule": {k: round(v, 4) for k, v in r2s.items()},
            "r2_spread": round(spread, 4),
            "median_abs_prediction_shift_half_vs_ros": round(shift, 4),
            "shift_as_pct_of_median": None if np.isnan(shift_rel) else round(shift_rel, 1),
        }
        rows.append({
            "target": target,
            "pct_censored": round(pct, 1),
            **{f"r2_{k}": round(v, 4) for k, v in r2s.items()},
            "r2_spread": round(spread, 4),
            "pred_shift_pct_of_median": None if np.isnan(shift_rel) else round(shift_rel, 1),
        })

        print(f"  {target:8s} censored {pct:4.0f}%  "
              f"DL/2={r2s['substitute_half']:+.3f}  DL={r2s['substitute_dl']:+.3f}  "
              f"0={r2s['substitute_zero']:+.3f}  ROS={r2s['ros']:+.3f}  "
              f"spread={spread:.3f}")

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "tier": TIER,
        "estimator": "model searched inside each training fold (same space as "
                     "stage 3.1); identical folds across rules, so only the "
                     "censoring treatment varies",
        "cv": f"{N_SPLITS}x{N_REPEATS} repeated CV on identical folds",
        "rules": {
            "substitute_half": "y = DL/2 (the common default)",
            "substitute_dl": "y = DL (upper bound)",
            "substitute_zero": "y = 0 (lower bound)",
            "ros": "regression on order statistics; lognormal fit to observed "
                   "values, censored values drawn truncated at their own DL",
        },
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.3 DONE\n")


if __name__ == "__main__":
    main()
