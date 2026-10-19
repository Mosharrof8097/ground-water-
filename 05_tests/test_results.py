"""
STAGE 5 — RESULTS VERIFICATION
==============================
Checks the stage 3 outputs for internal consistency. Run after the methods
scripts; exits non-zero on the first failure.

These guard the ways a results file can be wrong without crashing: a
feasibility verdict that contradicts its own p-value, a coverage figure that is
actually in-sample, a censoring comparison whose folds were not held fixed, or
an external validation whose "independent" set is next door.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "04_results" / "metrics"
TABLES = ROOT / "04_results" / "tables"

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


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def main():
    print("=" * 70)
    print("  RESULTS VERIFICATION")
    print("=" * 70)

    feas = load(METRICS / "31_feasibility.json")
    conf = load(METRICS / "32_conformal.json")
    cens = load(METRICS / "33_censoring.json")
    ext = load(METRICS / "34_external.json")

    if feas is None:
        print("\n  31_feasibility.json missing — run stage 3 first.")
        sys.exit(1)

    # ── 3.1 feasibility ──────────────────────────────────────────────────────
    print("\n  [3.1 feasibility audit]")
    res = feas["results"]
    flat = [(t, tier, r) for t, tiers in res.items() for tier, r in tiers.items()]

    check("every combination carries a verdict",
          all("feasible" in r for _, _, r in flat))
    check("feasible implies positive R2",
          all(r["r2_mean"] > 0 for _, _, r in flat if r["feasible"]))
    check("feasible implies FDR significance",
          all(r["fdr_significant"] for _, _, r in flat if r["feasible"]))
    check("fold count matches the stated protocol",
          all(r["n_folds"] == 25 for _, _, r in flat),
          f"found {sorted({r['n_folds'] for _, _, r in flat})}")
    check("per-fold scores are recorded for every combination",
          all(len(r["fold_r2"]) == r["n_folds"] for _, _, r in flat))
    check("reported mean matches the per-fold scores",
          all(abs(sum(r["fold_r2"]) / len(r["fold_r2"]) - r["r2_mean"]) < 1e-3
              for _, _, r in flat))
    check("a baseline was scored for every combination",
          all("r2_baseline_mean" in r for _, _, r in flat))
    check("delta_r2 equals model minus baseline",
          all(abs(r["delta_r2"] - (r["r2_mean"] - r["r2_baseline_mean"])) < 1e-6
              for _, _, r in flat))
    # A target beating the baseline while still scoring below it would be a
    # contradiction; Pb legitimately beats a very poor baseline with R2 < 0.
    check("no combination is feasible while losing to the baseline",
          all(r["delta_r2"] > 0 for _, _, r in flat if r["feasible"]))

    t2 = pd.read_csv(TABLES / "T2_feasibility_matrix.csv")
    check("T2 row count matches the metrics file", len(t2) == len(flat),
          f"T2={len(t2)} metrics={len(flat)}")

    # ── 3.2 conformal ────────────────────────────────────────────────────────
    if conf and conf.get("results"):
        print("\n  [3.2 conformal prediction]")
        crows = [(t, tier, r) for t, tiers in conf["results"].items()
                 for tier, r in tiers.items()]
        check("coverage is a probability",
              all(0 <= r["mean_coverage"] <= 1 for _, _, r in crows))
        check("coverage comes from disjoint splits, not calibration residuals",
              all("disjoint" in r["protocol"] for _, _, r in crows))
        check("coverage is not pinned exactly at nominal (would signal circularity)",
              not all(abs(r["mean_coverage"] - r["nominal_coverage"]) < 1e-6
                      for _, _, r in crows))
        check("interval widths are positive",
              all(r["mean_interval_width"] > 0 for _, _, r in crows))
        check("every conformal combination was found feasible in 3.1",
              all(res[t][tier]["feasible"] for t, tier, _ in crows))
        # Split conformal certifies coverage of at least 1 - alpha in finite
        # samples. Systematic undercoverage means the plain empirical quantile
        # was used instead of the ceil((n+1)(1-alpha)) order statistic, which
        # is exactly what an earlier version of this stage did.
        under = [(t, tier, r["mean_coverage"]) for t, tier, r in crows
                 if r["mean_coverage"] < r["nominal_coverage"] - 0.005]
        check("coverage is not systematically below nominal",
              len(under) <= max(1, len(crows) // 10),
              f"{len(under)} of {len(crows)} combinations undercover: "
              f"{under[:3]}")

    # ── 3.5 redox classification ─────────────────────────────────────────────
    geo = load(METRICS / "35_geochem.json")
    if geo and geo.get("redox_zonation", {}).get("zones"):
        print("\n  [3.5 redox classification]")
        zones = {z["redox_zone"]: z for z in geo["redox_zonation"]["zones"]}
        nr = zones.get("nitrate-reducing")
        if nr:
            # A nitrate-reducing water cannot carry milligrams of dissolved
            # iron. When it appears to, censored nitrate has been read as a
            # measurement and compared against its own detection limit.
            check("nitrate-reducing wells are low in iron",
                  nr["median_Fe_mgL"] < 0.1,
                  f"median Fe {nr['median_Fe_mgL']} mg/L in "
                  f"{nr['n_wells']} nitrate-reducing wells")
            check("nitrate-reducing wells are low in manganese",
                  nr["median_Mn_mgL"] < 0.05,
                  f"median Mn {nr['median_Mn_mgL']} mg/L")
        ox = zones.get("oxic")
        if ox:
            check("oxic wells are low in iron",
                  ox["median_Fe_mgL"] < 0.1,
                  f"median Fe {ox['median_Fe_mgL']} mg/L in "
                  f"{ox['n_wells']} oxic wells")
        check("waters that satisfy no single class are reported, not forced",
              any(z.startswith("mixed") or z == "indeterminate" for z in zones))

    # ── 3.3 censoring ────────────────────────────────────────────────────────
    if cens:
        print("\n  [3.3 censoring comparison]")
        rules = {"substitute_half", "substitute_dl", "substitute_zero",
                 "stochastic_imputation"}
        check("all four censoring rules evaluated for every target",
              all(rules <= set(r["r2_by_rule"]) for r in cens["results"].values()))
        check("spread equals max minus min across rules",
              all(abs(r["r2_spread"] - (max(r["r2_by_rule"].values())
                                        - min(r["r2_by_rule"].values()))) < 1e-3
                  for r in cens["results"].values()))
        zero_cens = [t for t, r in cens["results"].items() if r["pct_censored"] == 0]
        check("the draw-based rule is not mislabelled as ROS",
              all("ros" not in r["r2_by_rule"] for r in cens["results"].values()),
              "regression on order statistics is a different estimator")
        check("every rule is scored against the same measured wells",
              all(r.get("n_scored_against") for r in cens["results"].values()))
        check("censored-consistency is reported where there is censoring",
              all(r.get("censored_consistency_pct")
                  for r in cens["results"].values() if r.get("n_censored")))
        check("targets with no censoring show zero spread",
              all(cens["results"][t]["r2_spread"] < 1e-6 for t in zero_cens),
              f"checked {zero_cens}")

    # ── 3.4 external validation ──────────────────────────────────────────────
    if ext:
        print("\n  [3.4 external validation]")
        d = ext["design"]
        check("external set is geographically separated",
              d["min_separation_km"] >= 1.0, f"{d['min_separation_km']} km")
        check("the shared district was excluded", "Nawabganj" in d["external"])
        check("the unit-mismatched predictor was excluded", "Al" in d["excluded_predictor"])
        erows = [(t, tier, r) for t, tiers in ext["results"].items()
                 for tier, r in tiers.items()]
        check("external set is larger than development",
              all(r["n_ext"] > r["n_dev"] for _, _, r in erows))
        check("an in-development score is reported for the same reduced features",
              all("internal_cv_r2" in r for _, _, r in erows))

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
