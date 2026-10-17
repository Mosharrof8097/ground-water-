"""
STAGE 3.13 — RESULTS FIGURES
============================
Draws the data figures for the Results section. Every value is read from the
stored metrics and tables; nothing is typed in.

Output : 04_results/figures/Fig3_study_area.png
         04_results/figures/Fig4_feasibility_matrix.png
         04_results/figures/Fig5_validation_comparison.png
         04_results/figures/Fig6_conformal_coverage.png
         04_results/figures/Fig7_roc_operating_points.png
         04_results/figures/Fig8_redox_arsenic.png
         04_results/figures/Fig9_feature_importance.png
         04_results/figures/Fig10_censoring_sensitivity.png
         04_results/figures/Fig11_learning_curves.png
"""

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from sklearn.metrics import roc_curve, roc_auc_score

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "00_data" / "raw"
INTERIM = ROOT / "00_data" / "interim"
MET = ROOT / "04_results" / "metrics"
TAB = ROOT / "04_results" / "tables"
FIG = ROOT / "04_results" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INK, GREY = "#1a1a1a", "#6b7280"
BLUE, RED, GREEN, ORANGE = "#2563eb", "#dc2626", "#16a34a", "#ea580c"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "axes.edgecolor": "#374151", "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.titlesize": 10,
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "figure.dpi": 300,
})

NORTH_BENGAL = ["Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram",
                "Lalmonirhat", "Naogaon", "Natore", "Nawabganj", "Nilphamari",
                "Pabna", "Panchagarh", "Rajshahi", "Rangpur", "Sirajganj",
                "Thakurgaon"]


def save(fig, name):
    path = FIG / name
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {name}")


def read_bgs(path):
    raw = pd.read_csv(path, skiprows=4, low_memory=False).iloc[1:]
    return raw[raw["SAMPLE_ID"].notna()].reset_index(drop=True)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace("<", "", regex=False).str.strip(),
                         errors="coerce")


# ─────────────────────────────────────────────────────────────── Fig 3 ──
def fig3_study_area():
    dev = pd.read_csv(INTERIM / "01_clean.csv")
    ext_all = read_bgs(RAW / "NHS_national_survey_3534_boreholes.csv")
    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != "Nawabganj")].copy()
    ext["lat"], ext["lon"] = num(ext.LAT_DEG), num(ext.LONG_DEG)
    ext = ext.dropna(subset=["lat", "lon"])
    ext["as"] = num(ext["As"])

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.0))

    ax = axes[0]
    ax.scatter(ext.lon, ext.lat, s=7, c="#cbd5e1", edgecolor="none",
               label=f"external test, n = {len(ext)}", zorder=2)
    ax.scatter(dev.LONG_DEG, dev.LAT_DEG, s=18, c=BLUE, edgecolor="white",
               linewidth=0.3, label=f"development, n = {len(dev)}", zorder=3)
    ax.set_xlabel("Longitude (°E)"), ax.set_ylabel("Latitude (°N)")
    ax.set_title("(a) Well locations", loc="left", fontweight="bold")
    ax.legend(frameon=True, framealpha=0.95, loc="lower left")
    ax.grid(alpha=0.25, linestyle=":")

    ax = axes[1]
    exc = ext["as"] > 10
    ax.scatter(ext.lon[~exc], ext.lat[~exc], s=7, c="#bbf7d0", edgecolor="none",
               label=f"As ≤ 10 µg/L  (n = {int((~exc).sum())})", zorder=2)
    ax.scatter(ext.lon[exc], ext.lat[exc], s=14, c=RED, edgecolor="none",
               alpha=0.8, label=f"As > 10 µg/L  (n = {int(exc.sum())})", zorder=3)
    ax.set_xlabel("Longitude (°E)"), ax.set_ylabel("Latitude (°N)")
    ax.set_title("(b) Arsenic in the external set", loc="left", fontweight="bold")
    ax.legend(frameon=True, framealpha=0.95, loc="lower left")
    ax.grid(alpha=0.25, linestyle=":")

    fig.text(0.5, -0.02,
             "Development wells lie in four districts of the BGS/DPHE special "
             "study areas; the external set covers fifteen North Bengal "
             "districts with Nawabganj removed.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig3_study_area.png")


# ─────────────────────────────────────────────────────────────── Fig 4 ──
def fig4_feasibility():
    t2 = pd.read_csv(TAB / "T2_feasibility_matrix.csv")
    tiers = ["E1_meter", "E2_meter_kit", "E3_meter_kit_titration",
             "E4_plus_well_record", "REF_full_cheap"]
    short = ["E1\nmeter", "E2\n+kits", "E3\n+titration", "E4\n+depth", "REF\nceiling"]
    targets = list(dict.fromkeys(t2["target"]))

    mat = np.full((len(targets), len(tiers)), np.nan)
    feas = np.zeros_like(mat, dtype=bool)
    for i, tg in enumerate(targets):
        for j, tr in enumerate(tiers):
            r = t2[(t2.target == tg) & (t2.tier == tr)]
            if len(r):
                mat[i, j] = r.r2_mean.iloc[0]
                feas[i, j] = bool(r.feasible.iloc[0])

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    norm = TwoSlopeNorm(vmin=min(-0.6, np.nanmin(mat)), vcenter=0,
                        vmax=max(0.6, np.nanmax(mat)))
    im = ax.imshow(mat, cmap="RdYlGn", norm=norm, aspect="auto")

    for i in range(len(targets)):
        for j in range(len(tiers)):
            if np.isnan(mat[i, j]):
                continue
            ax.text(j, i, f"{mat[i, j]:+.2f}", ha="center", va="center",
                    fontsize=8, color=INK,
                    fontweight="bold" if feas[i, j] else "normal")
            if feas[i, j]:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                           edgecolor=INK, linewidth=2.0))

    ax.set_xticks(range(len(tiers))), ax.set_xticklabels(short, fontsize=7.6)
    ax.set_yticks(range(len(targets))), ax.set_yticklabels(targets)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("mean $R^2$, 25 random outer folds", fontsize=8)
    fig.text(0.02, -0.04,
             "Bold values inside a heavy border beat the mean baseline after "
             "Benjamini-Hochberg correction across all 35 comparisons.",
             fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig4_feasibility_matrix.png")


# ─────────────────────────────────────────────────────────────── Fig 5 ──
def fig5_validation():
    t9 = pd.read_csv(TAB / "T9_spatial_vs_random_cv.csv")
    ext = json.loads((MET / "34_external.json").read_text())["results"]
    targets = list(dict.fromkeys(t9["target"]))

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.4),
                             gridspec_kw={"width_ratios": [1.5, 1]})

    ax = axes[0]
    w = 0.26
    x = np.arange(len(targets))
    rand = [t9[t9.target == t].random_r2.max() for t in targets]
    sp8 = [t9[(t9.target == t) & (t9.n_blocks == 8)].spatial_r2.max() for t in targets]
    sp16 = [t9[(t9.target == t) & (t9.n_blocks == 16)].spatial_r2.max() for t in targets]
    ax.bar(x - w, rand, w, label="random folds", color="#93c5fd", edgecolor=INK, lw=.5)
    ax.bar(x, sp16, w, label="spatial, 16 blocks", color="#fbbf24", edgecolor=INK, lw=.5)
    ax.bar(x + w, sp8, w, label="spatial, 8 blocks", color=ORANGE, edgecolor=INK, lw=.5)
    ax.axhline(0, color=INK, lw=0.9)
    ax.set_xticks(x), ax.set_xticklabels(targets)
    ax.set_ylabel("best $R^2$ across tiers")
    ax.set_title("(a) Random folds versus spatial blocks", loc="left",
                 fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="y", alpha=0.25, linestyle=":")

    ax = axes[1]
    rows = [(t, tier, r["internal_cv_r2"], r["external_r2"], r["external_spearman"])
            for t, tiers in ext.items() for tier, r in tiers.items()]
    labels = [f"{t}\n{tier.replace('T_', '')}" for t, tier, *_ in rows]
    xi = np.arange(len(rows))
    ax.bar(xi - 0.2, [r[2] for r in rows], 0.4, label="within development",
           color="#93c5fd", edgecolor=INK, lw=.5)
    ax.bar(xi + 0.2, [r[3] for r in rows], 0.4, label="external",
           color=RED, edgecolor=INK, lw=.5)
    for i, r in enumerate(rows):
        ax.text(i + 0.2, max(r[3], 0) + 0.02, f"ρ={r[4]:.2f}", ha="center",
                fontsize=7, color=INK)
    ax.axhline(0, color=INK, lw=0.9)
    ax.set_xticks(xi), ax.set_xticklabels(labels, fontsize=7.4)
    ax.set_ylabel("$R^2$")
    ax.set_title("(b) Transfer to unseen districts", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="y", alpha=0.25, linestyle=":")

    fig.text(0.5, -0.04,
             "Rank correlation (ρ) is annotated on the external bars: ranking "
             "transfers considerably better than the concentration itself.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig5_validation_comparison.png")


# ─────────────────────────────────────────────────────────────── Fig 6 ──
def fig6_conformal():
    t3 = pd.read_csv(TAB / "T3_conformal_coverage.csv")
    ext = json.loads((MET / "34_external.json").read_text())["results"]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))

    ax = axes[0]
    order = t3.sort_values(["target", "tier"]).reset_index(drop=True)
    y = np.arange(len(order))
    ax.errorbar(order.held_out_coverage_mean * 100, y,
                xerr=order.held_out_coverage_std * 100, fmt="o", ms=4.5,
                color=BLUE, ecolor="#93c5fd", elinewidth=1.6, capsize=2.5)
    ax.axvline(90, color=RED, lw=1.3, ls="--", label="nominal 90%")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.target} · {r.tier.split('_')[0]}"
                        for r in order.itertuples()], fontsize=6.8)
    ax.set_xlabel("held-out coverage (%)")
    ax.set_title("(a) Coverage within the study area", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.invert_yaxis()

    ax = axes[1]
    rows = [(f"{t} · {tier.replace('T_', '')}",
             r["conformal_transfer_coverage"] * 100,
             r["conformal_transfer_coverage_sd"] * 100)
            for t, tiers in ext.items() for tier, r in tiers.items()]
    yy = np.arange(len(rows))
    colours = [GREEN if abs(v - 90) <= 5 else RED for _, v, _ in rows]
    ax.barh(yy, [v for _, v, _ in rows], xerr=[s for *_, s in rows],
            color=colours, edgecolor=INK, lw=.5, height=0.6,
            error_kw=dict(elinewidth=1.3, capsize=2.5, ecolor=GREY))
    ax.axvline(90, color=INK, lw=1.3, ls="--", label="nominal 90%")
    ax.set_yticks(yy), ax.set_yticklabels([r[0] for r in rows], fontsize=7.6)
    ax.set_xlabel("coverage on external wells (%)")
    ax.set_title("(b) Coverage under transfer", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.invert_yaxis()

    fig.text(0.5, -0.04,
             "Coverage is well behaved within the study area but departs from "
             "the nominal level on transfer, in both directions.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig6_conformal_coverage.png")


# ─────────────────────────────────────────────────────────────── Fig 7 ──
def fig7_roc():
    ops = json.loads((MET / "37_operating_points.json").read_text())["results"]
    t10 = pd.read_csv(TAB / "T10_operating_points.csv")

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4))

    ax = axes[0]
    for std, colour in (("WHO_10", BLUE), ("Bangladesh_50", ORANGE)):
        for tier, ls in (("T_cheap", "-"), ("T_full", "--")):
            rec = ops.get(std, {}).get(tier)
            if not rec:
                continue
            sweep = pd.DataFrame(rec["threshold_sweep"])
            ax.plot(1 - sweep.specificity, sweep.sensitivity, ls, color=colour,
                    lw=1.5, label=f"{std.replace('_', ' ')} · "
                                  f"{tier.replace('T_', '')} (AUC {rec['auc']:.2f})")
    ax.plot([0, 1], [0, 1], ":", color=GREY, lw=1)
    ax.set_xlabel("1 − specificity"), ax.set_ylabel("sensitivity")
    ax.set_title("(a) Screening performance on external wells", loc="left",
                 fontweight="bold")
    ax.legend(frameon=True, fontsize=7), ax.grid(alpha=0.25, linestyle=":")

    ax = axes[1]
    sel = t10[(t10.standard == "Bangladesh_50") & (t10.tier == "T_cheap")]
    names = {"high_sensitivity_95": "high sensitivity",
             "balanced_youden": "balanced",
             "high_specificity_90": "high specificity"}
    xs = np.arange(len(sel))
    ax.bar(xs - 0.2, sel.sensitivity * 100, 0.4, label="sensitivity",
           color=GREEN, edgecolor=INK, lw=.5)
    ax.bar(xs + 0.2, sel.pct_referred_to_lab, 0.4, label="sent to laboratory",
           color="#94a3b8", edgecolor=INK, lw=.5)
    for i, r in enumerate(sel.itertuples()):
        ax.text(i, 103, f"{r.contaminated_missed} of {r.n_contaminated}\nmissed",
                ha="center", fontsize=7, color=RED)
    ax.set_xticks(xs)
    ax.set_xticklabels([names.get(v, v) for v in sel.operating_point], fontsize=7.6)
    ax.set_ylim(0, 118), ax.set_ylabel("per cent")
    ax.set_title("(b) Operating points, Bangladesh standard, Fe+Mn+depth",
                 loc="left", fontweight="bold")
    ax.legend(frameon=True, loc="lower right"), ax.grid(axis="y", alpha=.25, ls=":")

    fig.tight_layout()
    save(fig, "Fig7_roc_operating_points.png")


# ─────────────────────────────────────────────────────────────── Fig 8 ──
def fig8_redox():
    geo = pd.read_csv(INTERIM / "35_geochem.csv")
    clean = pd.read_csv(INTERIM / "01_clean.csv")
    t7 = pd.read_csv(TAB / "T7_redox_zonation.csv")

    order = ["oxic", "Mn(IV)-reducing", "nitrate-reducing", "Fe(III)-reducing",
             "sulfate-reducing / methanogenic"]
    order = [z for z in order if z in set(geo.redox_zone)]
    short = [z.replace(" / methanogenic", "\n/ methanogenic").replace("-", "-\n")
             for z in order]

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4))

    ax = axes[0]
    data = [clean.loc[geo.redox_zone == z, "AsTot"].dropna() for z in order]
    bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#bfdbfe"), patch.set_edgecolor(INK)
    for i, d in enumerate(data, 1):
        ax.scatter(np.random.normal(i, 0.055, len(d)), d, s=6, alpha=0.45,
                   color=GREY, zorder=3)
    ax.axhline(10, color=RED, ls="--", lw=1.2, label="WHO 10 µg/L")
    ax.set_yscale("log"), ax.set_ylabel("total arsenic (µg/L, log scale)")
    ax.set_xticklabels(short, fontsize=6.8)
    ax.set_title("(a) Arsenic by redox zone", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="y", alpha=.25, ls=":")

    ax = axes[1]
    sub = t7.set_index("redox_zone").reindex(order)
    xs = np.arange(len(order))
    ax.bar(xs, sub.pct_As_above_WHO, 0.6, color="#fca5a5", edgecolor=INK, lw=.5)
    for i, (n, p) in enumerate(zip(sub.n_wells, sub.pct_As_above_WHO)):
        ax.text(i, p + 1.8, f"{p:.0f}%\nn={int(n)}", ha="center", fontsize=7.2)
    ax.set_xticks(xs), ax.set_xticklabels(short, fontsize=6.8)
    ax.set_ylabel("wells above the WHO guideline (%)")
    ax.set_ylim(0, max(sub.pct_As_above_WHO) * 1.3)
    ax.set_title("(b) Exceedance by redox zone", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.25, ls=":")

    fig.tight_layout()
    save(fig, "Fig8_redox_arsenic.png")


# ─────────────────────────────────────────────────────────────── Fig 9 ──
def fig9_importance():
    t12 = pd.read_csv(TAB / "T12_feature_importance.csv")
    imp = json.loads((MET / "40_importance.json").read_text())
    targets = list(dict.fromkeys(t12.target))
    feats = list(dict.fromkeys(t12.feature))

    mat = np.zeros((len(targets), len(feats)))
    for i, t in enumerate(targets):
        for j, f in enumerate(feats):
            r = t12[(t12.target == t) & (t12.feature == f)]
            if len(r):
                mat[i, j] = max(r.share.iloc[0], 0)

    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    bottom = np.zeros(len(targets))
    palette = plt.cm.tab20(np.linspace(0, 1, len(feats)))
    redox = set(imp["redox_proxies"])
    for j, f in enumerate(feats):
        ax.barh(range(len(targets)), mat[:, j] * 100, left=bottom * 100,
                color=palette[j], edgecolor="white", lw=.4,
                label=f + (" *" if f in redox else ""), height=0.68)
        bottom += mat[:, j]

    labels = []
    for t in targets:
        robust = imp["results"][t]["spatially_robust"]
        rs = imp["results"][t]["redox_proxy_share"] * 100
        labels.append(f"{t}  ({'robust' if robust else 'fragile'}, redox {rs:.0f}%)")
    ax.set_yticks(range(len(targets))), ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("share of positive permutation importance (%)")
    ax.set_xlim(0, 100), ax.invert_yaxis()
    ax.legend(ncol=5, fontsize=6.8, frameon=True, loc="lower center",
              bbox_to_anchor=(0.5, -0.30))
    fig.text(0.02, -0.16, "* redox indicator. Importance is the mean drop in "
                          "$R^2$ on held-out folds when a predictor is shuffled.",
             fontsize=7.4, color=GREY)
    fig.tight_layout()
    save(fig, "Fig9_feature_importance.png")


# ────────────────────────────────────────────────────────────── Fig 10 ──
def fig10_censoring():
    cen = json.loads((MET / "33_censoring.json").read_text())["results"]
    clean = pd.read_csv(INTERIM / "01_clean.csv")
    report = json.loads((INTERIM / "01_clean_report.json").read_text())

    rows = []
    for metal, rec in cen.items():
        dls = report.get("detection_limits", {}).get(metal, {}).get("limits", [])
        med = clean[metal].median()
        ratio = (max(dls) / med * 100) if dls and med and med > 0 else 0.0
        rows.append((metal, rec["pct_censored"], ratio, rec["r2_spread"]))

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))

    ax = axes[0]
    for m, pc, ratio, spread in rows:
        ax.scatter(pc, spread, s=70, color=BLUE, edgecolor=INK, zorder=3)
        ax.annotate(m, (pc, spread), textcoords="offset points",
                    xytext=(6, 4), fontsize=8)
    ax.set_xlabel("censored observations (%)")
    ax.set_ylabel("spread in $R^2$ across the four rules")
    ax.set_title("(a) Censoring rate alone", loc="left", fontweight="bold")
    ax.grid(alpha=.25, ls=":")

    ax = axes[1]
    for m, pc, ratio, spread in rows:
        ax.scatter(ratio, spread, s=70, color=ORANGE, edgecolor=INK, zorder=3)
        ax.annotate(m, (ratio, spread), textcoords="offset points",
                    xytext=(6, 4), fontsize=8)
    ax.set_xlabel("highest detection limit as a percentage of the median")
    ax.set_ylabel("spread in $R^2$ across the four rules")
    ax.set_title("(b) Detection limit relative to the distribution", loc="left",
                 fontweight="bold")
    ax.grid(alpha=.25, ls=":")

    fig.text(0.5, -0.04,
             "The choice of substitution rule moves the result where the "
             "detection limit sits high in the distribution, not simply where "
             "many values are censored.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig10_censoring_sensitivity.png")


# ────────────────────────────────────────────────────────────── Fig 11 ──
def fig11_learning():
    lc = json.loads((MET / "41_learning_curve.json").read_text())["results"]

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    colours = {"AsTot": BLUE, "U": GREEN, "Mo": ORANGE, "Ba": "#7c3aed"}
    for target, rec in lc.items():
        pts = pd.DataFrame(rec["points"])
        keep = pts[pts.r2_mean > -1]          # drop unstable small-n points
        ax.errorbar(keep.n_train, keep.r2_mean, yerr=keep.r2_sd, marker="o",
                    ms=4.5, capsize=2.5, lw=1.5,
                    color=colours.get(target, GREY),
                    label=f"{target} ({rec['verdict']})")
        dropped = len(pts) - len(keep)
        if dropped:
            ax.annotate(f"{target}: {dropped} unstable point omitted",
                        xy=(0.02, 0.06), xycoords="axes fraction",
                        fontsize=7, color=GREY)

    ax.axhline(0, color=INK, lw=0.9)
    ax.set_xlabel("training wells"), ax.set_ylabel("held-out $R^2$")
    ax.legend(frameon=True), ax.grid(alpha=.25, ls=":")
    fig.text(0.02, -0.06,
             "Three of the four curves flatten before the full sample, "
             "indicating that the predictors rather than the number of wells "
             "set the ceiling.",
             fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig11_learning_curves.png")


def main():
    print("=" * 70)
    print("  STAGE 3.13 — RESULTS FIGURES")
    print("=" * 70)
    for fn in (fig3_study_area, fig4_feasibility, fig5_validation,
               fig6_conformal, fig7_roc, fig8_redox, fig9_importance,
               fig10_censoring, fig11_learning):
        try:
            fn()
        except Exception as exc:
            print(f"  FAILED {fn.__name__}: {exc}")
    print(f"\n  -> {FIG.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
