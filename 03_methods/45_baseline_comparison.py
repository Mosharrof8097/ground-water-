"""
STAGE 3.15 — IS THE FITTED MODEL WORTH ANYTHING OVER RAW IRON?
==============================================================
Stage 3.7 found that iron on its own ranks the external wells better than any
fitted model. Before that can be said in print it has to survive four
questions, and this stage answers them.

  1. Is the iron threshold chosen on the development wells and frozen, so the
     external numbers are out of sample in the cut-off as well as the model?
  2. Does iron keep its advantage inside the Holocene aquifers, where the
     decision actually falls? The pre-Holocene units are oxidising, so their
     low iron and low arsenic are easy negatives that flatter iron most.
  3. Is the gap statistically real? Paired DeLong on the same wells, plus a
     bootstrap interval for the difference.
  4. Does the model beat iron on the development wells while losing on
     transfer? That is the proposed explanation and it has to be shown, not
     assumed.

A fifth question is practical. The iron here is an ICP determination, while a
field team would read a colorimetric kit. The rule is therefore re-scored
under kit-like precision and under a typical strip ladder.

Input  : 00_data/raw/special_study_areas_271_boreholes.csv
         00_data/raw/NHS_national_survey_3534_boreholes.csv
         00_data/raw/bangladesh_surface_geology.csv
Output : 04_results/metrics/45_baseline_comparison.json
         04_results/tables/T19_baseline_comparison.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "00_data" / "raw"
OUT_METRICS = ROOT / "04_results" / "metrics" / "45_baseline_comparison.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T19_baseline_comparison.csv"

SEED, N_JOBS, N_BOOT = 42, 4, 2000
WHO_AS, BANGLADESH_AS = 10.0, 50.0
TIER_CHEAP = ["Fe", "Mn", "WELL_DEPTH"]

NORTH_BENGAL = [
    "Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram", "Lalmonirhat",
    "Naogaon", "Natore", "Nawabganj", "Nilphamari", "Pabna", "Panchagarh",
    "Rajshahi", "Rangpur", "Sirajganj", "Thakurgaon",
]
EXCLUDE_DISTRICT = "Nawabganj"

PRE_HOLOCENE = ("Barind Clay Residuum", "Madhupur Clay Residuum",
                "Old gravelly sand", "Dihing & Dupi Tila undivi")
MIN_POSITIVES_FOR_AUC = 10

PARAM_GRID = [
    {"model": [Ridge()], "model__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
    {"model": [ElasticNet(max_iter=5000)], "model__alpha": [0.01, 0.1, 1.0],
     "model__l1_ratio": [0.2, 0.5, 0.8]},
    {"model": [HuberRegressor(max_iter=500)], "model__alpha": [1e-4, 1e-2],
     "model__epsilon": [1.35, 1.75]},
    {"model": [SVR(kernel="rbf")], "model__C": [1.0, 10.0],
     "model__gamma": ["scale"]},
    {"model": [RandomForestRegressor(n_estimators=150, random_state=SEED,
                                     n_jobs=1)],
     "model__max_depth": [None, 8], "model__min_samples_leaf": [1, 3]},
]


# ── data ────────────────────────────────────────────────────────────────────
def load(path):
    raw = pd.read_csv(path, skiprows=4, low_memory=False)
    df = raw.iloc[1:].reset_index(drop=True)
    return df[df["SAMPLE_ID"].notna()].reset_index(drop=True)


def numeric(s):
    return pd.to_numeric(s.astype(str).str.replace("<", "", regex=False).str.strip(),
                         errors="coerce")


def pipeline():
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()), ("model", Ridge())])


# ── DeLong ──────────────────────────────────────────────────────────────────
def _midrank(x):
    order = np.argsort(x)
    z = x[order]
    n = len(x)
    t = np.zeros(n)
    i = 0
    while i < n:
        j = i
        while j < n - 1 and z[j + 1] == z[i]:
            j += 1
        t[i:j + 1] = 0.5 * (i + j) + 1
        i = j + 1
    out = np.empty(n)
    out[order] = t
    return out


def delong(labels, score_a, score_b):
    """
    Paired comparison of two AUCs on the same cases (DeLong et al. 1988),
    following the fast algorithm of Sun and Xu (2014).

    Returns (auc_a, auc_b, difference, standard error, two-sided p).
    """
    pos = labels == 1
    m, n = int(pos.sum()), int((~pos).sum())
    # The algorithm indexes the pooled midranks as [positives, negatives], so
    # the rows have to be built in that order rather than left as they came.
    scores = np.vstack([np.hstack([score_a[pos], score_a[~pos]]),
                        np.hstack([score_b[pos], score_b[~pos]])])
    k = scores.shape[0]

    tx = np.empty((k, m))
    ty = np.empty((k, n))
    tz = np.empty((k, m + n))
    for r in range(k):
        tx[r] = _midrank(scores[r][:m])
        ty[r] = _midrank(scores[r][m:])
        tz[r] = _midrank(scores[r])

    aucs = tz[:, :m].sum(axis=1) / (m * n) - (m + 1.0) / (2.0 * n)
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m
    s01 = np.cov(v01)
    s10 = np.cov(v10)
    s = s01 / m + s10 / n
    s = np.atleast_2d(s)

    diff = float(aucs[0] - aucs[1])
    var = float(s[0, 0] + s[1, 1] - 2 * s[0, 1])
    se = float(np.sqrt(max(var, 0.0)))
    p = float(2 * stats.norm.sf(abs(diff) / se)) if se > 0 else float("nan")
    return float(aucs[0]), float(aucs[1]), diff, se, p


def bootstrap_auc_diff(labels, score_a, score_b, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(labels)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        lb = labels[idx]
        if lb.sum() == 0 or lb.sum() == len(lb):
            continue
        diffs.append(roc_auc_score(lb, score_a[idx])
                     - roc_auc_score(lb, score_b[idx]))
    if not diffs:
        return None
    return [round(float(np.percentile(diffs, 2.5)), 4),
            round(float(np.percentile(diffs, 97.5)), 4)]


# ── operating points ────────────────────────────────────────────────────────
def confusion(scores, labels, thr):
    flag = scores >= thr
    tp = int((flag & (labels == 1)).sum())
    fp = int((flag & (labels == 0)).sum())
    fn = int((~flag & (labels == 1)).sum())
    tn = int((~flag & (labels == 0)).sum())
    return {
        "threshold": round(float(thr), 4),
        "sensitivity": round(tp / (tp + fn), 4) if tp + fn else None,
        "specificity": round(tn / (tn + fp), 4) if tn + fp else None,
        "pct_referred_to_lab": round(100.0 * float(flag.mean()), 1),
        "contaminated_missed": fn,
        "n_contaminated": tp + fn,
    }


def freeze_threshold(dev_scores, dev_labels, min_sens=0.95):
    """Lowest laboratory burden on the development wells at the target sensitivity."""
    if dev_labels.sum() in (0, len(dev_labels)):
        return None
    cands = []
    for t in np.quantile(dev_scores, np.linspace(0.02, 0.98, 97)):
        c = confusion(dev_scores, dev_labels, t)
        if c["sensitivity"] is not None and c["sensitivity"] >= min_sens:
            cands.append((t, c["pct_referred_to_lab"]))
    if not cands:
        return None
    return float(sorted(cands, key=lambda tc: tc[1])[0][0])


def stratified(scores, labels, setting, thr):
    out = {}
    for name in ("Holocene alluvium", "pre-Holocene"):
        sel = setting == name
        n, pos = int(sel.sum()), int(labels[sel].sum())
        rec = {"n": n, "n_contaminated": pos}
        if n < 30 or pos < MIN_POSITIVES_FOR_AUC:
            rec["auc"] = "n.d."
            rec["note"] = f"only {pos} exceedances; ranking not meaningful"
        else:
            rec["auc"] = round(float(roc_auc_score(labels[sel], scores[sel])), 4)
        if thr is not None and n:
            flag = scores[sel] >= thr
            neg = ~labels[sel].astype(bool)
            rec["pct_referred_to_lab"] = round(100.0 * float(flag.mean()), 1)
            rec["n_false_referrals"] = int((flag & neg).sum())
            rec["false_positive_rate"] = (round(float((flag & neg).sum()) / int(neg.sum()), 4)
                                          if neg.sum() else None)
        out[name] = rec
    return out


# ── kit realism ─────────────────────────────────────────────────────────────
# A colorimetric iron kit does not return an ICP number. Two degradations are
# applied: multiplicative imprecision, and reading onto a typical strip ladder.
KIT_CV = 0.25
STRIP_LADDER = np.array([0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0])


def kit_noise(values, cv=KIT_CV, seed=SEED):
    rng = np.random.default_rng(seed)
    sigma = np.sqrt(np.log(1.0 + cv ** 2))
    return values * rng.lognormal(mean=-0.5 * sigma ** 2, sigma=sigma,
                                  size=len(values))


def to_strip(values):
    idx = np.abs(values[:, None] - STRIP_LADDER[None, :]).argmin(axis=1)
    return STRIP_LADDER[idx]


# ── main ────────────────────────────────────────────────────────────────────
def matched_referral(scores_a, scores_b, labels, referral_pcts):
    """
    Compare two rules at the same laboratory burden.

    Comparing each rule at its own frozen threshold answers two different
    questions at once. Holding the referral fraction equal asks the only
    question a programme can act on: for this many samples sent, how many
    contaminated wells does each rule miss?
    """
    out = []
    for pct in referral_pcts:
        q = 1.0 - pct / 100.0
        rec = {"pct_referred_to_lab": round(float(pct), 1)}
        for tag, sc in (("iron", scores_a), ("model", scores_b)):
            thr = float(np.quantile(sc, q))
            flag = sc >= thr
            tp = int((flag & (labels == 1)).sum())
            fn = int((~flag & (labels == 1)).sum())
            rec[tag] = {
                "threshold": round(thr, 4),
                "actual_pct_referred": round(100.0 * float(flag.mean()), 1),
                "sensitivity": round(tp / (tp + fn), 4) if tp + fn else None,
                "contaminated_missed": fn,
            }
        rec["missed_difference_iron_minus_model"] = (
            rec["iron"]["contaminated_missed"] - rec["model"]["contaminated_missed"])
        out.append(rec)
    return out


def by_district(frame, scores, labels, min_n=30, min_pos=10):
    """
    Iron's ranking performance district by district.

    A single pooled figure hides whether a rule is stable. It is not: the same
    iron rule scores differently in the development districts and in North
    Bengal, so the spread across districts is the quantity a programme in a
    new district actually faces.
    """
    out = {}
    districts = frame["DISTRICT"].astype(str).str.strip().to_numpy()
    for name in sorted(set(districts)):
        sel = districts == name
        n, pos = int(sel.sum()), int(labels[sel].sum())
        rec = {"n": n, "n_contaminated": pos}
        if n < min_n or pos < min_pos or pos == n:
            rec["auc"] = "n.d."
        else:
            rec["auc"] = round(float(roc_auc_score(labels[sel], scores[sel])), 4)
        out[name] = rec
    aucs = [v["auc"] for v in out.values() if isinstance(v["auc"], float)]
    summary = {"n_districts_scored": len(aucs)}
    if aucs:
        summary.update({"min": round(min(aucs), 4), "max": round(max(aucs), 4),
                        "median": round(float(np.median(aucs)), 4),
                        "range": round(max(aucs) - min(aucs), 4)})
    return {"per_district": out, "summary": summary}


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("  STAGE 3.15 — RAW IRON AGAINST THE FITTED MODEL")
    print("=" * 78)

    dev, ext_all = load(RAW / "special_study_areas_271_boreholes.csv"), \
        load(RAW / "NHS_national_survey_3534_boreholes.csv")
    for frame, cols in ((dev, TIER_CHEAP + ["AsTot"]),
                        (ext_all, TIER_CHEAP + ["As"])):
        for c in cols:
            if c in frame.columns:
                frame[c] = numeric(frame[c])

    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != EXCLUDE_DISTRICT)].copy()
    geo = pd.read_csv(RAW / "bangladesh_surface_geology.csv")
    ext = ext.merge(geo[["SAMPLE_ID", "GEOL_UNIT"]], on="SAMPLE_ID", how="left")

    results = {}
    rows = []

    for limit, label in ((WHO_AS, "WHO_10"), (BANGLADESH_AS, "Bangladesh_50")):
        print(f"\n  ── {label} " + "─" * 58)

        d = dev[TIER_CHEAP + ["AsTot"]].dropna(subset=["AsTot", "Fe"])
        e = ext[TIER_CHEAP + ["As", "GEOL_UNIT", "DISTRICT"]].dropna(
            subset=["As", "Fe"])
        X_dev = d[TIER_CHEAP].to_numpy(float)
        y_dev = d["AsTot"].to_numpy(float)
        X_ext = e[TIER_CHEAP].to_numpy(float)
        y_ext = e["As"].to_numpy(float)
        labels = (y_ext > limit).astype(int)
        dev_labels = (y_dev > limit).astype(int)
        setting = np.where(np.isin(e["GEOL_UNIT"].to_numpy(), PRE_HOLOCENE),
                           "pre-Holocene", "Holocene alluvium")

        # the fitted model, out of fold on development and fitted once for transfer
        oof = np.zeros(len(y_dev))
        for tr, te in KFold(5, shuffle=True, random_state=SEED).split(X_dev):
            gs = GridSearchCV(pipeline(), PARAM_GRID, cv=3,
                              scoring="neg_mean_squared_error", n_jobs=N_JOBS)
            gs.fit(X_dev[tr], np.log1p(y_dev[tr]))
            oof[te] = np.maximum(np.expm1(gs.best_estimator_.predict(X_dev[te])), 0.0)
        gs = GridSearchCV(pipeline(), PARAM_GRID, cv=3,
                          scoring="neg_mean_squared_error", n_jobs=N_JOBS)
        gs.fit(X_dev, np.log1p(y_dev))
        model_ext = np.maximum(np.expm1(gs.best_estimator_.predict(X_ext)), 0.0)

        fe_dev = d["Fe"].to_numpy(float)
        fe_ext = e["Fe"].to_numpy(float)

        # 4. does the model win where it was fitted, and lose on transfer?
        dev_auc_model = float(roc_auc_score(dev_labels, oof))
        dev_auc_fe = float(roc_auc_score(dev_labels, fe_dev))
        print(f"  development (out of fold)   model {dev_auc_model:.4f}   "
              f"iron {dev_auc_fe:.4f}   model advantage "
              f"{dev_auc_model - dev_auc_fe:+.4f}")

        # 3. is the external gap real?
        a_fe, a_mod, diff, se, p = delong(labels, fe_ext, model_ext)
        ci = bootstrap_auc_diff(labels, fe_ext, model_ext)
        print(f"  external                    model {a_mod:.4f}   "
              f"iron {a_fe:.4f}   iron advantage {diff:+.4f}")
        print(f"      DeLong paired: SE={se:.4f}  p={p:.2e}   bootstrap 95% CI {ci}")

        # 1. thresholds frozen on development
        thr_fe = freeze_threshold(fe_dev, dev_labels)
        thr_mod = freeze_threshold(oof, dev_labels)
        op_fe = confusion(fe_ext, labels, thr_fe) if thr_fe else None
        op_mod = confusion(model_ext, labels, thr_mod) if thr_mod else None
        if op_fe:
            print(f"      iron  rule Fe >= {thr_fe:.3f} mg/L (frozen on development): "
                  f"sens={op_fe['sensitivity']:.3f}  referred={op_fe['pct_referred_to_lab']}%  "
                  f"missed={op_fe['contaminated_missed']}/{op_fe['n_contaminated']}")
        if op_mod:
            print(f"      model rule: sens={op_mod['sensitivity']:.3f}  "
                  f"referred={op_mod['pct_referred_to_lab']}%  "
                  f"missed={op_mod['contaminated_missed']}/{op_mod['n_contaminated']}")

        # 2. the easy negatives
        strat_fe = stratified(fe_ext, labels, setting, thr_fe)
        strat_mod = stratified(model_ext, labels, setting, thr_mod)
        for name in ("Holocene alluvium", "pre-Holocene"):
            print(f"      {name:20s} iron AUC={strat_fe[name]['auc']}  "
                  f"referred={strat_fe[name].get('pct_referred_to_lab')}%   |   "
                  f"model AUC={strat_mod[name]['auc']}  "
                  f"referred={strat_mod[name].get('pct_referred_to_lab')}%")

        hol = setting == "Holocene alluvium"
        hol_delong = None
        if labels[hol].sum() >= MIN_POSITIVES_FOR_AUC:
            ha_fe, ha_mod, hdiff, hse, hp = delong(labels[hol], fe_ext[hol],
                                                   model_ext[hol])
            hol_delong = {"auc_iron": round(ha_fe, 4), "auc_model": round(ha_mod, 4),
                          "difference": round(hdiff, 4), "se": round(hse, 4),
                          "p_value": hp,
                          "bootstrap_ci95": bootstrap_auc_diff(
                              labels[hol], fe_ext[hol], model_ext[hol])}
            print(f"      Holocene only, DeLong: iron advantage {hdiff:+.4f}  "
                  f"p={hp:.2e}  CI {hol_delong['bootstrap_ci95']}")

        # 5. would a kit reproduce it?
        kit = {}
        for tag, series in (("kit_precision_cv25", kit_noise(fe_ext)),
                            ("strip_ladder", to_strip(fe_ext))):
            auc_k = float(roc_auc_score(labels, series))
            rec = {"auc": round(auc_k, 4)}
            if thr_fe:
                rec["operating_point"] = confusion(series, labels, thr_fe)
            kit[tag] = rec
            op = rec.get("operating_point")
            extra = (f"  at Fe>={thr_fe:.3f}: sens={op['sensitivity']:.3f}  "
                     f"missed={op['contaminated_missed']}/{op['n_contaminated']}  "
                     f"referred={op['pct_referred_to_lab']}%") if op else ""
            print(f"      iron as read by a {tag:20s} AUC={auc_k:.4f}{extra}")

        # like for like: what does each rule miss at the same burden?
        burdens = sorted({op_mod["pct_referred_to_lab"] if op_mod else 50.0,
                          op_fe["pct_referred_to_lab"] if op_fe else 60.0,
                          40.0, 50.0, 60.0})
        matched = matched_referral(fe_ext, model_ext, labels, burdens)
        print("      at equal laboratory burden:")
        for m in matched:
            print(f"        {m['pct_referred_to_lab']:5.1f}% referred -> "
                  f"iron misses {m['iron']['contaminated_missed']:3d}, "
                  f"model misses {m['model']['contaminated_missed']:3d}  "
                  f"(iron - model = {m['missed_difference_iron_minus_model']:+d})")

        districts = by_district(e, fe_ext, labels)
        ds = districts["summary"]
        if ds.get("n_districts_scored"):
            print(f"      iron AUC across {ds['n_districts_scored']} external "
                  f"districts: median {ds['median']}, range {ds['min']} to "
                  f"{ds['max']} (spread {ds['range']})")

        if hol_delong is not None:
            ci = hol_delong.get("bootstrap_ci95") or [None, None]
            touches_zero = ci[0] is not None and ci[0] <= 0 <= ci[1]
            hol_delong["verdict"] = ("borderline, inconclusive: the bootstrap "
                                     "interval includes zero"
                                     if touches_zero else
                                     "advantage holds within the Holocene")

        results[label] = {
            "n_external": int(len(y_ext)),
            "n_contaminated": int(labels.sum()),
            "development": {"auc_model_oof": round(dev_auc_model, 4),
                            "auc_iron": round(dev_auc_fe, 4),
                            "model_advantage": round(dev_auc_model - dev_auc_fe, 4)},
            "external": {"auc_model": round(a_mod, 4), "auc_iron": round(a_fe, 4),
                         "iron_advantage": round(diff, 4),
                         "delong_se": round(se, 4), "delong_p": p,
                         "bootstrap_ci95": ci},
            "external_holocene_only": hol_delong,
            "frozen_thresholds": {"iron_mgL": thr_fe, "model_ugL": thr_mod},
            "operating_points": {"iron": op_fe, "model": op_mod},
            "by_geology": {"iron": strat_fe, "model": strat_mod},
            "iron_as_a_field_kit": kit,
            "equal_burden_comparison": matched,
            "iron_auc_by_district": districts,
        }
        rows.append({
            "standard": label, "n_external": int(len(y_ext)),
            "n_contaminated": int(labels.sum()),
            "dev_auc_model_oof": round(dev_auc_model, 4),
            "dev_auc_iron": round(dev_auc_fe, 4),
            "ext_auc_model": round(a_mod, 4), "ext_auc_iron": round(a_fe, 4),
            "iron_advantage": round(diff, 4), "delong_p": p,
            "ext_auc_iron_holocene": (hol_delong or {}).get("auc_iron"),
            "ext_auc_model_holocene": (hol_delong or {}).get("auc_model"),
            "iron_auc_district_median": ds.get("median"),
            "iron_auc_district_range": ds.get("range"),
            "iron_auc_kit_cv25": kit["kit_precision_cv25"]["auc"],
            "iron_auc_strip": kit["strip_ladder"]["auc"],
        })

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "question": ("Whether a fitted model earns its place over the single "
                     "cheapest predictor it contains."),
        "protocol": ("Thresholds are chosen on the development wells and "
                     "frozen before the external wells are scored, for the "
                     "iron rule exactly as for the model. AUCs are compared "
                     "on identical wells with a paired DeLong test and a "
                     "bootstrap interval for the difference."),
        "kit_realism": (f"Iron here is an ICP determination. It is re-scored "
                        f"under multiplicative imprecision of CV={KIT_CV} and "
                        f"after reading onto the strip ladder "
                        f"{list(STRIP_LADDER)} mg/L."),
        "pre_holocene_units": list(PRE_HOLOCENE),
        "results": results,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.15 DONE")


if __name__ == "__main__":
    sys.exit(main())
