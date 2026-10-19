"""
STAGE 3.11 — LEARNING CURVES
============================
Would more wells help, or has performance reached what these predictors can
give?

Input  : 00_data/interim/02_features.csv, 02_design.json
Output : 04_results/metrics/41_learning_curve.json
         04_results/tables/T13_learning_curve.csv

A sample of 271 invites the objection that the study is simply too small, and
that objection deserves an answer rather than an apology. Training subsets of
increasing size are drawn and scored on a held-out portion that stays fixed in
size throughout, so the only quantity varying is how much the model has seen.

Reading the result: a curve still climbing at the full sample size means the
ceiling is the data, and collecting more wells would pay. A curve that has
flattened means the ceiling is the predictors, and more wells of the same kind
would not help. The two carry quite different implications for a monitoring
programme, and only the first is a limitation of this study rather than of the
approach.

Run on the targets that survive spatial validation, since a learning curve for
a target with no reliable signal describes nothing.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, HuberRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "00_data" / "interim" / "02_features.csv"
IN_DESIGN = ROOT / "00_data" / "interim" / "02_design.json"
IN_SPATIAL = ROOT / "04_results" / "metrics" / "36_spatial_cv.json"
OUT_METRICS = ROOT / "04_results" / "metrics" / "41_learning_curve.json"
OUT_TABLE = ROOT / "04_results" / "tables" / "T13_learning_curve.csv"

TIER = "E4_plus_well_record"
FRACTIONS = [0.25, 0.40, 0.55, 0.70, 0.85, 1.00]
TEST_FRACTION = 0.25
N_REPEATS, SEED, N_JOBS = 40, 42, 4

PARAM_GRID = [
    {"model": [Ridge()], "model__alpha": [0.01, 0.1, 1.0, 10.0, 100.0]},
    {"model": [ElasticNet(max_iter=5000)],
     "model__alpha": [0.01, 0.1, 1.0], "model__l1_ratio": [0.2, 0.5, 0.8]},
    {"model": [HuberRegressor(max_iter=500)],
     "model__alpha": [1e-4, 1e-2], "model__epsilon": [1.35, 1.75]},
    {"model": [SVR(kernel="rbf")],
     "model__C": [1.0, 10.0], "model__gamma": ["scale", 0.1]},
    {"model": [RandomForestRegressor(n_estimators=150, random_state=SEED, n_jobs=1)],
     "model__max_depth": [3, 5], "model__min_samples_leaf": [2, 5]},
]


def build_pipeline():
    return Pipeline([("imputer", SimpleImputer(strategy="median")),
                     ("scaler", StandardScaler()),
                     ("model", Ridge())])


def curve(X, y, rng):
    """Mean held-out R2 at each training fraction, test size held constant."""
    n = len(y)
    out = []
    for frac in FRACTIONS:
        scores, scores_log = [], []
        for _ in range(N_REPEATS):
            idx = rng.permutation(n)
            n_test = int(round(TEST_FRACTION * n))
            te, pool = idx[:n_test], idx[n_test:]
            n_train = max(20, int(round(frac * len(pool))))
            tr = pool[:n_train]

            search = GridSearchCV(build_pipeline(), PARAM_GRID, cv=3,
                                  scoring="neg_mean_squared_error", n_jobs=N_JOBS)
            search.fit(X[tr], np.log1p(y[tr]))
            pred = np.maximum(np.expm1(search.best_estimator_.predict(X[te])), 0.0)
            scores.append(r2_score(y[te], pred))
            scores_log.append(r2_score(np.log1p(y[te]), np.log1p(pred)))
        out.append({
            "fraction_of_pool": frac,
            "n_train": int(n_train),
            "n_test": int(n_test),
            "r2_mean": float(np.mean(scores)),
            "r2_sd": float(np.std(scores)),
            "r2_median": float(np.median(scores)),
            "r2_q1": float(np.percentile(scores, 25)),
            "r2_q3": float(np.percentile(scores, 75)),
            "r2_log_mean": float(np.mean(scores_log)),
            "r2_log_median": float(np.median(scores_log)),
        })
    return out


def main():
    OUT_METRICS.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(IN_CSV)
    design = json.loads(IN_DESIGN.read_text())
    spatial = json.loads(IN_SPATIAL.read_text())["results"]
    feats = [f for f in design["tiers"][TIER]["features"] if f in df.columns]

    targets = [t for t in design["targets_modellable"]
               if any(v["feasible"]
                      for v in spatial[t][TIER]["by_block_count"].values())]
    if not targets:
        targets = design["targets_modellable"][:3]

    print("=" * 74)
    print("  STAGE 3.11 — LEARNING CURVES")
    print("=" * 74)
    print(f"  tier {TIER}, {N_REPEATS} draws per point, "
          f"test fraction held at {TEST_FRACTION:.0%}")
    print(f"  targets surviving spatial validation: {', '.join(targets)}\n")

    rng = np.random.default_rng(SEED)
    rows, detail = [], {}
    for target in targets:
        sub = df[feats + [target]].dropna(subset=[target])
        X = sub[feats].to_numpy(float)
        y = sub[target].to_numpy(float)
        pts = curve(X, y, rng)
        detail[target] = pts

        first, last = pts[0]["r2_mean"], pts[-1]["r2_mean"]
        tail_gain = pts[-1]["r2_mean"] - pts[-2]["r2_mean"]
        verdict = ("still improving" if tail_gain > 0.02 else
                   "flattening" if tail_gain > -0.02 else "unstable")
        detail[target] = {"points": pts,
                          "gain_over_range": round(last - first, 4),
                          "gain_in_final_step": round(tail_gain, 4),
                          "verdict": verdict}

        print(f"  {target}")
        for p in pts:
            print(f"    n_train {p['n_train']:4d}  R2 {p['r2_mean']:+.3f} "
                  f"+-{p['r2_sd']:.3f}")
            rows.append({"target": target, **p})
        print(f"    -> gain over the range {last - first:+.3f}, "
              f"final step {tail_gain:+.3f}  [{verdict}]\n")

    pd.DataFrame(rows).to_csv(OUT_TABLE, index=False)
    json.dump({
        "design": {
            "tier": TIER,
            "fractions_of_training_pool": FRACTIONS,
            "test_fraction": TEST_FRACTION,
            "draws_per_point": N_REPEATS,
            "note": ("The test partition is a fixed fraction of the dataset and "
                     "is drawn afresh at each repeat, so the quantity varying "
                     "across points is the training size alone."),
        },
        "interpretation": ("A curve still rising at the full sample indicates "
                           "that data volume limits performance; a flat curve "
                           "indicates the predictors do."),
        "results": detail,
    }, open(OUT_METRICS, "w"), indent=2)

    print(f"  Saved -> {OUT_METRICS.relative_to(ROOT)}")
    print(f"  Saved -> {OUT_TABLE.relative_to(ROOT)}")
    print("\n  STAGE 3.11 DONE\n")


if __name__ == "__main__":
    main()
