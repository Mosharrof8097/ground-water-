"""
STAGE 2 — PREPROCESSING
=======================
Defines the cost-tiered predictor sets and decides which targets are worth
modelling at all.

Input  : 00_data/interim/01_clean.csv
Output : 00_data/interim/02_features.csv
         00_data/interim/02_design.json          (tiers, targets, reasons)
         04_results/tables/T1_target_screening.csv

Two decisions live here, both deliberately explicit.

**Predictor tiers.** The research question is about cost, so predictors are
grouped by what it actually takes to measure them in the field. Each tier adds
equipment or effort to the one before it, which lets stage 3 report performance
as a function of spend rather than as one undifferentiated feature set.

**Target screening.** Some metals cannot be modelled by any method, and saying
so up front is cheaper and more honest than letting cross-validation discover
it. A target is excluded when it is too heavily censored to carry information,
has essentially no variation, or has too few measurements. Every exclusion is
recorded with its reason, and the resulting table is a manuscript table in its
own right: it is the first result, not housekeeping.

Nothing is imputed or scaled here. That happens inside the cross-validation
fold in stage 3, otherwise information leaks from test to train.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "01_clean.csv"
OUT_DIR = ROOT / "00_data" / "interim"
OUT_CSV = OUT_DIR / "02_features.csv"
OUT_DESIGN = OUT_DIR / "02_design.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T1_target_screening.csv"

# ── Cost-tiered predictor sets ───────────────────────────────────────────────
# Each tier is cumulative. Cost notes are per sample after equipment purchase.
TIERS = {
    "E1_meter": {
        "features": ["pH", "Eh", "SEC", "T"],
        "cost": "multiparameter field meter only; negligible per-sample cost",
    },
    "E2_meter_kit": {
        "features": ["pH", "Eh", "SEC", "T", "Fe", "Mn"],
        "cost": "E1 + colorimetric field kits for Fe and Mn",
    },
    "E3_meter_kit_titration": {
        "features": ["pH", "Eh", "SEC", "T", "Fe", "Mn", "Cl", "HCO3"],
        "cost": "E2 + chloride and alkalinity titration",
    },
    "E4_plus_well_record": {
        "features": ["pH", "Eh", "SEC", "T", "Fe", "Mn", "Cl", "HCO3", "WELL_DEPTH"],
        "cost": "E3 + well depth from the installation record (free)",
    },
    "REF_full_cheap": {
        "features": ["pH", "Eh", "SEC", "T", "Fe", "Mn", "Cl", "HCO3", "WELL_DEPTH",
                     "SO4", "NH4-N", "DOC", "NO3-N", "diss O2"],
        "cost": "reference ceiling: every non-ICP-MS determinand, including the "
                "heavily censored ones; not a field-deployable tier",
    },
}

ALL_TARGETS = ["AsTot", "AsIII", "Cd", "Ni", "Pb", "Cr", "Cu",
               "Zn", "U", "Sb", "Se", "Mo", "Ba"]

# Screening thresholds. Chosen to exclude only the genuinely hopeless; a target
# that merely looks hard still goes forward so stage 3 can test it properly.
MAX_CENSORED_PCT = 60.0   # above this, most values are a single detection limit
MIN_VALID = 100           # fewer measurements than this cannot support 5x5 CV
MIN_DISTINCT = 10         # fewer distinct values than this is near-constant

# A censoring percentage alone misses a target that is nominally measured but
# piles up on one value. Sb is 46 % censored yet 46 % of all rows sit on the
# single value 0.02 (its detection limit); AsIII has 43 % on 6.0. Either is
# close enough to a constant that no model can learn from it, so cap the share
# any single value may hold.
MAX_MODAL_PCT = 40.0

WHO_LIMITS = {"AsTot": 10.0, "Cd": 3.0, "Ni": 20.0, "Pb": 10.0, "Cr": 50.0,
              "Cu": 2000.0, "Zn": 3000.0, "U": 30.0, "Sb": 20.0, "Se": 40.0,
              "Mo": 70.0, "Ba": 1300.0}


def screen_target(df, name):
    """Decide whether `name` can be modelled, and say why not when it cannot."""
    v = df[name]
    cens_pct = 100.0 * df[f"{name}_censored"].sum() / len(df)
    n_valid = int(v.notna().sum())
    n_distinct = int(v.dropna().nunique())

    vd = v.dropna()
    modal_pct = 0.0 if vd.empty else 100.0 * (vd == vd.mode().iloc[0]).sum() / len(df)
    modal_value = None if vd.empty else round(float(vd.mode().iloc[0]), 6)

    reasons = []
    if n_valid < MIN_VALID:
        reasons.append(f"only {n_valid} measurements (< {MIN_VALID})")
    if cens_pct > MAX_CENSORED_PCT:
        reasons.append(f"{cens_pct:.0f}% censored (> {MAX_CENSORED_PCT:.0f}%)")
    if n_distinct < MIN_DISTINCT:
        reasons.append(f"only {n_distinct} distinct values (< {MIN_DISTINCT})")
    if modal_pct > MAX_MODAL_PCT:
        reasons.append(f"{modal_pct:.0f}% of rows share the single value "
                       f"{modal_value} (> {MAX_MODAL_PCT:.0f}%)")

    limit = WHO_LIMITS.get(name)
    n_exceed = int((v > limit).sum()) if limit else None

    return {
        "target": name,
        "n_valid": n_valid,
        "pct_censored": round(cens_pct, 1),
        "n_distinct": n_distinct,
        "modal_value": modal_value,
        "pct_at_modal_value": round(modal_pct, 1),
        "median": None if n_valid == 0 else round(float(v.median()), 4),
        "max": None if n_valid == 0 else round(float(v.max()), 4),
        "who_limit_ug_L": limit,
        "n_exceeding_who": n_exceed,
        "modellable": len(reasons) == 0,
        "exclusion_reason": "; ".join(reasons) if reasons else "",
    }


def main():
    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(IN_CSV)

    print("=" * 70)
    print("  STAGE 2 — PREPROCESSING")
    print("=" * 70)
    print(f"  Wells: {len(df)}\n")

    # ── Target screening ─────────────────────────────────────────────────────
    screening = [screen_target(df, t) for t in ALL_TARGETS if t in df.columns]
    tbl = pd.DataFrame(screening).sort_values(
        ["modellable", "pct_censored"], ascending=[False, True])
    tbl.to_csv(OUT_TABLE, index=False)

    keep = [r["target"] for r in screening if r["modellable"]]
    drop = [r for r in screening if not r["modellable"]]

    print("  TARGET SCREENING")
    print(f"  {'target':8s} {'valid':>6s} {'cens%':>6s} {'modal%':>7s} "
          f"{'distinct':>9s}  verdict")
    for r in tbl.to_dict("records"):
        verdict = "MODEL" if r["modellable"] else f"drop - {r['exclusion_reason']}"
        print(f"  {r['target']:8s} {r['n_valid']:6d} {r['pct_censored']:5.0f}% "
              f"{r['pct_at_modal_value']:6.0f}% {r['n_distinct']:9d}  {verdict}")

    print(f"\n  -> {len(keep)} modellable: {', '.join(keep)}")
    print(f"  -> {len(drop)} excluded")

    # ── Predictor tier availability ──────────────────────────────────────────
    print("\n  PREDICTOR TIERS")
    tiers_out = {}
    for name, spec in TIERS.items():
        feats = [f for f in spec["features"] if f in df.columns]
        missing = [f for f in spec["features"] if f not in df.columns]
        complete = int(df[feats].notna().all(axis=1).sum())
        tiers_out[name] = {
            "features": feats,
            "missing": missing,
            "cost": spec["cost"],
            "n_complete_case": complete,
        }
        print(f"  {name:24s} {len(feats):2d} features, "
              f"{complete:3d}/{len(df)} complete cases")
        if missing:
            print(f"  {'':24s} missing: {missing}")

    # ── Write the modelling frame ────────────────────────────────────────────
    id_cols = [c for c in ["SAMPLE_ID", "DISTRICT", "THANA", "LAT_DEG", "LONG_DEG",
                           "WELL_DEPTH", "WELL_TYPE"] if c in df.columns]
    feat_cols = sorted({f for s in TIERS.values() for f in s["features"]
                        if f in df.columns})
    target_cols = keep + [f"{t}_censored" for t in keep if f"{t}_censored" in df.columns]

    out = df[id_cols + feat_cols + target_cols].copy()
    out.to_csv(OUT_CSV, index=False)

    design = {
        "n_wells": int(len(df)),
        "tiers": tiers_out,
        "targets_modellable": keep,
        "targets_excluded": [{"target": r["target"], "reason": r["exclusion_reason"]}
                             for r in drop],
        "screening_thresholds": {
            "max_censored_pct": MAX_CENSORED_PCT,
            "max_modal_pct": MAX_MODAL_PCT,
            "min_valid": MIN_VALID,
            "min_distinct": MIN_DISTINCT,
        },
        "who_limits_ug_L": WHO_LIMITS,
        "note": "No imputation or scaling applied here; both belong inside the "
                "cross-validation fold in stage 3.",
    }
    with open(OUT_DESIGN, "w") as f:
        json.dump(design, f, indent=2)

    print(f"\n  Saved -> {OUT_CSV.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_DESIGN.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 2 DONE\n")


if __name__ == "__main__":
    main()
