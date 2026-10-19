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

  dev-target sens 95 >= 95 % of contaminated wells caught *on the development
                     wells*, where the threshold is chosen. What the external
                     column then shows is what that frozen cut-off delivers
                     elsewhere, which is the honest question and need not be
                     95 % again.
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
from sklearn.model_selection import GridSearchCV, KFold
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


def oof_scores(X, y, grid, seed=SEED, n_splits=5):
    """
    Out-of-fold predictions on the development wells.

    Thresholds have to be chosen somewhere, and choosing them on the wells they
    are then scored against makes the reported sensitivity an in-sample number.
    These predictions give a held-out basis for that choice, after which the
    threshold is frozen and carried to the external set unchanged.
    """
    oof = np.zeros(len(y))
    for tr, te in KFold(n_splits=n_splits, shuffle=True, random_state=seed).split(X):
        pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                         ("scaler", StandardScaler()), ("model", Ridge())])
        search = GridSearchCV(pipe, grid, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        search.fit(X[tr], np.log1p(y[tr]))
        oof[te] = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)
    return oof


def bootstrap_ci(scores, labels, thr, n_boot=2000, seed=SEED):
    """Percentile intervals for sensitivity and AUC at a fixed threshold."""
    rng = np.random.default_rng(seed)
    n = len(labels)
    sens, aucs = [], []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        lb, sc = labels[idx], scores[idx]
        if lb.sum() == 0 or lb.sum() == len(lb):
            continue
        flag = sc >= thr
        tp = int((flag & (lb == 1)).sum())
        fn = int((~flag & (lb == 1)).sum())
        if tp + fn:
            sens.append(tp / (tp + fn))
        aucs.append(roc_auc_score(lb, sc))
    def ci(v):
        return [round(float(np.percentile(v, 2.5)), 4),
                round(float(np.percentile(v, 97.5)), 4)] if v else None
    return {"sensitivity_ci95": ci(sens), "auc_ci95": ci(aucs)}


def single_predictor_baselines(dev, ext, limit, label, detail):
    """
    What a tape measure or one colorimetric kit would achieve on its own.

    If well depth alone ranks the external wells nearly as well as the fitted
    model, the model is not what is doing the work, and that is worth knowing
    before any of it is recommended. Thresholds come from development out of
    fold predictions exactly as for the tiers.
    """
    out = {}
    for feat in ("WELL_DEPTH", "Fe", "Mn"):
        d = dev[[feat, "AsTot"]].dropna()
        e = ext[[feat, "As"]].dropna()
        if len(d) < 50 or len(e) < 50:
            continue
        y_ext = e["As"].to_numpy(float)
        labels = (y_ext > limit).astype(int)
        if labels.sum() in (0, len(labels)):
            continue

        # Depth runs the other way: shallow wells carry more arsenic.
        raw = e[feat].to_numpy(float)
        scores = -raw if feat == "WELL_DEPTH" else raw
        auc = float(roc_auc_score(labels, scores))

        dev_raw = d[feat].to_numpy(float)
        dev_scores = -dev_raw if feat == "WELL_DEPTH" else dev_raw
        dev_labels = (d["AsTot"].to_numpy(float) > limit).astype(int)
        thr = None
        if dev_labels.sum() not in (0, len(dev_labels)):
            sweep = [(t, confusion_at(dev_scores, dev_labels, t))
                     for t in np.quantile(dev_scores, np.linspace(0.02, 0.98, 49))]
            cands = [(t, c) for t, c in sweep if c["sensitivity"] >= 0.95]
            if cands:
                thr = sorted(cands, key=lambda tc: tc[1]["pct_referred_to_lab"])[0][0]

        rec = {"feature": feat, "n_external": int(len(y_ext)),
               "direction": "lower is worse" if feat == "WELL_DEPTH" else "higher is worse",
               "auc": round(auc, 4)}
        if thr is not None:
            rec["dev_target_sensitivity_95"] = confusion_at(scores, labels, float(thr))
        out[feat] = rec
        print(f"      baseline {feat:12s} AUC={auc:.3f}")
    detail.setdefault("single_predictor_baselines", {})[label] = out


# The terraces and the older units beneath them. Dihing and Dupi Tila are
# Pliocene to Plio-Pleistocene rather than Pleistocene proper, so the stratum
# is named for what its members share: everything older than the Holocene.
PRE_HOLOCENE = ("Barind Clay Residuum", "Madhupur Clay Residuum",
                "Old gravelly sand", "Dihing & Dupi Tila undivi")
MIN_POSITIVES_FOR_AUC = 10


def stratified_performance(scores, labels, geology, thr, detail, label, tier_name):
    """
    Performance within each geological setting.

    Pooling the pre-Holocene units with the Holocene aquifers supplies easy
    negatives and lifts the overall figure above what the decision actually
    faces. Those units also carry almost no exceedances, so ranking is close to
    undefined there and an area under the curve would be noise. What matters in
    that stratum is the opposite error: how many safe wells the rule sends to a
    laboratory for nothing. So ranking is reported where there are positives to
    rank, and false positive rate and referral where there are not.
    """
    if geology is None:
        return
    setting = np.where(np.isin(geology, PRE_HOLOCENE),
                       "pre-Holocene", "Holocene alluvium")
    out = {}
    for name in ("Holocene alluvium", "pre-Holocene"):
        sel = setting == name
        n, pos = int(sel.sum()), int(labels[sel].sum())
        rec = {"n": n, "n_contaminated": pos}
        if n < 30:
            rec["auc"] = "n.d."
            rec["note"] = "fewer than 30 wells"
        elif pos < MIN_POSITIVES_FOR_AUC:
            rec["auc"] = "n.d."
            rec["note"] = (f"only {pos} exceedances; ranking is not "
                           f"meaningful, so the cost of false referral is "
                           f"reported instead")
        else:
            rec["auc"] = round(float(roc_auc_score(labels[sel], scores[sel])), 4)

        if thr is not None:
            flag = scores[sel] >= thr
            neg = ~labels[sel].astype(bool)
            rec["threshold_ugL"] = round(float(thr), 3)
            rec["pct_referred_to_lab"] = round(100.0 * float(flag.mean()), 1)
            rec["false_positive_rate"] = (
                round(float((flag & neg).sum()) / int(neg.sum()), 4)
                if neg.sum() else None)
            rec["n_false_referrals"] = int((flag & neg).sum())
        out[name] = rec
        print(f"      {name:20s} n={n:4d}  exceed={pos:3d}  "
              f"AUC={rec['auc']}  referred="
              f"{rec.get('pct_referred_to_lab', '-')}%  "
              f"FPR={rec.get('false_positive_rate', '-')}")
    detail.setdefault("performance_by_geology", {}).setdefault(
        label, {})[tier_name] = out


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    dev, ext_all = load(DEV_CSV), load(EXT_CSV)

    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != EXCLUDE_DISTRICT)].copy()

    # surface geology, for the stratified area under the curve
    try:
        geo = pd.read_csv(ROOT / "00_data" / "raw" / "bangladesh_surface_geology.csv")
        ext = ext.merge(geo[["SAMPLE_ID", "GEOL_UNIT"]], on="SAMPLE_ID", how="left")
    except Exception as exc:
        print(f"  surface geology not joined: {exc}")
        ext["GEOL_UNIT"] = np.nan

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
        print(f"\n  [{label}] single-predictor baselines")
        single_predictor_baselines(dev, ext, limit, label, detail)
        for tier_name, feats in TIERS.items():
            d = dev[feats + ["AsTot"]].dropna(subset=["AsTot"])
            keep = feats + ["As"] + (["GEOL_UNIT"] if "GEOL_UNIT" in ext else [])
            e = ext[keep].dropna(subset=["As"])
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

            # Thresholds are chosen on held-out development predictions and
            # frozen; the external wells only ever see a fixed number.
            dev_scores = oof_scores(X_dev, y_dev, PARAM_GRID)
            dev_labels = (y_dev > limit).astype(int)
            if dev_labels.sum() == 0 or dev_labels.sum() == len(dev_labels):
                continue

            dev_sweep = [(t, confusion_at(dev_scores, dev_labels, t))
                         for t in np.quantile(dev_scores, np.linspace(0.02, 0.98, 49))]
            d_fpr, d_tpr, d_thr = roc_curve(dev_labels, dev_scores)
            finite = np.isfinite(d_thr)
            youden = (float(d_thr[finite][np.argmax(d_tpr[finite] - d_fpr[finite])])
                      if finite.any() else float(limit))

            def choose(predicate, key, reverse=False):
                cands = [(t, c) for t, c in dev_sweep if predicate(c)]
                if not cands:
                    return None
                return sorted(cands, key=lambda tc: tc[1][key], reverse=reverse)[0][0]

            chosen = {
                "dev_target_sensitivity_95": choose(lambda c: c["sensitivity"] >= 0.95,
                                              "pct_referred_to_lab"),
                "balanced_youden": youden,
                "dev_target_specificity_90": choose(lambda c: c["specificity"] >= 0.90,
                                              "sensitivity", reverse=True),
            }

            named = {}
            for name, t in chosen.items():
                if t is None:
                    named[name] = None
                    continue
                op = confusion_at(scores, labels, float(t))
                op["threshold_chosen_on"] = "development out-of-fold"
                op["dev_sensitivity"] = confusion_at(dev_scores, dev_labels,
                                                     float(t))["sensitivity"]
                op.update(bootstrap_ci(scores, labels, float(t)))
                named[name] = op

            hs = named.get("dev_target_sensitivity_95")
            stratified_performance(
                scores, labels,
                e["GEOL_UNIT"].to_numpy() if "GEOL_UNIT" in e else None,
                hs["threshold_ugL"] if hs else None,
                detail, label, tier_name)

            sweep = [confusion_at(scores, labels, t)
                     for t in np.quantile(scores, np.linspace(0.05, 0.95, 19))]

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
        "threshold_protocol": ("Thresholds are selected on out-of-fold "
                               "predictions over the development wells and then "
                               "frozen. The external wells are used only to "
                               "score them, so sensitivity and referral rate are "
                               "out-of-sample in both the model and the cut-off. "
                               "Bootstrap 95% intervals accompany each point."),
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
