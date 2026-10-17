"""
STAGE 1 — DATA CLEANING
=======================
Reads the raw BGS special-study-areas file and produces a typed, documented
table with censoring preserved.

Input  : 00_data/raw/special_study_areas_271_boreholes.csv
Output : 00_data/interim/01_clean.csv
         00_data/interim/01_clean_report.json

Three things this stage is careful about:

1. **Censoring is not substituted here.** A value like "< 0.02" becomes a
   numeric 0.02 in `<col>` plus True in `<col>_censored`. The detection limit
   is kept, not DL/2, so downstream code chooses its own rule explicitly and
   censoring-aware methods stay possible. Substituting at read time would throw
   the information away permanently.

2. **The pH sentinel is removed.** `pH == 0` is a missing-value marker in this
   file, not a measurement; it becomes NaN.

3. **Physically impossible values are flagged, not silently dropped.** Anything
   outside a plausible range is set to NaN and recorded in the report, so the
   count is visible rather than buried.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "raw" / "special_study_areas_271_boreholes.csv"
OUT_DIR = ROOT / "00_data" / "interim"
OUT_CSV = OUT_DIR / "01_clean.csv"
OUT_REPORT = OUT_DIR / "01_clean_report.json"

# BGS files carry four banner lines, then the column row, then a units row.
SKIP_BANNER = 4

ID_COLS = [
    "SAMPLE_ID", "SAMPLE_FIELD_ID", "SAMPLE_DATE", "LAT_DEG", "LONG_DEG",
    "YEAR_CONSTRUCTION", "WELL_TYPE", "WELL_DEPTH",
    "DIVISION", "DISTRICT", "THANA", "UNION", "MOUZA", "GEOCODE",
]

# Low-cost field-measurable predictors. Tier assignment happens in stage 2.
PREDICTORS = [
    "pH", "Eh", "SEC", "T", "diss O2",
    "Fe", "Mn", "NO3-N", "Cl", "HCO3", "SO4", "NH4-N", "DOC",
]

# Laboratory trace metals. Feasibility is decided in stage 3, not here.
TARGETS = [
    "AsTot", "AsIII", "Cd", "Ni", "Pb", "Cr", "Cu",
    "Zn", "U", "Sb", "Se", "Mo", "Ba",
]

# Major ions and minor anions. Cleaned on the same terms but kept out of both
# PREDICTORS and TARGETS: they need laboratory analysis, so using them as
# "low-cost" predictors would defeat the point of the study. Stage 3.5 uses
# them for charge balance, saturation indices and hydrochemical facies.
GEOCHEM = ["Ca", "Mg", "Na", "K", "F", "Br", "I", "Si", "Sr"]

# Plausible ranges. Deliberately wide — the job is to catch sentinels and
# transcription errors, not to trim the distribution.
PHYSICAL_RANGES = {
    "pH": (3.0, 11.0),
    "Eh": (-500.0, 800.0),
    "SEC": (1.0, 50000.0),
    "T": (5.0, 50.0),
    "diss O2": (0.0, 20.0),
    "WELL_DEPTH": (0.5, 500.0),
    "LAT_DEG": (20.0, 27.0),
    "LONG_DEG": (88.0, 93.0),
}

# pH == 0 is a missing-value marker in this file.
SENTINELS = {"pH": [0.0]}


def split_censored(series: pd.Series):
    """
    Split a possibly censored column into (value, censored_flag).

    "< 0.02" -> (0.02, True)   — the detection limit, not DL/2
    "0.31"   -> (0.31, False)
    ""       -> (NaN,  False)
    """
    s = series.astype(str).str.strip()
    censored = s.str.startswith("<")
    stripped = s.str.lstrip("<").str.strip()
    values = pd.to_numeric(stripped, errors="coerce")
    censored = censored & values.notna()
    return values, censored


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(IN_CSV, skiprows=SKIP_BANNER, low_memory=False)
    units = raw.iloc[0].to_dict()          # the units row, kept for the report
    raw = raw.iloc[1:].reset_index(drop=True)
    raw = raw[raw["SAMPLE_ID"].notna()].reset_index(drop=True)

    print("=" * 66)
    print("  STAGE 1 — DATA CLEANING")
    print("=" * 66)
    print(f"  Input : {IN_CSV.name}")
    print(f"  Rows  : {len(raw)}")

    out = pd.DataFrame()
    report = {
        "source_file": IN_CSV.name,
        "n_rows": int(len(raw)),
        "columns": {},
        "sentinels_removed": {},
        "out_of_range_removed": {},
        "missing_columns": [],
    }

    # Identifiers and coordinates
    for c in ID_COLS:
        if c not in raw.columns:
            report["missing_columns"].append(c)
            continue
        if c in ("LAT_DEG", "LONG_DEG", "WELL_DEPTH", "YEAR_CONSTRUCTION"):
            out[c] = pd.to_numeric(raw[c], errors="coerce")
        else:
            out[c] = raw[c].astype(str).str.strip().replace({"nan": np.nan})

    # Measured columns: value + censoring flag
    for c in PREDICTORS + TARGETS + GEOCHEM:
        if c not in raw.columns:
            report["missing_columns"].append(c)
            continue
        values, censored = split_censored(raw[c])

        for bad in SENTINELS.get(c, []):
            hit = (values == bad)
            if hit.any():
                values = values.mask(hit)
                report["sentinels_removed"][c] = int(hit.sum())

        out[c] = values
        out[f"{c}_censored"] = censored.fillna(False)

    # Range checks across every numeric column that has a defined range
    for c, (lo, hi) in PHYSICAL_RANGES.items():
        if c not in out.columns:
            continue
        bad = out[c].notna() & ((out[c] < lo) | (out[c] > hi))
        if bad.any():
            out.loc[bad, c] = np.nan
            report["out_of_range_removed"][c] = int(bad.sum())

    # Speciation consistency: As(III) is a fraction of total As, so AsIII > AsTot
    # is physically impossible and marks a reporting or batch error. Flag the
    # rows rather than dropping them — stage 3 decides whether to exclude, and
    # the count belongs in the manuscript's data-quality statement.
    if {"AsIII", "AsTot"}.issubset(out.columns):
        both = out["AsIII"].notna() & out["AsTot"].notna()
        # 1 % tolerance absorbs rounding in the published figures
        violation = both & (out["AsIII"] > out["AsTot"] * 1.01)
        out["as_speciation_violation"] = violation
        report["speciation_violations"] = {
            "n": int(violation.sum()),
            "n_comparable": int(both.sum()),
            "sample_ids": out.loc[violation, "SAMPLE_ID"].tolist(),
            "note": "AsIII exceeds AsTot; physically impossible. Flagged, not dropped.",
        }

    # Detection limits: a column analysed in several batches can carry more than
    # one limit, which puts an artificial step into the censored values. Record
    # them so stage 3 can model each limit separately instead of pooling them.
    report["detection_limits"] = {}
    for c in PREDICTORS + TARGETS + GEOCHEM:
        if c not in out.columns:
            continue
        dls = sorted(out.loc[out[f"{c}_censored"], c].dropna().unique().tolist())
        if dls:
            report["detection_limits"][c] = {
                "n_distinct": len(dls),
                "limits": [round(float(v), 6) for v in dls],
                "multiple": len(dls) > 1,
            }

    # Per-column summary
    for c in PREDICTORS + TARGETS + GEOCHEM:
        if c not in out.columns:
            continue
        v = out[c]
        report["columns"][c] = {
            "role": ("predictor" if c in PREDICTORS
                     else "target" if c in TARGETS else "geochemistry"),
            "unit": str(units.get(c, "")).strip(),
            "n_valid": int(v.notna().sum()),
            "n_censored": int(out[f"{c}_censored"].sum()),
            "pct_censored": round(100.0 * out[f"{c}_censored"].sum() / len(out), 1),
            "median": None if v.notna().sum() == 0 else round(float(v.median()), 6),
            "min": None if v.notna().sum() == 0 else round(float(v.min()), 6),
            "max": None if v.notna().sum() == 0 else round(float(v.max()), 6),
        }

    out.to_csv(OUT_CSV, index=False)
    with open(OUT_REPORT, "w") as f:
        json.dump(report, f, indent=2)

    if report["sentinels_removed"]:
        print(f"\n  Sentinels -> NaN     : {report['sentinels_removed']}")
    if report["out_of_range_removed"]:
        print(f"  Out of range -> NaN  : {report['out_of_range_removed']}")
    if report["missing_columns"]:
        print(f"  Columns not found    : {report['missing_columns']}")

    spec = report.get("speciation_violations", {})
    if spec.get("n"):
        print(f"  AsIII > AsTot        : {spec['n']}/{spec['n_comparable']} wells "
              f"(flagged, not dropped)")

    multi = {c: m["limits"] for c, m in report["detection_limits"].items() if m["multiple"]}
    if multi:
        print("  Multiple detection limits:")
        for c, lims in multi.items():
            print(f"    {c:10s} {lims}")

    print(f"\n  {'column':12s} {'role':9s} {'valid':>6s} {'cens%':>7s} {'median':>10s}")
    for c, m in report["columns"].items():
        median = "-" if m["median"] is None else f"{m['median']:.3f}"
        print(f"  {c:12s} {m['role']:9s} {m['n_valid']:6d} "
              f"{m['pct_censored']:6.0f}% {median:>10s}")

    print(f"\n  Saved -> {OUT_CSV.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_REPORT.relative_to(ROOT)}")
    print("\n  STAGE 1 DONE\n")


if __name__ == "__main__":
    main()
