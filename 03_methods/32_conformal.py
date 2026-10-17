"""
STAGE 3.2 — CONFORMAL PREDICTION
================================
Calibrated prediction intervals for the target x tier combinations that stage
3.1 found feasible.

Input  : 04_results/metrics/31_feasibility.json, 00_data/interim/02_features.csv
Output : 04_results/metrics/32_conformal.json
         04_results/tables/T3_conformal_coverage.csv

Split-conformal, done properly: train, calibration and test are three disjoint
splits. The model is fitted on the training split, q_hat is the (1 - alpha)
quantile of absolute residuals on the **calibration** split, and coverage is
measured on the **test** split, which neither of the other two has touched.
Repeated over many random partitions, since a single split of 271 wells is
noisy.

Why this matters enough to spell out:

    Taking q_hat from a set of residuals and then counting how many of *those
    same* residuals fall inside +-q_hat is circular. q_hat is by construction
    their (1 - alpha) quantile, so the count is pinned near the nominal rate
    whatever the model does — a zero-skill predictor scores the same. That
    error produced an "exactly 90.0 % coverage" claim in an earlier project in
    this repository, for two models whose R2 differed by a factor of twenty-
    five. Coverage is only evidence when it is measured out of sample.

Hyperparameters are selected inside the training split alone, so the reported
coverage pays for model selection too.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
IN_FEAS = ROOT / "04_results" / "metrics" / "31_feasibility.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "32_conformal.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T3_conformal_coverage.csv"

ALPHA = 0.10            # 90 % nominal coverage
# 100 partitions keeps the standard error of the coverage estimate small while
# leaving the whole stage inside a few minutes per combination.
N_REPEATS = 100
SEED = 42
FRAC_TRAIN, FRAC_CAL = 0.50, 0.25      # test takes the remaining 0.25
N_JOBS = 4

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


def build_pipeline():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge()),
    ])


def split_conformal(X, y, alpha=ALPHA, n_repeats=N_REPEATS, seed=SEED):
    """Held-out split-conformal coverage over repeated random partitions."""
    rng = np.random.default_rng(seed)
    n = len(y)
    n_train = int(round(FRAC_TRAIN * n))
    n_cal = int(round(FRAC_CAL * n))

    coverages, widths, q_hats = [], [], []
    for _ in range(n_repeats):
        perm = rng.permutation(n)
        tr, cal, te = perm[:n_train], perm[n_train:n_train + n_cal], perm[n_train + n_cal:]
        if len(te) == 0 or len(cal) == 0:
            continue

        search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X[tr], np.log1p(y[tr]))
        model = search.best_estimator_

        cal_pred = np.maximum(np.expm1(model.predict(X[cal])), 0.0)
        q_hat = float(np.quantile(np.abs(y[cal] - cal_pred), 1 - alpha))

        te_pred = np.maximum(np.expm1(model.predict(X[te])), 0.0)
        lo = np.maximum(te_pred - q_hat, 0.0)
        hi = te_pred + q_hat

        coverages.append(float(np.mean((y[te] >= lo) & (y[te] <= hi))))
        widths.append(float(np.mean(hi - lo)))
        q_hats.append(q_hat)

    return {
        "protocol": (f"split-conformal; disjoint train/calibration/test "
                     f"({FRAC_TRAIN:.0%}/{FRAC_CAL:.0%}/"
                     f"{1-FRAC_TRAIN-FRAC_CAL:.0%}), {len(coverages)} partitions"),
        "nominal_coverage": 1 - alpha,
        "mean_coverage": float(np.mean(coverages)),
        "std_coverage": float(np.std(coverages)),
        "mean_interval_width": float(np.mean(widths)),
        "median_q_hat": float(np.median(q_hats)),
        "n_partitions": len(coverages),
    }


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)

    if not IN_FEAS.exists():
        print("  Run 31_feasibility_audit.py first.")
        return

    df = pd.read_csv(IN_CSV)
    design = json.loads(IN_DESIGN.read_text())
    feas = json.loads(IN_FEAS.read_text())["results"]

    jobs = [(t, tier) for t, tiers in feas.items() for tier, r in tiers.items()
            if r.get("feasible")]

    print("=" * 76)
    print("  STAGE 3.2 — CONFORMAL PREDICTION")
    print("=" * 76)
    print(f"  {len(jobs)} feasible target x tier combinations, "
          f"{int((1-ALPHA)*100)}% nominal, {N_REPEATS} partitions each\n")

    if not jobs:
        print("  Nothing feasible from stage 3.1 — no intervals to calibrate.\n")
        json.dump({"results": {}, "note": "no feasible combinations"},
                  open(OUT_METRICS, "w"), indent=2)
        return

    out, rows = {}, []
    for target, tier_name in jobs:
        feats = [f for f in design["tiers"][tier_name]["features"] if f in df.columns]
        sub = df[feats + [target]].dropna(subset=[target])
        X = sub[feats].to_numpy(dtype=float)
        y = sub[target].to_numpy(dtype=float)

        res = split_conformal(X, y)
        out.setdefault(target, {})[tier_name] = res
        rows.append({
            "target": target,
            "tier": tier_name,
            "nominal_coverage": res["nominal_coverage"],
            "held_out_coverage_mean": round(res["mean_coverage"], 4),
            "held_out_coverage_std": round(res["std_coverage"], 4),
            "mean_interval_width": round(res["mean_interval_width"], 4),
            "median_q_hat": round(res["median_q_hat"], 4),
        })
        print(f"  {target:8s} {tier_name:24s} "
              f"coverage {res['mean_coverage']*100:5.1f}% "
              f"+-{res['std_coverage']*100:4.1f}pp "
              f"(nominal {(1-ALPHA)*100:.0f}%)  "
              f"width {res['mean_interval_width']:.3f}")

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "alpha": ALPHA,
        "note": ("Coverage is measured on test splits disjoint from the "
                 "calibration data used to set q_hat. Measuring it on the "
                 "calibration residuals themselves is circular and returns the "
                 "nominal rate for any model."),
        "results": out,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.2 DONE\n")


if __name__ == "__main__":
    main()
