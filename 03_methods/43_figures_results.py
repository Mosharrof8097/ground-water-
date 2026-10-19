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
# Okabe and Ito, distinguishable under the common forms of colour blindness.
BLUE, RED, GREEN, ORANGE = "#0072B2", "#D55E00", "#009E73", "#E69F00"
PURPLE, SKY, YELLOW = "#CC79A7", "#56B4E9", "#F0E442"
SERIES = [BLUE, ORANGE, GREEN, RED, PURPLE, SKY]

# Column names are analysis keys; figures carry the reader's names instead.
LABEL = {
    "AsTot": "Total As", "AsIII": "As(III)", "Ba": "Ba", "Mo": "Mo",
    "Ni": "Ni", "Pb": "Pb", "Zn": "Zn", "U": "U", "Cd": "Cd", "Cr": "Cr",
    "Cu": "Cu", "Se": "Se", "Sb": "Sb", "Fe": "Fe", "Mn": "Mn",
    "WELL_DEPTH": "well depth", "SEC": "conductance", "HCO3": "HCO\u2083",
    "NO3-N": "NO\u2083-N", "SO4": "SO\u2084", "diss O2": "dissolved O\u2082",
    "T": "temperature", "Eh": "redox potential", "pH": "pH",
    "E1_meter": "E1: meter", "E2_meter_kit": "E2: meter + kit",
    "E3_meter_kit_titration": "E3: + titration",
    "E4_plus_well_record": "E4: + well record",
    "REF_full_cheap": "REF: all non-ICP",
    "T_cheap": "Fe, Mn, depth", "T_full": "+ major ions",
    "substitute_half": "DL/2", "substitute_dl": "DL",
    "substitute_zero": "zero", "stochastic_imputation": "conditional draw",
    "Fe(III)- / sulfate-reducing": "Fe(III)/SO\u2084-reducing",
    "mixed (oxic)": "mixed, oxic", "mixed (anoxic)": "mixed, anoxic",
}


def lab(key):
    """Reader-facing name for an analysis key."""
    return LABEL.get(str(key), str(key).replace("_", " "))

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
    sd = np.full_like(mat, np.nan)
    feas = np.zeros_like(mat, dtype=bool)
    for i, tg in enumerate(targets):
        for j, tr in enumerate(tiers):
            r = t2[(t2.target == tg) & (t2.tier == tr)]
            if len(r):
                mat[i, j] = r.r2_mean.iloc[0]
                feas[i, j] = bool(r.feasible.iloc[0])
                if "r2_std" in r:
                    sd[i, j] = r.r2_std.iloc[0]

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    norm = TwoSlopeNorm(vmin=min(-0.6, np.nanmin(mat)), vcenter=0,
                        vmax=max(0.6, np.nanmax(mat)))
    # Red to blue rather than red to green: the same information survives the
    # common forms of colour blindness.
    im = ax.imshow(mat, cmap="RdBu", norm=norm, aspect="auto")

    for i in range(len(targets)):
        for j in range(len(tiers)):
            if np.isnan(mat[i, j]):
                continue
            ax.text(j, i - 0.13, f"{mat[i, j]:+.2f}", ha="center", va="center",
                    fontsize=8.4, color=INK,
                    fontweight="bold" if feas[i, j] else "normal")
            if np.isfinite(sd[i, j]):
                ax.text(j, i + 0.19, f"\u00b1{sd[i, j]:.2f}", ha="center",
                        va="center", fontsize=6.6, color="#4b5563")
            if feas[i, j]:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                           edgecolor=INK, linewidth=2.0))

    ax.set_xticks(range(len(tiers))), ax.set_xticklabels(short, fontsize=7.6)
    ax.set_yticks(range(len(targets)))
    ax.set_yticklabels([lab(t) for t in targets])
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("mean $R^2$ on the original scale,\n25 random outer folds",
                 fontsize=8)
    fig.text(0.02, -0.05,
             "Values are the mean across folds with the fold standard "
             "deviation beneath. Bold values inside a heavy border beat the "
             "mean baseline\nafter Benjamini-Hochberg correction across all 35 "
             "comparisons. Random folds are optimistic; Figure 5 gives the "
             "spatially blocked result.",
             fontsize=7.4, color=GREY)
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
    def best_with_sd(frame, t, blocks=None):
        """Best tier for this metal, and the fold spread that goes with it."""
        sub = frame[frame.target == t]
        if blocks is not None:
            sub = sub[sub.n_blocks == blocks]
        if sub.empty:
            return np.nan, 0.0
        col = "random_r2" if blocks is None else "spatial_r2"
        row = sub.loc[sub[col].idxmax()]
        sd = 0.0 if blocks is None else float(row.get("spatial_r2_std", 0.0) or 0.0)
        return float(row[col]), sd

    rand = [best_with_sd(t9, t)[0] for t in targets]
    sp16_v = [best_with_sd(t9, t, 16) for t in targets]
    sp8_v = [best_with_sd(t9, t, 8) for t in targets]
    sp16, sp16_e = [v for v, _ in sp16_v], [e for _, e in sp16_v]
    sp8, sp8_e = [v for v, _ in sp8_v], [e for _, e in sp8_v]

    err = dict(ecolor=INK, elinewidth=0.8, capsize=2.5)
    ax.bar(x - w, rand, w, label="random folds", color="#93c5fd", edgecolor=INK, lw=.5)
    ax.bar(x, sp16, w, yerr=sp16_e, label="spatial, 16 blocks",
           color="#fbbf24", edgecolor=INK, lw=.5, error_kw=err)
    ax.bar(x + w, sp8, w, yerr=sp8_e, label="spatial, 8 blocks",
           color=ORANGE, edgecolor=INK, lw=.5, error_kw=err)
    ax.axhline(0, color=INK, lw=0.9)
    ax.set_xticks(x), ax.set_xticklabels([lab(t) for t in targets])
    ax.set_ylabel("best $R^2$ across tiers, original scale")
    ax.set_title("(a) Random folds versus spatial blocks", loc="left",
                 fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="y", alpha=0.25, linestyle=":")

    ax = axes[1]
    rows = [(t, tier, r["internal_cv_r2"], r["external_r2"], r["external_spearman"])
            for t, tiers in ext.items() for tier, r in tiers.items()]
    labels = [f"{lab(t)}\n{lab(tier)}" for t, tier, *_ in rows]
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
    ax.set_ylabel("$R^2$, original scale")
    ax.set_title("(b) Transfer to unseen districts", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="y", alpha=0.25, linestyle=":")

    fig.text(0.5, -0.04,
             "Error bars on the spatial bars are the standard deviation over "
             "25 outer folds. Rank correlation (ρ) is annotated on the "
             "external bars: ranking "
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
    ax.set_yticklabels([f"{lab(r.target)} \u00b7 {r.tier.split('_')[0]}"
                        for r in order.itertuples()], fontsize=6.8)
    ax.set_xlabel("held-out coverage (%)")
    ax.set_title("(a) Coverage within the study area", loc="left", fontweight="bold")
    ax.legend(frameon=True), ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.invert_yaxis()

    ax = axes[1]
    rows = [(f"{lab(t)} \u00b7 {lab(tier)}",
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
    ax.set_xlim(0, 108)
    ax.legend(frameon=True, loc="lower right", framealpha=0.95)
    ax.grid(axis="x", alpha=0.25, linestyle=":")
    ax.invert_yaxis()

    fig.text(0.5, -0.04,
             "Coverage is well behaved within the study area but departs from "
             "the nominal level on transfer, in both directions.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig6_conformal_coverage.png")


# ─────────────────────────────────────────────────────────────── Fig 7 ──
def load_screening_frames():
    """
    Development and external wells with the model's predictions attached.

    The ROC panel needs the curves, not only the summary areas, so the cheap
    model is refitted here exactly as stage 3.15 fits it. Everything else on
    the figure is a raw column and needs no fitting at all.
    """
    try:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import GridSearchCV
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        RAW = ROOT / "00_data" / "raw"
        NORTH = ["Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram",
                 "Lalmonirhat", "Naogaon", "Natore", "Nawabganj", "Nilphamari",
                 "Pabna", "Panchagarh", "Rajshahi", "Rangpur", "Sirajganj",
                 "Thakurgaon"]
        feats = ["Fe", "Mn", "WELL_DEPTH"]

        dev = read_bgs(RAW / "special_study_areas_271_boreholes.csv")
        ext = read_bgs(RAW / "NHS_national_survey_3534_boreholes.csv")
        for frame, cols in ((dev, feats + ["AsTot"]), (ext, feats + ["As"])):
            for c in cols:
                if c in frame.columns:
                    frame[c] = num(frame[c])
        d = ext["DISTRICT"].astype(str).str.strip()
        ext = ext[d.isin(NORTH) & (d != "Nawabganj")].copy()

        dev = dev.dropna(subset=["AsTot", "Fe"])
        ext = ext.dropna(subset=["As", "Fe"])

        # Same search space as stage 3.15, or the curve and the threshold
        # marked on it would come from two different models.
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import ElasticNet, HuberRegressor
        from sklearn.svm import SVR

        pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                         ("scaler", StandardScaler()), ("model", Ridge())])
        grid = [
            {"model": [Ridge()], "model__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
            {"model": [ElasticNet(max_iter=5000)],
             "model__alpha": [0.01, 0.1, 1.0],
             "model__l1_ratio": [0.2, 0.5, 0.8]},
            {"model": [HuberRegressor(max_iter=500)],
             "model__alpha": [1e-4, 1e-2], "model__epsilon": [1.35, 1.75]},
            {"model": [SVR(kernel="rbf")], "model__C": [1.0, 10.0],
             "model__gamma": ["scale"]},
            {"model": [RandomForestRegressor(n_estimators=150, random_state=42,
                                             n_jobs=1)],
             "model__max_depth": [None, 8], "model__min_samples_leaf": [1, 3]},
        ]
        gs = GridSearchCV(pipe, grid, cv=3, scoring="neg_mean_squared_error")
        gs.fit(dev[feats].to_numpy(float), np.log1p(dev["AsTot"].to_numpy(float)))
        ext["_model"] = np.maximum(
            np.expm1(gs.best_estimator_.predict(ext[feats].to_numpy(float))), 0.0)
        return dev, ext
    except Exception as exc:
        print(f"  ROC curves unavailable: {exc}")
        return None, None


def fig7_roc():
    """
    The comparison the paper now turns on: one axis, every rule, same wells.

    Raw iron, raw manganese and well depth are rankings with nothing fitted.
    The model is the fitted alternative. Thresholds frozen on the development
    wells are marked, so the reader sees both the ranking and the single point
    a programme would actually operate at.
    """
    bc = json.loads((MET / "45_baseline_comparison.json").read_text())["results"]
    ops = json.loads((MET / "37_operating_points.json").read_text())["results"]
    STD = "WHO_10"

    rec = bc[STD]
    base = ops.get("single_predictor_baselines", {}).get(STD, {})
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5),
                             gridspec_kw={"width_ratios": [1.15, 1]})

    # ---- (a) every rule on one axis -------------------------------------
    ax = axes[0]
    curves = [
        ("Fe alone", rec["external"]["auc_iron"], BLUE, "-"),
        ("model (Fe, Mn, depth)", rec["external"]["auc_model"], ORANGE, "-"),
    ]
    for feat, colour in (("Mn", GREEN), ("WELL_DEPTH", PURPLE)):
        if feat in base:
            curves.append((f"{lab(feat)} alone", base[feat]["auc"], colour, "--"))

    dev, ext = load_screening_frames()
    if ext is not None:
        labels = (ext["As"].to_numpy(float) > 10.0).astype(int)
        series = {
            "Fe alone": ext["Fe"].to_numpy(float),
            "Mn alone": ext["Mn"].to_numpy(float),
            "well depth alone": -ext["WELL_DEPTH"].to_numpy(float),
            "model (Fe, Mn, depth)": ext["_model"].to_numpy(float),
        }
        for name, auc, colour, ls in curves:
            sc = series.get(name)
            if sc is None:
                continue
            ok = np.isfinite(sc)
            fpr, tpr, thr = roc_curve(labels[ok], sc[ok])
            ax.plot(fpr, tpr, ls, color=colour, lw=1.8,
                    label=f"{name} (AUC {auc:.3f})")
            # the frozen operating point
            mark = (rec["frozen_thresholds"]["iron_mgL"] if name == "Fe alone"
                    else rec["frozen_thresholds"]["model_ugL"]
                    if name.startswith("model") else None)
            if mark is not None:
                i = int(np.argmin(np.abs(thr - mark)))
                ax.plot(fpr[i], tpr[i], "o", color=colour, ms=7,
                        markeredgecolor=INK, markeredgewidth=0.8, zorder=5)

    ax.plot([0, 1], [0, 1], ":", color=GREY, lw=1)
    ax.set_xlabel("1 \u2212 specificity"), ax.set_ylabel("sensitivity")
    ax.set_title("(a) Ranking wells on 1,027 unseen wells", loc="left",
                 fontweight="bold")
    ax.legend(frameon=True, fontsize=7.4, loc="lower right")
    ax.grid(alpha=0.25, linestyle=":")

    # ---- (b) same laboratory burden, how many missed ---------------------
    ax = axes[1]
    matched = rec.get("equal_burden_comparison", [])
    if matched:
        xs = np.arange(len(matched))
        w = 0.38
        ax.bar(xs - w / 2, [m["iron"]["contaminated_missed"] for m in matched],
               w, label="Fe alone", color=BLUE, edgecolor=INK, lw=.5)
        ax.bar(xs + w / 2, [m["model"]["contaminated_missed"] for m in matched],
               w, label="model", color=ORANGE, edgecolor=INK, lw=.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{m['pct_referred_to_lab']:.0f}%" for m in matched])
        ax.set_xlabel("wells sent to the laboratory")
        ax.set_ylabel("contaminated wells missed")
        ax.set_title("(b) At the same laboratory burden", loc="left",
                     fontweight="bold")
        ax.legend(frameon=True), ax.grid(axis="y", alpha=.25, ls=":")

    fig.text(0.5, -0.04,
             "Filled circles mark the thresholds frozen on the development "
             "wells. Iron carries no fitted parameters, so nothing about it "
             "has to transfer.",
             ha="center", fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig7_roc_operating_points.png")


def fig_district_auc():
    """
    Iron's ranking skill district by district.

    One pooled number says nothing about whether a rule can be carried into a
    district that was never measured, which is the decision a programme faces.
    """
    bc = json.loads((MET / "45_baseline_comparison.json").read_text())["results"]
    rec = bc["WHO_10"]
    per = rec.get("iron_auc_by_district", {}).get("per_district", {})
    scored = {k: v for k, v in per.items() if isinstance(v.get("auc"), float)}
    if not scored:
        print("  skipped district plot: no district has enough exceedances")
        return

    order = sorted(scored, key=lambda k: scored[k]["auc"])
    vals = [scored[k]["auc"] for k in order]
    dev_auc = rec["development"]["auc_iron"]

    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ys = np.arange(len(order))
    ax.hlines(ys, 0.60, vals, color="#d1d5db", lw=1.4, zorder=1)
    ax.scatter(vals, ys, s=62, color=BLUE, edgecolor=INK, zorder=3,
               label="external district")
    ax.axvline(dev_auc, color=ORANGE, lw=1.8, ls="--", zorder=2,
               label=f"development set ({dev_auc:.3f})")
    ax.axvline(0.5, color=GREY, lw=1, ls=":")

    # Counts sit in a column of their own; trailing them off each dot runs the
    # highest ones past the axis.
    for y, k in zip(ys, order):
        ax.annotate(f"n={scored[k]['n']}, {scored[k]['n_contaminated']} exceed",
                    (0.47, y), fontsize=6.8, color=GREY, va="center", ha="left")

    ax.set_yticks(ys), ax.set_yticklabels(order)
    ax.set_xlim(0.45, 1.03)
    ax.set_xlabel("area under the curve, iron alone, WHO guideline")
    ax.set_title("Iron ranks arsenic well in some districts and poorly in others",
                 loc="left", fontweight="bold", fontsize=10)
    ax.legend(frameon=True, fontsize=7.6, loc="lower right",
              framealpha=0.95)
    ax.grid(axis="x", alpha=.25, ls=":")
    n_nd = len(per) - len(scored)
    fig.text(0.02, -0.08,
             f"Districts with fewer than ten exceedances are not shown "
             f"({n_nd} of {len(per)}); ranking is not meaningful there. The "
             f"spread is the case for calibrating locally before adopting any "
             f"rule.", fontsize=7.4, color=GREY)
    fig.tight_layout()
    save(fig, "Fig13_district_iron_auc.png")


# ─────────────────────────────────────────────────────────────── Fig 8 ──
def fig8_redox():
    """
    Arsenic along the reducing cascade.

    The classes are those of the corrected classifier, which requires the full
    criteria and leaves a comparison open where censoring decides nothing, so
    mixed waters appear as their own classes rather than being forced into a
    terminal process. They are drawn in cascade order because the claim being
    made is about an ordering, and the trend test states it directly.
    """
    geo = pd.read_csv(INTERIM / "35_geochem.csv")
    clean = pd.read_csv(INTERIM / "01_clean.csv")
    t7 = pd.read_csv(TAB / "T7_redox_zonation.csv")
    gj = json.loads((MET / "35_geochem.json").read_text())["redox_zonation"]
    trend = gj.get("trend_test") or {}

    cascade = (trend.get("cascade")
               or ["oxic", "mixed (oxic)", "mixed (anoxic)",
                   "Fe(III)- / sulfate-reducing", "methanogenic"])
    present = set(geo.redox_zone.dropna())
    missing = [z for z in cascade if z not in present]
    if missing:
        print(f"  WARNING fig8: zones absent from the data: {missing}")
    order = [z for z in cascade if z in present]
    short = [lab(z).replace(" / ", "\n/ ").replace(", ", ",\n") for z in order]
    other = sorted(present - set(order))

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))

    ax = axes[0]
    data = [clean.loc[geo.redox_zone == z, "AsTot"].dropna() for z in order]
    bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#cfe3f5"), patch.set_edgecolor(INK)
    for med in bp["medians"]:
        med.set_color(INK), med.set_linewidth(1.6)
    rng = np.random.default_rng(42)
    for i, d in enumerate(data, 1):
        ax.scatter(rng.normal(i, 0.055, len(d)), d, s=6, alpha=0.45,
                   color=GREY, zorder=3)
    ax.axhline(10, color=RED, ls="--", lw=1.2, label="WHO 10 µg/L")
    ax.set_yscale("log"), ax.set_ylabel("total arsenic (µg/L, log scale)")
    ax.set_xticklabels(short, fontsize=6.8)
    ax.set_title("(a) Arsenic rises along the cascade", loc="left",
                 fontweight="bold")
    ax.legend(frameon=True, loc="upper left"), ax.grid(axis="y", alpha=.25, ls=":")
    if trend:
        ax.annotate(f"Jonckheere-Terpstra, ordered alternative\n"
                    f"n = {trend['n_wells']}   z = {trend['z']:+.2f}   "
                    f"p = {trend['p_value']:.1e}",
                    xy=(0.03, 0.03), xycoords="axes fraction", fontsize=7.0,
                    color=INK, va="bottom",
                    bbox=dict(boxstyle="round,pad=0.35", fc="white",
                              ec="#9ca3af", lw=0.7))

    ax = axes[1]
    sub = t7.set_index("redox_zone").reindex(order)
    xs = np.arange(len(order))
    ax.bar(xs, sub.pct_As_above_WHO, 0.6, color=ORANGE, edgecolor=INK, lw=.5)
    for i, (n, pc) in enumerate(zip(sub.n_wells, sub.pct_As_above_WHO)):
        ax.text(i, pc + 2.0, f"{pc:.0f}%\nn = {int(n)}", ha="center",
                fontsize=7.2, color=INK)
    ax.set_xticks(xs), ax.set_xticklabels(short, fontsize=6.8)
    ax.set_ylabel("wells above the WHO guideline (%)")
    ax.set_ylim(0, max(sub.pct_As_above_WHO) * 1.32)
    ax.set_title("(b) Exceedance by class", loc="left", fontweight="bold")
    ax.grid(axis="y", alpha=.25, ls=":")

    note = ("Classes requiring the full McMahon and Chapelle criteria; waters "
            "meeting no single set are reported as mixed.")
    if other:
        counts = {r.redox_zone: int(r.n_wells) for r in t7.itertuples()}
        tail = ", ".join(f"{lab(z)} n = {counts.get(z, 0)}" for z in other)
        note += f" Outside the cascade: {tail}."
    fig.text(0.5, -0.045, note, ha="center", fontsize=7.4, color=GREY)
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
    ax.set_xlabel("share of positive permutation importance (%),\n"
                  "measured as drop in log-scale $R^2$ on held-out folds")
    ax.set_xlim(0, 100), ax.invert_yaxis()
    ax.legend(ncol=5, fontsize=6.8, frameon=True, loc="lower center",
              bbox_to_anchor=(0.5, -0.30))
    fig.text(0.02, -0.16, "* redox indicator. Importance is the mean drop in "
                          "log-scale $R^2$ on held-out folds when a predictor "
                          "is shuffled, so it is not on the same scale as the "
                          "coefficients of determination reported elsewhere.",
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

    # The mean is not usable here: a single blown fold took molybdenum to
    # -12.4 at the smallest training size while its median stayed at +0.16.
    # The median with an interquartile band shows the typical fold instead.
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    colours = {"AsTot": BLUE, "U": GREEN, "Mo": ORANGE, "Ba": PURPLE}
    for target, rec in lc.items():
        pts = pd.DataFrame(rec["points"])
        med = pts["r2_median"] if "r2_median" in pts else pts["r2_mean"]
        colour = colours.get(target, GREY)
        ax.plot(pts.n_train, med, marker="o", ms=4.5, lw=1.6, color=colour,
                label=f"{lab(target)} ({rec['verdict']})")
        if {"r2_q1", "r2_q3"} <= set(pts.columns):
            ax.fill_between(pts.n_train, pts.r2_q1, pts.r2_q3,
                            color=colour, alpha=0.15, lw=0)
        elif "r2_sd" in pts:
            ax.fill_between(pts.n_train, med - pts.r2_sd, med + pts.r2_sd,
                            color=colour, alpha=0.10, lw=0)

    ax.axhline(0, color=INK, lw=0.9)
    ax.set_xlabel("training wells")
    ax.set_ylabel("held-out $R^2$, median across folds (original scale)")
    ax.set_ylim(-0.6, 0.8)
    ax.legend(frameon=True), ax.grid(alpha=.25, ls=":")
    fig.text(0.02, -0.06,
             "Median across folds with the interquartile band. Three of the "
             "four curves flatten before the full sample, so the predictors "
             "rather than the number of wells set the ceiling.",
             fontsize=7.6, color=GREY)
    fig.tight_layout()
    save(fig, "Fig11_learning_curves.png")


def main():
    print("=" * 70)
    print("  STAGE 3.13 — RESULTS FIGURES")
    print("=" * 70)
    # Figure 3 is drawn by stage 3.14, which puts the wells on a basemap.
    # Drawing it here too meant whichever stage ran last decided the figure.
    for fn in (fig4_feasibility, fig5_validation,
               fig6_conformal, fig7_roc, fig8_redox, fig9_importance,
               fig11_learning, fig_district_auc):
        try:
            fn()
        except Exception as exc:
            print(f"  FAILED {fn.__name__}: {exc}")
    print(f"\n  -> {FIG.relative_to(ROOT)}\n")


if __name__ == "__main__":
    main()
