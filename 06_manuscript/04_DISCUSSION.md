# 4. Discussion

> **Draft 1.** Citation numbers continue the sequence of the Introduction.

---

## 4.1 What sets the limit on surrogate screening

The hypothesis advanced in Section 1.6 was that the binding constraint on
surrogate screening is analytical rather than geochemical. The screening
results support it. Six of thirteen metals were excluded before any model was
fitted, and in five of the six the reason was that the laboratory had reported
a detection limit rather than a measurement: chromium in 97 % of wells, cadmium
in 84 %, copper in 81 %, while antimony and As(III) placed 46 % and 42 % of
records on a single value. Selenium was excluded on different grounds, having
been measured in only 19 wells. No estimator can recover structure that was
never recorded.

The practical consequence is uncomfortable for the regional literature.
Cadmium is among the metals most often reported as a hazard in assessments
across the Bengal Basin [4, 5], yet here it is unmodellable, and its highest
observation reaches 6 % of the WHO guideline. Where a determinand is censored
at a limit comparable to the concentrations of interest, both the reported
occurrence and any model built on it rest on the detection limit as much as on
the water.

This also sharpens what "censoring rate" means. Uranium is censored in 23 % of
wells and the choice of substitution rule is immaterial, because its detection
limits of 0.007 and 0.01 µg/L lie far below its median of 0.42. Arsenic is
censored in
34 % and the rule shifts the coefficient of determination from +0.104 to
−0.032, because its upper limit of 6.0 µg/L is 27 % of the median. The
diagnostic quantity is the detection limit relative to the distribution, not
the proportion censored, and reporting the latter alone conceals the problem.

## 4.2 How much skill is real

Random cross validation gave 23 feasible target and tier combinations. Spatial
blocking reduced this to 15 under sixteen blocks and 9 under eight, and the
combinations lost were not evenly distributed. Nickel fell from R² = 0.288
under random folds to −0.204 under eight blocks and −0.113 under sixteen, and
became infeasible at every tier. Reported under random validation alone, which
is the prevailing practice in this literature (Table 1), nickel would have been
presented as screenable.

Four metals survive spatial blocking: arsenic, barium, molybdenum and uranium.
The two that survive the more demanding eight block design are molybdenum and
uranium.

External transfer imposes a further cost, and separates three things that are
easily conflated. The coefficient of determination falls heavily, for barium
from 0.650 within the development data to 0.074 on unseen districts under the
same reduced predictor set. Rank correlation holds up far better, reaching
ρ = 0.774 for barium and 0.502 for arsenic on that set. Classification holds up
best of all: against the WHO guideline the arsenic model attains an area under
the curve of 0.838 on 1,027 wells in districts it never saw, and 0.828 when
reduced to iron, manganese and well depth alone.

What transfers, therefore, is the ordering of wells by risk, not the estimate
of how contaminated each is. For a screening programme that ordering is the
operative quantity, and the distinction is worth stating plainly, because for
the arsenic model built on iron, manganese and depth a coefficient of
determination of −5.58 and an area under the curve of 0.828 describe the same
predictions.

## 4.3 Calibrated uncertainty, and where it fails

Within the study area the conformal intervals behaved as the theory promises,
with held out coverage between 87.2 % and 89.4 % against a nominal 90 %. We
are not aware of prior application of conformal prediction to groundwater
quality, and on this evidence it is well suited to the problem: it wraps any
estimator, requires no distributional assumption, and the slight shortfall
against nominal is what the sample size would predict.

Transfer is where it fails, and it fails in a way that offers no warning.
Barium under the reduced laboratory predictors retained 89.3 % coverage, close
to nominal; the same metal under iron, manganese and depth fell to 68.9 %; and
arsenic rose to 98.8 %. One of these would mislead a user into unwarranted
confidence and another into intervals too wide to act on, and nothing in the
calibration distinguishes them in advance.

This is consistent with the theoretical position that exchangeability is what
the guarantee rests on, and that spatial data satisfy it only locally
[49, 50, 51, 52]. The contribution here is to measure the size of the failure
on real wells rather than to restate the caveat. A conformal interval
calibrated in one district should not be presented as valid in another.

Even where coverage is correct, width may make the interval useless. The mean
conformal interval for arsenic ranges from 220.6 to 238.8 µg/L across tiers,
against a guideline of 10 µg/L. A statistically valid interval twenty two times
the regulatory threshold at its narrowest supports no decision at all, and
reporting coverage without width would misrepresent what the model offers.

## 4.4 The mechanism is the expected one

Iron is the single most informative predictor for arsenic, at 37 % of positive
permutation importance, and redox indicators together account for 45.9 %. For
uranium the dependence is stronger, iron alone reaching 79 %.

The redox zonation gives the same answer from different variables. Median
arsenic rises from 6.00 µg/L in oxic wells to 22.00 in Fe(III) reducing wells
and 85.50 in sulfate reducing and methanogenic wells, and exceedance from 38 %
to 69 %. Arsenic is elevated where iron oxyhydroxides are being reductively
dissolved, which is the established release mechanism in this basin
[11, 12, 13, 14, 17]. The surface geology reproduces the same division without any
modelling: no well in the Barind or Madhupur Clay Residuum exceeds the
guideline, against 68.9 % in the Chandina Alluvium.

The major ion composition is unexceptional for the region. The dominance of
the Ca-HCO₃ facies, Gibbs ratios lying in the rock weathering field and near
equilibrium with calcite match what hydrogeochemical surveys report across the
Bengal Basin and the adjacent alluvial tracts [18, 19, 22, 24, 25]. These wells
are therefore chemically typical of the wider setting, even though the
districts were selected for arsenic.

The models are therefore using the process rather than an incidental
correlation, which is the difference between a screening rule that may
generalise and one that will not.

Two caveats attach. Arsenic speciation does not corroborate the zonation, the
As(III) fraction failing to rise along the reducing sequence. Slow arsenic
redox kinetics and the instability of speciation between sampling and analysis
make disequilibrium unsurprising, but we report the non-confirmation rather
than omit it. Second, iron and arsenic decouple with depth: the deepest stratum
carries the highest median iron at 4.53 mg/L and the lowest median arsenic, so
an iron based rule will over-flag deep wells. This is a predictable and
correctable failure mode rather than a hidden one.

## 4.5 What this is worth in practice

A field kit for arsenic already exists, costs about USD 0.17 per test and
classified 88 % of wells correctly in evaluation [26, 27]. Any honest appraisal
must begin there: for arsenic alone, that kit is cheaper and more accurate than
the models reported here, and we do not propose replacing it.

The case for a surrogate approach rests on two things the kit cannot do. It is
analyte specific, so a programme concerned with more than arsenic needs a
separate consumable for each determinand, and no equivalent exists for uranium,
molybdenum or barium. And a single set of field measurements can, in principle,
inform several metals at once.

On the evidence here that principle delivers less than one might hope. Of
thirteen metals, only three exceed any guideline in any well, and of those only
arsenic and uranium both exceed and remain modellable after spatial
validation. Lead exceeds in one well and is infeasible at every tier. The
metals that model best, barium and molybdenum, never approach their guidelines.
The intersection of "hazardous here" and "screenable" contains two metals, and
for one of them a cheaper instrument already exists.

Uranium is the clearer case for the approach. It exceeds the WHO guideline in
four wells, survives spatial blocking at every tier from E2 upward and at both
block counts, depends overwhelmingly on iron, and has no field kit. It could
not be validated externally, because the national survey does not report it,
and that limits how firmly this can be stated.

Where the approach is used, the operating point matters more than the summary
statistic. Against the Bangladesh standard, a rule using iron, manganese and
well depth identifies 63 of 64 contaminated wells while referring 55 % of
wells for laboratory confirmation, and the balanced rule refers 40 % while
missing five. Whether that trade is acceptable is a policy judgement, and the
figures are reported side by side rather than combined so that it can be made
explicitly. Adding the laboratory major ions raises the area under the curve
from 0.828 to 0.838 against the WHO guideline and from 0.801 to 0.830 against
the Bangladesh standard, gains too small to justify their cost.

## 4.6 Limitations

The development set comprises 271 wells in four districts, selected by the
original survey because they are arsenic affected. Exceedance rates here are
therefore not prevalence estimates for Bangladesh. The data were collected in
1998 and 1999 and describe conditions at that time.

External validation applies to a reduced predictor set. The national survey
carries neither pH nor redox potential, so the tiers that make arsenic and
uranium work could not be transferred intact, and the external result tests a
weaker model than the one the development data support. The within development
score for that same reduced set is reported alongside, which separates the cost
of losing predictors from the cost of transfer, but it does not remove the
limitation.

Uranium, molybdenum and the remaining metals could not be validated externally
at all, since the national component does not report them. The strongest
statement available for uranium is that it survives spatial blocking within the
study area.

Learning curves flatten for arsenic, uranium and barium, indicating that the
predictors rather than the number of wells set the ceiling for those metals.
Molybdenum was still improving at the full sample. More wells of the same kind
would not materially improve three of the four.

All results use a single random seed. Repetition across seeds has not been
performed and the stability of the reported figures to that choice is
consequently unquantified.

Finally, the study assesses whether field measurable parameters can substitute
for laboratory analysis. It does not establish that a programme adopting such
a rule would improve health outcomes, which would require a different design
and a prospective comparison. Exposure based risk assessments in the region
show what that different question involves, combining measured concentrations
with intake assumptions to estimate hazard to a population rather than testing
whether a cheaper measurement can stand in for a dearer one [20, 21].

---

# 5. Conclusions

Thirteen trace metals were screened against parameters a field team can
measure, in 271 wells with field pH, redox potential, conductance and
dissolved oxygen alongside a laboratory metal suite, with validation extended
to 1,027 wells in districts the models never saw.

1. **Detection limits, not geochemistry, decide what can be screened.** Six of
   thirteen metals carried too little measured variation for any method, and
   what matters is the detection limit relative to the distribution rather than
   the proportion of records censored.

2. **Honest validation removes most of the apparent skill.** Feasible
   combinations fell from 23 under random folds to 9 under the most demanding
   spatial design. Nickel, which random validation would have reported as
   screenable, fails at every tier once folds are blocked.

3. **Ranking transfers; concentration does not.** On unseen districts the
   arsenic model built on iron, manganese and well depth returns a coefficient
   of determination of −5.58 while reaching an area under the curve of 0.828.
   For screening, the ordering is the quantity that matters.

4. **Conformal intervals are valid in place and unreliable on transfer.**
   Coverage held between 87.2 % and 89.4 % within the study area but ranged
   from 68.9 % to 98.8 % on external wells, with no advance indication of which
   way it would fail. Width is a separate constraint: the narrowest mean
   arsenic interval is 220.6 µg/L against a 10 µg/L guideline.

5. **The models use the expected process.** Iron dominates the arsenic and
   uranium models, arsenic rises along the reducing sequence from 6.00 to
   85.50 µg/L, and no well in the Pleistocene terrace units exceeds the
   guideline.

6. **The practical scope is narrower than the premise suggests.** Only arsenic
   and uranium are both hazardous here and screenable, and arsenic is already
   served by a cheaper field kit. Uranium, with no kit and a strong redox
   dependence, is the clearest candidate, though it could not be validated
   externally.

For monitoring programmes the implication is specific rather than general.
Field measurable parameters can order wells by risk well enough to halve a
laboratory workload while missing one contaminated well in sixty four, but they
cannot say how contaminated a well is, and a rule calibrated in one district
carries no guarantee in the next.

Two recommendations follow for data collection rather than for modelling.
Surveys should record pH and redox potential, without which surrogate screening
for the redox sensitive metals is not possible; the national component's
omission of both is what confined external validation here to a weaker model.
And detection limits should be chosen and reported with the intended analysis
in mind, since a limit set close to ambient concentrations forecloses both
modelling and reliable occurrence estimates.

---

## Notes for revision

- Section 4.5 concedes that the arsenic field kit beats these models on
  arsenic alone. That concession is load bearing and should not be removed; a
  reviewer who finds it absent will make the point less charitably.
- Section 4.6 records that seed stability was not assessed. If that analysis is
  run before submission, update this paragraph rather than deleting it.
- The uranium argument is the most promising and the least supported, since no
  external validation was possible. Keep the qualification in both 4.5 and 4.6.
- Conclusion 6 is the honest summary of scope. It will read as modest; it is
  also what the evidence supports.
