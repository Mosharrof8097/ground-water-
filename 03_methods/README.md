# Stage 3 — Methods

Not implemented yet. This file fixes the protocol *before* any model runs, so
the analysis cannot drift toward whatever happens to look good.

## 3.1 Feasibility audit

For each of the 9 modellable targets × 5 predictor tiers:

- **5×5 repeated nested cross-validation.** Outer loop estimates performance,
  inner loop selects hyperparameters. Imputation, scaling and the hyperparameter
  search all sit **inside** the outer fold.
- **Candidate estimators:** Ridge, ElasticNet, Huber, SVR (RBF), Random Forest,
  plus a mean-predictor baseline. The baseline is not decoration — with N = 271
  and skewed targets, beating it is the real test.
- **Target transform:** `log1p` where the target is right-skewed, raw otherwise,
  decided per target from the training fold only.
- **Reported:** R² (mean ± SD across outer folds), RMSE, MAE, Spearman ρ.
- **Multiple comparisons:** Benjamini–Hochberg FDR across all target × tier
  combinations. Testing 9 × 5 = 45 combinations without correction would
  manufacture significance.

A target is declared **feasible** only if it beats the mean baseline across
outer folds by a margin that survives FDR correction. Everything else is
reported as not feasible — that is a result, not a gap.

## 3.2 Conformal prediction

For feasible targets only.

Split-conformal with **disjoint train / calibration / test partitions**,
repeated over many random splits; `q̂` comes from the calibration split and
coverage is measured on the untouched test split.

> Coverage must never be computed on the residuals used to set `q̂`. Because
> `q̂` is by construction their (1−α) quantile, that statistic returns the
> nominal rate regardless of model quality — a zero-skill predictor scores the
> same. This error was found and corrected in the earlier project; it is
> recorded here so it is not repeated.

Report mean coverage ± SD and mean interval width against the nominal level,
including any shortfall.

## 3.3 Censoring

The hypothesis is that **detection limits, not geochemistry, decide which
metals are modellable.** Stage 2 already shows Cd at 84 % and Cr at 97 %
censored.

Planned:

1. Compare DL/2 substitution against censoring-aware alternatives — Tobit /
   censored regression, and regression on order statistics (ROS).
2. Quantify how much the substitution shortcut shifts the reported performance
   and the fitted coefficients.

Substitution is standard practice in this literature and known to be poor
(Helsel). Measuring its cost on real data is a contribution in itself.

## 3.4 Interpretation

Permutation importance and SHAP on the feasible targets, read against known
geochemistry — redox control for As, and whatever the data actually supports
for the rest. Associations are statistical, not causal, and should be written
that way.

## 3.5 Spatial validation

Wells cluster in four districts, so random folds can place neighbouring wells
in both train and test. Alongside random CV, run **spatial block CV** and
report both. The gap between them is itself worth reporting: it tells the
reader how much of the apparent skill is spatial autocorrelation.

## Outputs

| File | Contents |
|---|---|
| `04_results/metrics/03_feasibility.json` | every target × tier result |
| `04_results/tables/T2_feasibility_matrix.csv` | the headline matrix |
| `04_results/tables/T3_conformal_coverage.csv` | held-out coverage |
| `04_results/figures/` | figures, all reading from the metrics file |

**No number may be hardcoded into a table or figure script.** Everything is
read from the metrics file, so a re-run cannot leave stale values behind.
