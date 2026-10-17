"""
STAGE 3.7 — SCREENING OPERATING POINTS
======================================
Turns the arsenic model into the thing a monitoring programme would actually
use: a decision rule, with its costs stated.

Input  : 00_data/interim/02_features.csv, 02_design.json
         00_data/raw/NHS_national_survey_3534_boreholes.csv
Output : 04_results/metrics/37_operating_points.json
         04_results/tables/T10_operating_points.csv

An AUC of 0.83 says the model ranks wells well. It does not say what a
programme should do. A field team needs a threshold, and with it the two
numbers that matter: how many contaminated wells are missed, and how many
samples must be sent to the laboratory.

So for a sweep of thresholds this reports sensitivity, specificity, PPV, NPV,
the share of wells referred for laboratory confirmation, and the number of
contaminated wells missed. Three operating points are then named:

  high-sensitivity   >= 95 % of contaminated wells caught
  balanced           Youden's J maximised
  high-specificity   >= 90 % specificity

Evaluated on the external wells, not the development set, so these are numbers
a programme could expect in a new district rather than in the one the model
was fitted to.

Missing a contaminated well and sending a clean one to the laboratory are not
equally bad, and the asymmetry is left explicit in the table rather than folded
into a single score.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DEV_CSV = ROOT / "00_data" / "raw" / "special_study_areas_271_boreholes.csv"
EXT_CSV = ROOT / "00_data" / "raw" / "NHS_national_survey_3534_boreholes.csv"
OUT_METRICS = ROOT / "04_results" / "metrics" / "37_operating_points.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T10_operating_points.csv"

SEED, N_JOBS = 42, 4
WHO_AS = 10.0
BANGLADESH_AS = 50.0          # national drinking-water standard
TIERS = {
    "T_cheap": ["Fe", "Mn", "WELL_DEPTH"],
    "T_full": ["Fe", "Mn", "WELL_DEPTH", "Ca", "Mg", "Na", "SO4", "Si", "Sr"],
}
NORTH_BENGAL = [
    "Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram", "Lalmonirhat",
    "Naogaon", "Natore", "Nawabganj", "Nilphamari", "Pabna", "Panchagarh",
    "Rajshahi", "Rangpur", "Sirajganj", "Thakurgaon",
]
EXCLUDE_DISTRICT = "Nawabganj"

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


def load(path):
    raw = pd.read_csv(path, skiprows=4, low_memory=False)
    df = raw.iloc[1:].reset_index(drop=True)
    return df[df["SAMPLE_ID"].notna()].reset_index(drop=True)


def numeric(s):
    return pd.to_numeric(s.astype(str).str.replace("<", "", regex=False).str.strip(),
                         errors="coerce")


def confusion_at(scores, labels, thr):
    flag = scores >= thr
    tp = int((flag & (labels == 1)).sum())
    fp = int((flag & (labels == 0)).sum())
    fn = int((~flag & (labels == 1)).sum())
    tn = int((~flag & (labels == 0)).sum())
    sens = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    ppv = tp / (tp + fp) if tp + fp else np.nan
    npv = tn / (tn + fn) if tn + fn else np.nan
    return {
        "threshold_ugL": round(float(thr), 3),
        "sensitivity": round(float(sens), 4),
        "specificity": round(float(spec), 4),
        "ppv": round(float(ppv), 4) if not np.isnan(ppv) else None,
        "npv": round(float(npv), 4) if not np.isnan(npv) else None,
        "pct_referred_to_lab": round(100.0 * flag.mean(), 1),
        "contaminated_missed": fn,
        "n_contaminated": tp + fn,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    dev, ext_all = load(DEV_CSV), load(EXT_CSV)

    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != EXCLUDE_DISTRICT)].copy()

    for frame, cols in ((dev, ["Fe", "Mn", "WELL_DEPTH", "Ca", "Mg", "Na", "SO4",
                               "Si", "Sr", "AsTot"]),
                        (ext, ["Fe", "Mn", "WELL_DEPTH", "Ca", "Mg", "Na", "SO4",
                               "Si", "Sr", "As"])):
        for c in cols:
            if c in frame.columns:
                frame[c] = numeric(frame[c])

    print("=" * 78)
    print("  STAGE 3.7 — SCREENING OPERATING POINTS (arsenic)")
    print("=" * 78)
    print(f"  Development {len(dev)} wells -> external {len(ext)} wells "
          f"({EXCLUDE_DISTRICT} excluded)\n")

    rows, detail = [], {}
    for limit, label in ((WHO_AS, "WHO_10"), (BANGLADESH_AS, "Bangladesh_50")):
        detail[label] = {}
        for tier_name, feats in TIERS.items():
            d = dev[feats + ["AsTot"]].dropna(subset=["AsTot"])
            e = ext[feats + ["As"]].dropna(subset=["As"])
            X_dev, y_dev = d[feats].to_numpy(float), d["AsTot"].to_numpy(float)
            X_ext, y_ext = e[feats].to_numpy(float), e["As"].to_numpy(float)

            pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                             ("scaler", StandardScaler()), ("model", Ridge())])
            search = GridSearchCV(pipe, PARAM_GRID, cv=3,
                                  scoring="neg_mean_squared_error", n_jobs=N_JOBS)
            search.fit(X_dev, np.log1p(y_dev))
            scores = np.maximum(np.expm1(search.best_estimator_.predict(X_ext)), 0.0)

            labels = (y_ext > limit).astype(int)
            if labels.sum() == 0 or labels.sum() == len(labels):
                continue
            auc = float(roc_auc_score(labels, scores))

            # Candidate thresholds from the ROC, plus the regulatory value itself
            fpr, tpr, thr = roc_curve(labels, scores)
            thr = thr[np.isfinite(thr)]
            youden = thr[np.argmax(tpr[np.isfinite(roc_curve(labels, scores)[2])]
                                   - fpr[np.isfinite(roc_curve(labels, scores)[2])])] \
                if len(thr) else limit

            sweep = [confusion_at(scores, labels, t)
                     for t in np.quantile(scores, np.linspace(0.05, 0.95, 19))]

            def pick(predicate, key, reverse=False):
                cands = [s for s in sweep if predicate(s)]
                if not cands:
                    return None
                return sorted(cands, key=lambda s: s[key], reverse=reverse)[0]

            named = {
                "high_sensitivity_95": pick(lambda s: s["sensitivity"] >= 0.95,
                                            "pct_referred_to_lab"),
                "balanced_youden": confusion_at(scores, labels, float(youden)),
                "high_specificity_90": pick(lambda s: s["specificity"] >= 0.90,
                                            "sensitivity", reverse=True),
            }

            detail[label][tier_name] = {
                "n_external": int(len(y_ext)),
                "n_contaminated": int(labels.sum()),
                "prevalence_pct": round(100.0 * labels.mean(), 1),
                "auc": round(auc, 4),
                "operating_points": named,
                "threshold_sweep": sweep,
            }

            print(f"  [{label}] {tier_name}   AUC={auc:.3f}   "
                  f"prevalence {100*labels.mean():.1f}% "
                  f"({int(labels.sum())}/{len(labels)})")
            for name, op in named.items():
                if op is None:
                    print(f"      {name:22s} not attainable")
                    continue
                print(f"      {name:22s} thr={op['threshold_ugL']:7.2f}  "
                      f"sens={op['sensitivity']*100:5.1f}%  "
                      f"spec={op['specificity']*100:5.1f}%  "
                      f"lab={op['pct_referred_to_lab']:5.1f}%  "
                      f"missed={op['contaminated_missed']:3d}/{op['n_contaminated']}")
                rows.append({"standard": label, "tier": tier_name,
                             "operating_point": name, "auc": round(auc, 4), **op})
            print()

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "note": ("Operating points are evaluated on external wells, so they "
                 "describe what a programme could expect in a district the model "
                 "was not fitted to. 'pct_referred_to_lab' is the laboratory "
                 "burden the rule creates; 'contaminated_missed' is its cost in "
                 "missed exposure. The two are reported side by side rather than "
                 "combined, since their relative weight is a policy choice."),
        "standards_ugL": {"WHO": WHO_AS, "Bangladesh": BANGLADESH_AS},
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.7 DONE\n")


if __name__ == "__main__":
    main()
