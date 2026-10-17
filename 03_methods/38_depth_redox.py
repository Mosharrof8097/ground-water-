"""
STAGE 3.8 — DEPTH, REDOX AND ARSENIC
====================================
Tests the belief that drilling deeper gives safer water.

Input  : 00_data/interim/01_clean.csv, 35_geochem.csv
Output : 04_results/metrics/38_depth_redox.json
         04_results/tables/T11_depth_strata.csv

Deepening tubewells is the standard mitigation advice in the Bengal Basin, and
a reviewer will expect the depth relationship to be addressed explicitly. It is
tested here three ways rather than asserted:

  1. correlation of each metal with depth, Spearman, with BH-FDR across metals
  2. concentrations by depth stratum, with a Kruskal-Wallis test
  3. whether depth predicts redox zone, which is the mechanism the advice
     implicitly relies on

The outcome is reported whichever way it falls. An earlier project in this
repository claimed shallow wells were more contaminated when its own data said
the opposite, so the comparison is made in the open.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kruskal, mannwhitneyu, chi2_contingency

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CLEAN = ROOT / "00_data" / "interim" / "01_clean.csv"
IN_GEO = ROOT / "00_data" / "interim" / "35_geochem.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "38_depth_redox.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T11_depth_strata.csv"

WHO = {"AsTot": 10.0, "Ni": 20.0, "Pb": 10.0, "Zn": 3000.0,
       "U": 30.0, "Mo": 70.0, "Ba": 1300.0}
STRATA = [(0, 20, "shallow <20 m"), (20, 30, "intermediate 20-30 m"),
          (30, 50, "deep 30-50 m"), (50, 1e9, "very deep >=50 m")]


def bh(pvals, alpha=0.05):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    thresh = alpha * (np.arange(1, len(p) + 1) / len(p))
    ok = p[order] <= thresh
    keep = np.zeros(len(p), bool)
    if ok.any():
        keep[order[: np.max(np.where(ok)[0]) + 1]] = True
    return keep


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(IN_CLEAN)
    g = pd.read_csv(IN_GEO)
    targets = json.loads(IN_DESIGN.read_text())["targets_modellable"]
    d["redox_zone"] = g["redox_zone"]

    print("=" * 76)
    print("  STAGE 3.8 — DEPTH, REDOX AND ARSENIC")
    print("=" * 76)
    depth = d["WELL_DEPTH"]
    print(f"  Depth: n={depth.notna().sum()}, median {depth.median():.1f} m, "
          f"range {depth.min():.1f}-{depth.max():.1f} m\n")

    # ── 1. Correlation with depth ────────────────────────────────────────────
    print("  [1] METAL vs DEPTH  (Spearman, BH-FDR across metals)")
    rows, pvals = [], []
    for t in targets:
        sub = d[["WELL_DEPTH", t]].dropna()
        r = spearmanr(sub["WELL_DEPTH"], sub[t])
        rows.append({"metal": t, "n": len(sub), "spearman_rho": round(float(r.statistic), 4),
                     "p_raw": float(r.pvalue)})
        pvals.append(r.pvalue)
    keep = bh(pvals)
    for row, k in zip(rows, keep):
        row["fdr_significant"] = bool(k)
        print(f"      {row['metal']:8s} rho={row['spearman_rho']:+.3f}  "
              f"p={row['p_raw']:.3f}  {'FDR-significant' if k else 'not significant'}")

    # ── 2. Depth strata ──────────────────────────────────────────────────────
    print("\n  [2] ARSENIC BY DEPTH STRATUM")
    strata_rows, groups = [], []
    for lo, hi, label in STRATA:
        m = (d["WELL_DEPTH"] >= lo) & (d["WELL_DEPTH"] < hi)
        if m.sum() == 0:
            continue
        sub = d.loc[m, "AsTot"].dropna()
        groups.append(sub.values)
        exceed = int((sub > WHO["AsTot"]).sum())
        strata_rows.append({
            "stratum": label, "n_wells": int(m.sum()),
            "median_As_ugL": round(float(sub.median()), 2),
            "mean_As_ugL": round(float(sub.mean()), 2),
            "n_above_WHO": exceed,
            "pct_above_WHO": round(100.0 * exceed / len(sub), 1),
            "median_Fe_mgL": round(float(d.loc[m, "Fe"].median()), 3),
        })
        print(f"      {label:22s} n={int(m.sum()):3d}  As median={sub.median():7.2f}  "
              f">WHO {exceed:3d} ({100*exceed/len(sub):4.1f}%)  "
              f"Fe={d.loc[m,'Fe'].median():6.3f}")
    kw_p = float(kruskal(*groups).pvalue) if len(groups) > 1 else np.nan
    print(f"      Kruskal-Wallis across strata: p={kw_p:.4f}")

    shallow = d.loc[d["WELL_DEPTH"] < 30, "AsTot"].dropna()
    deep = d.loc[d["WELL_DEPTH"] >= 30, "AsTot"].dropna()
    mw_p = float(mannwhitneyu(shallow, deep, alternative="greater").pvalue)
    print(f"      shallow (<30 m) n={len(shallow)} median={shallow.median():.2f}  |  "
          f"deep (>=30 m) n={len(deep)} median={deep.median():.2f}")
    print(f"      Mann-Whitney (shallow > deep): p={mw_p:.4f}")

    # ── 3. Does depth determine redox zone? ──────────────────────────────────
    print("\n  [3] DEPTH vs REDOX ZONE")
    valid = d["redox_zone"].notna() & d["WELL_DEPTH"].notna()
    zone_rows = []
    for zone in d.loc[valid, "redox_zone"].value_counts().index:
        sel = valid & (d["redox_zone"] == zone)
        zone_rows.append({"redox_zone": zone, "n": int(sel.sum()),
                          "median_depth_m": round(float(d.loc[sel, "WELL_DEPTH"].median()), 1)})
        print(f"      {zone:34s} n={int(sel.sum()):3d}  "
              f"median depth={d.loc[sel,'WELL_DEPTH'].median():6.1f} m")
    strata_lbl = pd.cut(d.loc[valid, "WELL_DEPTH"],
                        bins=[0, 20, 30, 50, 1e9],
                        labels=[s[2] for s in STRATA])
    ct = pd.crosstab(strata_lbl, d.loc[valid, "redox_zone"])
    chi_p = float(chi2_contingency(ct)[1]) if ct.shape[0] > 1 and ct.shape[1] > 1 else np.nan
    print(f"      chi-square, depth stratum vs redox zone: p={chi_p:.4f}")

    pd.DataFrame(strata_rows).to_csv(OUT_TABLE, index=False)

    depth_protects = (mw_p < 0.05) and (shallow.median() > deep.median())
    verdict = ("deeper wells are significantly cleaner in this dataset"
               if depth_protects else
               "depth does not predict arsenic in this dataset")
    print(f"\n  VERDICT: {verdict}")
    if not depth_protects:
        print("      The common 'drill deeper' advice is not supported here. Redox")
        print("      condition, not depth, separates contaminated from clean wells")
        print("      (see stage 3.5: reducing zones carry the arsenic).")

    json.dump({
        "depth_summary": {"n": int(depth.notna().sum()),
                          "median_m": float(depth.median()),
                          "min_m": float(depth.min()), "max_m": float(depth.max())},
        "metal_vs_depth": rows,
        "arsenic_by_stratum": strata_rows,
        "kruskal_p_across_strata": kw_p,
        "shallow_vs_deep": {
            "cut_m": 30,
            "n_shallow": int(len(shallow)), "median_shallow": float(shallow.median()),
            "n_deep": int(len(deep)), "median_deep": float(deep.median()),
            "mannwhitney_p_shallow_greater": mw_p,
        },
        "depth_vs_redox": {"by_zone": zone_rows, "chi2_p": chi_p},
        "verdict": verdict,
        "note": ("Reported in both directions. Mitigation advice to deepen wells "
                 "rests on depth predicting redox condition; where it does not, "
                 "the advice does not follow from these data."),
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.8 DONE\n")


if __name__ == "__main__":
    main()
