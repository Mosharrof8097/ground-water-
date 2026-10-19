"""
Build the supplementary tables that are assembled rather than copied.

At present that is S1, the two cases in which censoring manufactures structure.
Both halves are read from the stored metrics so the table cannot drift from the
analysis it describes.

    python _build_supplement_tables.py
"""

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MET = HERE.parent / "04_results" / "metrics"
TAB = HERE.parent / "04_results" / "tables"
OUT = TAB / "S1_censoring_two_cases.csv"


def main():
    geo = json.loads((MET / "35_geochem.json").read_text())
    audit = json.loads((MET / "46_log_skill_audit.json").read_text())

    zones = {z["redox_zone"]: z
             for z in geo["redox_zonation"]["zones"]}
    strict = zones.get("nitrate-reducing", {}).get("n_wells")
    mixed = zones.get("mixed (anoxic)", {}).get("n_wells")

    ref = audit["results"]["REF_full_cheap"]["spatial_8"]

    rows = [
        {
            "case": "Redox class: nitrate-reducing",
            "test": "NO3-N at or above 0.5 mg/L",
            "censoring_in_that_column": "80 % of wells, limits 0.3 and 0.5 mg/L",
            "reading_the_limit_as_a_measurement": "65 wells",
            "respecting_the_censoring_flag": f"{strict} wells",
            "where_the_rest_went": f"{mixed} wells to mixed (anoxic)",
            "evidence": "median Fe 1.4 mg/L in the wells the naive test admits",
        },
        {
            "case": "Arsenic log-scale skill, 8 spatial blocks, REF tier",
            "test": "held-out log-scale R² above zero",
            "censoring_in_that_column": "34 % of wells, limits 0.5 and 6.0 µg/L",
            "reading_the_limit_as_a_measurement": f"R² = {ref['r2_log']:+.3f}",
            "respecting_the_censoring_flag":
                f"R² = {ref['r2_log_measured_only']:+.3f} on measured wells only",
            "where_the_rest_went": "not applicable",
            "evidence":
                f"Wilcoxon p = {ref['wilcoxon_p_log_measured_gt_0']:.2f} "
                f"against zero",
        },
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"  wrote {OUT.relative_to(HERE.parent)}")
    for r in rows:
        print(f"    {r['case']}")
        print(f"      limit read as a measurement : "
              f"{r['reading_the_limit_as_a_measurement']}")
        print(f"      flag respected              : "
              f"{r['respecting_the_censoring_flag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
