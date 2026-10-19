# Revision status against the editorial review

All 53 verified points, as of 19 Oct 2026, 18:45.

**27 fixed · 5 partly · 21 outstanding**

The six items the review called "must fix, can change results" are done, and
every one of them moved the paper in its own favour.

---

## 1. Machine learning and statistics

| # | Issue | Status | What was done |
|---|---|---|---|
| **M1** | Thresholds chosen on the test set | **Fixed** | Chosen on development out-of-fold predictions and frozen, with 2,000-sample bootstrap intervals. Bangladesh standard went from 63/64 caught to **64/64** |
| **M2** | Coverage below nominal | **Fixed** | Finite-sample quantile ⌈(n+1)(1−α)⌉. Coverage **0.8981 to 0.9170, mean 0.9089**; 22 of 23 at or above nominal, the exception 0.0019 low against its own SD of 0.058 |
| M3 | Symmetric intervals by construction | Outstanding | Written as a limitation. A log-scale conformal score for arsenic is the cheap next step and has not been run |
| M4 | Conformal on random splits; AOA and weighted conformal cited but unused | Outstanding | Written as a limitation. AOA is the cheap one and would test the "no warning" claim directly |
| **M5** | Naive back-transform, original-scale R² | **Partly** | Log-scale R² and MAE now reported alongside in stages 33, 34, 36, 41. Duan smearing not applied |
| **M6** | log1p unit-dependent | **Fixed** | Barium converted to µg/L at cleaning, all targets now share one unit |
| **M7** | Censoring arms scored against four different truths | **Fixed** | One common reference, measured test wells only, plus a censored-consistency column so the lower tail is not lost. "ROS" renamed to stochastic conditional imputation |
| M8 | Wilcoxon over dependent repeated-CV folds | Outstanding | Written as a limitation |
| M9 | Importance on the log scale against original-scale R² | Outstanding | Documented. The review's alternative explanation, training data, was wrong: importance is already computed on held-out folds |
| **M10** | No simple-rule baseline | **Fixed** | Depth-only, Fe-only and Mn-only, same frozen-threshold protocol. **This produced the largest finding of the revision** |
| M11 | No gradient boosting, single seed | Outstanding | Written as a limitation |

### What M10 found

| | development (out of fold) | external | external, Holocene only |
|---|---|---|---|
| Fitted model | **0.867** | 0.828 | 0.809 |
| Raw iron alone | 0.742 | **0.891** | **0.876** |
| | model +0.125 | iron +0.063 | iron +0.068 |

DeLong p = 1.8 × 10⁻⁸ pooled, 3.1 × 10⁻⁷ within the Holocene. At equal
laboratory burden iron misses fewer wells at every level tested. It survives
kit-grade imprecision (CV 25 %: AUC 0.891 unchanged) and a strip ladder
(0.883). Depth alone is worthless at 0.496.

---

## 2. Groundwater and hydrogeochemistry

| # | Issue | Status | What was done |
|---|---|---|---|
| **G1** | Hypothesis one-sided, own data refute it | **Fixed** | Rewritten as two-sided in the Introduction headline, Results 3.3, Discussion 4.1 and Conclusion 1 |
| **G2** | Redox classification mis-implemented | **Fixed** | Three-valued censoring-aware tests, full McMahon and Chapelle criteria, mixed and indeterminate classes |
| **G3** | Field-kit tier uses laboratory ICP | **Partly** | Caveat written into Methods 2.4; measurement-error sensitivity done for iron. **No USD cost table yet** |
| **G4** | Manganese omitted from the hazard conclusion | **Fixed** | Mn and Fe added to the exceedance table with the WHO 2021 value of 80 µg/L; Discussion 4.5 and Conclusion 6 rewritten |
| **G5** | Uranium overstated | **Fixed** | Reframed as a hypothesis for future work. ALE/PDP direction plots not done |
| **G6** | Eh unreliable | **Fixed** | Stated in the limitations with the evidence: +71.5 mV median in the most reducing class, permutation share 0.0037 |
| G7 | Missing low-cost comparators | **Partly** | Literature identified and recorded in `LITERATURE_GUIDE.md`. **Not yet written into the Introduction and Discussion** |
| **G8** | Easy negatives inflate AUC | **Fixed** | Stratified by Holocene and pre-Holocene, with false-positive rate and referral where exceedances are too few to rank |
| G9 | PHREEQC; p = 1.000 unexplained | **Partly** | The p = 1.000 is the As(III) speciation Mann-Whitney, printed by stage 35. PHREEQC not done |
| **G10** | Data age must be argued | **Fixed** | Argument written into Methods 2.1 |

### What G2 found

| | before | after |
|---|---|---|
| nitrate-reducing | 65 wells, median Fe 1.08 mg/L | **2 wells**, median Fe 0.044 |
| oxic | 34 wells, median Fe 0.22 | **4 wells**, median Fe 0.049 |
| meeting full criteria | 2 of 65 | all of them |

40 of the 65 qualified only because a reported "< 0.5" nitrate carried its own
detection limit into a `>= 0.5` test. The 63 displaced wells became mixed
(anoxic) 63 and mixed (oxic) 30; none became indeterminate. Arsenic is now
monotonic along the full cascade, 3.25 → 3.65 → 6.0 → 6.0 → 22.0 → 86.0 µg/L,
which the earlier classification was not.

---

## 3. Internal inconsistencies

**11 of 17 fixed.**

Fixed: nickel guideline 20 → 70 µg/L · selenium censoring 7 % → 100 % of
measured · pH unit "nan" → "pH units" · zinc and molybdenum labelled as
acceptability and health-based values · barium one unit throughout ·
"Section 1.6" references · complete cases against n = 271 · novelty wording ·
lead added to the exceedance sentence · figures renumbered 1 to 12 by first
citation · tables renumbered 3 to 18.

Outstanding: copper minimum 0.03 below its stated DL of 1 · DOC minimum of 0 ·
the arsenic fragility under 8-block CV not stated in the Abstract · Table 9's
E1 instability not discussed · the "expected below nominal" sentence not yet
deleted now that M2 is fixed · references 26 to 28 and 43 still missing pages
and DOIs.

---

## 4. Minor and presentation

**4 fixed, 1 partly, 10 outstanding.**

Fixed: original analytical methods and QA/QC described · learning-curve median
reported alongside the mean · Figure 5 carries fold standard deviations · Data
availability, CRediT, Funding and Competing interests statements added.

Partly: tables still read as pipeline output, though headers are de-underscored,
values cut to four significant figures and the four widest given landscape pages.

Outstanding: abstract length and leading with AUC rather than R² · softening the
cadmium claim · reading the 13 reviewed studies in full text · co-located wells
in the splits · block geometry against variogram ranges · trimming the
Discussion's repetition of Results · stating that the geology section overlaps
the test set · writing the Fe-As decoupling mechanism · moving large tables to
a supplement · Zenodo DOI and a better repository name.

---

## 5. Problems found during the revision that the review did not raise

1. **The central RQ4 claim does not survive its own data.** Section 4.1, the
   Abstract and Figure 8 assert that the diagnostic is the detection limit
   relative to the distribution rather than the censoring rate. Across all
   seven modelled targets: DL/median ρ = +0.143 (p = 0.79), mass at or below
   the DL ρ = +0.257 (p = 0.62), censoring rate ρ = +0.486 (p = 0.33). Nothing
   is significant, and the quantity the paper dismisses correlates best. The
   spread is effectively one point: arsenic 0.125, next highest nickel 0.014.
   **The claim must be deleted**, and replaced by a two-condition
   interpretation: a substitution rule can only matter where the model has
   skill to lose and the limit sits high enough to move a meaningful share of
   the target. Only arsenic satisfies both.

2. **Arsenic has no original-scale skill on measured wells under any rule**:
   −0.031, +0.000, −0.125, −0.047. The earlier +0.104 came from the censored
   wells. On the log scale there is skill (+0.150 to +0.216), but that is from
   random folds and must not be claimed until the spatial log R² from stage 36
   confirms it.

3. **A DeLong implementation bug in our own code**, found while checking the
   iron result. Fixed and validated against `roc_auc_score` to 1e-16.

4. **`requirements.txt` lists statsmodels, seaborn and shap**, none of which is
   imported anywhere. Methods 2.10 also credits statsmodels. The statsmodels
   entry is annotated "censored / Tobit regression", which is the very thing
   M7 says was never fitted.

5. **Conformal intervals widened** with the corrected quantile: arsenic mean
   width 220.6 → 298.7 to 318.5 µg/L. This strengthens the "interval is too
   wide to act on" argument from 22× the guideline to roughly 30×, and every
   occurrence of 220.6 must be updated.

6. **Transfer coverage shifted**: 68.9 to 98.8 % becomes **72.7 to 99.0 %**.

---

## 6. What still has to happen, in order

1. Finish the running rerun: 36 → 37 → 38 → 40 → 41 → 42 → 39 → 43 → 44.
2. Then run **33 and 35 separately**, which the rerun does not cover, followed
   by 43 again. Stage 33 gained the detection-limit mass index and stage 35
   gained the Jonckheere-Terpstra trend test after they had already run.
3. Delete the "DL relative to median, not censoring rate" claim from the
   Abstract, Discussion 4.1, Conclusion 1, Results 3.12 and both panel titles
   of Figure 8.
4. Write the two-condition interpretation in its place, as interpretation.
5. Keep or drop the log-scale skill claim depending on stage 36.
6. Write the prior-art paragraphs: platform staining, the Matlab study,
   iArsenic as a direct competitor, Horneman on As-Fe decoupling, and the
   Nawabganj result that explains the low development iron AUC.
7. Update every number in Results, Discussion and Abstract from the new output.
8. Abstract and Conclusions last.
