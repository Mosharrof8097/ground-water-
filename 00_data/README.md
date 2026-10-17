# Data

Third-party data. Nothing here was collected by this project.
**`raw/` is read-only** — no stage writes to it. Cleaned output goes to
`interim/`, which stage 1 creates.

## Citation (required)

> BGS and DPHE (2001). *Arsenic contamination of groundwater in Bangladesh.*
> Kinniburgh, D.G. and Smedley, P.L. (eds). British Geological Survey Technical
> Report WC/00/19. British Geological Survey, Keyworth.

Funded by DFID, carried out by the British Geological Survey with the Department
of Public Health Engineering, Government of Bangladesh. **Any publication using
these data must acknowledge DFID and the BGS/DPHE partners.** Reuse is otherwise
free.

Downloaded 17 October 2026 from the BGS groundwater pages. Integrity:
`md5sum -c raw/CHECKSUMS.md5`.

## Files

| File | Wells | Role |
|---|---|---|
| `special_study_areas_271_boreholes.csv` | 271 | **primary** — the only file with field and redox parameters |
| `NHS_national_survey_3534_boreholes.csv` | 3,534 | national context; no pH/Eh, no Cd/Ni/Pb, no anions |
| `village_survey_mandari_236_boreholes.csv` | 236 | Lakshmipur only; limited suite |
| `NHS_additional_trace_elements_icpms.csv` | ~25 | Cd, Ni, Pb + rare earths by ICP-MS |

Source URLs are listed at the bottom.

### Why `special_study_areas` is the primary file

It is the only one carrying measured `pH`, `Eh`, `diss O2`, `DOC`, `SEC` and
`T` alongside the trace metals. Districts: Nawabganj 125, Lakshmipur 74,
Faridpur 64, Noakhali 8. Nawabganj (Chapai Nawabganj) is in North Bengal.

## File format

Every BGS CSV has the same shape:

```
line 1-4   banner text (organisation, project, "National Survey Data", release date)
line 5     column names
line 6     units
line 7+    data
```

Read with `skiprows=4`, then drop the first row (units). Stage 1 handles this.

**Left-censored values are strings prefixed with `<`** — e.g. `< 0.02` means
"below a detection limit of 0.02". Stage 1 splits each measured column into a
numeric column holding the detection limit and a `*_censored` boolean, so no
substitution rule is baked in at read time.

**`pH` contains `0.00` as a missing-value sentinel.** Stage 1 converts it to
NaN. No other column is known to use a sentinel, but stage 5 range-checks them.

## Columns in the primary file

**Identifiers and location** — `SAMPLE_ID`, `SAMPLE_FIELD_ID`, `SAMPLE_DATE`,
`LAT_DEG`, `LONG_DEG` (real well coordinates, not administrative centroids),
`YEAR_CONSTRUCTION`, `WELL_TYPE`, `WELL_DEPTH` (m), `DIVISION`, `DISTRICT`,
`THANA`, `UNION`, `MOUZA`, `GEOCODE`.

**Candidate low-cost predictors**

| Column | Unit | How measured | non-null | censored |
|---|---|---|---|---|
| `pH` | – | field meter | 260 | 0 |
| `Eh` | mV | field meter | 269 | 0 |
| `SEC` | µS/cm | field meter | 271 | 0 |
| `T` | °C | field meter | 271 | 0 |
| `diss O2` | mg/L | field meter | 268 | 201 |
| `Fe` | mg/L | field test kit | 271 | 1 |
| `Mn` | mg/L | field test kit | 271 | 1 |
| `NO3-N` | mg/L | field test kit | 271 | 217 |
| `Cl` | mg/L | titration | 269 | 0 |
| `HCO3` | mg/L | titration | 271 | 0 |
| `SO4` | mg/L | kit | 271 | 57 |
| `NH4-N` | mg/L | kit | 271 | 87 |
| `DOC` | mg/L | laboratory | 258 | 9 |
| `WELL_DEPTH` | m | well record | 261 | 0 |

`diss O2` and `NO3-N` are heavily censored and are expected to carry little
information despite being cheap.

**Candidate targets** (all require laboratory ICP-MS; `AsTot`/`AsIII` by
hydride generation)

| Column | WHO limit (µg/L) | censored | median | max | exceeding |
|---|---|---|---|---|---|
| `AsTot` | 10 | 34 % | 22.0 | 2400 | 156/271 |
| `AsIII` | – | 52 % | 6.0 | 2540 | – |
| `Ni` | 20 | 1 % | 2.40 | 18.8 | 0 |
| `Zn` | 3000 | 0 % | 8.0 | 301 | 0 |
| `Mo` | 70 | 7 % | 1.10 | 20.5 | 0 |
| `U` | 30 | 23 % | 0.42 | 47.1 | 4/271 |
| `Pb` | 10 | 13 % | 0.10 | 28.6 | 1/271 |
| `Ba` | 1300 | 0 % | 0.114 | 0.7 | 0 |
| `Sb` | 20 | 46 % | 0.03 | 1.2 | 0 |
| `Se` | 40 | 7 % | 0.20 | 0.2 | 0 |
| `Cu` | 2000 | 81 % | 1.0 | 19.3 | 0 |
| `Cd` | 3 | 84 % | 0.02 | 0.2 | 0 |
| `Cr` | 50 | 97 % | 0.5 | 1.3 | 0 |

Stable isotopes `d13C`, `d18O`, `d2H`, `d34S` are present and unused for now.

Read these numbers as the reason for the research question, not as results:
`Cr` at 97 % censored and `Se` with no variation at all cannot be modelled by
any method. Whether `Cd` at 84 % can is an open question stage 3 should answer
rather than assume.

## Relationship to the earlier project's 40 samples

The earlier dataset (`data/raw/` at the repository root) uses the **same
sample-ID convention** (`S98_xxxxx`), so it very likely comes from the same
BGS/DPHE programme. But its ID block `S98_01785`–`S98_01834` **appears in none
of these public files**:

| File | ID numeric range |
|---|---|
| National survey | 701 – 7383 (no rows in the 1785–1834 window) |
| Special study areas | 331 – 916 |

Provenance of those 40 is still unconfirmed — possibly WC/00/19 **Volume 4
(Data compilation)**, or a direct DPHE release. Worth asking the supervisor,
since more may be available from the same source. Those 40 are **not** used
here; if their provenance is confirmed they could serve as an external
validation set.

## Source URLs

- Index: https://www.bgs.ac.uk/groundwater/quality/groundwater-and-health/arsenic-contamination-of-groundwater/bangladesh-reports/
- Special study areas: https://www.bgs.ac.uk/groundwater/download/bangladesh-special-study-areas/
- National survey: https://www.bgs.ac.uk/groundwater/download/dphe-bgs-national-hydrochemical-survey/
- Village survey: https://www.bgs.ac.uk/groundwater/download/bangladesh-village-survey/
- Additional trace elements: https://www.bgs.ac.uk/groundwater/download/additional-nhs-data-for-some-trace-elements/
- Volume 4 (Data compilation), PDF: https://www.bgs.ac.uk/groundwater/download/arsenic-contamination-groundwater-bangladesh-vol4-data-compilation/
