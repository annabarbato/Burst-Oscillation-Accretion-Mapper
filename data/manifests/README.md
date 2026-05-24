# Phase 0 Manifests

These manifests are the first data-facing Phase 0 artifact. They define how source metadata and RXTE validation targets will be recorded before any ingestion code exists.

Canonical design constraints:

- Follow `docs/architecture.md` for provenance, source metadata, instrument handling, and RXTE-first validation.
- Follow `docs/roadmap.md` Phase 0 for scope: source-list seed design, validation-target list design, and citation/source tracking.
- Do not add a source, spin, coordinate, ephemeris, or validation target without a reference.
- Do not use these manifests to bypass later pipeline provenance. They are seed inputs, not science outputs.

## Files

- `sources.csv`: source-level seed metadata for known thermonuclear bursters and candidate RXTE validation sources.
- `observations.csv`: observation-level manifest for future RXTE ObsID curation, archive links, local raw-product status, and provenance keys.
- `validation_targets.csv`: small, curated RXTE MVP target list used to choose the first ObsIDs and sources for Phase 1 validation.
- `references.csv`: tracked index of authoritative sources used by docs, manifests, and future provenance records.

The current rows include a small observation-level RXTE/PCA validation set with exact ObsIDs and MINBAR burst IDs where available. Phase 1 should use these rows as the initial validation manifest before expanding to additional sources or NICER/XTI.

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

## Observation Manifest Columns

`observations.csv`

| Column | Required | Meaning |
| --- | --- | --- |
| `observation_id` | Yes when rows exist | Stable internal ID, lower snake case, usually source plus ObsID. |
| `source_id` | Yes when rows exist | Must match `sources.csv`. |
| `instrument` | Yes when rows exist | Must be `RXTE/PCA` during Phase 0 and Phase 1. |
| `obs_id` | Yes when rows exist | Mission observation ID. |
| `archive_uri` | No | Authoritative HEASARC or archive URI for the observation. |
| `archive_ref` | No | Reference ID or URL for the archive source. |
| `start_time` | No | Observation start time when curated, preferably ISO-8601 UTC. |
| `stop_time` | No | Observation stop time when curated, preferably ISO-8601 UTC. |
| `exposure_s` | No | Cleaned or catalog exposure in seconds, with caveat in `notes`. |
| `data_mode` | No | RXTE mode such as event mode or GoodXenon, when known. |
| `raw_status` | No | `candidate`, `selected`, `downloaded`, `verified`, or `rejected`. |
| `local_raw_path` | No | Local untracked path for downloaded raw products. |
| `checksum` | No | Checksum for raw products when available. |
| `event_product_uri` | No | Future processed event product path; blank in Phase 0. |
| `software_version` | No | Future processing software version; blank before processing. |
| `caldb_version` | No | Future calibration version; blank before processing. |
| `screening_hash` | No | Future screening configuration hash; blank before processing. |
| `barycorr_ref` | No | Future barycenter correction reference; blank before processing. |
| `quality_flags` | No | Pipe-separated caveats. |
| `notes` | No | Short curation notes and caveats. |

Rules:

- Phase 0 may define the schema and add selected RXTE rows after ObsIDs are reference-checked.
- Do not add NICER/XTI rows until the roadmap advances to NICER work.
- `event_product_uri`, `software_version`, `caldb_version`, `screening_hash`, and `barycorr_ref` remain blank until processing exists.
- Local raw paths must point to untracked local storage; do not commit raw mission products.

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
2. Add `observations.csv` rows only after the source row exists and the ObsID/archive reference is checked.
3. Add `validation_targets.csv` rows only after the source row exists; add `obs_id` only when the matching observation row exists.
4. Add or reuse `references.csv` rows for durable claims and source-specific values.
5. Prefer RXTE/PCA targets with MINBAR coverage for the first Phase 1 MVP.
6. Record missing but important references in `notes`; do not guess.
7. Run `python tests/validate_manifests.py` after manifest edits.

## Current Seed Status

The Phase 0 validation seed contains five RXTE/PCA observation-level targets across four burst-oscillation sources:

- 4U 1636-536 ObsID `10088-01-07-02`, `MINBAR.2257`, secure 581 Hz recovery target.
- 4U 1728-34 ObsID `10073-01-01-00`, `MINBAR.2204`, secure 363 Hz recovery target.
- 4U 1728-34 ObsID `10073-01-02-00`, `MINBAR.2206`, expected non-detection control.
- 4U 1702-429 ObsID `20084-02-01-00`, `MINBAR.2322`, probable near-330 Hz recovery target for Phase 1 review.
- KS 1731-260 ObsID `30061-01-02-01`, `MINBAR.2431`, probable near-524 Hz recovery target for Phase 1 review.

These rows are enough to start the Phase 1 RXTE validation MVP. The two probable recovery targets remain deliberately conservative until event-level Phase 1 checks confirm burst-specific oscillation behavior.

References checked on 2026-05-24:

- SIMBAD source coordinates and LMXB object types: https://simbad.u-strasbg.fr/simbad/
- 4U 1636-536 581 Hz burst oscillation reference: https://academic.oup.com/mnras/article/383/1/387/1070628
- 4U 1636-536 tail oscillation table: https://academic.oup.com/mnras/article/436/3/2276/1249211
- 4U 1728-34 363 Hz RXTE burst oscillation reference: https://academic.oup.com/mnras/article/455/2/2004/1123266
- 4U 1702-429 near-330 Hz RXTE burst oscillation reference: https://ntrs.nasa.gov/citations/19990023258
- KS 1731-260 near-524 Hz RXTE burst oscillation reference: https://arxiv.org/abs/astro-ph/0003229
- MINBAR web interface and burst entries: https://burst.sci.monash.edu/
