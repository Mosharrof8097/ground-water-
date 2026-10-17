# Low-Cost Surrogate Screening for Trace Metals in Groundwater

A fresh project, separate from the earlier North Bengal work in this repository.
Nothing here reads from or writes to `groundwater_pipeline/`, `app/`, `data/` or
`paper_publication_bundle/` — those stay exactly as they are.

## Research question

**Which trace metals in groundwater can be predicted from parameters that are
cheap to measure in the field, and which cannot?**

The point is not to build one more arsenic map. It is to establish, honestly and
across many metals at once, *where low-cost surrogate screening is feasible at
all* — and to report the failures as results rather than hiding them.

Three things make this answerable here and not in the earlier work:

1. **The predictors are genuinely cheap.** pH, Eh, specific conductance,
   temperature and dissolved oxygen come from field meters; Fe, Mn and NO₃-N
   from test kits; Cl and alkalinity from titration. The earlier project's
   "easy" inputs (`pH_proxy`, `TDS_calc`) were derived from a full laboratory
   ion panel, which quietly broke the low-cost premise.
2. **Redox is measured.** Eh is the master control on trace-metal mobility and
   was absent from the earlier dataset entirely.
3. **N = 271 rather than 40**, with 13 candidate target metals.

## Target

Q1 journal — *Science of the Total Environment*, *Journal of Hydrology*, or
*Environmental Pollution* class. See `06_manuscript/DRAFT.md` for the framing.

## Intended contributions

1. **A multi-metal feasibility audit.** Thirteen metals, tiered predictor sets,
   nested cross-validation, with negative results reported as findings.
2. **Calibrated uncertainty via conformal prediction.** A literature scan found
   quantile-regression and ensemble approaches in groundwater-quality modelling
   but no conformal treatment. Coverage is to be evaluated on held-out splits —
   never on the residuals used for calibration, which is circular and returns
   the nominal rate even for a zero-skill model.
3. **Censoring treated as a first-class constraint.** Censoring rates here range
   from 0 % to 97 %. The working hypothesis is that detection limits, not
   geochemistry, decide which metals are modellable. Substituting DL/2 is known
   to be poor practice (Helsel); the plan is to use censoring-aware methods and
   quantify how much the substitution shortcut distorts conclusions.

## Pipeline

| Stage | Folder | Status |
|---|---|---|
| 0 | `00_data/` | **done** — raw data + provenance in `00_data/README.md` |
| 1 | `01_data_cleaning/` | **done** — parse, type, preserve censoring flags |
| 2 | `02_preprocessing/` | **done** — predictor tiers E1–E4, target selection |
| 3 | `03_methods/` | *scaffold* — feasibility audit, conformal |
| 4 | `04_results/` | *empty* — tables, figures, metrics land here |
| 5 | `05_tests/` | **done** — validates stages 1–2 |
| 6 | `06_manuscript/` | *skeleton* — `DRAFT.md` |

Run everything:

```bash
cd q1_surrogate_screening
pip install -r requirements.txt
python run_pipeline.py
python 05_tests/test_pipeline.py
```

Each stage writes to `00_data/interim/` or `04_results/` and can be run alone.

## Design rules

Carried over from the earlier project, where several were learned the hard way:

- Imputation, scaling and hyperparameter search happen **inside** the
  cross-validation fold, never before it.
- No synthetic data, no SMOTE, no resampling as training data.
- Conformal coverage is measured on held-out splits only.
- Every reported number is read from a metrics file — never hardcoded into a
  table or figure script.
- Censoring flags travel with the data; DL/2 substitution is a documented
  choice at the point of use, not a silent default.
- Negative results are reported.

## Known caveats

- The special study areas were **selected because they are arsenic-affected**,
  so the 58 % As exceedance rate is not a national figure. Fine for a
  feasibility study; it does not support prevalence claims.
- Data are from 1998–99. Suitable for the methodological question; not a
  statement about present-day conditions.
- `WELL_DEPTH` is a reported figure, not a surveyed screen depth.
