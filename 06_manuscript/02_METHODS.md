# 2. Materials and methods

> **Draft 1.** Numbered citations continue the sequence established in the
> Introduction and are listed there. New sources appearing first in this
> section are marked `[NEW: author year]` and must be inserted into the
> reference list before submission.

---

## 2.1 Study area and data

The analysis uses the special study areas component of the National
Hydrochemical Survey conducted jointly by the British Geological Survey and the
Department of Public Health Engineering between 1998 and 1999, released in 2001
[1]. The survey is publicly available and its reuse requires acknowledgement of
the funding and implementing partners.

Of the components released, only the special study areas carry field measured
redox potential, dissolved oxygen and dissolved organic carbon alongside a
laboratory trace metal suite, and this component is therefore used as the
development set. It comprises 271 wells distributed across four districts,
namely Nawabganj (125 wells), Lakshmipur (74), Faridpur (64) and Noakhali (8).
Each record carries surveyed well coordinates rather than administrative
centroids, together with well type, reported installation depth and the
administrative hierarchy.

A second component, the national survey restricted to the sixteen districts of
North Bengal, provides an independent test set. Nawabganj is the single
district common to both components, and eleven development wells lie within
500 m of a national survey well, so Nawabganj is removed in its entirety from
the external set. The remaining 1,027 wells occupy fifteen districts that the
models never encounter during fitting, and the shortest distance between any
development well and any external well is 1.64 km, which is asserted at run
time rather than assumed.

These study areas were selected by the original survey because they are
arsenic affected, so the exceedance rates reported here are not national
prevalence figures. The design question is one of feasibility rather than of
prevalence, and this selection does not compromise it. The data date from 1998
to 1999 and describe conditions at that time.

Maps are drawn over the national boundary, district lines, rivers and
coastline supplied as reference files with the same survey, which the
publisher describes as approximate and not intended for precise mapping. A
companion file classifies every national survey site by surface geology after
Alam et al. (1990), and is used in Section 2.8.

Figure 1 summarises the flow of data through the analysis, and Figure 3 shows
the two sets of wells against those boundaries.

{{FIGURE:Fig1}}

{{FIGURE:Fig3}}

## 2.2 Data preparation

Every measured column is parsed into a numeric value together with a Boolean
censoring flag. Where the survey reports a value as falling below the
analytical detection limit, the numeric column retains that limit and the flag
is set, so that no substitution rule is embedded at the point of reading. This
matters because the comparison in Section 2.7 requires the original censoring
structure to remain recoverable, which substitution would destroy
irreversibly [53].

Three further checks are applied. Values of pH equal to zero are a
missing value sentinel in this file rather than measurements and are converted
to missing. Numeric columns with a defined plausible range, namely pH, redox
potential, specific conductance, temperature, dissolved oxygen, well depth and
the coordinates, are checked against that range and any value outside it is set
to missing and recorded. Arsenic speciation is checked for internal
consistency, since As(III) cannot exceed total arsenic; seven wells violate
this and are flagged rather than deleted, so that the count is available as a
data quality statement and the affected records can be excluded from
speciation analysis alone.

Detection limits are recorded per determinand. Several columns carry more than
one limit, reflecting analysis in separate batches: total arsenic has two
(0.5 and 6.0 µg/L), As(III) has three, and lead, uranium and antimony have two
each. This is retained in the metadata because pooling observations censored at
different limits introduces an artificial step into the lower tail.

Major ions, minor anions and the stable isotopes are cleaned on identical terms
but are held apart from both the predictor and the target sets, since they
require laboratory analysis and their use as predictors would defeat the
purpose of the study. They are used only for the hydrogeochemical
characterisation described in Section 2.8.

## 2.3 Target screening

Thirteen trace metals are screened against criteria fixed before any model was
fitted. A metal proceeds to modelling only if fewer than 60 % of its
observations are censored, no single value accounts for more than 40 % of
records, at least 100 valid measurements are present, and at least ten distinct
values occur.

The modal share criterion is included because a censoring percentage alone can
conceal a near constant column. Antimony, for instance, is 46 % censored yet
46 % of all records sit on the single value 0.02 µg/L, which is its detection
limit, and As(III) places 43 % of records on 6.0 µg/L. Neither carries
sufficient variation for any estimator to exploit, irrespective of the
underlying geochemistry.

Seven metals satisfy all four criteria and are carried forward: total arsenic,
nickel, lead, zinc, uranium, molybdenum and barium. Six are excluded: As(III),
cadmium, chromium, copper, antimony and selenium. The outcome of this screening
is reported as a result rather than as a preliminary step, since the pattern of
exclusion is itself informative. Chromium is 97 % censored and cadmium 84 %,
which places both beyond the reach of any method.

## 2.4 Predictor tiers

Predictors are grouped into nested tiers by what their acquisition costs in the
field, so that performance can be read against expenditure rather than against
an undifferentiated feature set. Tier E1 contains the four determinands
obtainable from a multiparameter field meter alone, namely pH, redox potential,
specific conductance and temperature. Tier E2 adds iron and manganese from
colorimetric field kits. Tier E3 adds chloride and bicarbonate by titration.
Tier E4 adds the reported well depth, which is obtained from the installation
record at no cost. A fifth set, denoted REF, includes every determinand in the
dataset that does not require inductively coupled plasma mass spectrometry,
including the heavily censored nitrate and dissolved oxygen columns. REF is not
field deployable and serves as a ceiling against which the deployable tiers are
compared.

Complete cases number 254 for E1 and E2, 253 for E3, 243 for E4 and 229 for
REF. Figure 2 sets out the tiers alongside the validation schemes.

{{FIGURE:Fig2}}

No imputation or scaling is performed at this stage. Both are pipeline steps
fitted inside the training fold, for the reasons set out in Section 2.5.

## 2.5 Model fitting and validation

### 2.5.1 Estimation and nested cross validation

Each target is modelled on the log1p scale, which is applied because every
target is strongly right skewed, and predictions are inverted before scoring so
that all reported coefficients of determination refer to the original
concentration scale. Negative predictions after inversion are truncated at
zero.

Performance is estimated by five fold cross validation repeated five times,
giving 25 outer folds. Within each outer training fold a three fold grid search
selects both the model family and its hyperparameters from a single search
space spanning ridge regression, elastic net, Huber regression, support vector
regression with a radial basis kernel, and random forests. Placing family
selection inside the inner loop means that the reported score already pays for
that selection; choosing the best family first and scoring it afterwards would
allow the test folds to inform the choice.

Median imputation and standardisation are pipeline steps fitted on the training
fold only. A mean predictor is scored on the identical folds as a baseline,
which is the comparison of interest: with 271 wells and skewed targets, a
positive coefficient of determination is less informative than whether the
model improves on predicting the mean.

Each target and tier combination is compared against its baseline by a one
sided Wilcoxon signed rank test on the 25 paired fold scores. Because 35
comparisons are performed, p values are corrected by the Benjamini and Hochberg
procedure at a false discovery rate of 0.05 [64].
A combination is declared feasible only where it both exceeds the baseline
after correction and attains a positive coefficient of determination.

### 2.5.2 Spatial cross validation

Random folds are optimistic when samples are spatially dependent [60, 61, 62].
The development set contains such dependence at short range: 24 wells share
exact coordinates, 28 have a neighbour within 50 m, and 117 of 271 have one
within 1 km.

Block size is set from the data rather than by eye. The empirical variogram of
each log transformed target is computed over lag bins at 0 to 1, 1 to 2, 2 to
5, 5 to 10, 10 to 20 and 20 to 40 km. Most targets approach pure nugget at the
shortest lag, with total arsenic in particular showing semivariance at the sill
from 0 to 1 km, consistent with the reported variability of arsenic over tens
to hundreds of metres [37, 38]. Barium and nickel retain structure to roughly
10 to 20 km.

Spatial dependence is also summarised by a single statistic, since the
variogram describes decay with separation but offers no reference
distribution. Moran's I is computed on log transformed arsenic with inverse
distance weights among wells within 10 km, and its significance assessed
against 999 random permutations of the values across the same locations.

Wells are grouped into spatial blocks by k means clustering on coordinates
projected to approximate kilometres, and folds are formed by grouped five fold
partitioning over whole blocks. Two block counts, eight and sixteen, are
evaluated so that the conclusion does not rest on a single choice, the former
giving a median block diameter of 18.8 km and the latter 11.4 km. Blocking is
repeated over five independent layouts at each count, giving 25 outer folds and
matching the fold count of the random design. Repetition is necessary rather
than cosmetic: a single five fold spatial pass cannot return a one sided
Wilcoxon p value below 0.031 even when the model wins every fold, so a
significance criterion applied to it would reject on power rather than on
optimism.

### 2.5.3 External validation

Models are fitted on all 271 development wells and tested on the 1,027 external
wells described in Section 2.1.

The external component does not carry pH, redox potential, specific
conductance, temperature, chloride, bicarbonate or nitrate, so the tiers of
Section 2.4 cannot be transferred intact. Two reduced predictor sets common to
both components are used instead. The first, denoted T-cheap, contains iron,
manganese and well depth, all of which remain inexpensive to obtain. The second,
T-full, adds calcium, magnesium, sodium, sulfate, silicon and strontium, which
require laboratory analysis and therefore serve only as an upper bound.
Aluminium is excluded because it is reported in µg/L in the development
component and mg/L in the external component, a discrepancy of three orders of
magnitude that would be silently destructive. Units are compared across all
shared columns before use and the run halts on any mismatch.

Because the transferable predictor set is smaller than that of Section 2.4, the
same reduced set is also scored within the development data, so that the
performance lost by discarding predictors can be separated from the performance
lost in transfer.

Only total arsenic and barium can be validated externally, the remaining
modelled metals being absent from the national component.

## 2.6 Conformal prediction

Prediction intervals are constructed by split conformal prediction [45, 46, 47,
48] at a nominal coverage of 90 %.

Coverage is evaluated under the protocol the method actually specifies, with
three disjoint partitions. The model is fitted on half the wells, the
nonconformity quantile is calibrated on a further quarter, and coverage is
measured on the remaining quarter, which neither of the other partitions has
touched. The procedure is repeated over 100 random partitions, and the mean and
standard deviation of the test partition coverage are reported.

This separation is not a refinement but a requirement. Taking the quantile from
a set of residuals and then counting how many of those same residuals fall
within it is circular, because the quantile is by construction their
(1 − α) percentile: the count returns approximately the nominal rate whatever
the model does, and a zero skill predictor attains the same figure. Reported
coverage is therefore informative only when measured out of sample.

The guarantee provided by split conformal prediction holds under
exchangeability, which does not hold between the development and external
components [49, 50, 51, 52]. Transfer is therefore examined directly: the
quantile is calibrated on held out development wells and coverage is measured
on the external wells, over 100 partitions, so that the extent to which the
guarantee survives can be quantified rather than assumed.

## 2.7 Sensitivity to the treatment of censored values

Substituting half the detection limit for censored observations remains the
prevailing default and has been criticised for decades [53, 54, 55, 56]. Its
influence on the present conclusions is measured directly.

Four treatments are compared on identical folds: substitution of half the
detection limit, substitution of the limit itself, substitution of zero, and
regression on order statistics [57]. Under the last, a lognormal distribution
is fitted to the uncensored observations of each target and censored values are
drawn from that distribution truncated above at the detection limit applying to
each individual sample, which both preserves the shape of the lower tail and
respects the multiple detection limits noted in Section 2.2.

The model family is searched inside each training fold exactly as in
Section 2.5.1, so that the only quantity varying between runs is the censoring
treatment. An earlier formulation holding the estimator fixed at ridge
regression was discarded, because targets requiring a non-linear model then
scored poorly regardless of the censoring rule and the spread between rules
reflected an ill fitting model rather than the substitution choice.

Alongside the spread in performance, the median absolute shift in predicted
concentration between the conventional substitution and regression on order
statistics is reported, since a difference expressed in predicted micrograms
per litre is harder to dismiss than a difference in a goodness of fit
statistic.

## 2.8 Hydrogeochemical characterisation

Four analyses place the statistical results in a geochemical context and
provide the data quality evidence expected of a hydrochemical study.

Charge balance error is computed from calcium, magnesium, sodium and potassium
against chloride, bicarbonate, sulfate, nitrate and fluoride, all converted to
milliequivalents per litre. Samples outside ±10 % are flagged rather than
removed, and the rate is reported.

Redox condition is assigned by the cascade of McMahon and Chapelle [15, 16],
which proceeds through dissolved oxygen, nitrate, manganese, iron and sulfate
using threshold concentrations of 0.5, 0.5, 0.05, 0.1 and 0.5 mg/L
respectively, assigning each well a terminal electron accepting process.

Saturation indices for calcite and siderite are computed from pH, temperature
and the major ions, with activity coefficients from the Davies equation and
carbonate speciation obtained from bicarbonate and pH through the second
dissociation constant of carbonic acid. Siderite is included because its
precipitation limits dissolved iron and therefore bears directly on the use of
iron as a proxy.

Hydrochemical facies are assigned by dominance on a milliequivalent percentage
basis, which is the quantitative content of a Piper diagram, and Gibbs ratios
are computed to distinguish weathering from evaporation control.

The geological setting is characterised by joining the surface geology
classification to the national survey records and summarising arsenic within
each unit represented by at least thirty wells. This is descriptive rather than
predictive: surface geology is not used as a model input, since it is a map
attribute attached to a location rather than a quantity a field team measures.

Arsenic speciation is examined as an independent check on the redox assignment,
using only wells where both As(III) and total arsenic are genuine measurements.
Computed over all wells the ratio is an artefact, because in low arsenic wells
both determinands sit at a common detection limit of 6.0 µg/L and the ratio is
forced to unity.

## 2.9 Screening operating points

An area under the receiver operating characteristic curve describes ranking but
does not tell a monitoring programme what to do. For total arsenic, therefore,
predicted concentrations on the external wells are swept across thresholds and
sensitivity, specificity, positive and negative predictive value, the
proportion of wells referred for laboratory confirmation, and the number of
contaminated wells missed are reported at each.

Three operating points are named: the threshold attaining at least 95 %
sensitivity at the lowest laboratory burden, the threshold maximising Youden's
index, and the threshold attaining at least 90 % specificity. Both the World
Health Organization guideline of 10 µg/L and the Bangladesh national standard
of 50 µg/L are evaluated.

Laboratory burden and wells missed are reported side by side rather than
combined into a single score, because their relative weight is a policy
judgement rather than a statistical one.

## 2.10 Software and reproducibility

The analysis is implemented in Python 3.12 using scikit learn, pandas, NumPy,
SciPy and statsmodels. Random seeds are fixed throughout.

Each stage writes its outputs to disk, and every value appearing in a table or
figure is read from those stored files rather than written into the reporting
code, so that a re-run cannot leave a stale number behind. A verification suite
of 55 assertions checks the properties the analysis depends on, among them that
censoring counts survive cleaning unchanged, that detection limits rather than
substituted values are retained, that no target passes screening in violation
of its own stated criteria, that features remain unscaled and unimputed before
cross validation, that conformal coverage derives from disjoint partitions, and
that the external set is geographically separated from the development set.

The complete pipeline, including the raw data as released, is available at
https://github.com/Mosharrof8097/ground-water-.

---

## Notes for revision

- Benjamini and Hochberg (1995) is the only new citation required. The
  repository link is in place; confirm it is public before submission.
- Section 2.5.3 should be read carefully by a co-author. It concedes that
  external validation applies to a reduced model, which is the honest position,
  and the concession is load bearing: without it a reviewer could reasonably
  claim the external result does not test the model described in Section 2.4.
- The sentence in 2.6 explaining circular coverage is deliberately explicit.
  It is the clearest methodological contribution of the paper and should
  survive editing for length.
- Section 2.7 records that an earlier formulation was discarded. Some editors
  prefer such material in supplementary information; it is retained here
  because it explains why the comparison is constructed as it is.
- Confirm the Python and library versions against the environment before
  submission.
