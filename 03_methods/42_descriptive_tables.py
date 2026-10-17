"""
STAGE 3.12 — DESCRIPTIVE AND EXCEEDANCE TABLES
==============================================
The two tables a water chemistry reviewer looks for first.

Input  : 00_data/interim/01_clean.csv, 02_design.json, 35_geochem.csv
Output : 04_results/tables/T0_descriptive_statistics.csv
         04_results/tables/T0b_exceedance_summary.csv
         04_results/metrics/42_descriptive.json

T0 reports, for every predictor and every candidate target, the number of valid
observations, the censoring rate, the detection limits in force, and the
distribution. Censored observations are summarised at their detection limit,
which is stated, rather than at a substituted value.

T0b reports how many wells exceed the relevant drinking water standard. This is
the contamination picture the modelling rests on, and it is what decides
whether a metal matters: a model for a metal that never approaches its limit
answers a question nobody asked.

Percentiles are computed on the values as recorded. Where a column is heavily
censored the lower percentiles sit at a detection limit, and the censoring
column states how far that reaches.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CLEAN = ROOT / "00_data" / "interim" / "01_clean.csv"
IN_REPORT = ROOT / "00_data" / "interim" / "01_clean_report.json"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
IN_GEO = ROOT / "00_data" / "interim" / "35_geochem.csv"
OUT_T0 = ROOT / "04_results" / "tables" / "T0_descriptive_statistics.csv"
OUT_T0B = ROOT / "04_results" / "tables" / "T0b_exceedance_summary.csv"
OUT_METRICS = ROOT / "04_results" / "metrics" / "42_descriptive.json"

# Drinking water standards, ug/L unless noted. WHO guideline values; the
# Bangladesh national standard is given where it differs.
STANDARDS = {
    "AsTot": {"who": 10.0, "bd": 50.0, "unit": "ug/L"},
    "AsIII": {"who": None, "bd": None, "unit": "ug/L"},
    "Cd": {"who": 3.0, "bd": 5.0, "unit": "ug/L"},
    "Cr": {"who": 50.0, "bd": 50.0, "unit": "ug/L"},
    "Cu": {"who": 2000.0, "bd": 1000.0, "unit": "ug/L"},
    "Ni": {"who": 70.0, "bd": 100.0, "unit": "ug/L"},
    "Pb": {"who": 10.0, "bd": 50.0, "unit": "ug/L"},
    "Zn": {"who": 3000.0, "bd": 5000.0, "unit": "ug/L"},
    "U": {"who": 30.0, "bd": None, "unit": "ug/L"},
    "Mo": {"who": 70.0, "bd": None, "unit": "ug/L"},
    "Sb": {"who": 20.0, "bd": None, "unit": "ug/L"},
    "Se": {"who": 40.0, "bd": 10.0, "unit": "ug/L"},
    "Ba": {"who": 1300.0, "bd": None, "unit": "ug/L"},
}

ROLE_ORDER = {"predictor": 0, "target": 1, "geochemistry": 2}


def describe(series, censored, unit, role, dls):
    v = series.dropna()
    n = len(v)
    if n == 0:
        return None
    return {
        "role": role,
        "unit": unit,
        "n_valid": int(n),
        "n_censored": int(censored.sum()),
        "pct_censored": round(100.0 * censored.sum() / len(series), 1),
        "detection_limits": "; ".join(f"{d:g}" for d in dls) if dls else "",
        "min": round(float(v.min()), 4),
        "p25": round(float(v.quantile(0.25)), 4),
        "median": round(float(v.median()), 4),
        "p75": round(float(v.quantile(0.75)), 4),
        "max": round(float(v.max()), 4),
        "mean": round(float(v.mean()), 4),
        "sd": round(float(v.std()), 4),
    }


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(IN_CLEAN)
    report = json.loads(IN_REPORT.read_text())
    design = json.loads(IN_DESIGN.read_text())
    dl_map = {k: v["limits"] for k, v in report.get("detection_limits", {}).items()}

    print("=" * 74)
    print("  STAGE 3.12 — DESCRIPTIVE AND EXCEEDANCE TABLES")
    print("=" * 74)
    print(f"  wells: {len(d)}\n")

    # ── T0 descriptive statistics ───────────────────────────────────────────
    rows = []
    for col, meta in report["columns"].items():
        if col not in d.columns:
            continue
        cens = d.get(f"{col}_censored", pd.Series(False, index=d.index)).fillna(False)
        rec = describe(d[col], cens, meta.get("unit", ""), meta["role"],
                       dl_map.get(col, {}).get("limits") if isinstance(
                           dl_map.get(col), dict) else dl_map.get(col))
        if rec:
            rows.append({"variable": col, **rec})

    # well depth belongs in the table although it is an identifier column
    if "WELL_DEPTH" in d.columns:
        rows.append({"variable": "WELL_DEPTH",
                     **describe(d["WELL_DEPTH"],
                                pd.Series(False, index=d.index), "m",
                                "predictor", None)})

    t0 = pd.DataFrame(rows)
    t0["_order"] = t0["role"].map(ROLE_ORDER).fillna(3)
    t0 = t0.sort_values(["_order", "pct_censored", "variable"]).drop(columns="_order")
    t0.to_csv(OUT_T0, index=False)

    print("  [T0] DESCRIPTIVE STATISTICS")
    print(f"  {'variable':12s} {'role':11s} {'n':>4s} {'cens%':>6s} "
          f"{'median':>10s} {'max':>11s}")
    for _, r in t0.iterrows():
        print(f"  {r['variable']:12s} {r['role']:11s} {r['n_valid']:4d} "
              f"{r['pct_censored']:5.0f}% {r['median']:10.3f} {r['max']:11.2f}")

    # ── T0b exceedance ──────────────────────────────────────────────────────
    # Standards are quoted in ug/L. Barium is reported by the survey in mg/L,
    # so each guideline is converted into the unit of the column it is compared
    # against rather than the values being rescaled, which keeps the table in
    # the units the laboratory reported.
    exc_rows = []
    for metal, std in STANDARDS.items():
        if metal not in d.columns:
            continue
        v = d[metal].dropna()
        if len(v) == 0:
            continue
        col_unit = report["columns"].get(metal, {}).get("unit", "ug/L")
        factor = 0.001 if col_unit.lower() == "mg/l" else 1.0
        who = std["who"] * factor if std["who"] else None
        bd = std["bd"] * factor if std["bd"] else None
        rec = {
            "metal": metal,
            "unit": col_unit,
            "n_valid": int(len(v)),
            "pct_censored": round(100.0 * d[f"{metal}_censored"].sum() / len(d), 1),
            "median": round(float(v.median()), 4),
            "max": round(float(v.max()), 4),
            "who_guideline": who,
            "n_above_who": int((v > who).sum()) if who else None,
            "pct_above_who": round(100.0 * (v > who).mean(), 1) if who else None,
            "bangladesh_standard": bd,
            "n_above_bd": int((v > bd).sum()) if bd else None,
            "max_as_pct_of_who": round(100.0 * float(v.max()) / who, 1) if who else None,
            "modelled": metal in design["targets_modellable"],
        }
        exc_rows.append(rec)

    t0b = pd.DataFrame(exc_rows).sort_values(
        "n_above_who", ascending=False, na_position="last")
    t0b.to_csv(OUT_T0B, index=False)

    print("\n  [T0b] EXCEEDANCE OF DRINKING WATER STANDARDS")
    print(f"  {'metal':7s} {'unit':>5s} {'WHO':>8s} {'median':>9s} {'max':>10s} "
          f"{'>WHO':>9s} {'max/WHO':>8s}  modelled")
    for _, r in t0b.iterrows():
        who = f"{r['who_guideline']:g}" if pd.notna(r["who_guideline"]) else "-"
        nab = f"{int(r['n_above_who'])}/{r['n_valid']}" if pd.notna(r["n_above_who"]) else "-"
        pct = f"{r['max_as_pct_of_who']:.0f}%" if pd.notna(r["max_as_pct_of_who"]) else "-"
        print(f"  {r['metal']:7s} {r['unit']:>5s} {who:>8s} {r['median']:9.3f} "
              f"{r['max']:10.2f} {nab:>9s} {pct:>8s}  "
              f"{'yes' if r['modelled'] else 'no'}")

    # ── Headline counts for the text ────────────────────────────────────────
    any_exc = [r["metal"] for r in exc_rows
               if r["n_above_who"] not in (None, 0)]
    none_exc = [r["metal"] for r in exc_rows if r["n_above_who"] == 0]

    print(f"\n  metals exceeding the WHO guideline in at least one well: "
          f"{', '.join(any_exc) if any_exc else 'none'}")
    print(f"  metals never exceeding it: {', '.join(none_exc)}")

    json.dump({
        "n_wells": int(len(d)),
        "standards_source": ("WHO Guidelines for Drinking-water Quality; "
                             "Bangladesh ECR 1997 Schedule 3 where it differs"),
        "n_variables_described": int(len(t0)),
        "metals_exceeding_who": any_exc,
        "metals_never_exceeding_who": none_exc,
        "note": ("Censored observations are summarised at their detection "
                 "limit, not at a substituted value, so percentiles in heavily "
                 "censored columns reflect that limit."),
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_T0.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_T0B.relative_to(ROOT)}")
    print("\n  STAGE 3.12 DONE\n")


if __name__ == "__main__":
    main()
