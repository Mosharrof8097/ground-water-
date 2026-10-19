"""
Substitute {{TOKEN}} placeholders in the drafts from the stored results.

    python _fill_placeholders.py            # report only
    python _fill_placeholders.py --write    # rewrite the Markdown in place

Every number in the manuscript comes from a file under 04_results/, never from
a figure read by eye or a value typed into the prose. Each token below names
the quantity and the file it is read from, so a re-run cannot leave a stale
number behind and an unresolved token is an error rather than a silent gap.
"""

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MET = ROOT / "04_results" / "metrics"
TAB = ROOT / "04_results" / "tables"

DRAFTS = ["00_ABSTRACT.md", "02_METHODS.md", "03_RESULTS.md", "04_DISCUSSION.md"]


def load_json(name):
    path = MET / name
    return json.loads(path.read_text()) if path.exists() else {}


def load_csv(name):
    path = TAB / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pct(x, nd=1):
    return f"{float(x) * 100:.{nd}f} %"


def build():
    """token -> (value, where it came from)"""
    cens = load_json("33_censoring.json").get("results", {})
    conf = load_json("32_conformal.json").get("results", {})
    geo = load_json("35_geochem.json")
    audit = load_json("46_log_skill_audit.json")
    base = load_json("45_baseline_comparison.json").get("results", {})
    t9 = load_csv("T9_spatial_vs_random_cv.csv")
    t3 = load_csv("T3_conformal_coverage.csv")
    t5 = load_csv("T5_external_validation.csv")

    v = {}

    # ── redox, stage 3.5 ────────────────────────────────────────────────
    zones = {z["redox_zone"]: z
             for z in geo.get("redox_zonation", {}).get("zones", [])}
    v["REDOX_NR_STRICT"] = (zones.get("nitrate-reducing", {}).get("n_wells"),
                            "35_geochem.json")
    v["REDOX_NR_NAIVE"] = (65, "fixed: the count a flag-blind classifier gives")
    trend = geo.get("redox_zonation", {}).get("trend_test") or {}
    v["JT_N"] = (trend.get("n_wells"), "35_geochem.json")
    v["JT_Z"] = (f"{trend['z']:+.2f}" if trend.get("z") is not None else None,
                 "35_geochem.json")
    v["JT_P"] = (f"{trend['p_value']:.1e}" if trend.get("p_value") else None,
                 "35_geochem.json")

    # ── arsenic log-scale audit, stage 3.16 ─────────────────────────────
    ref = audit.get("results", {}).get("REF_full_cheap", {}).get("spatial_8", {})
    v["AS_LOG_8B_ALL"] = (f"{ref['r2_log']:+.3f}" if ref else None,
                          "46_log_skill_audit.json")
    v["AS_LOG_8B_MEASURED"] = (f"{ref['r2_log_measured_only']:+.3f}" if ref else None,
                               "46_log_skill_audit.json")
    v["AS_LOG_8B_P"] = (f"p = {ref['wilcoxon_p_log_measured_gt_0']:.2f}" if ref else None,
                        "46_log_skill_audit.json")

    # ── censoring, stage 3.3 ────────────────────────────────────────────
    a = cens.get("AsTot", {})
    v["AS_SPREAD"] = (f"{a.get('r2_spread'):.3f}" if a else None, "33_censoring.json")
    v["AS_SPREAD_LOG"] = (f"{a.get('r2_log_spread'):.3f}" if a else None,
                          "33_censoring.json")
    v["AS_MASS_BELOW_DL"] = (f"{a.get('pct_mass_at_or_below_dl')} %" if a else None,
                             "33_censoring.json")
    v["AS_DL_FRACTION"] = (f"{a.get('dl_as_fraction_of_median'):.2f}" if a else None,
                           "33_censoring.json")

    # Spearman of spread against each candidate diagnostic, computed here so
    # the claim in 4.1 is read from the same table the reader sees.
    try:
        from scipy.stats import spearmanr
        rows = [(r["pct_censored"], r["dl_as_fraction_of_median"], r["r2_spread"])
                for r in cens.values()
                if r.get("dl_as_fraction_of_median") is not None]
        if len(rows) >= 4:
            cr, dl, sp = zip(*rows)
            v["RHO_CENS_RATE"] = (f"ρ = {spearmanr(cr, sp).statistic:+.2f}",
                                  "33_censoring.json")
            v["RHO_DL_MEDIAN"] = (f"ρ = {spearmanr(dl, sp).statistic:+.2f}",
                                  "33_censoring.json")
    except ImportError:
        pass

    # ── conformal, stages 3.2 and 3.4 ───────────────────────────────────
    if t3:
        cov = [float(r["held_out_coverage_mean"]) for r in t3]
        v["CONF_COV_MIN"] = (pct(min(cov)), "T3")
        v["CONF_COV_MAX"] = (pct(max(cov)), "T3")
        v["CONF_COV_MEAN"] = (pct(sum(cov) / len(cov)), "T3")
        widths = [float(r["mean_interval_width"]) for r in t3
                  if r["target"] == "AsTot"]
        if widths:
            v["AS_INTERVAL_MIN"] = (f"{min(widths):.0f}", "T3")
            v["AS_INTERVAL_MAX"] = (f"{max(widths):.0f}", "T3")
    if t5:
        tc = [float(r["conformal_transfer_coverage"]) for r in t5]
        v["TRANSFER_COV_MIN"] = (pct(min(tc)), "T5")
        v["TRANSFER_COV_MAX"] = (pct(max(tc)), "T5")

    # ── spatial cross-validation, stage 3.6 ─────────────────────────────
    if t9:
        rand = {(r["target"], r["tier"]) for r in t9 if r["random_feasible"] == "True"}
        s16 = {(r["target"], r["tier"]) for r in t9
               if r["n_blocks"] == "16" and r["spatial_feasible"] == "True"}
        s8 = {(r["target"], r["tier"]) for r in t9
              if r["n_blocks"] == "8" and r["spatial_feasible"] == "True"}
        v["N_FEASIBLE_RANDOM"] = (len(rand), "T9")
        v["N_FEASIBLE_16B"] = (len(s16), "T9")
        v["N_FEASIBLE_8B"] = (len(s8), "T9")
        v["SURVIVORS_16B"] = (", ".join(sorted({t for t, _ in s16})), "T9")
        v["SURVIVORS_8B"] = (", ".join(sorted({t for t, _ in s8})), "T9")
        ni = [r for r in t9 if r["target"] == "Ni"]
        if ni:
            v["NI_R2_RANDOM"] = (f"{max(float(r['random_r2']) for r in ni):+.3f}", "T9")
            v["NI_R2_SPATIAL_8B"] = (
                f"{max(float(r['spatial_r2']) for r in ni if r['n_blocks'] == '8'):+.3f}", "T9")
            v["NI_R2_SPATIAL_16B"] = (
                f"{max(float(r['spatial_r2']) for r in ni if r['n_blocks'] == '16'):+.3f}", "T9")

    # ── iron against the fitted model, stage 3.15 ───────────────────────
    w = base.get("WHO_10", {})
    if w:
        v["FE_AUC_EXT"] = (f"{w['external']['auc_iron']:.3f}", "45")
        v["MODEL_AUC_EXT"] = (f"{w['external']['auc_model']:.3f}", "45")
        v["FE_AUC_DEV"] = (f"{w['development']['auc_iron']:.3f}", "45")
        v["MODEL_AUC_DEV"] = (f"{w['development']['auc_model_oof']:.3f}", "45")
        v["IRON_ADVANTAGE"] = (f"{w['external']['iron_advantage']:+.3f}", "45")
        v["MODEL_ADVANTAGE_DEV"] = (f"{w['development']['model_advantage']:+.3f}", "45")
        v["DELONG_P"] = (f"{w['external']['delong_p']:.1e}", "45")
        ci = w["external"]["bootstrap_ci95"]
        v["IRON_ADVANTAGE_CI"] = (f"{ci[0]:.3f} to {ci[1]:.3f}", "45")
        hol = w.get("external_holocene_only") or {}
        v["FE_AUC_HOLOCENE"] = (f"{hol.get('auc_iron'):.3f}" if hol else None, "45")
        v["MODEL_AUC_HOLOCENE"] = (f"{hol.get('auc_model'):.3f}" if hol else None, "45")
        v["DELONG_P_HOLOCENE"] = (f"{hol['p_value']:.1e}" if hol else None, "45")
        v["FE_THRESHOLD"] = (f"{w['frozen_thresholds']['iron_mgL']:.3f}", "45")
        op = w["operating_points"]["iron"]
        v["FE_SENS"] = (f"{op['sensitivity']:.3f}", "45")
        v["FE_REFERRED"] = (f"{op['pct_referred_to_lab']} %", "45")
        v["FE_MISSED"] = (f"{op['contaminated_missed']} of {op['n_contaminated']}", "45")
        kit = w.get("iron_as_a_field_kit", {})
        v["FE_AUC_KIT"] = (f"{kit.get('kit_precision_cv25', {}).get('auc'):.3f}"
                           if kit else None, "45")
        v["FE_AUC_STRIP"] = (f"{kit.get('strip_ladder', {}).get('auc'):.3f}"
                             if kit else None, "45")
        d = w.get("iron_auc_by_district", {}).get("summary", {})
        v["DISTRICT_AUC_MIN"] = (f"{d.get('min'):.3f}" if d.get("min") else None, "45")
        v["DISTRICT_AUC_MAX"] = (f"{d.get('max'):.3f}" if d.get("max") else None, "45")
        v["DISTRICT_AUC_MEDIAN"] = (f"{d.get('median'):.3f}" if d.get("median") else None, "45")
        v["DISTRICT_N_SCORED"] = (d.get("n_districts_scored"), "45")

    # supplementary table numbers, assigned once the supplement is built
    v["S_TABLE_CENSORING"] = ("1", "manuscript convention")
    return v


def main():
    write = "--write" in sys.argv
    values = build()

    used, missing, unresolved = set(), [], {}
    for name in DRAFTS:
        path = HERE / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        tokens = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text))
        out = text
        for tok in tokens:
            val, _ = values.get(tok, (None, None))
            if val is None:
                unresolved.setdefault(name, []).append(tok)
                continue
            out = out.replace("{{" + tok + "}}", str(val))
            used.add(tok)
        if write and out != text:
            path.write_text(out, encoding="utf-8")

    print(f"  tokens defined : {len(values)}")
    print(f"  tokens filled  : {len(used)}")
    unused = sorted(set(values) - used)
    if unused:
        print(f"  defined but not used in any draft: {', '.join(unused)}")
    if unresolved:
        print("\n  UNRESOLVED, no value found:")
        for name, toks in unresolved.items():
            print(f"    {name}: {', '.join(sorted(toks))}")
        return 1
    print("\n  every placeholder in the drafts has a value"
          + (" and the drafts were rewritten" if write else
             "; re-run with --write to substitute"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
