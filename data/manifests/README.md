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

Both files are intentionally schema-only for now. Filling them with real targets is a separate Phase 0 task because each row needs literature or catalog references.

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
| `validation_goal` | Yes | What this target validates: burst detection, known oscillation recovery, non-detection control, false-positive control, or timing fixture. |
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

## Curation Workflow

1. Add or update `sources.csv` rows with references for coordinates, source class, spin/frequency, and MINBAR mapping.
2. Add `validation_targets.csv` rows only after the source row exists.
3. Prefer RXTE/PCA targets with MINBAR coverage for the first Phase 1 MVP.
4. Record missing but important references in `notes`; do not guess.
5. Run the manifest sanity checks once a validation script exists.

