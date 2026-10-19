# Verification of the editorial review

Every claim in *Editorial Review — Surrogate Screening of Trace Metals in
Bangladesh Groundwater* (19 Oct 2026) checked against the code in
`03_methods/`, the tables in `04_results/`, and the cleaned data in
`00_data/interim/01_clean.csv`.

**Bottom line: the review is accurate.** Of 53 substantive points, 49 stand as
written and 4 need amending (M2, M9, G9 and the abstract word count), each
correct in substance but carrying a wrong or unverifiable explanation. Nothing
in it is invented, and two findings are worse than the reviewer could tell from
the manuscript alone.

---

## 1. The two things that must be fixed first

**G2 is worse than stated.** The reviewer suspected the redox classifier lets
censored nitrate through a `>= 0.5` test. It does, and the damage is
measurable:

| Check | Result |
|---|---|
| Wells classed nitrate-reducing | 65 |
| of which NO₃-N is **censored**, carrying the DL 0.5 into a `>= 0.5` test | **40 (61.5 %)** |
| Meeting the full McMahon and Chapelle criteria (Fe < 0.1 **and** Mn < 0.05) | **2 of 65** |
| Wells classed oxic meeting the full criteria | **4 of 34** |

`classify_redox` in `35_hydrogeochemistry.py:87` tests only `no3 >= TH_NO3_N`
and never consults `NO3-N_censored`, although that column exists and is used
elsewhere in the same file (line 265). This is the exact failure mode the paper
is about, inside the paper's own mechanistic section. Section 3.8, Table T7,
Figure 8 and the Mann-Whitney contrast all rest on it.

**M2 is real, and the cause is the quantile alone.**
`32_conformal.py:104` uses `np.quantile(residuals, 1 - alpha)`, the plain
empirical quantile, with no finite-sample correction. With n_cal ≈ 67 the
correct order statistic is ⌈(67+1)×0.9⌉/67 = 0.925, not 0.90, which is the
right order of magnitude to explain coverage landing at 0.872 to 0.894 across
all 23 combinations rather than at or above 0.90.

---

## 2. Point-by-point verdicts

### Machine learning and statistics

| # | Verdict | Evidence |
|---|---|---|
| M1 | **Confirmed** | `37_screening_operating_points.py:160-181`. `sweep` thresholds are `np.quantile(scores, ...)` of **external** predictions; Youden comes from `roc_curve(labels, scores)` on external labels; `pick()` then selects the point meeting sensitivity ≥ 0.95 on those same wells. "63 of 64 at 55 % referral" is in-sample with respect to threshold choice. |
| M2 | **Confirmed**, one wrong alternative | Quantile confirmed above. The reviewer's second guess, truncation at zero, is **not** a cause: `lo = max(pred − q̂, 0)` cannot lose a true value because y ≥ 0 throughout. Drop that clause. |
| M3 | **Confirmed** | Score is `abs(y − pred)` on the original scale, so intervals are symmetric and constant-width. Arsenic widths 220.6 to 238.8 µg/L follow from that choice, not from conformal prediction as such. |
| M4 | **Confirmed** | `split_conformal` uses `rng.permutation(n)`. Grep across `03_methods/*.py` for AOA, dissimilarity index, weighted conformal and covariate shift returns **zero hits**: [50] and [63] are cited in the Introduction and never applied. |
| M5 | **Confirmed** | `expm1(predict(log1p(y)))` with no smearing correction, scored on the original scale, in five scripts: 31, 34, 36, 37, 41. |
| M6 | **Confirmed** | T0: Ba is the only target in mg/L (0.005 to 0.657); every other target is µg/L. `log1p` is near-identity for Ba and strongly compressive for the rest. |
| M7 | **Confirmed on all three sub-points** | (a) `33_censoring_comparison.py:135-175` rebuilds the whole `y` vector per arm and scores `r2_score(y[te], p)` against that arm's own `y`, so four arms are judged against four truths. (b) `ros_impute` fits a lognormal to detects and draws each censored value from the truncated distribution: that is stochastic conditional imputation, not regression on order statistics, and it is a single draw, not multiple imputation. (c) No Tobit or AFT learner exists anywhere in `03_methods/`. |
| M8 | **Confirmed** | `RepeatedKFold(n_splits=5, n_repeats=5)` then `wilcoxon` over the resulting 25 dependent scores, in both `31_feasibility_audit.py:178` and `36_spatial_cv.py:214`. |
| M9 | **Confirmed in substance, wrong on one cause** | Numbers exact: As Fe drop 0.3928 against T2 R² 0.1040; U Fe drop 0.98246 against 0.3233. Importance **is** computed on held-out folds (`permutation_importance(..., X[te], y[te])`), so "or on training data" is wrong. The real cause is scale: `40_feature_importance.py:95` sets `y = np.log1p(...)` and scores `r2` on the log scale, while T2 reports original-scale R². The two are simply not comparable, which is the reviewer's point. |
| M10 | **Confirmed** | No single-variable or simple-rule baseline exists in `37_screening_operating_points.py` or anywhere else. |
| M11 | **Confirmed** | Model grid is Ridge, ElasticNet, Huber, SVR, RandomForest. No gradient boosting of any kind. |

### Groundwater and hydrogeochemistry

| # | Verdict | Evidence |
|---|---|---|
| G1 | **Confirmed** | Ni (1.1 % censored), Zn (0.4 %) and Pb (12.5 %) are feasible at **no** tier under **either** blocking scheme. Low censoring plainly does not imply modellable, so the one-sided hypothesis is falsified by the paper's own Table T9. |
| G2 | **Confirmed, and worse** | See Section 1. |
| G3 | **Confirmed** | Fe and Mn in this file are ICP determinations on filtered, acidified samples, per `00_data/README.md`. The E2 tier is therefore a laboratory proxy for a field kit, and the cost ladder prices nothing: there is no USD figure anywhere in the manuscript. |
| G4 | **Confirmed** | Mn median **543 µg/L** exactly as stated. WHO lowered the manganese health-based value to **80 µg/L** (2021, provisional, driven by bottle-fed infants), replacing 400 µg/L. **90.4 %** of these wells exceed 80 µg/L and 84.1 % exceed 100 µg/L. Mn is a predictor, not one of the thirteen targets, but the abstract and Conclusion 6 say "hazardous here" without that qualification. |
| G5 | **Confirmed** | U exceeds 30 µg/L in exactly 4 of 271 wells. A regression R² of 0.25 to 0.35 on a 4-positive target supports no screening claim, so "uranium is the clearer case" overreaches. |
| G6 | **Confirmed** | T7 gives median Eh of **+71.5 mV** in the sulfate-reducing and methanogenic class, which is not credible as a redox measure, and Eh carries a permutation share of **0.0037** for arsenic, effectively zero. |
| G7 | **Valid, not checkable here** | A literature positioning request. Sediment-colour and depth-based screening are genuinely the operative field alternatives and are absent from the manuscript. |
| G8 | **Confirmed** | T14: Barind Clay Residuum (n = 205) and Madhupur Clay Residuum (n = 73) have **0.0 %** exceedance. These are easy negatives and they do inflate AUC on the pooled external set. |
| G9 | **Partly checkable** | PHREEQC request is a reasonable Q1 expectation. I could not locate a reported p = 1.000 for the As(III) test in `35_geochem.json`; ask the reviewer which line they mean, or state the test name and statistic explicitly so the question cannot arise. |
| G10 | **Valid** | Framing request, correct on the facts: this is the only component carrying field Eh, DO and DOC with a full trace-metal suite, which is already stated in Methods 2.1 but not used as the justification it is. |

### Internal inconsistencies

All seventeen rows check out. Detail where it matters:

| Row | Verdict | Evidence |
|---|---|---|
| Ni limit 20 vs 70 | **Confirmed** | T1 says 20.0, T0b says 70.0. WHO is 70; T1 is wrong. |
| Se "7 % censored" | **Confirmed** | T0: n_valid 19, n_censored 19, pct 7.0. The percentage is over all 271 rows, not the 19 measured. All measured Se is censored. |
| Cu min 0.03 vs DL 1 | **Confirmed** | T0 min 0.03, detection_limits "1". |
| DOC min 0 | **Confirmed** | T0 min 0.0 with DLs 0.1 and 1. |
| pH unit "nan" | **Confirmed** | T0 prints `nan`. |
| Zn and Mo labelled WHO guidelines | **Confirmed** | WHO sets no health-based guideline for zinc; the Mo 70 µg/L figure is a health-based value, not a formal guideline. |
| Ba 1,300 µg/L vs 1.3 mg/L | **Confirmed as a unit clash, not a value error** | Both equal 1,300 µg/L. Presentation only. |
| "Section 1.6" | **Confirmed** | Cited in Results line 67 and Discussion line 9; the Introduction has no numbered subsections. |
| Abstract vs 3.5 on arsenic | **Confirmed** | AsTot is feasible at **no** tier under 8 blocks and at four tiers under 16, with fold SD up to 0.79. The fragility is real and unstated. |
| T9 As E1 | **Confirmed** | random R² −0.0702 (infeasible) against 16-block spatial +0.078 (feasible). Spatial beating random is evidence of instability. |
| 3.6 vs 4.3 coverage "expected" | **Confirmed** | Falls with M2. |
| 2.4 vs T2 n | **Confirmed** | Methods states complete cases 254/254/253/243/229; T2 carries n = 271 (260 for Zn) at every tier, because `SimpleImputer(strategy="median")` runs inside the fold. Needs one sentence. |
| Novelty wording | **Confirmed** | Narrow the claim and add "to our knowledge". |
| 3.8 "the two that exceed" | **Confirmed** | Three metals exceed: AsTot (156), U (4) and **Pb (1)**. Qualify the sentence. |
| Figure order | **Confirmed** | Figure 1, then 3, then 2, then 4, 5, 7, 6, 10, 9, 8, 12, 11. |
| Table numbering | **Confirmed** | Table 1, Table 2, then T6, T0, T8, T0b, T1, T2, T9, T5, T3, T4, T12, T7, T14, T11, T13, T10. |
| Refs 26-28, 43 | **Mostly confirmed** | [27] 46(20) no pages, [28] 488-489 no pages, [43] 688 no pages; none has a DOI. [26] does carry 39(1):299-303 and lacks only the DOI. |

### Minor and presentation points

| Point | Verdict |
|---|---|
| Abstract length | **Wrong on the number, right on the risk.** It is **300** words, not ~290. The 250 cap is journal-specific: STOTEN and Environmental Pollution allow 300, Journal of Hydrology 250. If J. Hydrology is the target, it must be cut. |
| Lead with AUC, not R² = −5.58 | **Valid.** Presentational, and a fair warning. |
| Soften the cadmium claim (4.1) | **Valid.** Our Cd DL is 0.02 µg/L in four arsenic-selected districts in 1998-99; "in these wells" is the defensible phrasing. |
| Literature review: 7 of 13 from abstract only | **Confirmed exactly.** Table 1's "Checked against" column reads "Abstract" alone in 7 of the 13 studies; 3 more are abstract plus fragments; only 2 are full text and 1 a preprint. Table 2's "0 of 13" negative counts cannot be supported on that basis. |
| Describe original analytical methods and QA/QC | **Valid**, absent from Methods. |
| Co-located wells | **Confirmed.** 24 wells share exact coordinates across 12 locations, and nothing in the random CV or conformal splits accounts for it. |
| Block geometry vs variogram | **Confirmed.** Methods 2.5.2 reports median block diameters of 18.8 km (8 blocks) and 11.4 km (16 blocks) but never sets them against the variogram ranges. |
| Learning curves: report median | **Confirmed and important.** Mo at n_train 51 has mean R² **−12.44** (SD 78.5) but median **+0.164**. The mean is one blown fold. |
| Discussion repeats Results | **Valid.** Sections 4.2 to 4.4 restate Results numbers almost verbatim. |
| 3.9 geology overlaps the test set | **Confirmed.** T14 sums to **3,465** national wells, which include the 1,027 external wells. |
| Fe-As decoupling needs the established explanation | **Valid.** Currently reported, not explained. |
| Tables are raw pipeline dumps | **Valid.** snake_case headers, Booleans, 4 to 6 decimals. |
| Figures 4 and 5 lack uncertainty | **Valid.** Fold SD exists in T2 and T9 and is not plotted. |
| Data availability, CRediT, funding, competing interests | **Valid**, all absent. |
| Zenodo DOI and repository name | **Valid.** `ground-water-` is the current name. |

### Strengths and summary claims

The eight strengths are all accurate. Two notes on the editor's summary:

- "a censoring comparison that changes the ground truth between arms" and the
  other four named flaws are all confirmed above.
- "mislabel ~65 wells as nitrate-reducing" understates it slightly: 63 of the
  65 fail the full criteria, and 40 are there by censoring artefact alone.

---

## 3. Corrections to make to the review itself

Four items where the review should be amended before you work from it:

1. **M2**: delete "or truncating predictions at zero after computing the
   interval". Clipping the lower bound at zero cannot reduce coverage for a
   non-negative target. The quantile is the sole cause.
2. **M9**: delete "or on training data". Importance is already computed on
   held-out folds. Replace with: importance is computed on the log scale while
   feasibility R² is reported on the original scale.
3. **Abstract length**: 300 words, not ~290; and the 250-word cap applies to
   Journal of Hydrology, not to STOTEN or Environmental Pollution.
4. **G9**: the p = 1.000 the reviewer refers to is not in
   `04_results/metrics/35_geochem.json`. Either they are reading a different
   artefact or it has since changed. Worth one clarifying question.

---

## 4. What I would do, in order

The reviewer's ordering is sound. One change: **G2 belongs first**, not third.
It is a two-line fix with a large blast radius, and leaving it until after the
conformal and threshold work means rewriting the mechanism sections twice.

1. **G2** — add a censoring guard to `classify_redox`, require the full
   McMahon and Chapelle criteria, add `mixed` and `indeterminate` classes.
   Rerun 35, 38, 43; rewrite 3.8 and 4.4.
2. **M2** — finite-sample quantile. Rerun 32 and 34; delete the "expected"
   sentence in 3.6 and the matching line in 4.3.
3. **M1** — freeze thresholds on development out-of-fold predictions, add
   bootstrap CIs. Rerun 37; rewrite 3.12 and 4.5. The abstract's "63 of 64 at
   55 %" will move.
4. **M5, M6** — log-scale metrics, Duan smearing, unify targets to µg/L.
   Touches almost every number in Results.
5. **M7** — common reference truth, rename ROS, add a Tobit or AFT arm.
6. **M10, G8** — depth-only and Fe-only AUC, stratified by geology.
7. **G1, G4, G5** — the framing rewrites, once the numbers have settled.
8. The seventeen inconsistencies, which are mechanical.

Items 1 to 3 can change headline numbers in the abstract, so the abstract
should be rewritten last, not now.

---

## 5. One thing the review does not say

The paper's central claim is that detection limits, not geochemistry, bound
what can be screened. G2 shows the same failure mode operating undetected
inside our own redox classification, and M7 shows a censoring comparison whose
arms are not comparable. Fixing both and saying so plainly would strengthen the
paper rather than weaken it: it is direct evidence for the thesis, found in our
own pipeline. That is a better answer to G1 than a defensive rewrite.
