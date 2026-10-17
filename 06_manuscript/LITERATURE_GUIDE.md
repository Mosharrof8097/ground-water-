# Literature extraction — what to collect and why

A filled row in `LITERATURE_EXTRACTION_TEMPLATE.csv` should let you write a
sentence without opening the paper again. The columns exist because each one
feeds a specific claim the Introduction has to make.

The existing `waterrrrrrrrrrrrr.docx` matrix covers block A below and nothing
else. Its term counts: heavy metal 46, health risk 24, PCA 17, WQI 12 —
machine learning 0, surrogate 0, conformal 0, detection limit 0, screening 0.
It is a good start on the domain and no help at all on the methods argument,
which is where this paper's contribution sits.

---

## The claim map

Every claim below needs citations. Collect papers until each row has enough.

| # | Claim the Introduction must make | Papers needed | Have |
|---|---|---|---|
| **A1** | Trace metals in Bengal Basin groundwater are a serious health problem | 5–8 | ✅ 17 in the docx |
| **A2** | Arsenic specifically is widespread and regulated | 3–4 | ✅ in the docx |
| **B1** | Current assessment relies on laboratory ICP-MS/AAS and full ion panels | 6–10 | ✅ use the docx — this is its best use |
| **B2** | Laboratory testing is a binding cost constraint on monitoring coverage | 2–3 | ❌ need |
| **C1** | ML has been applied to groundwater arsenic, mostly spatially | 4–6 | ❌ **critical** |
| **C2** | Those models predict one metal, from geology or location, not chemistry | 2–3 | ❌ **critical** |
| **C3** | Surrogate/proxy prediction from cheap measurements is proposed but rarely audited | 3–4 | ❌ need |
| **D1** | Uncertainty in these models is point estimates or uncalibrated intervals | 3–4 | ❌ need |
| **D2** | Conformal prediction gives distribution-free calibrated intervals | 3–4 | ❌ **critical** |
| **D3** | Conformal validity assumes exchangeability, which spatial transfer breaks | 2–3 | ❌ need |
| **E1** | Left-censored environmental data is standard and substitution is criticised | 3–4 | ❌ **critical** (Helsel) |
| **E2** | Censoring-aware alternatives exist (ROS, Tobit, MLE) | 2–3 | ❌ need |
| **F1** | Random CV leaks across spatially correlated samples | 2–3 | ❌ need (Roberts et al. 2017) |
| **G1** | Redox controls arsenic mobility via reductive dissolution of Fe oxyhydroxides | 4–6 | ⚠️ partly in the docx |
| **G2** | Redox zonation frameworks exist and are standard | 2 | ❌ need (McMahon & Chapelle 2008) |

**Marked ❌ critical = a Q1 reviewer will reject without these.** Submitting
with only block A citations invites "the authors appear unaware of the machine
learning literature on this dataset."

---

## Search terms per block

**B2 — cost of monitoring**
`groundwater monitoring cost developing countries` ·
`arsenic testing cost field kit Bangladesh` ·
`low-cost water quality screening`

**C1, C2 — ML on groundwater metals**
`machine learning groundwater arsenic Bangladesh` ·
`random forest arsenic prediction hazard map` ·
`Podgorski Smedley arsenic machine learning` ·
`groundwater quality prediction XGBoost`
Already known: Podgorski et al. 2020 *ES&T*; Chapainawabganj arsenic ML 2024
*ESPR*; Hossain et al. 2007 geostatistics.

**C3 — surrogate / proxy**
`surrogate model water quality proxy parameters` ·
`predicting trace metals from major ions` ·
`proxy variables groundwater contamination screening`

**D1, D2, D3 — uncertainty**
`conformal prediction environmental data` ·
`Angelopoulos Bates conformal prediction tutorial` ·
`Vovk algorithmic learning in a random world` ·
`conformal prediction distribution shift` ·
`prediction interval groundwater machine learning`

**E1, E2 — censoring**
`Helsel nondetects and data analysis` ·
`substitution detection limit bias environmental` ·
`regression on order statistics censored water quality` ·
`Tobit regression environmental concentration`

**F1 — spatial CV**
`spatial cross-validation Roberts 2017` ·
`spatial autocorrelation model evaluation overfitting`

**G1, G2 — geochemistry**
`reductive dissolution iron oxyhydroxide arsenic Bengal` ·
`McMahon Chapelle redox framework groundwater` ·
`Nickson arsenic mobilisation Bangladesh`

Open-access sources: Google Scholar, Semantic Scholar, PubMed Central,
doaj.org. For paywalled papers the abstract usually fills most columns.

---

## How to fill the table

One row per paper. Keep entries short — a phrase, not a sentence.

**`supports_claim`** is the column that matters most. Put the claim IDs from
the map above, comma separated (`B1,C2`). When you write, filter on this column
and every citation for that sentence is in front of you.

**`predictor_cost_class`** — use exactly one:
- `field` — meter or test kit only
- `lab_major_ions` — needs an ion panel
- `lab_icpms` — needs ICP-MS/AAS
- `geospatial` — geology, elevation, land use, coordinates
- `mixed` — say which in `notes`

This column alone proves claim B1. If every row says `lab_icpms`, you can write
that no existing assessment uses field-measurable inputs — and you will have
the evidence, not just the assertion.

**`validation_scheme`** — `none` · `train_test` · `random_cv` · `spatial_cv` ·
`external`. Most will be `random_cv` or `none`, which supports F1 and makes
your spatial CV and external validation stand out.

**`uncertainty_reported`** — `none` · `point_only` · `confidence_interval` ·
`quantile` · `bootstrap` · `conformal`. Expect almost no `conformal`. That is
claim D1 and your contribution.

**`censoring_handling`** — `not_stated` · `ignored` · `substitute_half` ·
`substitute_zero` · `ros` · `tobit` · `mle`. Expect `not_stated` to dominate.
That silence is itself the finding for E1.

---

## Target: 35–45 papers

| Block | Papers | Status |
|---|---|---|
| A — domain context | 10–12 | ✅ have 17 |
| B — cost of current practice | 6–8 | partly, reuse A |
| C — ML and surrogate modelling | 8–10 | ❌ |
| D — uncertainty and conformal | 6–8 | ❌ |
| E — censored data | 4–5 | ❌ |
| F — spatial validation | 2–3 | ❌ |
| G — redox geochemistry | 5–6 | ⚠️ partly |

Roughly 25 new papers. At a few minutes each from the abstract, that is two or
three working sessions.

---

## Two cautions

**Do not reuse the research-gap column from the existing docx.** Those are
domain gaps — microbial–geochemical interaction, monitoring policy. Your gap is
methodological. Different sentence, different evidence.

**Record what each paper did, not what it concluded.** The argument here is
about method, so `predictor_cost_class`, `validation_scheme`,
`uncertainty_reported` and `censoring_handling` carry the weight. A paper with
an unremarkable conclusion can still be the perfect citation for "everyone uses
DL/2 substitution without saying so."
