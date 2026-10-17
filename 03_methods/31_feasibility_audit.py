"""
STAGE 3.1 — FEASIBILITY AUDIT
=============================
For every modellable target and every cost tier: can cheap field parameters
beat simply predicting the mean?

Input  : 00_data/interim/02_features.csv, 02_design.json
Output : 04_results/metrics/31_feasibility.json
         04_results/tables/T2_feasibility_matrix.csv

Protocol (fixed in 03_methods/README.md before any of this ran):

- **5x5 repeated nested CV.** 25 outer folds estimate performance; a 3-fold
  inner search picks the model and its hyperparameters.
- **Model choice sits inside the inner loop.** Ridge, ElasticNet, Huber, SVR
  and random forest compete within each training fold, so the reported score
  already pays for model selection. Picking the best model first and scoring it
  afterwards would leak the test folds into that choice.
- **Imputation and scaling are pipeline steps**, fitted on the training fold
  only.
- **log1p target transform**, applied because every target here is strongly
  right-skewed; predictions are inverted before scoring, so R2 is always on the
  original concentration scale.
- **Baseline.** A mean predictor is scored on the identical folds. With n = 271
  and skewed targets, beating it is the real test, not a positive R2.
- **Significance.** Wilcoxon signed-rank on the 25 paired outer-fold scores
  (model vs baseline), then Benjamini-Hochberg across all target x tier
  comparisons, since 35 of them are run at once.

A target x tier combination is called feasible when it beats the baseline and
survives FDR correction. Everything else is reported as not feasible, which is
a result rather than a gap.
"""

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon, spearmanr
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "31_feasibility.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T2_feasibility_matrix.csv"

N_SPLITS, N_REPEATS, SEED = 5, 5, 42
N_JOBS = 4          # physical cores; hyperthreads add little on data this small
ALPHA_FDR = 0.05

# One search space spanning several model families. GridSearchCV treats a list
# of dicts as alternatives, so the inner loop chooses the family too.
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
        ("model", Ridge()),            # replaced by the grid
    ])


def nested_cv(X, y_raw):
    """
    5x5 repeated nested CV on log1p(y), scored on the original scale.

    Returns per-fold scores for the model and for a mean baseline fitted on the
    same folds, so the two are paired and can be compared directly.
    """
    y_t = np.log1p(y_raw)
    outer = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)

    rows = []
    for train_idx, test_idx in outer.split(X):
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr_t, y_te = y_t[train_idx], y_raw[test_idx]

        search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X_tr, y_tr_t)
        pred = np.maximum(np.expm1(search.best_estimator_.predict(X_te)), 0.0)

        base = DummyRegressor(strategy="mean").fit(X_tr, y_raw[train_idx])
        base_pred = base.predict(X_te)

        rows.append({
            "r2": r2_score(y_te, pred),
            "rmse": float(np.sqrt(mean_squared_error(y_te, pred))),
            "mae": float(mean_absolute_error(y_te, pred)),
            "r2_baseline": r2_score(y_te, base_pred),
            "rmse_baseline": float(np.sqrt(mean_squared_error(y_te, base_pred))),
            "model": type(search.best_estimator_.named_steps["model"]).__name__,
            "y_true": y_te.tolist(),
            "y_pred": pred.tolist(),
        })
    return rows


def benjamini_hochberg(pvals, alpha=ALPHA_FDR):
    """Return a boolean array of which p-values survive BH-FDR at `alpha`."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    thresholds = alpha * (np.arange(1, n + 1) / n)
    passed_sorted = p[order] <= thresholds
    keep = np.zeros(n, dtype=bool)
    if passed_sorted.any():
        last = np.max(np.where(passed_sorted)[0])
        keep[order[: last + 1]] = True
    return keep


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_CSV)
    design = json.loads(IN_DESIGN.read_text())
    targets = design["targets_modellable"]
    tiers = design["tiers"]

    only = None
    if "--target" in sys.argv:
        only = sys.argv[sys.argv.index("--target") + 1]
        targets = [t for t in targets if t == only]

    print("=" * 76)
    print("  STAGE 3.1 — FEASIBILITY AUDIT")
    print("=" * 76)
    print(f"  {len(targets)} targets x {len(tiers)} tiers, "
          f"{N_SPLITS}x{N_REPEATS} nested CV\n")

    results, flat = {}, []
    t_start = time.time()

    for target in targets:
        results[target] = {}
        print(f"  {target}")
        for tier_name, tier in tiers.items():
            feats = [f for f in tier["features"] if f in df.columns]
            sub = df[feats + [target]].dropna(subset=[target])
            X = sub[feats].to_numpy(dtype=float)
            y = sub[target].to_numpy(dtype=float)

            t0 = time.time()
            folds = nested_cv(X, y)
            r2 = np.array([f["r2"] for f in folds])
            r2_base = np.array([f["r2_baseline"] for f in folds])

            # Paired comparison against the baseline on identical folds
            try:
                stat, pval = wilcoxon(r2, r2_base, alternative="greater")
            except ValueError:          # identical scores
                stat, pval = np.nan, 1.0

            y_true = np.concatenate([f["y_true"] for f in folds])
            y_pred = np.concatenate([f["y_pred"] for f in folds])
            rho = float(spearmanr(y_true, y_pred).statistic)
            families = pd.Series([f["model"] for f in folds]).value_counts()

            rec = {
                "n": int(len(y)),
                "n_features": len(feats),
                "r2_mean": float(r2.mean()),
                "r2_std": float(r2.std()),
                "r2_median": float(np.median(r2)),
                "r2_baseline_mean": float(r2_base.mean()),
                "delta_r2": float(r2.mean() - r2_base.mean()),
                "rmse_mean": float(np.mean([f["rmse"] for f in folds])),
                "mae_mean": float(np.mean([f["mae"] for f in folds])),
                "spearman_pooled": round(rho, 4),
                "wilcoxon_p": float(pval),
                "folds_won_vs_baseline": int((r2 > r2_base).sum()),
                "n_folds": len(folds),
                "model_family_counts": families.to_dict(),
                "dominant_model": families.index[0],
                "fold_r2": r2.round(4).tolist(),
            }
            results[target][tier_name] = rec
            flat.append({"target": target, "tier": tier_name, **{
                k: rec[k] for k in ("n", "n_features", "r2_mean", "r2_std",
                                    "r2_baseline_mean", "delta_r2", "rmse_mean",
                                    "spearman_pooled", "wilcoxon_p",
                                    "folds_won_vs_baseline", "dominant_model")}})

            print(f"    {tier_name:24s} R2={r2.mean():+.3f}+-{r2.std():.3f}  "
                  f"base={r2_base.mean():+.3f}  rho={rho:+.3f}  "
                  f"p={pval:.4f}  [{rec['dominant_model']}]  {time.time()-t0:.0f}s")

    # FDR across every target x tier comparison
    tbl = pd.DataFrame(flat)
    tbl["fdr_significant"] = benjamini_hochberg(tbl["wilcoxon_p"].values)
    tbl["feasible"] = tbl["fdr_significant"] & (tbl["r2_mean"] > 0)
    tbl = tbl.sort_values(["target", "tier"])
    tbl.to_csv(OUT_TABLE, index=False)

    for _, r in tbl.iterrows():
        results[r["target"]][r["tier"]]["fdr_significant"] = bool(r["fdr_significant"])
        results[r["target"]][r["tier"]]["feasible"] = bool(r["feasible"])

    payload = {
        "protocol": {
            "cv": f"{N_SPLITS}x{N_REPEATS} repeated nested CV ({N_SPLITS*N_REPEATS} outer folds)",
            "model_selection": "inside the inner loop, across 5 model families",
            "target_transform": "log1p, inverted before scoring",
            "baseline": "mean predictor on identical folds",
            "test": "Wilcoxon signed-rank on paired outer-fold R2",
            "correction": f"Benjamini-Hochberg at alpha={ALPHA_FDR}",
            "n_comparisons": int(len(tbl)),
        },
        "results": results,
        "elapsed_seconds": round(time.time() - t_start, 1),
    }
    with open(OUT_METRICS, "w") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 76)
    print("  FEASIBILITY SUMMARY (after BH-FDR)")
    print("=" * 76)
    feasible = tbl[tbl["feasible"]]
    if feasible.empty:
        print("  No target x tier combination beat the mean baseline.")
    else:
        for target in tbl["target"].unique():
            rows = feasible[feasible["target"] == target]
            if rows.empty:
                print(f"  {target:8s} not feasible at any tier")
                continue
            best = rows.loc[rows["r2_mean"].idxmax()]
            cheapest = rows.iloc[0]
            print(f"  {target:8s} feasible at {len(rows)}/{len(tiers)} tiers | "
                  f"best {best['tier']} R2={best['r2_mean']:+.3f} | "
                  f"cheapest {cheapest['tier']} R2={cheapest['r2_mean']:+.3f}")

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print(f"  Elapsed {payload['elapsed_seconds']:.0f}s\n")


if __name__ == "__main__":
    main()
