"""
STAGE 3.16 — IS THE ARSENIC LOG-SCALE SKILL REAL, OR IS IT THE CENSORING?
=========================================================================
Stage 3.6 found that total arsenic keeps a positive log-scale R2 under spatial
blocking while its original-scale R2 is negative. Before that can carry an
abstract claim it has to survive an obvious alternative.

Arsenic is censored in 34 % of wells at two limits, 0.5 and 6.0 ug/L. On the
log scale the lower tail carries a lot of weight, so a model that has merely
learned which wells were reported as a limit, or which analytical batch they
came from, would also show a positive log R2. If limit assignment tracks
district, spatial blocking does not remove it either.

The test is to score the same spatially blocked folds twice: on every test
well, and on only those test wells whose value is a genuine measurement. If
the skill holds on measured wells alone, censoring structure is not what is
driving it.

Random folds are scored the same way, so the optimism gap can be read on the
log scale too.

Input  : 00_data/interim/01_clean.csv, 02_features.csv, 02_design.json
Output : 04_results/metrics/46_log_skill_audit.json
         04_results/tables/T20_log_skill_audit.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ROOT = Path(__file__).resolve().parents[1]
IN_CLEAN = ROOT / "00_data" / "interim" / "01_clean.csv"
IN_FEATURES = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "46_log_skill_audit.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T20_log_skill_audit.csv"

TARGET = "AsTot"
SEED, N_JOBS = 42, 4
N_FOLDS, N_BLOCK_REPEATS = 5, 5
N_SPLITS, N_REPEATS = 5, 5
BLOCK_COUNTS = (8, 16)
MIN_SCORED = 5

# Identical to stage 3.6. The audit only changes which test wells are scored,
# so every other choice has to match or the comparison is not like for like.
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
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()), ("model", Ridge())])


def score_folds(X, y, measured, folds):
    """
    Three scores per fold: original scale, log scale, and log scale over the
    test wells that carry a measurement rather than a detection limit.
    """
    orig, log_all, log_meas = [], [], []
    for tr, te in folds:
        search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X[tr], np.log1p(y[tr]))
        pred = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)

        orig.append(r2_score(y[te], pred))
        log_all.append(r2_score(np.log1p(y[te]), np.log1p(pred)))

        keep = measured[te]
        if keep.sum() >= MIN_SCORED:
            log_meas.append(r2_score(np.log1p(y[te][keep]),
                                     np.log1p(pred[keep])))
    return np.array(orig), np.array(log_all), np.array(log_meas)


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("  STAGE 3.16 — ARSENIC LOG-SCALE SKILL, WITH AND WITHOUT THE")
    print("               CENSORED WELLS IN THE SCORE")
    print("=" * 78)

    clean = pd.read_csv(IN_CLEAN)
    feats_df = pd.read_csv(IN_FEATURES)
    design = json.loads(IN_DESIGN.read_text())

    mask = clean[TARGET].notna().to_numpy()
    y = clean.loc[mask, TARGET].to_numpy(float)
    censored = clean.loc[mask, f"{TARGET}_censored"].to_numpy(bool)
    measured = ~censored

    # Match stage 3.6 exactly: project to kilometres, cluster over every well,
    # then subset. Clustering raw degrees would stretch longitude against
    # latitude and produce different blocks.
    lat = clean["LAT_DEG"].to_numpy(float)
    lon = clean["LONG_DEG"].to_numpy(float)
    xy_all = np.column_stack([lon * 111.32 * np.cos(np.radians(np.nanmean(lat))),
                              lat * 110.57])

    print(f"  {TARGET}: {mask.sum()} wells, {censored.sum()} censored "
          f"({100 * censored.mean():.1f} %), {measured.sum()} measured")
    print(f"  detection limits in use: "
          f"{sorted(set(np.round(y[censored], 4).tolist()))}\n")

    block_sets = {}
    for nb in BLOCK_COUNTS:
        block_sets[nb] = [KMeans(n_clusters=nb, random_state=SEED + r,
                                 n_init=10).fit(xy_all).labels_[mask]
                          for r in range(N_BLOCK_REPEATS)]

    rows, detail = [], {}
    for tier_name, spec in design["tiers"].items():
        feats = [f for f in spec["features"] if f in feats_df.columns]
        X = feats_df.loc[mask, feats].to_numpy(float)

        # random folds, for the optimism gap on the log scale
        rnd = list(RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS,
                                 random_state=SEED).split(X))
        r_orig, r_log, r_logm = score_folds(X, y, measured, rnd)

        rec = {"tier": tier_name, "n_features": len(feats),
               "random": {"r2": round(float(r_orig.mean()), 4),
                          "r2_log": round(float(r_log.mean()), 4),
                          "r2_log_measured_only": round(float(r_logm.mean()), 4)}}
        print(f"  {tier_name:24s} random   "
              f"orig={r_orig.mean():+.4f}  log={r_log.mean():+.4f}  "
              f"log(measured)={r_logm.mean():+.4f}")

        for nb in BLOCK_COUNTS:
            folds = []
            for groups in block_sets[nb]:
                folds += list(GroupKFold(n_splits=N_FOLDS).split(X, y, groups))
            s_orig, s_log, s_logm = score_folds(X, y, measured, folds)

            try:
                _, p_log = wilcoxon(s_logm, alternative="greater")
            except ValueError:
                p_log = float("nan")

            rec[f"spatial_{nb}"] = {
                "r2": round(float(s_orig.mean()), 4),
                "r2_log": round(float(s_log.mean()), 4),
                "r2_log_measured_only": round(float(s_logm.mean()), 4),
                "r2_log_measured_only_sd": round(float(s_logm.std()), 4),
                "n_folds_scored": int(len(s_logm)),
                "wilcoxon_p_log_measured_gt_0": float(p_log),
                "log_optimism_gap": round(float(r_log.mean() - s_log.mean()), 4),
            }
            print(f"  {tier_name:24s} {nb:2d} blocks "
                  f"orig={s_orig.mean():+.4f}  log={s_log.mean():+.4f}  "
                  f"log(measured)={s_logm.mean():+.4f}  p={p_log:.2e}")

            rows.append({
                "target": TARGET, "tier": tier_name, "n_blocks": nb,
                "random_r2": round(float(r_orig.mean()), 4),
                "random_r2_log": round(float(r_log.mean()), 4),
                "random_r2_log_measured": round(float(r_logm.mean()), 4),
                "spatial_r2": round(float(s_orig.mean()), 4),
                "spatial_r2_log": round(float(s_log.mean()), 4),
                "spatial_r2_log_measured": round(float(s_logm.mean()), 4),
                "log_optimism_gap": round(float(r_log.mean() - s_log.mean()), 4),
                "wilcoxon_p_log_measured": round(float(p_log), 6),
            })
        detail[tier_name] = rec
        print()

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)

    held = [r for r in rows if r["n_blocks"] == 8
            and r["spatial_r2_log_measured"] > 0]
    verdict = ("log-scale skill survives on measured wells alone under the "
               "most demanding blocking, so it is not an artefact of which "
               "wells were censored"
               if len(held) >= 3 else
               "log-scale skill does not hold on measured wells alone; it "
               "cannot be separated from the censoring structure and should "
               "not be claimed")

    json.dump({
        "question": ("Whether the positive log-scale R2 for arsenic reflects "
                     "chemistry or merely the structure of which wells were "
                     "reported as a detection limit."),
        "design": ("Identical spatially blocked folds scored twice, on all "
                   "test wells and on measured test wells only. Random folds "
                   "scored the same way give the optimism gap on the log "
                   "scale. Feasibility itself is unchanged and remains the "
                   "pre-specified original-scale criterion."),
        "n_wells": int(mask.sum()), "n_censored": int(censored.sum()),
        "tiers_holding_at_8_blocks": len(held),
        "verdict": verdict,
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print("=" * 78)
    print(f"  {verdict}")
    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.16 DONE")


if __name__ == "__main__":
    sys.exit(main())
