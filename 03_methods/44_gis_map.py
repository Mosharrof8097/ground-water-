"""
STAGE 3.14 — STUDY AREA MAP AND SPATIAL STATISTICS
==================================================
Replaces the bare scatter plot of Figure 3 with a map carrying the national
boundary, district lines, rivers and the sea, and adds the spatial
autocorrelation statistic a reviewer will expect alongside the variogram.

Input  : 00_data/raw/bangladesh_coastline_and_districts.csv
         00_data/raw/bangladesh_surface_geology.csv
         00_data/interim/01_clean.csv
         00_data/raw/NHS_national_survey_3534_boreholes.csv
Output : 04_results/figures/Fig3_study_area.png      (replaced)
         04_results/figures/Fig12_geology_arsenic.png
         04_results/metrics/44_spatial_statistics.json
         04_results/tables/T14_geology_arsenic.csv

The boundary file encodes feature type in a third column, with blank lines
marking discontinuities between separate line segments, so each segment is
drawn separately rather than joined across gaps.

Moran's I is computed on log-transformed arsenic using inverse distance
weights within a fixed radius, with significance assessed by permutation. It
complements the variogram of stage 3.6: the variogram describes how
similarity decays with separation, while Moran's I gives a single statistic
with a reference distribution, which is the form most readers expect.
"""

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "00_data" / "raw"
INTERIM = ROOT / "00_data" / "interim"
FIG = ROOT / "04_results" / "figures"
MET = ROOT / "04_results" / "metrics"
TAB = ROOT / "04_results" / "tables"
for p in (FIG, MET, TAB):
    p.mkdir(parents=True, exist_ok=True)

INK, GREY = "#1a1a1a", "#6b7280"
# Okabe and Ito, so the map survives the common forms of colour blindness.
BLUE, RED, GREEN = "#0072B2", "#D55E00", "#009E73"
SEA, RIVER, DISTRICT, BORDER = "#dbeafe", "#60a5fa", "#d1d5db", "#4b5563"

NORTH_BENGAL = ["Bogra", "Dinajpur", "Gaibandha", "Jaipurhat", "Kurigram",
                "Lalmonirhat", "Naogaon", "Natore", "Nawabganj", "Nilphamari",
                "Pabna", "Panchagarh", "Rajshahi", "Rangpur", "Sirajganj",
                "Thakurgaon"]
EARTH_R = 6371.0
MORAN_RADIUS_KM = 10.0
MORAN_PERMUTATIONS = 999

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "axes.edgecolor": "#374151", "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.6,
    "figure.dpi": 300,
})


def load_basemap():
    """Return {feature type: [segments]}, each segment an (lon, lat) array."""
    rows = []
    with open(RAW / "bangladesh_coastline_and_districts.csv", encoding="utf-8",
              errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("'") or line.lower().startswith("longitude"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                rows.append(None)                 # discontinuity
                continue
            try:
                rows.append((float(parts[0]), float(parts[1]), int(float(parts[2]))))
            except ValueError:
                rows.append(None)

    features, current, current_type = {}, [], None
    for row in rows + [None]:
        if row is None:
            if current and current_type is not None:
                features.setdefault(current_type, []).append(np.array(current))
            current, current_type = [], None
            continue
        lon, lat, kind = row
        if current_type is not None and kind != current_type:
            features.setdefault(current_type, []).append(np.array(current))
            current = []
        current_type = kind
        current.append((lon, lat))
    return features


def draw_basemap(ax, features, extent=None):
    for seg in features.get(3, []):                       # sea
        ax.fill(seg[:, 0], seg[:, 1], color=SEA, zorder=0, lw=0)
    for seg in features.get(4, []):                       # islands
        ax.fill(seg[:, 0], seg[:, 1], color="white", ec=BORDER, lw=0.3, zorder=1)
    for seg in features.get(2, []):                       # rivers
        ax.plot(seg[:, 0], seg[:, 1], color=RIVER, lw=0.5, zorder=1, alpha=0.75)
    for seg in features.get(1, []):                       # districts
        ax.plot(seg[:, 0], seg[:, 1], color=DISTRICT, lw=0.4, zorder=1)
    for seg in features.get(0, []):                       # national boundary
        ax.plot(seg[:, 0], seg[:, 1], color=BORDER, lw=0.9, zorder=2)
    if extent:
        ax.set_xlim(extent[0], extent[1]), ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(1.0 / np.cos(np.radians(24)))


def read_bgs(path):
    raw = pd.read_csv(path, skiprows=4, low_memory=False).iloc[1:]
    return raw[raw["SAMPLE_ID"].notna()].reset_index(drop=True)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace("<", "", regex=False).str.strip(),
                         errors="coerce")


def pairwise_km(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    a = (np.sin((la[None, :] - la[:, None]) / 2) ** 2
         + np.cos(la[:, None]) * np.cos(la[None, :])
         * np.sin((lo[None, :] - lo[:, None]) / 2) ** 2)
    return 2 * EARTH_R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def morans_i(values, lat, lon, radius_km, n_perm, seed=42):
    """Moran's I with inverse distance weights inside a fixed radius."""
    d = pairwise_km(lat, lon)
    with np.errstate(divide="ignore"):
        w = np.where((d > 0) & (d <= radius_km), 1.0 / np.maximum(d, 1e-6), 0.0)
    np.fill_diagonal(w, 0.0)
    if w.sum() == 0:
        return None

    z = values - values.mean()
    denom = (z ** 2).sum()

    def statistic(zz):
        return (len(zz) / w.sum()) * (zz @ w @ zz) / denom

    observed = statistic(z)
    rng = np.random.default_rng(seed)
    null = np.array([statistic(rng.permutation(z)) for _ in range(n_perm)])
    p = (np.sum(np.abs(null) >= abs(observed)) + 1) / (n_perm + 1)
    return {
        "radius_km": radius_km,
        "morans_I": round(float(observed), 4),
        "expected_I": round(-1.0 / (len(z) - 1), 4),
        "p_permutation": round(float(p), 4),
        "n_permutations": n_perm,
        "mean_neighbours": round(float((w > 0).sum(axis=1).mean()), 1),
    }


def figure3(features):
    dev = pd.read_csv(INTERIM / "01_clean.csv")
    ext_all = read_bgs(RAW / "NHS_national_survey_3534_boreholes.csv")
    district = ext_all["DISTRICT"].astype(str).str.strip()
    ext = ext_all[district.isin(NORTH_BENGAL) & (district != "Nawabganj")].copy()
    ext["lat"], ext["lon"], ext["as"] = num(ext.LAT_DEG), num(ext.LONG_DEG), num(ext["As"])
    ext = ext.dropna(subset=["lat", "lon"])

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 5.6))

    ax = axes[0]
    draw_basemap(ax, features, extent=(87.8, 92.8, 20.5, 26.8))
    ax.scatter(ext.lon, ext.lat, s=8, c="#9ca3af", edgecolor="none",
               label=f"external test, n = {len(ext)}", zorder=4)
    ax.scatter(dev.LONG_DEG, dev.LAT_DEG, s=20, c=BLUE, edgecolor="white",
               linewidth=0.35, label=f"development, n = {len(dev)}", zorder=5)
    ax.set_xlabel("Longitude (°E)"), ax.set_ylabel("Latitude (°N)")
    ax.set_title("(a) Well locations", loc="left", fontweight="bold", fontsize=10)
    ax.legend(frameon=True, framealpha=0.95, loc="lower left")

    # The pre-Holocene terraces are where arsenic is almost uniformly at the
    # limit. Marking them shows what the stratified area under the curve in
    # Section 3.13 is separating, rather than leaving it to the reader.
    PRE_HOLOCENE = ("Barind Clay Residuum", "Madhupur Clay Residuum",
                    "Old gravelly sand", "Dihing & Dupi Tila undivi")
    try:
        geo_units = pd.read_csv(RAW / "bangladesh_surface_geology.csv")
        ext = ext.merge(geo_units[["SAMPLE_ID", "GEOL_UNIT"]],
                        on="SAMPLE_ID", how="left")
        pre = ext["GEOL_UNIT"].isin(PRE_HOLOCENE).to_numpy()
    except Exception as exc_err:
        print(f"  surface geology not joined: {exc_err}")
        pre = np.zeros(len(ext), dtype=bool)

    ax = axes[1]
    draw_basemap(ax, features, extent=(87.8, 90.5, 23.4, 26.8))
    exc = (ext["as"] > 10).to_numpy()

    if pre.any():
        ax.scatter(ext.lon[pre], ext.lat[pre], s=42, facecolor="#e5e7eb",
                   edgecolor="#9ca3af", linewidth=0.5, zorder=3,
                   label=f"pre-Holocene setting  (n = {int(pre.sum())})")
    ax.scatter(ext.lon[~exc], ext.lat[~exc], s=9, c=GREEN, alpha=0.65,
               edgecolor="none", label=f"As ≤ 10 µg/L  (n = {int((~exc).sum())})",
               zorder=4)
    ax.scatter(ext.lon[exc], ext.lat[exc], s=16, c=RED, alpha=0.85,
               edgecolor="none", label=f"As > 10 µg/L  (n = {int(exc.sum())})",
               zorder=5)
    ax.set_xlabel("Longitude (°E)"), ax.set_ylabel("Latitude (°N)")
    ax.set_title("(b) Arsenic and geological setting, North Bengal", loc="left",
                 fontweight="bold", fontsize=10)
    ax.legend(frameon=True, framealpha=0.95, loc="lower left", fontsize=7.4)

    fig.text(0.5, 0.015,
             "Boundaries, rivers and coastline from the BGS Bangladesh "
             "reference files. Development wells occupy four special study "
             "areas; the external set covers fifteen North Bengal districts "
             "with Nawabganj removed.",
             ha="center", fontsize=7.4, color=GREY)
    fig.tight_layout(rect=(0, 0.035, 1, 0.97))
    fig.savefig(FIG / "Fig3_study_area.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("  saved Fig3_study_area.png  (with basemap)")


def figure12_geology():
    geo = pd.read_csv(RAW / "bangladesh_surface_geology.csv")
    nat = read_bgs(RAW / "NHS_national_survey_3534_boreholes.csv")
    nat["as"] = num(nat["As"])
    merged = nat.merge(geo[["SAMPLE_ID", "GEOL_UNIT", "LITHOLOGY"]],
                       on="SAMPLE_ID", how="inner").dropna(subset=["as"])

    grp = (merged.groupby("GEOL_UNIT")["as"]
           .agg(n="size", median="median",
                above=lambda s: int((s > 10).sum()))
           .reset_index())
    grp["pct_above"] = (100 * grp["above"] / grp["n"]).round(1)
    grp = grp[grp["n"] >= 30].sort_values("median", ascending=False)
    grp.to_csv(TAB / "T14_geology_arsenic.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    y = np.arange(len(grp))
    ax.barh(y, grp["median"], color="#93c5fd", edgecolor=INK, lw=0.5, height=0.66)
    for i, r in enumerate(grp.itertuples()):
        ax.text(r.median + max(grp["median"]) * 0.015, i,
                f"{r.pct_above:.0f}% above WHO   n={r.n}",
                va="center", fontsize=7.2, color=INK)
    ax.axvline(10, color=RED, ls="--", lw=1.2, label="WHO 10 µg/L")
    ax.set_yticks(y), ax.set_yticklabels(grp["GEOL_UNIT"], fontsize=7.6)
    ax.set_xlabel("median total arsenic (µg/L)")
    ax.set_xlim(0, max(grp["median"]) * 1.55)
    ax.invert_yaxis()
    ax.legend(frameon=True), ax.grid(axis="x", alpha=0.25, ls=":")
    fig.text(0.02, -0.04,
             "Units represented by at least 30 wells. Geological "
             "classification after Alam et al. (1990), as supplied with the "
             "survey.", fontsize=7.4, color=GREY)
    fig.tight_layout()
    fig.savefig(FIG / "Fig12_geology_arsenic.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("  saved Fig12_geology_arsenic.png")
    return grp


def main():
    print("=" * 72)
    print("  STAGE 3.14 — STUDY AREA MAP AND SPATIAL STATISTICS")
    print("=" * 72)

    features = load_basemap()
    print("  basemap segments: " + ", ".join(
        f"{k}:{len(v)}" for k, v in sorted(features.items())))

    figure3(features)
    grp = figure12_geology()

    # ── Moran's I on the development wells ──────────────────────────────────
    dev = pd.read_csv(INTERIM / "01_clean.csv").dropna(
        subset=["AsTot", "LAT_DEG", "LONG_DEG"])
    mi = morans_i(np.log1p(dev["AsTot"].to_numpy()),
                  dev["LAT_DEG"].to_numpy(), dev["LONG_DEG"].to_numpy(),
                  MORAN_RADIUS_KM, MORAN_PERMUTATIONS)
    print(f"\n  Moran's I, log arsenic, {MORAN_RADIUS_KM:.0f} km radius:")
    print(f"    I = {mi['morans_I']:+.4f}  (expected {mi['expected_I']:+.4f})  "
          f"p = {mi['p_permutation']:.4f}  mean neighbours {mi['mean_neighbours']}")
    verdict = ("significant positive clustering" if mi["p_permutation"] < 0.05
               and mi["morans_I"] > mi["expected_I"] else
               "no significant spatial autocorrelation at this scale")
    print(f"    -> {verdict}")

    json.dump({
        "morans_I_arsenic_development": {**mi, "verdict": verdict,
                                         "transform": "log1p"},
        "basemap_source": ("BGS Bangladesh coastline and districts reference "
                           "file; approximate, not for precise mapping"),
        "geology_source": ("BGS surface geology classification of survey sites "
                           "after Alam et al. (1990)"),
        "geology_units_reported": int(len(grp)),
        "note": ("Moran's I complements the variogram of stage 3.6 by giving a "
                 "single statistic with a permutation reference distribution."),
    }, open(MET / "44_spatial_statistics.json", "w"), indent=2)

    print(f"\n  Saved -> 04_results/metrics/44_spatial_statistics.json")
    print(f"  Saved -> 04_results/tables/T14_geology_arsenic.csv")
    print("\n  STAGE 3.14 DONE\n")


if __name__ == "__main__":
    main()
