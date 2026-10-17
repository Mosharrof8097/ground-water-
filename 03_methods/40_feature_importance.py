"""
STAGE 3.10 — FEATURE IMPORTANCE
===============================
Which of the low cost predictors carry the signal, and does the answer agree
with the geochemistry.

Input  : 00_data/interim/02_features.csv, 02_design.json, 35_geochem.csv
         04_results/metrics/36_spatial_cv.json
Output : 04_results/metrics/40_importance.json
         04_results/tables/T12_feature_importance.csv

Permutation importance is computed on held-out folds rather than on the fitted
model, so that it reflects loss of predictive skill rather than how the
estimator happened to allocate coefficients. Values are the mean drop in
R-squared across folds when one predictor is shuffled.

The purpose is to connect the statistical result to the mechanism. Stage 3.5
found arsenic elevated in Fe(III) and sulfate reducing zones, which is the
established route of release by reductive dissolution. If iron and manganese
dominate the arsenic model, that correlation has a named cause; if they do not,
the mechanism claimed in the discussion is not the one the model is using.

The E4 tier is used, being the richest set that remains field deployable.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.model_selection import GridSearchCV, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
IN_SPATIAL = ROOT / "04_results" / "metrics" / "36_spatial_cv.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "40_importance.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T12_feature_importance.csv"

TIER = "E4_plus_well_record"
N_SPLITS, N_REPEATS, SEED = 5, 2, 42       # 10 folds is ample for importance
N_PERM = 15
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

# Predictors that index redox condition, as used by the zonation in stage 3.5
REDOX_PROXIES = {"Fe", "Mn", "Eh", "diss O2"}


def build_pipeline():
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()),
                     ("model", Ridge())])


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(IN_CSV)
    design = json.loads(IN_DESIGN.read_text())
    spatial = json.loads(IN_SPATIAL.read_text())["results"]
    targets = design["targets_modellable"]
    feats = [f for f in design["tiers"][TIER]["features"] if f in df.columns]

    print("=" * 74)
    print("  STAGE 3.10 — PERMUTATION FEATURE IMPORTANCE")
    print("=" * 74)
    print(f"  tier {TIER}, {len(feats)} predictors, "
          f"{N_SPLITS * N_REPEATS} folds, {N_PERM} permutations\n")

    rows, detail = [], {}
    for target in targets:
        sub = df[feats + [target]].dropna(subset=[target])
        X = sub[feats].to_numpy(float)
        y = np.log1p(sub[target].to_numpy(float))

        cv = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
        per_fold = []
        for tr, te in cv.split(X):
            search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                                  scoring="neg_mean_squared_error", n_jobs=N_JOBS)
            search.fit(X[tr], y[tr])
            imp = permutation_importance(
                search.best_estimator_, X[te], y[te],
                n_repeats=N_PERM, random_state=SEED, scoring="r2", n_jobs=1)
            per_fold.append(imp.importances_mean)

        arr = np.vstack(per_fold)
        mean, sd = arr.mean(axis=0), arr.std(axis=0)
        total = np.clip(mean, 0, None).sum()
        share = np.clip(mean, 0, None) / total if total > 0 else np.zeros_like(mean)

        order = np.argsort(mean)[::-1]
        redox_share = float(sum(share[i] for i, f in enumerate(feats)
                                if f in REDOX_PROXIES))

        # does this target survive spatial validation at this tier?
        sp = spatial[target][TIER]["by_block_count"]
        robust = any(v["feasible"] for v in sp.values())

        detail[target] = {
            "tier": TIER,
            "spatially_robust": bool(robust),
            "redox_proxy_share": round(redox_share, 4),
            "importance": {feats[i]: {"mean_r2_drop": round(float(mean[i]), 5),
                                      "sd": round(float(sd[i]), 5),
                                      "share": round(float(share[i]), 4)}
                           for i in order},
        }
        for i in order:
            rows.append({"target": target, "feature": feats[i],
                         "mean_r2_drop": round(float(mean[i]), 5),
                         "sd": round(float(sd[i]), 5),
                         "share": round(float(share[i]), 4),
                         "redox_proxy": feats[i] in REDOX_PROXIES,
                         "spatially_robust_target": bool(robust)})

        top = ", ".join(f"{feats[i]} {share[i]*100:.0f}%" for i in order[:3])
        print(f"  {target:6s} {'robust' if robust else 'fragile':8s} "
              f"redox share {redox_share*100:5.1f}%   top: {top}")

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "method": ("permutation importance on held-out folds, mean drop in "
                   "R-squared over 15 permutations, model searched within each "
                   "training fold"),
        "tier": TIER,
        "redox_proxies": sorted(REDOX_PROXIES),
        "note": ("Share is computed over positive importances only; a negative "
                 "mean drop indicates a predictor whose removal does not hurt, "
                 "and is reported but not given share."),
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.10 DONE\n")


if __name__ == "__main__":
    main()
