# Phase 0 Status

Last updated: 2026-05-24

Status: Closed.

This checklist tracks the current Phase 0 state against `docs/roadmap.md`. It is not a replacement for the roadmap or architecture; it is the working gate that says whether the repository is ready to advance to Phase 1.

## Deliverables

| Roadmap item | Status | Evidence |
| --- | --- | --- |
| Architecture and roadmap docs | Complete | `docs/architecture.md`, `docs/roadmap.md` |
| Source-list seed file design | Complete | `data/manifests/sources.csv`, `data/manifests/README.md` |
| Known-source seed rows | Complete for source-level seeds | Four RXTE/PCA high-priority burst-oscillation sources in `sources.csv` |
| Validation-target list for RXTE MVP | Complete | Five RXTE/PCA observation-level targets in `validation_targets.csv`, including exact ObsIDs and MINBAR burst IDs |
| Environment decision | Complete | `docs/environment.md` |
| Citation/source tracking policy | Complete | `docs/source-citation-policy.md`, `data/manifests/references.csv` |
| Initial repository structure proposal | Complete | `docs/repository-structure.md` |
| Manifest sanity check | Complete | `tests/validate_manifests.py` |
| Git hygiene for generated data | Complete | `.gitignore` |

## RXTE Validation Set

| Role | Source | ObsID | MINBAR burst | Expected signal | Evidence |
| --- | --- | --- | --- | --- | --- |
| Secure recovery | 4U 1636-536 | `10088-01-07-02` | `MINBAR.2257` | 581 Hz detection | `minbar_entry_2257`; `bo_4u_1636_536_tail_osc_table` |
| Secure recovery | 4U 1728-34 | `10073-01-01-00` | `MINBAR.2204` | 363 Hz detection | `minbar_entry_2204`; `bo_4u_1728_34_363hz` |
| Non-detection control | 4U 1728-34 | `10073-01-02-00` | `MINBAR.2206` | Non-detection | `minbar_entry_2206`; `bo_4u_1728_34_363hz` |
| Probable recovery | 4U 1702-429 | `20084-02-01-00` | `MINBAR.2322` | Near-330 Hz source target | `minbar_entry_2322`; `bo_4u_1702_429_330hz` |
| Probable recovery | KS 1731-260 | `30061-01-02-01` | `MINBAR.2431` | Near-524 Hz source target | `minbar_entry_2431`; `bo_ks_1731_260_524hz` |

The two probable recovery rows are intentionally not promoted to secure detections in Phase 0. They are observation-level targets for Phase 1 review against event data and literature details.

## Acceptance Criteria

| Criterion | Status | Notes |
| --- | --- | --- |
| A new contributor can explain the scientific question, selection correction, and RXTE-first strategy | Complete | Covered in architecture, roadmap, and top-level README |
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

None. Phase 0 is closed as of 2026-05-24.

## Phase 1 Gate

Phase 1 can begin because:

- `observations.csv` contains a small RXTE/PCA validation set with checked MINBAR references.
- `validation_targets.csv` links validation goals to exact ObsIDs and MINBAR burst IDs where available.
- The target list includes known detections, probable source-level recovery targets, and one expected non-detection control.
- The manifest validator passes.
