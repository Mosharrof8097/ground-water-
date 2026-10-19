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


def stochastic_conditional_impute(values, censored, seed=SEED):
    """
    Stochastic conditional imputation.

    Fit a lognormal to the uncensored observations, then draw each censored
    value from that distribution truncated above at its own detection limit.

    This is deliberately not called regression on order statistics. ROS in the
    sense of Helsel plots the detected values against their normal scores, fits
    a line and reads the censored values off that line, which is deterministic.
    Drawing from a fitted distribution is a different estimator, and a single
    draw at that; proper treatment would use multiple imputation.
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


def cv_r2(X, y, grid, y_ref=None, score_mask=None):
    """
    5x5 repeated CV, trained on log1p(y), scored on one common reference.

    The model is searched inside each training fold, exactly as in stage 3.1.
    An earlier version fixed Ridge for every target, which confounded the
    comparison: targets that need a non-linear model scored badly regardless of
    the censoring rule, and the spread between rules then reflected an
    ill-fitting model rather than the substitution choice.

    A second confound mattered more. Each rule rebuilds the whole target
    vector, so scoring every arm against its own vector judged four models
    against four different truths and the spread between them measured target
    variance as much as model distortion. The rule now governs the training
    target only: `y_ref` supplies the values every arm is scored against, and
    `score_mask` restricts scoring to test wells whose value is a genuine
    measurement rather than a reconstructed one.

    Scores are reported on the original scale and on the log scale. The
    original scale is dominated by a few high wells, the log scale is the one
    the model was fitted on, and the two answer different questions.
    """
    if y_ref is None:
        y_ref = y
    if score_mask is None:
        score_mask = np.ones(len(y), dtype=bool)

    cv = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
    scores, scores_log, maes, preds = [], [], [], np.zeros(len(y))
    for tr, te in cv.split(X):
        base = Pipeline([("i", SimpleImputer(strategy="median")),
                         ("s", StandardScaler()),
                         ("model", Ridge())])
        search = GridSearchCV(base, grid, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X[tr], np.log1p(y[tr]))
        p = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)
        preds[te] = p

        keep = score_mask[te]
        if keep.sum() < 3:
            continue
        truth, pred = y_ref[te][keep], p[keep]
        scores.append(r2_score(truth, pred))
        scores_log.append(r2_score(np.log1p(truth), np.log1p(pred)))
        maes.append(float(np.mean(np.abs(np.log1p(truth) - np.log1p(pred)))))
    return (np.array(scores), preds, np.array(scores_log), np.array(maes))


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
            "stochastic_imputation": stochastic_conditional_impute(y_dl, cens),
        }

        # Every arm is scored against the same truth, on the test wells whose
        # value was actually measured. The rule then governs only what the
        # model was trained on, which is the thing being compared.
        uncensored = ~cens
        med = float(np.median(y_dl))
        n_ref = int(uncensored.sum())
        if n_ref < 30:
            print(f"  {target:8s} skipped: only {n_ref} uncensored wells to "
                  f"score against")
            continue

        scores, preds, logs, maes = {}, {}, {}, {}
        for name, y in variants.items():
            sc, pr, lg, ma = cv_r2(X, y, PARAM_GRID,
                                   y_ref=y_dl, score_mask=uncensored)
            scores[name], preds[name], logs[name], maes[name] = sc, pr, lg, ma

        # Scoring only on measured wells leaves out the lower tail, which is
        # exactly where a substitution rule bites, so the spread above can
        # understate the rule's effect. This second column looks at the
        # censored wells without needing a truth for them: a prediction that
        # respects "< DL" should itself fall below that DL. Read the two
        # together; a shrinking spread with a falling consistency means the
        # effect moved out of view rather than away.
        consistency = {}
        for name, pr in preds.items():
            if cens.sum() == 0:
                consistency[name] = None
                continue
            below = pr[cens] < y_dl[cens]
            consistency[name] = round(100.0 * float(below.mean()), 1)

        r2s = {k: float(v.mean()) for k, v in scores.items()}
        r2log = {k: float(v.mean()) for k, v in logs.items()}
        mae = {k: float(v.mean()) for k, v in maes.items()}
        spread = max(r2s.values()) - min(r2s.values())
        spread_log = max(r2log.values()) - min(r2log.values())

        # How far predictions move between the common default and the draw
        shift = float(np.median(np.abs(preds["substitute_half"]
                                       - preds["stochastic_imputation"])))
        shift_rel = 100.0 * shift / med if med > 0 else np.nan

        # How much of the distribution the detection limit actually covers.
        # The censoring rate alone says how many values were reported as a
        # limit; this adds the measured values that fall at or below the same
        # limit, which is the mass a substitution rule can move. Lead shows why
        # both are needed: its limit sits at half the median, higher than
        # arsenic's, yet so little mass lies beneath it that no rule has
        # anything to move.
        max_dl = float(np.nanmax(y_dl[cens])) if cens.any() else float("nan")
        mass_at_or_below_dl = (float(np.mean(y_dl <= max_dl)) * 100.0
                               if np.isfinite(max_dl) else 0.0)

        detail[target] = {
            "pct_censored": round(pct, 1),
            "largest_detection_limit": None if not np.isfinite(max_dl) else round(max_dl, 6),
            "dl_as_fraction_of_median": (None if not np.isfinite(max_dl) or med <= 0
                                         else round(max_dl / med, 4)),
            "pct_mass_at_or_below_dl": round(mass_at_or_below_dl, 1),
            "n_scored_against": n_ref,
            "n_censored": int(cens.sum()),
            "censored_consistency_pct": consistency,
            "r2_by_rule": {k: round(v, 4) for k, v in r2s.items()},
            "r2_log_by_rule": {k: round(v, 4) for k, v in r2log.items()},
            "mae_log_by_rule": {k: round(v, 4) for k, v in mae.items()},
            "r2_spread": round(spread, 4),
            "r2_log_spread": round(spread_log, 4),
            "median_abs_prediction_shift_half_vs_imputation": round(shift, 4),
            "shift_as_pct_of_median": None if np.isnan(shift_rel) else round(shift_rel, 1),
        }
        rows.append({
            "target": target,
            "pct_censored": round(pct, 1),
            "largest_detection_limit": None if not np.isfinite(max_dl) else round(max_dl, 6),
            "dl_as_fraction_of_median": (None if not np.isfinite(max_dl) or med <= 0
                                         else round(max_dl / med, 4)),
            "pct_mass_at_or_below_dl": round(mass_at_or_below_dl, 1),
            "n_scored_against": n_ref,
            "n_censored": int(cens.sum()),
            **{f"consistency_{k}": consistency[k] for k in consistency},
            **{f"r2_{k}": round(v, 4) for k, v in r2s.items()},
            "r2_spread": round(spread, 4),
            **{f"r2log_{k}": round(v, 4) for k, v in r2log.items()},
            "r2_log_spread": round(spread_log, 4),
            "pred_shift_pct_of_median": None if np.isnan(shift_rel) else round(shift_rel, 1),
        })

        print(f"           detection limit {max_dl:g} = {max_dl/med:.2f} of the "
              f"median, with {mass_at_or_below_dl:.0f}% of wells at or below it")
        print(f"  {target:8s} censored {pct:4.0f}%  scored on {n_ref:3d} "
              f"measured wells  DL/2={r2s['substitute_half']:+.3f}  "
              f"DL={r2s['substitute_dl']:+.3f}  0={r2s['substitute_zero']:+.3f}  "
              f"draw={r2s['stochastic_imputation']:+.3f}  spread={spread:.3f}  "
              f"(log spread={spread_log:.3f})")
        if cens.sum():
            print(f"           censored-consistency (% of {int(cens.sum())} "
                  f"censored wells predicted below their own DL): "
                  + "  ".join(f"{k.replace('substitute_', '')}="
                              f"{consistency[k]:.0f}%" for k in consistency))

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
            "stochastic_imputation": "lognormal fit to the observed values, "
                   "each censored value drawn from it truncated at its own "
                   "detection limit; a single draw, not multiple imputation, "
                   "and not regression on order statistics in Helsel's sense",
        },
        "censored_consistency": ("Percentage of censored test wells whose "
                    "out-of-fold prediction falls below that well's own "
                    "detection limit. It needs no truth for those wells and "
                    "covers the lower tail that the common reference excludes."),
        "scoring": ("Every rule is scored against the same reference, the "
                    "reported values at test wells that were actually "
                    "measured, so the comparison isolates distortion of the "
                    "model from variance in the reconstructed target. Scores "
                    "are given on the original and the log scale."),
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.3 DONE\n")


if __name__ == "__main__":
    main()
