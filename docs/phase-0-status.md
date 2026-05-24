# Phase 0 Status

Last updated: 2026-05-24

This checklist tracks the current Phase 0 state against `docs/roadmap.md`. It is not a replacement for the roadmap or architecture; it is the working gate that says whether the repository is ready to advance to Phase 1.

## Deliverables

| Roadmap item | Status | Evidence |
| --- | --- | --- |
| Architecture and roadmap docs | Complete | `docs/architecture.md`, `docs/roadmap.md` |
| Source-list seed file design | Complete | `data/manifests/sources.csv`, `data/manifests/README.md` |
| Known-source seed rows | Complete for source-level seeds | Four RXTE/PCA high-priority burst-oscillation sources in `sources.csv` |
| Validation-target list for RXTE MVP | Partial | Source-level targets exist; exact RXTE ObsIDs and MINBAR burst IDs remain blank |
| Environment decision | Complete | `docs/environment.md` |
| Citation/source tracking policy | Complete | `docs/source-citation-policy.md`, `data/manifests/references.csv` |
| Initial repository structure proposal | Complete | `docs/repository-structure.md` |
| Manifest sanity check | Complete | `tests/validate_manifests.py` |
| Git hygiene for generated data | Complete | `.gitignore` |

## Acceptance Criteria

| Criterion | Status | Notes |
| --- | --- | --- |
| A new contributor can explain the scientific question, selection correction, and RXTE-first strategy | Complete | Covered in architecture, roadmap, and agent rules |
| Required external tools and data sources are identified before code | Complete | HEASoft, NICERDAS, CALDB, HEASARC, MINBAR, SIMBAD, RXTE/PCA, NICER/XTI, and Stingray references are tracked |
| Current mission/catalog claims are timestamped and linked | Complete | Dated source notes and `references.csv` rows exist |

## Validation Checks

| Check | Status | Evidence |
| --- | --- | --- |
| Confirm RXTE/PCA and NICER/XTI assumptions against HEASARC | Complete | Architecture notes and reference manifest rows |
| Confirm MINBAR counts and validation utility | Complete | Architecture notes and MINBAR reference rows |
| Confirm Stingray timing primitives | Complete | Architecture notes and Stingray reference row |
| Validate tracked manifests | Complete | `python tests/validate_manifests.py` |

## Remaining Phase 0 Work

Phase 0 should not advance to Phase 1 until the RXTE validation target list is observation-level rather than only source-level.

Remaining tasks:

- Select exact RXTE/PCA ObsIDs for the initial 3-5 validation sources.
- Add matching `observations.csv` rows with archive references and curation status.
- Add MINBAR burst identifiers or table references where available.
- Add at least one expected non-detection or control target before Phase 1 validation claims begin.
- Re-run `python tests/validate_manifests.py` after every manifest edit.

## Phase 1 Gate

Phase 1 can begin when:

- `observations.csv` contains a small RXTE/PCA validation set with checked archive references.
- `validation_targets.csv` links source-level goals to exact ObsIDs where needed.
- The target list includes known detections and at least one non-detection or control.
- The manifest validator passes.

