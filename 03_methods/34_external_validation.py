"""
STAGE 3.4 — EXTERNAL VALIDATION
===============================
Fits on the 271 special-study-area wells and tests on independent wells from
the national survey: different districts, different sampling campaign,
different analytical batch.

Input  : 00_data/raw/special_study_areas_271_boreholes.csv   (development)
         00_data/raw/NHS_national_survey_3534_boreholes.csv  (external)
Output : 04_results/metrics/34_external.json
         04_results/tables/T5_external_validation.csv

Three things had to be settled before this was meaningful.

**Geographic independence.** Nawabganj is the one district the two files share,
and 11 development wells sit within 500 m of a national-survey well — some at
the same coordinates. Nawabganj is therefore dropped from the external set,
leaving 15 districts with no spatial overlap. The minimum separation is
asserted at run time rather than assumed.

**Units.** Al is reported in ug/L in the development file and mg/L in the
national file, a silent factor of 1000. It is excluded, and every remaining
shared column has its unit string checked before use.

**The transferable predictor set is smaller than the one stage 3.1 used.** The
national survey carries no pH, Eh, SEC, temperature, Cl, HCO3 or NO3-N, so the
E2 tier that made arsenic work cannot be transferred. What follows validates a
*reduced* model, and the in-development score for that same reduced set is
reported alongside, so the drop attributable to transfer can be separated from
the drop attributable to losing predictors.

Performance is expected to fall. By how much is the result.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DEV_CSV = ROOT / "00_data" / "raw" / "special_study_areas_271_boreholes.csv"
EXT_CSV = ROOT / "00_data" / "raw" / "NHS_national_survey_3534_boreholes.csv"
OUT_METRICS = ROOT / "04_results" / "metrics" / "34_external.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T5_external_validation.csv"

SKIP_BANNER = 4
SEED = 42
N_SPLITS, N_REPEATS = 5, 5
N_CONFORMAL_SPLITS = 100
ALPHA = 0.10
N_JOBS = 4
MIN_SEPARATION_KM = 1.0      # asserted between development and external wells

NORTH_BENGAL = [
    "Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram", "Lalmonirhat",
    "Naogaon", "Natore", "Nawabganj", "Nilphamari", "Pabna", "Panchagarh",
    "Rajshahi", "Rangpur", "Sirajganj", "Thakurgaon",
]
EXCLUDE_DISTRICT = "Nawabganj"      # shared with the development set

# Shared predictors. Al is deliberately absent: ug/L here, mg/L there.
TIERS = {
    "T_cheap": ["Fe", "Mn", "WELL_DEPTH"],
    "T_full": ["Fe", "Mn", "WELL_DEPTH", "Ca", "Mg", "Na", "SO4", "Si", "Sr"],
}

# development column -> external column
TARGETS = {"AsTot": "As", "Ba": "Ba"}
WHO_LIMIT = {"AsTot": 10.0, "Ba": 1300.0}

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


def conformal_quantile(scores, alpha):
    """Finite-sample split-conformal quantile; see stage 3.2 for the reasoning."""
    scores = np.sort(np.asarray(scores, dtype=float))
    n = len(scores)
    k = int(np.ceil((n + 1) * (1.0 - alpha)))
    return float(scores[-1] if k > n else scores[k - 1])


def load_bgs(path):
    """Read a BGS file, returning the data frame and its units row."""
    raw = pd.read_csv(path, skiprows=SKIP_BANNER, low_memory=False)
    units = raw.iloc[0].to_dict()
    df = raw.iloc[1:].reset_index(drop=True)
    return df[df["SAMPLE_ID"].notna()].reset_index(drop=True), units


def numeric(series):
    """Strip '<' from censored entries and coerce to float (keeps the limit)."""
    return pd.to_numeric(
        series.astype(str).str.replace("<", "", regex=False).str.strip(),
        errors="coerce")


def haversine_min_km(lat1, lon1, lat2, lon2):
    """Nearest-neighbour distance in km from each point in set 1 to set 2."""
    R = 6371.0
    la1, lo1 = np.radians(lat1)[:, None], np.radians(lon1)[:, None]
    la2, lo2 = np.radians(lat2)[None, :], np.radians(lon2)[None, :]
    a = (np.sin((la2 - la1) / 2) ** 2
         + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2)
    return (2 * R * np.arcsin(np.sqrt(a))).min(axis=1)


def build_pipeline():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge()),
    ])


def fit_searched(X, y_log):
    search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                          scoring="neg_mean_squared_error", n_jobs=N_JOBS)
    search.fit(X, y_log)
    return search.best_estimator_


def internal_cv(X, y):
    """In-development CV for the same reduced predictor set, for comparison."""
    cv = RepeatedKFold(n_splits=N_SPLITS, n_repeats=N_REPEATS, random_state=SEED)
    scores, scores_log = [], []
    for tr, te in cv.split(X):
        model = fit_searched(X[tr], np.log1p(y[tr]))
        pred = np.maximum(np.expm1(model.predict(X[te])), 0.0)
        scores.append(r2_score(y[te], pred))
        scores_log.append(r2_score(np.log1p(y[te]), np.log1p(pred)))
    return (float(np.mean(scores)), float(np.std(scores)),
            float(np.mean(scores_log)))


def conformal_transfer(X_dev, y_dev, X_ext, y_ext, rng):
    """
    Calibrate q_hat on held-out development wells, then measure coverage on the
    external set. Split-conformal guarantees validity only under
    exchangeability; development and external wells are not exchangeable, so
    this measures how far the guarantee actually travels.
    """
    n = len(y_dev)
    coverages, widths = [], []
    for _ in range(N_CONFORMAL_SPLITS):
        perm = rng.permutation(n)
        n_tr = int(round(0.70 * n))
        tr, cal = perm[:n_tr], perm[n_tr:]

        model = fit_searched(X_dev[tr], np.log1p(y_dev[tr]))
        cal_pred = np.maximum(np.expm1(model.predict(X_dev[cal])), 0.0)
        q_hat = conformal_quantile(np.abs(y_dev[cal] - cal_pred), ALPHA)

        ext_pred = np.maximum(np.expm1(model.predict(X_ext)), 0.0)
        lo = np.maximum(ext_pred - q_hat, 0.0)
        coverages.append(float(np.mean((y_ext >= lo) & (y_ext <= ext_pred + q_hat))))
        widths.append(2.0 * q_hat)
    return float(np.mean(coverages)), float(np.std(coverages)), float(np.mean(widths))


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    dev, dev_units = load_bgs(DEV_CSV)
    ext_all, ext_units = load_bgs(EXT_CSV)

    print("=" * 76)
    print("  STAGE 3.4 — EXTERNAL VALIDATION")
    print("=" * 76)

    # ── Unit check on every shared column actually used ──────────────────────
    shared = sorted({c for feats in TIERS.values() for c in feats} | set(TARGETS.values()))
    mismatches = []
    for col in shared:
        d_col = "AsTot" if col == "As" else col
        ud = str(dev_units.get(d_col, "")).strip().lower()
        ue = str(ext_units.get(col, "")).strip().lower()
        if ud and ue and ud != ue:
            mismatches.append((d_col, ud, col, ue))
    if mismatches:
        print("  UNIT MISMATCH — refusing to continue:")
        for a, ua, b, ub in mismatches:
            print(f"    {a} [{ua}]  vs  {b} [{ub}]")
        raise SystemExit(1)
    print(f"  Units checked on {len(shared)} shared columns: all consistent")
    print("  Al excluded by design (ug/L in development, mg/L in external)")

    # ── External set: North Bengal minus the shared district ─────────────────
    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != EXCLUDE_DISTRICT)].copy()

    for frame in (dev, ext):
        frame["lat"] = pd.to_numeric(frame["LAT_DEG"], errors="coerce")
        frame["lon"] = pd.to_numeric(frame["LONG_DEG"], errors="coerce")
    dev = dev.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    ext = ext.dropna(subset=["lat", "lon"]).reset_index(drop=True)

    nearest = haversine_min_km(dev["lat"].values, dev["lon"].values,
                               ext["lat"].values, ext["lon"].values)
    print(f"\n  Development wells : {len(dev)}  (4 districts)")
    print(f"  External wells    : {len(ext)}  "
          f"({ext['DISTRICT'].astype(str).str.strip().nunique()} districts, "
          f"{EXCLUDE_DISTRICT} removed)")
    print(f"  Nearest external well to any development well: {nearest.min():.2f} km")
    if nearest.min() < MIN_SEPARATION_KM:
        print(f"  Separation below {MIN_SEPARATION_KM} km — not independent.")
        raise SystemExit(1)
    print(f"  Separation >= {MIN_SEPARATION_KM} km confirmed")

    for c in ["WELL_DEPTH", "Fe", "Mn", "Ca", "Mg", "Na", "SO4", "Si", "Sr", "Ba"]:
        if c in dev.columns:
            dev[c] = numeric(dev[c])
        if c in ext.columns:
            ext[c] = numeric(ext[c])
    dev["AsTot"] = numeric(dev["AsTot"])
    ext["As"] = numeric(ext["As"])

    rows, detail = [], {}
    for dev_target, ext_target in TARGETS.items():
        detail[dev_target] = {}
        print(f"\n  {dev_target}")
        for tier_name, feats in TIERS.items():
            d = dev[feats + [dev_target]].dropna(subset=[dev_target])
            e = ext[feats + [ext_target]].dropna(subset=[ext_target])
            X_dev = d[feats].to_numpy(float)
            y_dev = d[dev_target].to_numpy(float)
            X_ext = e[feats].to_numpy(float)
            y_ext = e[ext_target].to_numpy(float)

            int_r2, int_sd, int_r2_log = internal_cv(X_dev, y_dev)

            model = fit_searched(X_dev, np.log1p(y_dev))
            pred = np.maximum(np.expm1(model.predict(X_ext)), 0.0)
            ext_r2 = r2_score(y_ext, pred)
            # The original scale is dominated by a handful of very high wells,
            # and the model was fitted on the log scale, so both are reported.
            ext_r2_log = r2_score(np.log1p(y_ext), np.log1p(pred))
            ext_mae_log = float(np.mean(np.abs(np.log1p(y_ext) - np.log1p(pred))))
            ext_rho = float(spearmanr(y_ext, pred).statistic)

            limit = WHO_LIMIT[dev_target]
            labels = (y_ext > limit).astype(int)
            auc = (float(roc_auc_score(labels, pred))
                   if 0 < labels.sum() < len(labels) else None)

            cov, cov_sd, width = conformal_transfer(X_dev, y_dev, X_ext, y_ext, rng)

            rec = {
                "n_dev": int(len(y_dev)), "n_ext": int(len(y_ext)),
                "features": feats,
                "internal_cv_r2": round(int_r2, 4),
                "internal_cv_r2_sd": round(int_sd, 4),
                "internal_cv_r2_log": round(int_r2_log, 4),
                "external_r2": round(float(ext_r2), 4),
                "external_r2_log": round(float(ext_r2_log), 4),
                "external_mae_log": round(ext_mae_log, 4),
                "external_spearman": round(ext_rho, 4),
                "external_auc_who": None if auc is None else round(auc, 4),
                "n_exceeding_who_external": int(labels.sum()),
                "conformal_transfer_coverage": round(cov, 4),
                "conformal_transfer_coverage_sd": round(cov_sd, 4),
                "conformal_interval_width": round(width, 4),
                "nominal_coverage": 1 - ALPHA,
            }
            detail[dev_target][tier_name] = rec
            rows.append({"target": dev_target, "tier": tier_name, **{
                k: rec[k] for k in ("n_dev", "n_ext", "internal_cv_r2", "external_r2",
                                    "external_spearman", "external_auc_who",
                                    "conformal_transfer_coverage",
                                    "conformal_transfer_coverage_sd")}})

            auc_txt = "n/a" if auc is None else f"{auc:.3f}"
            print(f"    {tier_name:9s} internal R2={int_r2:+.3f} -> external R2={ext_r2:+.3f} | "
                  f"rho={ext_rho:+.3f} | AUC(WHO)={auc_txt} | "
                  f"conformal {cov*100:.1f}%+-{cov_sd*100:.1f}pp")

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "design": {
            "development": f"special study areas, n={len(dev)}, 4 districts",
            "external": (f"national survey North Bengal excluding {EXCLUDE_DISTRICT}, "
                         f"n={len(ext)}"),
            "min_separation_km": round(float(nearest.min()), 3),
            "excluded_predictor": "Al (ug/L vs mg/L between files)",
            "caveat": ("The external file has no pH, Eh, SEC, T, Cl, HCO3 or NO3-N, "
                       "so this validates a reduced model. internal_cv_r2 is the "
                       "same reduced predictor set scored in development, which "
                       "separates the cost of losing predictors from the cost of "
                       "transfer."),
            "conformal": ("q_hat calibrated on held-out development wells, coverage "
                          "measured on external wells; exchangeability does not hold "
                          "across the two sets, so this measures how far the "
                          "guarantee travels."),
        },
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.4 DONE\n")


if __name__ == "__main__":
    main()
