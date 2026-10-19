# 3. Results

> **Draft 1.** Every value below is taken from the stored metrics files. Table
> and figure numbers refer to the files in `04_results/`. Citation numbers
> continue the sequence established in the Introduction.

---

## 3.1 Data quality and hydrochemical setting

Charge balance error was computed for all 271 wells. The median absolute error
is 1.54 %, 261 wells fall within ±5 % and 270 of 271 within ±10 %, so the major
ion determinations are internally consistent and no sample was removed on this
ground (Table 3).

{{TABLE:T6}}

Censoring varies sharply across the suite (Table 4). Among the predictors,
pH, redox potential, specific conductance, temperature, chloride and
bicarbonate are entirely uncensored, whereas nitrate is censored in 80 % of
wells and dissolved oxygen in 74 %. Among the candidate targets the range runs
from barium and zinc, with no censored observations, to chromium at 97 % and
cadmium at 84 %. Several determinands carry more than one detection limit,
total arsenic having two, at 0.5 and 6.0 µg/L.

{{TABLE:T0}}

The waters are dominated by the Ca-HCO₃ facies, which accounts for 182 of 271
wells (67.2 %), followed by Na+K-HCO₃ with 40 wells (14.8 %) and Mg-HCO₃ with
28 (10.3 %) (Table 5). Gibbs ratios of 0.261 for Na/(Na+Ca) and 0.048 for
Cl/(Cl+HCO₃) place the samples firmly in the rock weathering field. Calcite is
close to equilibrium, with a median saturation index of −0.02 and 44.3 % of
wells oversaturated, while siderite is oversaturated in 67.5 % of wells with a
median index of +0.37.

{{TABLE:T8}}

## 3.2 Which metals constitute a hazard (RQ1, first part)

Only three of the thirteen metals exceed their drinking water guideline in any
well (Table 6). Total arsenic exceeds the WHO guideline of 10 µg/L in 156 of
271 wells, and its maximum of 2,400 µg/L is 240 times that guideline. Uranium
exceeds 30 µg/L in four wells and lead exceeds 10 µg/L in one. The remaining
ten metals never approach their guidelines: the highest cadmium observation
reaches 6 % of its limit, chromium 3 % and copper 1 %.

{{TABLE:T0b}}

This is the first result the modelling has to respect. A surrogate model for a
metal that never approaches its guideline answers a question of limited
practical interest, however well it performs.

## 3.3 Which metals can be modelled at all (RQ1)

Of the thirteen metals screened against the criteria fixed in Section 2.3,
seven proceed and six are excluded (Table 7). The exclusions are governed by
censoring rather than by chemistry. Chromium is excluded at 97 % censored with
only six distinct values, cadmium at 84 %, and copper at 81 %. Antimony and
As(III) fail the modal share criterion rather than the censoring threshold:
both are nominally below 60 % censored, yet 46 % of antimony records and 43 %
of As(III) records sit on a single value, which is in each case the detection
limit. Selenium is excluded on sample size, with 19 valid measurements and a
single distinct value.

{{TABLE:T1}}

The pattern bears on the first half of the hypothesis set out in Section 1.
Cadmium is among the metals most frequently reported as a hazard in the
regional literature [4, 5], yet in these wells it cannot be modelled, not
because its geochemistry is intractable but because 84 % of its observations
are a detection limit rather than a measurement. Censoring sets a ceiling. It
does not follow that metals below that ceiling are modellable, and Section 3.5
shows that several are not.

## 3.4 Predictive skill and its cost (RQ2)

Under random cross validation, 23 of the 35 target and tier combinations
exceed the mean baseline after correction (Figure 4, Table 8). Best
performance by metal is barium at R² = 0.597, uranium at 0.374, molybdenum at
0.361, nickel at 0.288 and total arsenic at 0.104, each at the REF tier except
arsenic, which peaks at E4. Lead and zinc do not beat the baseline at any tier.

{{FIGURE:Fig4}}

{{TABLE:T2}}

Cost matters, and it matters differently by metal. For arsenic and uranium the
meter alone is insufficient and the addition of iron and manganese field kits
is what makes the model work: arsenic moves from R² = −0.070 at E1 to +0.035 at
E2, and uranium from −0.019 to +0.305. For molybdenum and barium the meter
alone already yields a positive result, at 0.088 and 0.268 respectively.

Coefficients of determination and rank correlations diverge sharply for
arsenic, which attains R² = 0.104 but a pooled Spearman ρ of 0.717. The model
orders wells considerably better than it estimates their concentrations.

## 3.5 How much skill survives honest validation (RQ2)

Arsenic is spatially structured at the regional scale. Moran's I on log
transformed arsenic in the development wells is +0.259 against an expected
value of −0.004 under no autocorrelation, with p = 0.001 over 999 permutations
and a mean of 43.3 neighbours within the 10 km radius. The variogram of
Section 2.5.2 and this statistic describe the same field from two directions:
clustering is real at the regional scale, yet semivariance is already at the
sill in the shortest lag bin, so neighbouring wells differ sharply. Both
findings argue for blocked validation.

Spatial blocking changes the picture substantially (Figure 5a, Table 9). The
number of feasible combinations falls from 23 under random folds to 15 under
sixteen blocks and to 10 under eight blocks, the larger blocks
being the more
demanding test.

{{FIGURE:Fig5}}

{{TABLE:T9}}

The optimism attributable to spatial autocorrelation differs greatly by metal.
The median gap between random and spatial R² is +0.784 for barium and +0.492
for nickel under eight blocks, against +0.033 for molybdenum. Nickel collapses
from R² = 0.288 under random folds to −0.204 under eight blocks and −0.113
under sixteen, and is feasible at no tier under either blocking scheme. Reported under random
validation alone, nickel would have been presented as screenable.

Four metals remain feasible under at least one spatial scheme, namely total
arsenic, barium, molybdenum and uranium. Only molybdenum and uranium survive
the more demanding eight block design.

External transfer degrades performance further (Figure 5b, Table 10). For
barium the coefficient of determination falls from 0.650 within the
development data to 0.074 on the external wells using the same reduced
predictor set, and for arsenic from 0.111 to 0.035. Rank correlation is more
robust, at ρ = 0.774 for barium and 0.502 for arsenic.

{{TABLE:T5}}

The practical consequence is better expressed by classification. On the 1,027
external wells the arsenic model attains an area under the curve of 0.828 using
iron, manganese and well depth alone, and 0.838 with the laboratory major ions
added (Figure 11a). The expensive predictors add 0.010 of discrimination.

## 3.6 Calibrated uncertainty and its limits (RQ3)

Within the study area the conformal intervals behave as intended. Across the 23
feasible combinations, held out coverage ranges from 89.8 % to
91.7 % against a nominal 90 %, with standard deviations between 4.6
and 6.2 percentage points (Figure 6a, Table 11). Coverage sits at or slightly
above nominal in 22 of the 23 combinations, which is
expected at this sample size.

{{FIGURE:Fig6}}

{{TABLE:T3}}

Transfer is a different matter (Figure 6b). Calibrating the quantile on held
out development wells and applying it to the external wells gives coverage of
90.7 % for barium under the T-full predictors, which is close to nominal, but
72.7 % for the same metal under T-cheap, and
99.0 % for arsenic under T-full. The departures run in both
directions. Under coverage of 72.7 % against a nominal 90 %
would mislead a user into unwarranted confidence, while coverage of
99.0 % indicates intervals so wide as to be uninformative.

This is the clearest limitation we identify. Conformal prediction supplies
valid intervals where the exchangeability assumption holds, and gives no
warning when it does not.

## 3.7 The cost of the conventional censoring rule (RQ4)

Across the four treatments compared on identical folds, the spread in R² is
negligible for most metals but substantial for arsenic (Table 12, Figure 8).
Barium, with no censored observations, shows a spread of 0.000; zinc 0.003;
uranium 0.007 despite 23 % censoring; molybdenum 0.009; lead 0.005; nickel
0.014. Arsenic, at 34 % censored, shows a spread of 0.125 on the
original scale and 0.288 on the log scale, which is larger than its
entire performance signal: no rule gives it positive skill on the measured
wells, the coefficient of determination running from +0.000 under the detection
limit to −0.125 under zero substitution.


{{TABLE:T4}}

Censoring rate alone does not predict this. Uranium is censored in 23 % of
wells yet the choice of rule is immaterial, because its detection limits of
0.007 and 0.01 µg/L lie far below its median of 0.42. Arsenic carries a limit
of 6.0 µg/L against a median of 22.0, which is 27 % of the median, and there
the rule changes the answer. Figure 8 contrasts the two framings: the
relationship with censoring rate is weak, while the relationship with the
detection limit expressed as a fraction of the median is clear.

Predictions move as well as scores. Substituting half the detection limit
rather than drawing each censored value from a fitted distribution shifts the
median predicted arsenic concentration by 8.4 % of the median observed
value.

## 3.8 What the models use, and whether it is the expected mechanism

Permutation importance identifies iron as the single most informative predictor
for arsenic, accounting for 37 % of positive importance, with pH contributing
31 % (Figure 7, Table 13). Redox indicators together account for 45.9 %. For
uranium the pattern is stronger still, iron alone accounting for 79 % and redox
indicators for 83.2 %.

{{FIGURE:Fig9}}

{{TABLE:T12}}

The two metals whose models rely on redox indicators, total arsenic and
uranium, are the two that both exceed their guidelines and survive spatial
validation. Lead also exceeds, in a single well, but is infeasible at every
tier. Molybdenum and barium, which survive spatial validation without
approaching their guidelines, depend on different predictors: molybdenum on pH, at 49 %, with
redox indicators contributing only 13.5 %, and barium on well depth, at 50 %.

The redox zonation provides an independent account of the arsenic result
(Figure 8, Table 14). Of the 271 wells, 95 are Fe(III) reducing, 68 sulfate
reducing or methanogenic, 65 nitrate reducing, 34 oxic, 7 Mn(IV) reducing and 2
suboxic. Median arsenic rises along this sequence, from 6.00 µg/L in oxic
wells, through 22.00 in Fe(III) reducing wells, to 85.50 in sulfate reducing
and methanogenic wells. Exceedance of the WHO guideline follows: 38 % of oxic
wells against 69 % of sulfate reducing wells. Taking the reducing zones
together, median arsenic is 36.0 µg/L across 170 wells against 10.7 µg/L in the
remaining 101, and the difference is significant (Mann-Whitney, p = 0.0029).

{{FIGURE:Fig8}}

{{TABLE:T7}}

Arsenic is therefore elevated where iron oxyhydroxides are being reductively
dissolved [11, 12, 13, 14], and the model's reliance on iron reflects that
process rather than an incidental correlation.

Arsenic speciation does not corroborate the zonation. Restricted to the 122
wells where both As(III) and total arsenic are genuine measurements, the
As(III) fraction does not rise along the reducing sequence (p = 1.000).
Computed over all wells the ratio appears highest in oxic water, but that is an
artefact: where arsenic is low both determinands sit at a common detection
limit of 6.0 µg/L and the ratio is forced to unity. We report this as a
non-confirmation. Arsenic redox kinetics are slow and speciation is unstable
between sampling and analysis, so disequilibrium is not unexpected.

## 3.9 Geological setting

Arsenic separates cleanly by surface geology across the 3,465 national survey
wells carrying a classification (Figure 9, Table 15). Median arsenic is
114.00 µg/L in the Chandina Alluvium, where 68.9 % of wells exceed the WHO
guideline, 44.85 µg/L in Deltaic Silt (65.9 %) and 42.30 µg/L in Deltaic Sand
(68.4 %).

{{FIGURE:Fig12}}

{{TABLE:T14}}

At the other extreme, the two Pleistocene terrace units contain no exceeding
well at all: Barind Clay Residuum across 205 wells and Madhupur Clay Residuum
across 73, both with a median of 0.50 µg/L, which is the detection limit. Old
gravelly sand follows at 3.6 % across 111 wells.

The contrast between Holocene deltaic and alluvial deposits on the one hand and
the uplifted Pleistocene terraces on the other is the established regional
pattern [11, 14, 37], and the data reproduce it without any modelling. It also
bears on the external validation of Section 3.5: the external set spans both
settings, so transfer is being tested across a genuine geological contrast
rather than within a single depositional environment.

## 3.10 Depth

Arsenic declines significantly with depth (Spearman ρ = −0.305, FDR
significant; Table 16). Median arsenic falls from 65.00 µg/L in wells
shallower than 20 m, through 15.00 µg/L at 20 to 30 m and 8.90 µg/L at 30 to
50 m, to 6.00 µg/L below 50 m, and exceedance falls correspondingly from 75.9 %
to 30.8 %. Comparing wells shallower and deeper than 30 m gives medians of
45.00 and 6.00 µg/L (Mann-Whitney, p = 1.7 × 10⁻⁵).

{{TABLE:T11}}

Uranium, molybdenum and zinc also decline with depth, at ρ = −0.340, −0.419 and
−0.231 respectively, all FDR significant. Barium rises, at ρ = +0.398. Nickel
and lead show no significant relationship.

One detail bears on the use of iron as a proxy. The deepest stratum carries the
highest median iron of the four, at 4.53 mg/L, while carrying the lowest median
arsenic. Iron and arsenic decouple at depth, so an iron based rule will
over-flag deep wells.

## 3.11 Does more data help? (RQ2, limits)

Learning curves were computed for the four metals surviving spatial validation
(Figure 10, Table 17). Three flatten before the full sample is reached. For
arsenic the final increment in training size changes R² by −0.006, for uranium
by +0.004 and for barium by −0.012, against gains of +0.155, +0.154 and +0.261
over the whole range. Molybdenum is still improving, gaining +0.057 in the
final step.

{{FIGURE:Fig11}}

{{TABLE:T13}}

For three of the four metals, therefore, the ceiling is set by the predictors
rather than by the number of wells, and collecting further wells of the same
kind would not materially improve them.

> Note: at the smallest training size molybdenum returns R² = −12.44 with a
> standard deviation of 78.49, an instability of very small training sets
> rather than a meaningful value. That point is omitted from Figure 10 and the
> gain over the full range is not reported for molybdenum.

## 3.12 What a screening programme could expect (RQ2, applied)

Operating points were evaluated on the 1,027 external wells using iron,
manganese and well depth (Table 18, Figure 11b).

{{TABLE:T10}}

Each threshold is chosen on out of fold predictions over the development wells
and frozen before the external wells are scored, so the figures below are out
of sample in the cut off as well as in the model.

Against the Bangladesh standard of 50 µg/L, where 64 of the external wells
exceed, the rule targeting 95 % sensitivity on the development wells attains
100 % on the external wells, missing none of the 64 while referring 58.3 % for
laboratory confirmation. The balanced rule attains 92.2 %, misses five and
refers 42.5 %. Against the WHO guideline of 10 µg/L, where 194 wells exceed,
the corresponding rule attains 97.9 % and misses four at a burden of 63.5 %.

A programme willing to send roughly half its samples to a laboratory could
therefore identify almost every well exceeding the national standard using
three inexpensive measurements. The same models cannot state how contaminated
those wells are: the mean conformal interval for arsenic spans
299 to 318 µg/L against a guideline of
10 µg/L.

## 3.13 Does the fitted model earn its place? (RQ2, applied)

The tiers are built from predictors, and a tier can only be judged against the
alternative of using one of those predictors on its own. Three single
predictor rules were therefore scored under the same frozen threshold protocol
(Figure 11a, Table 19).

{{FIGURE:Fig7}}

{{TABLE:T19}}

Well depth alone is worthless on the external wells, at an area under the curve
of 0.496. Manganese alone reaches 0.760. Dissolved iron alone reaches
0.891, which exceeds the 0.828 of the model built on iron,
manganese and depth together. The difference of +0.063 has a
bootstrap interval of 0.042 to 0.094 and a paired DeLong test gives
1.8e-08 on identical wells.

Three checks were applied before accepting this. Restricting to the Holocene
aquifers, where the pre-Holocene terraces no longer supply easy negatives, the
advantage widens rather than narrows, 0.876 against
0.809 (3.1e-07). Comparing the two rules at
equal laboratory burden rather than at their own thresholds, iron misses fewer
contaminated wells at every burden examined, from 40 % to 63 % of wells
referred (Figure 11b). And the iron here is an inductively coupled plasma
determination rather than a kit reading, so the rule was re-scored under
multiplicative imprecision of 25 % and after reading onto a typical colorimetric
strip ladder; the area under the curve held at 0.891 and
0.883, and at the frozen threshold of 0.165 mg/L
sensitivity remained 0.985 with 3 of 194 wells missed.

On the development wells the ordering reverses. There the model reaches
0.867 against 0.742 for iron, an advantage of
+0.125. The model is not a weak one; it is fitted, and what it
fits does not survive transfer, whereas a raw concentration carries no
coefficients.

Neither rule is stable across regions. Across the 7
external districts with at least ten exceedances, the area under the curve for
iron alone runs from 0.731 to 0.993 with a median
of 0.910, against 0.742 in the development set
(Figure 10). The spread is larger than the gap between the two rules.

{{FIGURE:Fig13}}

---

## Notes for revision

- Section 3.2 should be read before 3.3 is edited for length. The two together
  carry the paper's main claim and are deliberately placed before any
  modelling result.
- Section 3.6 states a negative finding about our own method. It should not be
  softened; it is the most useful thing we report.
- Section 3.8 reports that speciation does not confirm the zonation, and
  explains the artefact that made an earlier version appear to show the
  opposite. Keep both halves.
- The arsenic interval width of about 300 µg/L against a 10 µg/L guideline is the
  single most important caveat in the paper and recurs in the Discussion.
- Check whether the journal prefers Table T0 and T0b renumbered as Tables 1 and
  2, with the present Table 1 of the Introduction becoming Table 3.
