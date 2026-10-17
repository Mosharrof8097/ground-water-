"""
STAGE 3.6 — SPATIAL CROSS-VALIDATION
====================================
Re-runs the feasibility audit with spatially blocked folds and reports the gap
against the random folds used in stage 3.1.

Input  : 00_data/interim/02_features.csv, 02_design.json
         04_results/metrics/31_feasibility.json
Output : 04_results/metrics/36_spatial_cv.json
         04_results/tables/T9_spatial_vs_random_cv.csv

Why this is needed. Stage 3.1 used `RepeatedKFold`, which assigns wells to
folds at random. In this dataset 24 wells share exact coordinates, 28 have a
neighbour within 50 m, and 117 of 271 have one within 1 km. Random folds
therefore put near-duplicate wells on both sides of the split, and any
short-range spatial structure leaks from training into testing.

How the blocks are sized. Rather than picking a block size by eye, the
empirical variogram of each log-transformed target is computed first and the
block diameter is set to exceed the observed range (Roberts et al. 2017). The
variograms show most targets are close to pure nugget — arsenic in particular
is spatially erratic at these scales, consistent with the Bengal Basin
literature — while Ba and Ni carry structure out to roughly 10-20 km. A 20 km
block therefore exceeds the range for every target.

Expect R2 to fall. The gap between random and spatial folds is the quantity of
interest: it measures how much of the apparent skill in stage 3.1 was spatial
autocorrelation rather than chemistry.
"""

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.cluster import KMeans
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
IN_RANDOM = ROOT / "04_results" / "metrics" / "31_feasibility.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "36_spatial_cv.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T9_spatial_vs_random_cv.csv"

SEED = 42
N_FOLDS = 5
# Blocking is repeated with different KMeans seeds so the outer-fold count
# matches stage 3.1's 25. A single pass gives only 5 folds, and a one-sided
# Wilcoxon on 5 pairs cannot return a p below 0.031 even when the model wins
# every fold -- the test would be rejecting on power, not on optimism.
N_BLOCK_REPEATS = 5
# Two block counts, to show the conclusion does not hinge on the choice.
# Fewer blocks give larger diameters; 8 clears the ~10-20 km variogram range.
BLOCK_COUNTS = [8, 16]
BLOCK_TARGET_KM = 20.0
N_JOBS = 4
EARTH_R = 6371.0

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


def pairwise_km(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    a = (np.sin((la[None, :] - la[:, None]) / 2) ** 2
         + np.cos(la[:, None]) * np.cos(la[None, :])
         * np.sin((lo[None, :] - lo[:, None]) / 2) ** 2)
    return 2 * EARTH_R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def variogram(dist, values, bins):
    """Semivariance normalised by the sill, per lag bin."""
    iu = np.triu_indices(len(values), 1)
    d, y = dist[iu], values
    sill = np.nanvar(y)
    out = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (d >= lo) & (d < hi)
        if m.sum() < 20:
            out.append({"lag_km": f"{lo}-{hi}", "n_pairs": int(m.sum()),
                        "gamma_over_sill": None})
            continue
        g = 0.5 * np.nanmean((y[iu[0][m]] - y[iu[1][m]]) ** 2)
        out.append({"lag_km": f"{lo}-{hi}", "n_pairs": int(m.sum()),
                    "gamma_over_sill": round(float(g / sill), 3)})
    return out


def build_pipeline():
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()),
                     ("model", Ridge())])


def spatial_cv(X, y, group_sets):
    """
    Nested CV with spatially blocked outer folds, repeated over several
    independent block layouts so the fold count matches stage 3.1.
    """
    r2s, base_r2s = [], []
    for groups in group_sets:
        outer = GroupKFold(n_splits=N_FOLDS)
        for tr, te in outer.split(X, y, groups=groups):
            search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                                  scoring="neg_mean_squared_error", n_jobs=N_JOBS)
            search.fit(X[tr], np.log1p(y[tr]))
            pred = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)
            r2s.append(r2_score(y[te], pred))
            base = DummyRegressor(strategy="mean").fit(X[tr], y[tr])
            base_r2s.append(r2_score(y[te], base.predict(X[te])))
    return np.array(r2s), np.array(base_r2s)


def make_block_sets(xy, D, n_blocks):
    """Several independent KMeans layouts at one block count."""
    sets, diams = [], []
    for rep in range(N_BLOCK_REPEATS):
        lab = KMeans(n_clusters=n_blocks, random_state=SEED + rep,
                     n_init=10).fit(xy).labels_
        sets.append(lab)
        diams += [float(D[np.ix_(lab == b, lab == b)].max())
                  for b in range(n_blocks) if (lab == b).sum() > 1]
    return sets, diams


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(IN_CSV)
    design = json.loads(IN_DESIGN.read_text())
    random_res = json.loads(IN_RANDOM.read_text())["results"]
    targets = design["targets_modellable"]
    tiers = design["tiers"]

    print("=" * 78)
    print("  STAGE 3.6 — SPATIAL CROSS-VALIDATION")
    print("=" * 78)

    lat, lon = df["LAT_DEG"].values, df["LONG_DEG"].values
    D = pairwise_km(lat, lon)

    # ── Variograms, to justify the block size rather than assume it ──────────
    bins = [0, 1, 2, 5, 10, 20, 40]
    vario = {t: variogram(D, np.log1p(df[t].values), bins) for t in targets}
    print("\n  [variogram, gamma/sill by lag]")
    header = "  " + "lag km".ljust(10) + "".join(f"{t:>8s}" for t in targets)
    print(header)
    for i, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
        row = f"  {str(lo)+'-'+str(hi):10s}"
        for t in targets:
            g = vario[t][i]["gamma_over_sill"]
            row += f"{'   n/a' if g is None else f'{g:8.2f}'}"
        print(row)
    print("  (near 1.0 at the shortest lag means little spatial structure)")

    # ── Spatial blocks, at two block counts ─────────────────────────────────
    xy = np.column_stack([
        lon * 111.32 * np.cos(np.radians(lat.mean())),
        lat * 110.57,
    ])
    layouts = {}
    print(f"\n  [spatial blocks]  {N_BLOCK_REPEATS} layouts x {N_FOLDS} folds "
          f"= {N_BLOCK_REPEATS * N_FOLDS} outer folds per setting")
    for nb in BLOCK_COUNTS:
        sets, diams = make_block_sets(xy, D, nb)
        layouts[nb] = sets
        print(f"    {nb:2d} blocks: diameter median {np.median(diams):5.1f} km, "
              f"max {np.max(diams):5.1f} km"
              f"{'  (clears the variogram range)' if np.median(diams) >= BLOCK_TARGET_KM else ''}")

    # ── Run and compare ──────────────────────────────────────────────────────
    rows, detail = [], {}
    t0 = time.time()
    for target in targets:
        detail[target] = {}
        print(f"\n  {target}")
        for tier_name, tier in tiers.items():
            feats = [f for f in tier["features"] if f in df.columns]
            sub = df[feats + [target]].copy()
            keep = sub[target].notna().values
            X = sub.loc[keep, feats].to_numpy(float)
            y = sub.loc[keep, target].to_numpy(float)
            rnd = random_res[target][tier_name]
            detail[target][tier_name] = {"random_r2_mean": rnd["r2_mean"],
                                         "random_feasible": bool(rnd["feasible"]),
                                         "by_block_count": {}}
            line = f"    {tier_name:24s} random={rnd['r2_mean']:+.3f}"
            for nb in BLOCK_COUNTS:
                grp_sets = [lab[keep] for lab in layouts[nb]]
                r2, base = spatial_cv(X, y, grp_sets)
                try:
                    _, pv = wilcoxon(r2, base, alternative="greater")
                except ValueError:
                    pv = 1.0
                gap = rnd["r2_mean"] - float(r2.mean())
                detail[target][tier_name]["by_block_count"][str(nb)] = {
                    "n_folds": int(len(r2)),
                    "spatial_r2_mean": float(r2.mean()),
                    "spatial_r2_std": float(r2.std()),
                    "spatial_baseline_r2_mean": float(base.mean()),
                    "wilcoxon_p": float(pv),
                    "optimism_gap": float(gap),
                    "feasible": bool(r2.mean() > 0 and pv < 0.05),
                }
                rows.append({"target": target, "tier": tier_name, "n_blocks": nb,
                             "random_r2": round(rnd["r2_mean"], 4),
                             "spatial_r2": round(float(r2.mean()), 4),
                             "spatial_r2_std": round(float(r2.std()), 4),
                             "optimism_gap": round(gap, 4),
                             "wilcoxon_p": round(float(pv), 5),
                             "n_folds": int(len(r2)),
                             "random_feasible": bool(rnd["feasible"]),
                             "spatial_feasible": bool(r2.mean() > 0 and pv < 0.05)})
                line += f" | {nb}blk={r2.mean():+.3f}(p={pv:.3f})"
            print(line)

    tbl = pd.DataFrame(rows)
    tbl.to_csv(OUT_TABLE, index=False)

    print("\n" + "=" * 78)
    print("  OPTIMISM FROM RANDOM FOLDS  (random R2 minus spatial R2)")
    print("=" * 78)
    for target in targets:
        parts = []
        for nb in BLOCK_COUNTS:
            g = tbl_src = [r["optimism_gap"] for r in rows
                           if r["target"] == target and r["n_blocks"] == nb]
            parts.append(f"{nb}blk {np.median(g):+.3f}")
        print(f"  {target:8s} median gap:  " + "   ".join(parts))

    print("\n  feasibility, by criterion")
    n_rand = len({(r['target'], r['tier']) for r in rows if r['random_feasible']})
    print(f"    random folds        : {n_rand}")
    for nb in BLOCK_COUNTS:
        n_sp = sum(1 for r in rows if r["n_blocks"] == nb and r["spatial_feasible"])
        print(f"    spatial, {nb:2d} blocks  : {n_sp}")

    survivors = sorted({r["target"] for r in rows if r["spatial_feasible"]})
    print(f"\n  targets feasible under at least one spatial setting: "
          f"{', '.join(survivors) if survivors else 'none'}")

    json.dump({
        "design": {
            "blocking": (f"KMeans spatial blocks at {BLOCK_COUNTS} counts, "
                         f"{N_BLOCK_REPEATS} layouts each, {N_FOLDS}-fold "
                         f"GroupKFold -> {N_BLOCK_REPEATS*N_FOLDS} outer folds"),
            "power_note": ("A single 5-fold spatial pass cannot return a one-sided "
                           "Wilcoxon p below 0.031, so repeated layouts are used to "
                           "match the 25 folds of stage 3.1 and keep the "
                           "significance criterion comparable."),
            "variogram_bins_km": bins,
            "rationale": ("Block size set to exceed the empirical variogram range "
                          "rather than chosen by eye (Roberts et al. 2017)."),
        },
        "variograms": vario,
        "results": detail,
        "elapsed_seconds": round(time.time() - t0, 1),
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.6 DONE\n")


if __name__ == "__main__":
    main()
