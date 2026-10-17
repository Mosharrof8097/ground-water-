"""
STAGE 3.5 — HYDROGEOCHEMISTRY
=============================
Gives the statistical results a geochemical reading, and checks the data the
way a water-chemistry reviewer will.

Input  : 00_data/interim/01_clean.csv
Output : 00_data/interim/35_geochem.csv          (per-well geochemical variables)
         04_results/metrics/35_geochem.json
         04_results/tables/T6_charge_balance.csv
         04_results/tables/T7_redox_zonation.csv
         04_results/tables/T8_water_types.csv

Four blocks:

1. **Charge balance error.** The first thing asked of any paper reporting major
   ions. Samples outside +-10 % are flagged, not deleted; the rate is a
   data-quality statement.

2. **Redox zonation** after McMahon & Chapelle (2008): a cascade through O2,
   NO3, Mn, Fe and SO4 that assigns each well a terminal electron-accepting
   process. This is what turns "adding Fe and Mn made the arsenic model work"
   from a correlation into a mechanism — arsenic is released by reductive
   dissolution of Fe oxyhydroxides, so Fe and Mn are not arbitrary predictors
   but direct indicators of the process that mobilises it.

3. **Saturation indices** for calcite and siderite, computed from pH,
   temperature and major ions with Davies activity coefficients. Siderite
   matters here: precipitation limits dissolved Fe and therefore weakens Fe as
   an arsenic proxy.

4. **Hydrochemical facies** from meq-percent dominance, the quantitative core
   of a Piper diagram, plus Gibbs ratios for weathering versus evaporation
   control.

Constants are standard; the arsenic interpretation follows the Bengal Basin
literature on reductive dissolution.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "01_clean.csv"
OUT_CSV = ROOT / "00_data" / "interim" / "35_geochem.csv"
OUT_METRICS = ROOT / "04_results" / "metrics" / "35_geochem.json"
OUT_CB = ROOT / "04_results" / "tables" / "T6_charge_balance.csv"
OUT_REDOX = ROOT / "04_results" / "tables" / "T7_redox_zonation.csv"
OUT_TYPES = ROOT / "04_results" / "tables" / "T8_water_types.csv"

# mg per meq (atomic or formula weight / charge)
EQ_WEIGHT = {
    "Ca": 20.04, "Mg": 12.15, "Na": 22.99, "K": 39.10,
    "Cl": 35.45, "HCO3": 61.02, "SO4": 48.03, "F": 19.00,
}
N_EQ = 14.007          # NO3-N and NH4-N are reported as N
CB_TOLERANCE = 10.0    # percent; 5 % is ideal, 10 % usual for dilute waters

# McMahon & Chapelle (2008) threshold concentrations, mg/L
TH_O2, TH_NO3_N, TH_MN, TH_FE, TH_SO4 = 0.5, 0.5, 0.05, 0.1, 0.5

# log K at 25 C
LOGK_CALCITE = -8.48          # CaCO3
LOGK_SIDERITE = -10.89        # FeCO3
LOGK2_CARBONIC = -10.33       # HCO3- = H+ + CO3(2-)


def meq(series, ion):
    return series / EQ_WEIGHT[ion]


def davies_gamma(z, ionic_strength):
    """Davies activity coefficient; valid to roughly I = 0.5 M."""
    I = np.clip(ionic_strength, 1e-9, None)
    sqrt_I = np.sqrt(I)
    log_gamma = -0.509 * (z ** 2) * (sqrt_I / (1 + sqrt_I) - 0.3 * I)
    return 10 ** log_gamma


def classify_redox(row):
    """
    Terminal electron-accepting process, following the cascade in
    McMahon & Chapelle (2008). Order matters: each step assumes the previous
    acceptor is exhausted.
    """
    o2, no3, mn, fe, so4 = (row["diss O2"], row["NO3-N"], row["Mn"],
                            row["Fe"], row["SO4"])
    if pd.isna(o2) and pd.isna(fe) and pd.isna(mn):
        return "indeterminate"
    if pd.notna(o2) and o2 >= TH_O2:
        return "oxic"
    if pd.notna(no3) and no3 >= TH_NO3_N:
        return "nitrate-reducing"
    if pd.notna(mn) and mn >= TH_MN and (pd.isna(fe) or fe < TH_FE):
        return "Mn(IV)-reducing"
    if pd.notna(fe) and fe >= TH_FE:
        if pd.notna(so4) and so4 < TH_SO4:
            return "sulfate-reducing / methanogenic"
        return "Fe(III)-reducing"
    if pd.notna(so4) and so4 < TH_SO4:
        return "sulfate-reducing / methanogenic"
    return "suboxic"


def water_type(row):
    """Dominant cation and anion on a meq-percent basis — the Piper facies."""
    cations = {"Ca": row["Ca_meq"], "Mg": row["Mg_meq"],
               "Na+K": row["Na_meq"] + row["K_meq"]}
    anions = {"HCO3": row["HCO3_meq"], "Cl": row["Cl_meq"], "SO4": row["SO4_meq"]}
    if not np.isfinite(sum(cations.values())) or sum(cations.values()) <= 0:
        return "undetermined"
    if not np.isfinite(sum(anions.values())) or sum(anions.values()) <= 0:
        return "undetermined"
    return f"{max(cations, key=cations.get)}-{max(anions, key=anions.get)}"


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    OUT_CB.parent.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(IN_CSV)

    print("=" * 76)
    print("  STAGE 3.5 — HYDROGEOCHEMISTRY")
    print("=" * 76)
    print(f"  Wells: {len(d)}\n")

    g = d[["SAMPLE_ID", "DISTRICT", "WELL_DEPTH"]].copy()

    # ── 1. Charge balance ────────────────────────────────────────────────────
    for ion in ["Ca", "Mg", "Na", "K"]:
        g[f"{ion}_meq"] = meq(d[ion], ion)
    for ion in ["Cl", "HCO3", "SO4"]:
        g[f"{ion}_meq"] = meq(d[ion], ion)
    g["NO3_meq"] = d["NO3-N"] / N_EQ
    g["F_meq"] = meq(d["F"], "F") if "F" in d.columns else 0.0

    g["sum_cations_meq"] = g[["Ca_meq", "Mg_meq", "Na_meq", "K_meq"]].sum(axis=1)
    g["sum_anions_meq"] = g[["Cl_meq", "HCO3_meq", "SO4_meq", "NO3_meq", "F_meq"]].sum(axis=1)
    total = g["sum_cations_meq"] + g["sum_anions_meq"]
    g["charge_balance_pct"] = 100.0 * (g["sum_cations_meq"] - g["sum_anions_meq"]) / total
    g["cb_within_tolerance"] = g["charge_balance_pct"].abs() <= CB_TOLERANCE

    cb_ok = int(g["cb_within_tolerance"].sum())
    cb_valid = int(g["charge_balance_pct"].notna().sum())
    print("  [1] CHARGE BALANCE")
    print(f"      median |CBE| = {g['charge_balance_pct'].abs().median():.2f}%")
    print(f"      within +-{CB_TOLERANCE:.0f}% : {cb_ok}/{cb_valid} "
          f"({100*cb_ok/cb_valid:.1f}%)")
    print(f"      within +-5%  : {int((g['charge_balance_pct'].abs()<=5).sum())}/{cb_valid}")

    pd.DataFrame({
        "statistic": ["n_evaluated", "median_abs_CBE_pct", "within_5pct",
                      "within_10pct", "pct_within_10"],
        "value": [cb_valid, round(float(g["charge_balance_pct"].abs().median()), 3),
                  int((g["charge_balance_pct"].abs() <= 5).sum()), cb_ok,
                  round(100 * cb_ok / cb_valid, 1)],
    }).to_csv(OUT_CB, index=False)

    # ── 2. Redox zonation ────────────────────────────────────────────────────
    for c in ["diss O2", "NO3-N", "Mn", "Fe", "SO4"]:
        g[c] = d[c]
    g["redox_zone"] = g.apply(classify_redox, axis=1)

    print("\n  [2] REDOX ZONATION  (McMahon & Chapelle 2008)")
    zone_rows = []
    for zone, n in g["redox_zone"].value_counts().items():
        sub = d.loc[g["redox_zone"] == zone]
        as_med = sub["AsTot"].median()
        as_exc = int((sub["AsTot"] > 10).sum())
        zone_rows.append({
            "redox_zone": zone, "n_wells": int(n),
            "pct_wells": round(100 * n / len(g), 1),
            "median_As_ugL": None if pd.isna(as_med) else round(float(as_med), 2),
            "n_As_above_WHO": as_exc,
            "pct_As_above_WHO": round(100 * as_exc / n, 1),
            "median_Fe_mgL": round(float(sub["Fe"].median()), 3),
            "median_Mn_mgL": round(float(sub["Mn"].median()), 3),
            "median_Eh_mV": None if sub["Eh"].isna().all() else round(float(sub["Eh"].median()), 1),
        })
        print(f"      {zone:34s} n={n:3d} ({100*n/len(g):4.1f}%)  "
              f"As median={as_med:7.2f}  >WHO {as_exc:3d} ({100*as_exc/n:4.1f}%)  "
              f"Fe={sub['Fe'].median():6.3f}")
    pd.DataFrame(zone_rows).sort_values("n_wells", ascending=False).to_csv(OUT_REDOX, index=False)

    # ── 3. Saturation indices ────────────────────────────────────────────────
    # Ionic strength from the major ions, then Davies gammas.
    I = 0.5 * (
        g["Ca_meq"] * 2 + g["Mg_meq"] * 2 + g["Na_meq"] + g["K_meq"]
        + g["Cl_meq"] + g["HCO3_meq"] + g["SO4_meq"] * 2
    ) / 1000.0
    g["ionic_strength_M"] = I
    gamma1, gamma2 = davies_gamma(1, I), davies_gamma(2, I)

    ph = d["pH"]
    hco3_molar = d["HCO3"] / 61018.0                 # mg/L -> mol/L
    co3_molar = hco3_molar * 10 ** (LOGK2_CARBONIC + ph)   # HCO3- -> CO3(2-)
    ca_molar = d["Ca"] / 40078.0
    fe_molar = d["Fe"] / 55845.0

    with np.errstate(divide="ignore", invalid="ignore"):
        g["SI_calcite"] = np.log10(gamma2 * ca_molar * gamma2 * co3_molar) - LOGK_CALCITE
        g["SI_siderite"] = np.log10(gamma2 * fe_molar * gamma2 * co3_molar) - LOGK_SIDERITE

    print("\n  [3] SATURATION INDICES  (SI > 0 oversaturated)")
    for m in ["SI_calcite", "SI_siderite"]:
        v = g[m].replace([np.inf, -np.inf], np.nan).dropna()
        print(f"      {m:12s} median={v.median():+.2f}  "
              f"oversaturated {int((v > 0).sum())}/{len(v)} "
              f"({100*(v > 0).mean():.0f}%)")

    # ── 4. Hydrochemical facies and Gibbs ratios ─────────────────────────────
    g["water_type"] = g.apply(water_type, axis=1)
    denom_cat = g["Na_meq"] + g["Ca_meq"]
    denom_an = g["Cl_meq"] + g["HCO3_meq"]
    g["gibbs_cation_ratio"] = g["Na_meq"] / denom_cat.replace(0, np.nan)
    g["gibbs_anion_ratio"] = g["Cl_meq"] / denom_an.replace(0, np.nan)

    print("\n  [4] HYDROCHEMICAL FACIES")
    types = g["water_type"].value_counts()
    type_rows = []
    for t, n in types.items():
        sub = d.loc[g["water_type"] == t]
        type_rows.append({"water_type": t, "n_wells": int(n),
                          "pct_wells": round(100 * n / len(g), 1),
                          "median_As_ugL": None if sub["AsTot"].isna().all()
                          else round(float(sub["AsTot"].median()), 2)})
        if n >= 5:
            print(f"      {t:12s} n={n:3d} ({100*n/len(g):4.1f}%)  "
                  f"As median={sub['AsTot'].median():7.2f}")
    pd.DataFrame(type_rows).to_csv(OUT_TYPES, index=False)
    print(f"      Gibbs Na/(Na+Ca) median = {g['gibbs_cation_ratio'].median():.3f}  "
          f"Cl/(Cl+HCO3) median = {g['gibbs_anion_ratio'].median():.3f}")

    # ── 5. The link back to the ML result ────────────────────────────────────
    print("\n  [5] WHY Fe AND Mn CARRY THE ARSENIC SIGNAL")
    reducing = g["redox_zone"].isin(["Fe(III)-reducing", "Mn(IV)-reducing",
                                     "sulfate-reducing / methanogenic"])
    as_red = d.loc[reducing, "AsTot"]
    as_ox = d.loc[~reducing, "AsTot"]
    try:
        p = mannwhitneyu(as_red.dropna(), as_ox.dropna(), alternative="greater").pvalue
    except ValueError:
        p = np.nan
    print(f"      reducing zones   n={int(reducing.sum()):3d}  "
          f"As median={as_red.median():7.2f}  >WHO {int((as_red>10).sum())}")
    print(f"      non-reducing     n={int((~reducing).sum()):3d}  "
          f"As median={as_ox.median():7.2f}  >WHO {int((as_ox>10).sum())}")
    print(f"      Mann-Whitney (reducing > rest): p={p:.2e}")

    # ── 6. Arsenic speciation: a check that does NOT confirm the zonation ───
    # As(III) is expected to dominate under reducing conditions. It does not
    # here, and the first version of this check was worse than uninformative:
    # computed over all wells it showed the As(III) fraction *highest* in oxic
    # water. That was an artefact. In low-arsenic wells both AsIII and AsTot sit
    # at their detection limits (both 6.0 ug/L), forcing the ratio to 1.0. The
    # ratio is therefore computed only where both are genuine measurements.
    usable = (d["AsIII"].notna() & d["AsTot"].notna() & (d["AsTot"] > 0)
              & ~d["AsIII_censored"].fillna(False)
              & ~d["AsTot_censored"].fillna(False)
              & ~d["as_speciation_violation"].fillna(False))
    g["AsIII_fraction"] = np.where(usable, d["AsIII"] / d["AsTot"], np.nan)

    print("\n  [6] ARSENIC SPECIATION  (uncensored pairs only)")
    spec_rows = []
    for zone in ["oxic", "Mn(IV)-reducing", "nitrate-reducing",
                 "Fe(III)-reducing", "sulfate-reducing / methanogenic"]:
        sel = (g["redox_zone"] == zone) & g["AsIII_fraction"].notna()
        if sel.sum() == 0:
            continue
        frac = g.loc[sel, "AsIII_fraction"]
        spec_rows.append({"redox_zone": zone, "n": int(sel.sum()),
                          "median_AsIII_fraction": round(float(frac.median()), 3)})
        print(f"      {zone:34s} n={int(sel.sum()):3d}  "
              f"median As(III)/As(total) = {frac.median():.3f}")

    red = g.loc[reducing & g["AsIII_fraction"].notna(), "AsIII_fraction"].dropna()
    oth = g.loc[~reducing & g["AsIII_fraction"].notna(), "AsIII_fraction"].dropna()
    p_spec = np.nan
    if len(red) >= 5 and len(oth) >= 5:
        p_spec = float(mannwhitneyu(red, oth, alternative="greater").pvalue)

    n_usable = int(usable.sum())
    print(f"      usable pairs: {n_usable}/{len(d)} "
          f"(AsIII censored in {int(d['AsIII_censored'].sum())}, "
          f"AsTot in {int(d['AsTot_censored'].sum())})")
    print(f"      Mann-Whitney (reducing > rest): p={p_spec:.3f}")
    print("      -> speciation does NOT track the zonation. Arsenic redox "
          "kinetics are slow,")
    print("         so As(III)/As(V) is often out of equilibrium; speciation is "
          "also unstable")
    print("         between sampling and analysis. Reported as a non-"
          "confirmation, not as support.")

    g.to_csv(OUT_CSV, index=False)
    json.dump({
        "charge_balance": {
            "tolerance_pct": CB_TOLERANCE,
            "n_evaluated": cb_valid,
            "median_abs_pct": round(float(g["charge_balance_pct"].abs().median()), 3),
            "n_within_tolerance": cb_ok,
            "pct_within_tolerance": round(100 * cb_ok / cb_valid, 1),
            "n_within_5pct": int((g["charge_balance_pct"].abs() <= 5).sum()),
        },
        "redox_zonation": {
            "framework": "McMahon & Chapelle (2008)",
            "thresholds_mgL": {"O2": TH_O2, "NO3-N": TH_NO3_N, "Mn": TH_MN,
                               "Fe": TH_FE, "SO4": TH_SO4},
            "zones": zone_rows,
        },
        "saturation_indices": {
            m: {"median": round(float(g[m].replace([np.inf, -np.inf], np.nan).median()), 3),
                "pct_oversaturated": round(float(
                    100 * (g[m].replace([np.inf, -np.inf], np.nan) > 0).mean()), 1)}
            for m in ["SI_calcite", "SI_siderite"]
        },
        "water_types": type_rows,
        "gibbs": {
            "median_Na_over_Na_Ca": round(float(g["gibbs_cation_ratio"].median()), 3),
            "median_Cl_over_Cl_HCO3": round(float(g["gibbs_anion_ratio"].median()), 3),
        },
        "arsenic_speciation": {
            "n_excluded_violation": int(d["as_speciation_violation"].fillna(False).sum()),
            "by_zone": spec_rows,
            "mannwhitney_p_reducing_greater": None if np.isnan(p_spec) else float(p_spec),
            "n_usable_pairs": n_usable,
            "finding": "does not confirm the zonation",
            "note": ("The As(III) fraction does not rise along the reducing "
                     "cascade. Computed over all wells it appeared to fall, but "
                     "that was a censoring artefact: where arsenic is low, AsIII "
                     "and AsTot both sit at a 6.0 ug/L detection limit and the "
                     "ratio is forced to 1.0. Restricted to uncensored pairs the "
                     "gradient is absent. This is consistent with slow arsenic "
                     "redox kinetics and with speciation instability between "
                     "sampling and analysis; it is reported as a non-"
                     "confirmation rather than as support for the zonation."),
        },
        "arsenic_redox_link": {
            "n_reducing": int(reducing.sum()),
            "median_As_reducing": round(float(as_red.median()), 3),
            "median_As_non_reducing": round(float(as_ox.median()), 3),
            "mannwhitney_p_reducing_greater": None if np.isnan(p) else float(p),
            "interpretation": (
                "Arsenic is elevated in Fe(III)- and Mn(IV)-reducing zones, "
                "consistent with release by reductive dissolution of Fe "
                "oxyhydroxides. Fe and Mn are therefore direct indicators of the "
                "mobilising process, which is why adding a field iron kit (tier "
                "E1 -> E2) is what makes the arsenic model work."),
        },
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"\n  Saved -> {OUT_CSV.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> T6 charge balance, T7 redox zonation, T8 water types")
    print("\n  STAGE 3.5 DONE\n")


if __name__ == "__main__":
    main()
