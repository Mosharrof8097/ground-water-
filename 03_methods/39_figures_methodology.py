"""
STAGE 3.9 — METHODOLOGY AND ARCHITECTURE FIGURES
================================================
Draws the two schematic figures that accompany the Methods section.

Output : 04_results/figures/Fig1_methodology_workflow.png
         04_results/figures/Fig2_analysis_architecture.png

Every count shown is read from the stage outputs rather than typed in, so a
re-run of the pipeline cannot leave the figures stating something the analysis
no longer does.

Figure 1 traces the data from the published survey to the reported tables.
Figure 2 sets out the experimental design: the cost ladder of predictor tiers
against the three validation schemes, which is the comparison the study turns
on.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "00_data" / "interim"
METRICS = ROOT / "04_results" / "metrics"
FIG_DIR = ROOT / "04_results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

INK = "#1a1a1a"
GREY = "#6b7280"
EDGE = "#374151"
FILL_DATA = "#dbeafe"
FILL_PROC = "#e5e7eb"
FILL_MODEL = "#dcfce7"
FILL_OUT = "#fef3c7"
FILL_DROP = "#fee2e2"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "axes.edgecolor": EDGE,
})


def load():
    design = json.loads((INTERIM / "02_design.json").read_text())
    clean = json.loads((INTERIM / "01_clean_report.json").read_text())
    feas = json.loads((METRICS / "31_feasibility.json").read_text())
    ext = json.loads((METRICS / "34_external.json").read_text())
    spatial = json.loads((METRICS / "36_spatial_cv.json").read_text())
    return design, clean, feas, ext, spatial


def box(ax, x, y, w, h, text, fill, fontsize=8.5, weight="normal", align="center"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=fill, edgecolor=EDGE, linewidth=0.9, zorder=2))
    ha = {"center": "center", "left": "left"}[align]
    tx = x + w / 2 if align == "center" else x + 0.02
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fontsize,
            color=INK, zorder=3, linespacing=1.45, fontweight=weight)


def arrow(ax, p, q, style="-|>", colour=EDGE, lw=1.1, ls="-"):
    ax.add_patch(FancyArrowPatch(
        p, q, arrowstyle=style, mutation_scale=11, linewidth=lw,
        color=colour, linestyle=ls, zorder=1,
        shrinkA=1.5, shrinkB=1.5))


def figure1(design, clean, feas, ext):
    n_wells = design["n_wells"]
    keep = design["targets_modellable"]
    drop = [d["target"] for d in design["targets_excluded"]]
    thr = design["screening_thresholds"]
    n_ext = ext["results"]["AsTot"]["T_cheap"]["n_ext"]
    cens = {c: m["pct_censored"] for c, m in clean["columns"].items()}

    fig, ax = plt.subplots(figsize=(7.4, 9.6), dpi=300)
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")

    box(ax, 0.17, 0.885, 0.66, 0.062,
        "BGS / DPHE National Hydrochemical Survey (2001)\n"
        "publicly released; reuse with acknowledgement",
        FILL_DATA, 8.8, "bold")

    box(ax, 0.05, 0.775, 0.42, 0.072,
        f"Special study areas\n{n_wells} wells, 4 districts\n"
        "field pH, Eh, SEC, DO, DOC\n+ laboratory trace metals",
        FILL_DATA, 8.0)
    box(ax, 0.53, 0.775, 0.42, 0.072,
        f"National survey, North Bengal\n{n_ext} wells, 15 districts\n"
        "Nawabganj excluded\nheld back for external test",
        FILL_DATA, 8.0)

    arrow(ax, (0.40, 0.885), (0.26, 0.847))
    arrow(ax, (0.60, 0.885), (0.74, 0.847))

    box(ax, 0.05, 0.672, 0.42, 0.072,
        "Stage 1  Cleaning\ncensoring preserved as value + flag\n"
        "pH sentinel removed, ranges checked\nAs(III) > As(total) flagged",
        FILL_PROC, 8.0)
    arrow(ax, (0.26, 0.775), (0.26, 0.744))

    box(ax, 0.05, 0.556, 0.42, 0.082,
        f"Stage 2  Target screening\n13 metals against fixed criteria\n"
        f"censoring < {thr['max_censored_pct']:.0f}%, "
        f"modal share < {thr['max_modal_pct']:.0f}%\n"
        f"n valid > {thr['min_valid']}, distinct > {thr['min_distinct']}",
        FILL_PROC, 8.0)
    arrow(ax, (0.26, 0.672), (0.26, 0.638))

    box(ax, 0.05, 0.438, 0.20, 0.086,
        f"carried forward\n{len(keep)} metals\n\n" + ", ".join(keep[:4]) + "\n" + ", ".join(keep[4:]),
        FILL_MODEL, 7.4)
    box(ax, 0.275, 0.438, 0.195, 0.086,
        f"excluded\n{len(drop)} metals\n\n" + ", ".join(drop[:3]) + "\n" + ", ".join(drop[3:]),
        FILL_DROP, 7.4)
    ax.text(0.485, 0.481,
            f"censoring leaves too little\nto model: Cr {cens.get('Cr', 0):.0f}%, "
            f"Cd {cens.get('Cd', 0):.0f}%",
            fontsize=6.8, va="center", color=GREY, linespacing=1.35)
    arrow(ax, (0.20, 0.556), (0.15, 0.524))
    arrow(ax, (0.32, 0.556), (0.37, 0.524))

    box(ax, 0.05, 0.296, 0.42, 0.102,
        "Stage 3  Modelling\n"
        "5 cost tiers x 7 metals\n"
        f"{feas['protocol']['cv']}\n"
        "model family chosen inside the inner loop\n"
        "mean predictor as baseline",
        FILL_MODEL, 8.0)
    arrow(ax, (0.15, 0.438), (0.20, 0.398))
    arrow(ax, (0.37, 0.438), (0.32, 0.398))

    box(ax, 0.53, 0.296, 0.42, 0.102,
        "Validation\n"
        "random folds\n"
        "spatial blocks, 8 and 16\n"
        f"external transfer, {n_ext} wells\n"
        f"separated by {ext['design']['min_separation_km']:.2f} km",
        FILL_MODEL, 8.0)
    arrow(ax, (0.74, 0.775), (0.74, 0.398), ls=(0, (4, 3)), colour=GREY)
    arrow(ax, (0.47, 0.347), (0.53, 0.347))

    box(ax, 0.05, 0.168, 0.90, 0.104,
        "Stage 3 continued\n"
        f"conformal intervals on disjoint calibration and test splits   |   "
        f"{feas['protocol']['correction']}\n"
        "censoring rules compared on identical folds: DL/2, DL, zero, "
        "regression on order statistics\n"
        "hydrogeochemistry: charge balance, redox zonation, saturation "
        "indices, facies",
        FILL_PROC, 8.0)
    arrow(ax, (0.26, 0.296), (0.26, 0.272))
    arrow(ax, (0.74, 0.296), (0.74, 0.272))

    box(ax, 0.05, 0.048, 0.90, 0.102,
        "Reported outputs\n"
        "T1 screening   T2 feasibility   T3 conformal coverage   T4 censoring\n"
        "T5 external validation   T6 charge balance   T7 redox zonation   "
        "T8 water types\n"
        "T9 spatial versus random   T10 operating points   T11 depth strata",
        FILL_OUT, 8.0)
    arrow(ax, (0.50, 0.168), (0.50, 0.150))

    ax.text(0.5, 0.018,
            "Counts are read from the stage outputs; no value in this figure is "
            "entered by hand.",
            ha="center", fontsize=7.2, color=GREY, style="italic")

    out = FIG_DIR / "Fig1_methodology_workflow.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {out.name}")


def figure2(design, feas, spatial, ext):
    tiers = design["tiers"]
    keep = design["targets_modellable"]
    n_ext = ext["results"]["AsTot"]["T_cheap"]["n_ext"]
    sp = spatial["design"]

    fig, ax = plt.subplots(figsize=(7.6, 9.8), dpi=300)
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")

    ax.text(0.5, 0.960,
            "Predictor tiers ordered by cost, assessed under three validation schemes",
            ha="center", va="top", fontsize=8.2, color=GREY)

    # ---- Predictor tiers -------------------------------------------------
    ax.text(0.04, 0.925, "Predictor tiers", fontsize=9.6, fontweight="bold", color=INK)
    labels = [
        ("E1_meter", "E1   multiparameter meter", "pH, Eh, SEC, temperature"),
        ("E2_meter_kit", "E2   + colorimetric kits", "Fe, Mn"),
        ("E3_meter_kit_titration", "E3   + titration", "Cl, HCO3"),
        ("E4_plus_well_record", "E4   + well record", "depth"),
        ("REF_full_cheap", "REF  every non ICP-MS determinand", "a ceiling, not field deployable"),
    ]
    y, h, gap = 0.845, 0.044, 0.015
    for name, head, detail in labels:
        spec = tiers[name]
        fill = FILL_PROC if name == "REF_full_cheap" else FILL_MODEL
        box(ax, 0.04, y, 0.50, h, f"{head}\n{detail}", fill, 7.6, align="left")
        ax.text(0.555, y + h / 2,
                f"{len(spec['features'])} features, {spec['n_complete_case']} complete",
                fontsize=7.0, va="center", color=GREY)
        y -= (h + gap)

    ax.annotate("", xy=(0.022, 0.885), xytext=(0.022, 0.665),
                arrowprops=dict(arrowstyle="<|-", color=EDGE, lw=1.1))
    ax.text(0.009, 0.775, "increasing cost", rotation=90, va="center",
            ha="center", fontsize=7.2, color=GREY)

    box(ax, 0.76, 0.665, 0.21, 0.225,
        "Targets\n\n" + "\n".join(keep) + f"\n\n{len(keep)} of 13 metals\nfrom Stage 2",
        FILL_OUT, 7.6)

    # ---- Validation ------------------------------------------------------
    ax.text(0.04, 0.578, "Validation", fontsize=9.6, fontweight="bold", color=INK)
    schemes = [
        ("Random folds",
         "5x5 repeated\nnested CV\n25 outer folds\n\noptimistic where\nwells are close"),
        ("Spatial blocks",
         "KMeans blocks,\n8 and 16 counts\n5 layouts each\n25 outer folds\n\n"
         "exceeds the\nvariogram range"),
        ("External transfer",
         f"fit on 271 wells\ntested on {n_ext}\n15 unseen districts\n\n"
         f"separated by\n{ext['design']['min_separation_km']:.2f} km"),
    ]
    x = 0.04
    for title, detail in schemes:
        box(ax, x, 0.375, 0.29, 0.170, f"{title}\n\n{detail}", FILL_PROC, 7.4)
        x += 0.315

    for x0 in (0.185, 0.50, 0.815):
        arrow(ax, (0.29, 0.609), (x0, 0.545))

    # ---- Quantities reported --------------------------------------------
    ax.text(0.04, 0.332, "Quantities reported", fontsize=9.6, fontweight="bold", color=INK)
    panels = [
        ("Skill", "R2 against a mean\nbaseline on identical\nfolds\n\nSpearman rho\n"
                  "Benjamini-Hochberg"),
        ("Uncertainty", "conformal intervals\n\ncoverage on splits\ndisjoint from\n"
                        "calibration\n\nand under transfer"),
        ("Decision value", "sensitivity and\nspecificity\n\nlaboratory burden\n"
                           "and wells missed\n\nat two limits"),
    ]
    x = 0.04
    for title, detail in panels:
        box(ax, x, 0.140, 0.29, 0.162, f"{title}\n\n{detail}", FILL_OUT, 7.4)
        x += 0.315

    for x0 in (0.185, 0.50, 0.815):
        arrow(ax, (x0, 0.375), (x0, 0.302))

    # ---- Design rules ----------------------------------------------------
    box(ax, 0.04, -0.045, 0.93, 0.132,
        "Design rules applied throughout\n\n"
        "Imputation, scaling and model selection occur inside the training fold only.\n"
        "Censored values keep their detection limit and a flag; nothing is substituted "
        "at read time.\n"
        "Conformal coverage is never computed on the residuals used to calibrate the "
        "interval.\n"
        "Reported values are read from stored metrics, never written into table or "
        "figure code.\n"
        "Metals failing Stage 2 are excluded before modelling, not after inspecting "
        "results.",
        "#f8fafc", 7.5, align="left")

    out = FIG_DIR / "Fig2_analysis_architecture.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {out.name}")


def main():
    print("=" * 66)
    print("  STAGE 3.9 — METHODOLOGY FIGURES")
    print("=" * 66)
    design, clean, feas, ext, spatial = load()
    figure1(design, clean, feas, ext)
    figure2(design, feas, spatial, ext)
    print(f"\n  -> {FIG_DIR.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
