"""
STAGE 5 — VERIFICATION
======================
Checks the cleaning and preprocessing stages against the raw file. Run after
`run_pipeline.py`; exits non-zero on the first failure.

These are correctness checks, not style checks. Each one guards a specific way
the pipeline could be silently wrong: censoring quietly substituted, a sentinel
left in, a target surviving screening it should have failed, or scaling applied
before cross-validation.
"""

import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "00_data" / "raw" / "special_study_areas_271_boreholes.csv"
CLEAN = ROOT / "00_data" / "interim" / "01_clean.csv"
FEATURES = ROOT / "00_data" / "interim" / "02_features.csv"
DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
REPORT = ROOT / "00_data" / "interim" / "01_clean_report.json"

PASSED = 0
FAILED = []


def check(name, condition, detail=""):
    global PASSED
    if condition:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def main():
    print("=" * 70)
    print("  VERIFICATION SUITE")
    print("=" * 70)

    for p in (CLEAN, FEATURES, DESIGN, REPORT):
        if not p.exists():
            print(f"\n  Missing {p.relative_to(ROOT)} — run run_pipeline.py first.")
            sys.exit(1)

    raw = pd.read_csv(RAW, skiprows=4, low_memory=False).iloc[1:]
    raw = raw[raw["SAMPLE_ID"].notna()].reset_index(drop=True)
    clean = pd.read_csv(CLEAN)
    feats = pd.read_csv(FEATURES)
    design = json.loads(DESIGN.read_text())
    report = json.loads(REPORT.read_text())

    print("\n  [row integrity]")
    check("no wells lost in cleaning", len(clean) == len(raw),
          f"raw={len(raw)} clean={len(clean)}")
    check("no wells lost in preprocessing", len(feats) == len(clean),
          f"clean={len(clean)} feats={len(feats)}")
    check("sample IDs unique", clean.SAMPLE_ID.is_unique)

    print("\n  [censoring preserved, not substituted]")
    # Every "<" in the raw column must survive as a True flag.
    for col in ["Cd", "AsTot", "Cr", "NO3-N"]:
        raw_n = raw[col].astype(str).str.strip().str.startswith("<").sum()
        clean_n = int(clean[f"{col}_censored"].sum())
        check(f"{col}: censored count matches raw", raw_n == clean_n,
              f"raw={raw_n} clean={clean_n}")

    # A censored value must equal the detection limit, never DL/2.
    cd_cens = clean.loc[clean["Cd_censored"], "Cd"].dropna().unique()
    check("censored values keep the detection limit (no DL/2 baked in)",
          len(cd_cens) > 0 and all(v > 0 for v in cd_cens),
          f"values={sorted(cd_cens)[:5]}")

    print("\n  [sentinels and ranges]")
    check("pH sentinel 0.0 removed", not (clean["pH"] == 0).any())
    check("pH within 3-11 where present",
          clean["pH"].dropna().between(3, 11).all())
    check("pH sentinel removal was recorded",
          report["sentinels_removed"].get("pH", 0) > 0)
    check("Eh plausible", clean["Eh"].dropna().between(-500, 800).all())
    check("latitude plausible", clean["LAT_DEG"].dropna().between(20, 27).all())

    print("\n  [target screening is consistent with its own rules]")
    thr = design["screening_thresholds"]
    for t in design["targets_modellable"]:
        pct = 100.0 * clean[f"{t}_censored"].sum() / len(clean)
        check(f"{t} kept and under the censoring limit",
              pct <= thr["max_censored_pct"],
              f"{pct:.0f}% > {thr['max_censored_pct']}%")
    excluded = {d["target"] for d in design["targets_excluded"]}
    check("Cd excluded (heavily censored)", "Cd" in excluded)
    check("Cr excluded (heavily censored)", "Cr" in excluded)
    check("every exclusion carries a reason",
          all(d["reason"] for d in design["targets_excluded"]))

    print("\n  [feature table]")
    for tier, spec in design["tiers"].items():
        missing = [f for f in spec["features"] if f not in feats.columns]
        check(f"{tier} features all present", not missing, f"missing={missing}")
    check("no tier is empty", all(spec["features"] for spec in design["tiers"].values()))

    print("\n  [no leakage: nothing scaled or imputed before CV]")
    # Raw units should survive. Scaled data would be centred near zero.
    check("SEC retains raw scale", feats["SEC"].median() > 50,
          f"median={feats['SEC'].median()}")
    check("HCO3 retains raw scale", feats["HCO3"].median() > 50,
          f"median={feats['HCO3'].median()}")
    check("missing values still present (not imputed)",
          feats[["pH", "DOC"]].isna().any().any())

    print("\n" + "=" * 70)
    if FAILED:
        print(f"  {len(FAILED)} FAILED, {PASSED} passed")
        for f in FAILED:
            print(f"    - {f}")
        print("=" * 70)
        sys.exit(1)
    print(f"  ALL {PASSED} CHECKS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
