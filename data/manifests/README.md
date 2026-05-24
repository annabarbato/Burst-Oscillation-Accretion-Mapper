# Phase 0 Manifests

These manifests are the first data-facing Phase 0 artifact. They define how source metadata and RXTE validation targets will be recorded before any ingestion code exists.

Canonical design constraints:

- Follow `docs/architecture.md` for provenance, source metadata, instrument handling, and RXTE-first validation.
- Follow `docs/roadmap.md` Phase 0 for scope: source-list seed design, validation-target list design, and citation/source tracking.
- Do not add a source, spin, coordinate, ephemeris, or validation target without a reference.
- Do not use these manifests to bypass later pipeline provenance. They are seed inputs, not science outputs.

## Files

- `sources.csv`: source-level seed metadata for known thermonuclear bursters and candidate RXTE validation sources.
- `validation_targets.csv`: small, curated RXTE MVP target list used to choose the first ObsIDs and sources for Phase 1 validation.
- `references.csv`: tracked index of authoritative sources used by docs, manifests, and future provenance records.

The current rows are source-level Phase 1 candidates only. Exact RXTE ObsIDs and MINBAR burst IDs are intentionally left blank until the next curation pass verifies observation-level targets.

## Source Manifest Columns

`sources.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `source_id` | Yes | Stable internal ID, lower snake case, e.g. `example_source`. |
| `canonical_name` | Yes | Preferred source name used in docs, manifests, and catalog joins. |
| `aliases` | No | Pipe-separated aliases. |
| `ra_deg` | Yes | Right ascension in decimal degrees. |
| `dec_deg` | Yes | Declination in decimal degrees. |
| `coordinate_ref` | Yes | Reference for coordinates. |
| `source_class` | No | Source class such as atoll, AMXP, UCXB, or unknown. |
| `known_spin_hz` | No | Known spin or burst-oscillation frequency in Hz. |
| `spin_ref` | No | Reference for spin or burst-oscillation frequency. |
| `binary_ephemeris_ref` | No | Reference for binary ephemeris, if used. |
| `minbar_name` | No | Matching MINBAR source name, if available. |
| `rxte_priority` | No | Phase 1 validation priority: `high`, `medium`, `low`, or blank. |
| `notes` | No | Short curation notes and caveats. |

Rules:

- Coordinates must be decimal degrees, not sexagesimal text.
- Frequencies must be numeric Hz values with references; leave blank when unknown or uncertain.
- Use blank fields rather than guessed values.
- If an ephemeris is source-specific and time-limited, describe the caveat in `notes`.

## Validation Target Columns

`validation_targets.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `target_id` | Yes | Stable internal ID for the validation target row. |
| `source_id` | Yes | Must match `sources.csv`. |
| `instrument` | Yes | Must be `RXTE/PCA` for Phase 1 validation targets. |
| `obs_id` | No | RXTE ObsID when the target is an observation-specific test. |
| `minbar_burst_id` | No | MINBAR burst identifier or table reference, if available. |
| `validation_goal` | Yes | What this target validates: `burst_detection`, `known_oscillation_recovery`, `non_detection_control`, `false_positive_control`, or `timing_fixture`. |
| `expected_signal` | Yes | `secure_detection`, `probable_detection`, `non_detection`, `control`, or `unknown`. |
| `expected_frequency_hz` | No | Expected oscillation frequency if the target has a known signal. |
| `frequency_ref` | No | Reference for expected frequency. |
| `burst_time_ref` | No | Reference for burst timing, usually MINBAR or a paper. |
| `priority` | Yes | `high`, `medium`, or `low`. |
| `notes` | No | Short review notes and caveats. |

Rules:

- Phase 1 validation targets must be RXTE/PCA only.
- Include both expected detections and expected non-detections before Phase 1 is considered complete.
- Do not mark a target as `secure_detection` without a reference for the expected frequency or burst-oscillation detection.
- Keep the initial Phase 1 target list small: 3-5 known burst-oscillation sources, as described in the roadmap.

## Reference Manifest Columns

`references.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `ref_id` | Yes | Stable lower snake case identifier for reuse in manifests and docs. |
| `category` | Yes | Reference type: `mission_status`, `instrument_spec`, `catalog`, `software_doc`, `literature`, or `ephemeris`. |
| `title` | Yes | Short human-readable source title. |
| `url` | Yes | Authoritative URL where the source can be checked. |
| `doi` | No | DOI when available. |
| `bibcode` | No | ADS bibcode when available. |
| `version_or_date` | No | Source version, publication year, catalog release, or mission notice date. |
| `checked_date` | Yes | Date the source was checked in `YYYY-MM-DD` format. |
| `authoritative_for` | Yes | Concise statement of what this source supports. |
| `notes` | No | Short caveats. |

Rules:

- Add a reference row before adding durable new science, mission, instrument, catalog, software, or ephemeris claims.
- Use `mission_status` for claims that can change and include a current checked date.
- Prefer primary mission pages, catalog docs, peer-reviewed papers, ADS-linked records, or official software docs.
- Keep `authoritative_for` narrow so future reviewers know exactly why the source was cited.

## Curation Workflow

1. Add or update `sources.csv` rows with references for coordinates, source class, spin/frequency, and MINBAR mapping.
2. Add `validation_targets.csv` rows only after the source row exists.
3. Add or reuse `references.csv` rows for durable claims and source-specific values.
4. Prefer RXTE/PCA targets with MINBAR coverage for the first Phase 1 MVP.
5. Record missing but important references in `notes`; do not guess.
6. Run `python tests/validate_manifests.py` after manifest edits.

## Current Seed Status

The initial high-priority validation seed contains four RXTE/PCA burst-oscillation sources:

- 4U 1636-536 at approximately 581 Hz.
- 4U 1728-34 at approximately 363 Hz.
- 4U 1702-429 at approximately 330 Hz.
- KS 1731-260 at approximately 524 Hz.

These rows are enough to drive the next Phase 0 task: selecting exact RXTE ObsIDs and MINBAR burst references. They are not yet enough for Phase 1 implementation because the observation-level targets are still blank.

References checked on 2026-05-24:

- SIMBAD source coordinates and LMXB object types: https://simbad.u-strasbg.fr/simbad/
- 4U 1636-536 581 Hz burst oscillation reference: https://academic.oup.com/mnras/article/383/1/387/1070628
- 4U 1728-34 363 Hz RXTE burst oscillation reference: https://academic.oup.com/mnras/article/455/2/2004/1123266
- 4U 1702-429 near-330 Hz RXTE burst oscillation reference: https://ntrs.nasa.gov/citations/19990023258
- KS 1731-260 near-524 Hz RXTE burst oscillation reference: https://arxiv.org/abs/astro-ph/0003229
