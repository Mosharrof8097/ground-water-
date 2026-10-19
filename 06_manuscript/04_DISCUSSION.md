# 4. Discussion

> **Draft 1.** Citation numbers continue the sequence of the Introduction.

---

## 4.1 What sets the limit on surrogate screening

The hypothesis advanced in Section 1 was that the binding constraint on
surrogate screening is analytical rather than geochemical. The results support
half of it, and refute the other half. Six of thirteen metals were excluded before any model was
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

What does not follow is the converse, and our own data refute it. If detection
limits were the whole story, metals with little censoring would be modellable
whatever their geochemistry. Nickel is censored in 1.1 % of wells, zinc in
0.4 % and lead in 12.5 %, and all three are infeasible at every tier under
every spatial scheme. Below the censoring ceiling the limit is set by something
else: whether the field measurable predictors carry information about that
metal at all. The defensible claim is therefore two sided. Censoring imposes a
ceiling, and for the heavily censored metals that ceiling is the whole
explanation; for the rest, feasibility is decided by predictor information, and
nothing about a low censoring rate promises it.

So far censoring has appeared in one role, as something that hides a signal.
Chromium, cadmium and copper carry so little measured variation that no model
can be built, and that ceiling is the whole of their story. The same mechanism
has a second role that is easier to miss and more damaging, because it runs the
other way: censoring can manufacture a signal that is not there. An analysis
that ignores the censoring flag would classify 65 wells as
nitrate reducing, and would report positive log-scale skill for arsenic under
spatial blocking. Neither survives when the flag is respected.

Both cases turn on reading a stored detection limit as though it were a
measurement. Nitrate is censored in 80 % of these wells at limits of 0.3 and
0.5 mg/L, so a well reported as "< 0.5" carries the value 0.5 and passes a
test for nitrate at or above 0.5 mg/L. Of the 65 wells that
test places in the nitrate reducing class, only 2 meet the
full criteria; the rest are anoxic waters carrying iron and manganese in
milligrams per litre. Arsenic shows the same thing in a different metric. On
the log scale the lower tail carries disproportionate weight, so the split
between the two detection limits of 0.5 and 6.0 µg/L is itself learnable. The
coefficient of determination is +0.227 under the most demanding
blocking, but restricted to the wells that carry a genuine measurement it falls
to +0.022 (p = 0.42). Table S1
reports both cases side by side.

This is Helsel's objection [53] made concrete. Substitution does not merely
lose information, it fabricates structure, and the fabricated structure is
strong enough to pass a cross validated model search and a spatially blocked
design. The practical consequence for this paper is that arsenic retains no
concentration skill under spatial blocking on either scale. What it retains is
the ranking of wells by exceedance, which the next section takes up.

One class of result is unaffected. Classification against the WHO guideline of
10 µg/L does not depend on how censored values are filled, because a well
reported below 6.0 or below 0.5 µg/L is below 10 µg/L whatever number is
substituted, so its negative label is correct by construction. The areas under
the curve reported here are therefore not exposed to the mechanism described
above.

A diagnostic that predicts which determinands will be sensitive to the
substitution rule would be useful, and we cannot offer one. Across the seven
modelled targets, the rank correlation between the spread in R² and the
detection limit as a fraction of the median is ρ = +0.14, and against
the censoring rate ρ = +0.49; neither is distinguishable from chance
with seven points, and arsenic is the only target whose spread is material.
What the cases have in common is better read as two conditions than as a
correlation. A substitution rule can only matter where the model has skill to
lose and where the limit sits high enough to move an appreciable share of the
target. Uranium fails the second condition, its limits lying two orders of
magnitude below its median; lead fails the first, its models carrying no skill
at any tier although its limit sits at half its median. Only arsenic meets
both.

## 4.2 How much skill is real

Random cross validation gave 23 feasible target and tier combinations. Spatial
blocking reduced this to 15 under sixteen blocks and
10 under eight, and the
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
with held out coverage at or above the nominal 90 %. To our knowledge
conformal prediction has not previously been applied to trace metal
concentrations in groundwater, and on this evidence it suits the problem: it
wraps any estimator and requires no distributional assumption.

Transfer is where it fails, and it fails in a way that offers no warning.
Barium under the reduced laboratory predictors retained 90.7 % coverage, close
to nominal; the same metal under iron, manganese and depth fell to
72.7 %; and arsenic rose to 99.0 %. One of these would mislead a user into unwarranted
confidence and another into intervals too wide to act on, and nothing in the
calibration distinguishes them in advance.

This is consistent with the theoretical position that exchangeability is what
the guarantee rests on, and that spatial data satisfy it only locally
[49, 50, 51, 52]. The contribution here is to measure the size of the failure
on real wells rather than to restate the caveat. A conformal interval
calibrated in one district should not be presented as valid in another.

Even where coverage is correct, width may make the interval useless. The mean
conformal interval for arsenic ranges from 299 to
318 µg/L across tiers,
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

The second thing an honest appraisal must concede is that the fitted model does
not earn its place. On the external wells a single measurement of dissolved
iron ranks them better than the model built on iron, manganese and well depth
together, 0.891 against 0.828, a difference of
+0.063 with a bootstrap interval of 0.042 to 0.094 and
1.8e-08 on a paired DeLong test. The gap is not an artefact of easy
negatives: within the Holocene aquifers alone, where the decision actually
falls, it widens to 0.876 against 0.809. Nor is
it an artefact of where each threshold happened to sit, since iron misses fewer
contaminated wells than the model at every laboratory burden we examined.
Depth on its own is worth nothing, at an area under the curve of 0.496.

What makes this interpretable rather than merely awkward is the development
set. There the ordering reverses: the model beats iron by +0.125,
0.867 against 0.742. The model is not weak. It is fitted,
and what it fits does not survive the journey to another district, whereas a
raw concentration carries no coefficients and so has nothing to lose. This is
the same lesson as Section 4.2, arriving by a different route.

Iron indicating arsenic is not a new idea and we do not claim it. Red staining
on a tubewell platform marks iron reduction and with it arsenic release, while
black staining marks manganese reduction, and the idea is already deployed: the
iArsenic application predicts well risk from depth, location and platform
colour with a reported accuracy of 84 % [67, 68]. The sediment colour a driller
reports serves the same purpose [71].

The gap this paper fills is one of setting rather than of mechanism. The
validation that established platform colour was carried out at Matlab, where
99 % of the 233 red-platform wells among 272 exceeded the WHO guideline [65].
Where almost every well is contaminated, a rule that flags almost every well is
correct almost always and screens nothing; the authors say as much, calling for
re-examination where arsenic varies more between wells. In the alluvial
aquifers of eastern India, where it does, platform colour identified
contaminated wells with about 83 % accuracy, and performance rose with
prevalence [66]. Our external districts carry a prevalence of 18.9 %, 194 of
1,027 wells, which is the mixed regime in which the heuristic has not been
tested quantitatively.

What this paper adds is therefore a measured and kit-checkable form of that
heuristic, carried through the validation the earlier work did not have: a
threshold frozen on one set of districts, applied unchanged to 1,027 wells in
fifteen others at a prevalence where the rule can fail, and compared against a
fitted alternative on identical wells.

The mechanism also explains the pattern that defeated the regression. Arsenic
is released when Fe(III) coatings are converted to Fe(II) phases such as
siderite or vivianite, and that conversion need not put iron into solution
[69]. Concentrations of the two therefore decouple while their ordering need
not, which is why a correlation search finds little and a ranking finds a great
deal. It is also consistent with iron ranking poorly in our own development
set, 125 of whose 271 wells lie in Nawabganj: a study of ten municipal wells
there, repeatedly sampled, reported no relationship between arsenic and iron
[70]. Ten wells cannot establish a district-wide pattern, and we offer it as
consistent with our result rather than as an explanation of it.

Two qualifications bound the recommendation. The iron used here is an
inductively coupled plasma determination, not a kit reading, so the rule was
re-scored under kit-grade imprecision and after reading onto a typical strip
ladder; the area under the curve held at 0.891 and 0.883,
and the frozen threshold of 0.165 mg/L falls between two rungs of
that ladder rather than on one. More seriously, no rule is stable across
regions. Iron's area under the curve runs from 0.731 to
0.993 across the 7 external districts with
enough exceedances to rank, against 0.742 in the development set. A
programme entering a district it has not measured should calibrate against a
small laboratory sub-sample before adopting any threshold, ours included.

The case for a surrogate approach rests on two things the kit cannot do. It is
analyte specific, so a programme concerned with more than arsenic needs a
separate consumable for each determinand, and no equivalent exists for uranium,
molybdenum or barium. And a single set of field measurements can, in principle,
inform several metals at once.

On the evidence here that principle delivers less than one might hope. Of the
thirteen metals screened, only three exceed any guideline in any well, and of
those only arsenic and uranium both exceed and remain modellable after spatial
validation. Lead exceeds in one well and is infeasible at every tier. The
metals that model best, barium and molybdenum, never approach their guidelines.
The intersection of "hazardous here" and "screenable" contains two metals, and
for one of them a cheaper instrument already exists.

One hazard sits outside that accounting and should be named. Manganese enters
this study as a predictor rather than as a target, so it is absent from the
thirteen and from the exceedance table, yet the World Health Organization
lowered its health based value to 80 µg/L in 2021 and the median well here
carries 543 µg/L. On that basis most of these wells exceed it. The point cuts
against the premise of surrogate screening rather than for it: manganese is
measured directly in the E2 tier, so for manganese there is nothing to
substitute. A programme equipping field teams with iron and manganese kits
would be measuring a hazard, not predicting one, and would obtain the arsenic
ranking as a by product.

Uranium is the most promising candidate and the least evidenced. It survives
spatial blocking at every tier from E2 upward and at both block counts,
depends overwhelmingly on iron, and has no field kit. But it exceeds the WHO
guideline in four wells out of 271, and a coefficient of determination between
0.25 and 0.35 on a target with four positives says nothing about whether
exceedances can be detected. It could not be validated externally either,
because the national survey does not report it. Uranium is therefore a
hypothesis for a future study with a sufficient number of exceedances, not a
screening result.

The direction of the dependence is at least consistent with the known
chemistry. Uranium is mobile as uranyl carbonate complexes in less reducing
water and is removed as conditions become iron reducing, so uranium should fall
as iron rises, and bicarbonate appearing as the second predictor fits that
account. Permutation importance gives magnitude but not sign, so this remains
an interpretation rather than a demonstration.

Where the approach is used, the operating point matters more than the summary
statistic. Against the Bangladesh standard, a rule using iron, manganese and
well depth identifies all 64 contaminated wells while referring 58.3 % of
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

Several methodological choices bound what the numbers can bear, and are stated
here rather than left for a reader to find. Targets are modelled on a log1p
scale and inverted with the exponential before scoring, without a smearing
correction, so the back transformed prediction estimates a conditional median
and the coefficients of determination on the original scale are pulled down by
a small number of high wells. The conformal score is the absolute residual on
the original scale, which produces intervals of constant width by construction;
conformalised quantile regression or a score on the log scale would give
multiplicative intervals and is the natural next step. Conformal calibration
uses random partitions, so the optimism this paper demonstrates for random
folds applies to the coverage estimates too, and 24 wells sharing exact
coordinates are not accounted for in those splits. Covariate shift weighted
conformal and the area of applicability are discussed but not applied, and
applying them would test the claim that transfer fails without warning. The
comparison of censoring rules scores each rule against its own reconstructed
target, so part of the spread reported for arsenic is variance in the target
rather than distortion of the model, and no censoring aware learner such as a
Tobit or accelerated failure time model was fitted. Significance is assessed
with Wilcoxon tests over repeated cross validation folds that share wells,
which makes those p values anti conservative. Permutation importance is
computed on the log scale while the feasibility table reports the original
scale, so the two sets of numbers are not directly comparable, and no
single predictor baseline was computed, which leaves open how much of the
classification performance well depth alone would deliver. The model family
search covers regularised linear models, support vector and random forest
regression but no gradient boosting. All results use a single random seed, and
stability across seeds is unquantified.

Two features of the setting also flatter the external results. The redox
potential is a mixed potential on a platinum electrode rather than a measure of
a single couple, and the data show it: the median in the most reducing class is
positive, and its permutation importance for arsenic is indistinguishable from
zero. And the external districts include the Barind and Madhupur terraces,
where arsenic is almost uniformly at the detection limit; these are easy
negatives, and the pooled area under the curve is higher than it would be
within the Holocene aquifers where the decision actually matters.

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
measure, in 271 wells carrying field pH, redox potential, conductance and
dissolved oxygen alongside a laboratory metal suite, with validation extended
to 1,027 wells in fifteen districts the models never saw.

1. **Censoring both hides and manufactures structure.** Six of thirteen metals
   carried too little measured variation for any method, which is the familiar
   ceiling. The second direction is easier to miss: an analysis that reads a
   stored detection limit as a measurement classifies 65 wells
   as nitrate reducing where only 2 meet the criteria, and
   credits arsenic with log-scale skill (+0.227) that falls to
   +0.022 once only measured wells are scored. Substitution
   does not merely lose information; it fabricates structure strong enough to
   pass a cross validated search and a spatially blocked design.

2. **Below that ceiling, predictor information decides.** Nickel, zinc and lead
   are almost uncensored and still fail at every tier, so a low censoring rate
   promises nothing.

3. **Honest validation removes most of the apparent skill.** Feasible
   combinations fell from 23 under random folds to
   10 under the most demanding spatial design. Nickel, which
   random validation would have reported as screenable at
   R² = +0.288, reaches -0.204 once folds are blocked.
   Arsenic is feasible under sixteen blocks but not under eight, and that
   fragility should be read as instability rather than as skill.

4. **Ranking transfers; concentration does not.** No model retained
   concentration skill on unseen districts on either the original or the log
   scale. Exceedance ranking transferred, and classification against the WHO
   guideline is unaffected by the substitution rule, since a well reported
   below 6.0 µg/L is below 10 µg/L whatever value is filled in.

5. **The fitted model earns nothing over the cheapest measurement it
   contains.** On unseen districts a single dissolved iron reading ranked wells
   better than the model built on iron, manganese and depth, 0.891
   against 0.828 (1.8e-08, interval
   0.042 to 0.094), held its advantage within the Holocene aquifers
   (0.876 against 0.809), and missed fewer
   contaminated wells at every laboratory burden. On the development wells the
   ordering reversed, 0.867 against 0.742. The model is
   not weak; it is fitted, and a raw concentration has no coefficients to lose
   in transit.

6. **Calibrated uncertainty is local.** Coverage held between
   89.8 % and 91.7 % within the study area but ranged from
   72.7 % to 99.0 % on transfer, with no advance
   indication of direction. Width is a separate constraint: the arsenic
   interval spans 299 to 318 µg/L against a
   10 µg/L guideline.

7. **The models use the expected process.** Arsenic rises along the reducing
   cascade (259 wells, Jonckheere-Terpstra z = +3.88,
   p = 1.0e-04), and no well in the pre-Holocene units exceeds the guideline.

8. **The practical scope is narrower than the premise suggests.** Only arsenic
   and uranium both exceed a guideline here and survive spatial validation, and
   arsenic is already served by a cheaper field kit. Uranium remains a
   hypothesis, exceeding in four wells. Manganese, used here as a predictor
   rather than screened as a target, exceeds the WHO health based value in most
   of these wells and is the hazard a field kit could address directly.

For monitoring programmes the implication is specific. Field measurable
parameters can order wells by risk well enough to halve a laboratory workload
while missing very few contaminated wells, but they cannot say how contaminated
a well is, and no rule is stable across regions: iron's area under the curve
runs from 0.731 to 0.993 across the external
districts. A programme entering a district it has not measured should calibrate
against a small laboratory sub-sample before adopting any threshold.

Two recommendations follow for data collection rather than for modelling.
Surveys should record pH and redox potential, without which surrogate screening
for the redox sensitive metals is not possible. And detection limits should be
chosen and reported with the intended analysis in mind, since a limit set close
to ambient concentrations forecloses modelling, distorts occurrence estimates,
and as shown here can create apparent structure where none exists.

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
