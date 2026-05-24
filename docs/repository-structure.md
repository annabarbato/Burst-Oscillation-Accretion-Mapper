# Repository Structure

Last updated: 2026-05-24

This document records the Phase 0 repository structure proposal from `docs/roadmap.md`. It is intentionally a foundation document, not a pipeline implementation plan. The architecture remains canonical in `docs/architecture.md`.

## Current Layout

```text
.
|-- AGENTS.md
|-- LICENSE
|-- data/
|   |-- README.md
|   `-- manifests/
|       |-- README.md
|       |-- observations.csv
|       |-- references.csv
|       |-- sources.csv
|       `-- validation_targets.csv
|-- docs/
|   |-- architecture.md
|   |-- environment.md
|   |-- repository-structure.md
|   |-- roadmap.md
|   `-- source-citation-policy.md
|-- notebooks/
|   `-- README.md
|-- pipelines/
|   `-- README.md
|-- src/
|   `-- README.md
`-- tests/
    |-- README.md
    `-- validate_manifests.py
```

## Directory Roles

- `docs/`: canonical project design, roadmap, repo conventions, and future design notes.
- `data/manifests/`: small, tracked CSV inputs for source metadata, observation curation, validation target selection, references, and reproducibility manifests.
- `data/`: local data area. Large raw, processed, and derived mission products must stay out of Git unless a future task explicitly adds a tiny test fixture.
- `src/`: future Python package code. No pipeline code belongs here until the Phase 0 foundation and environment decisions are complete.
- `tests/`: automated checks and future small synthetic fixtures. The current Phase 0 check validates manifest schemas and curation rules.
- `pipelines/`: future Snakemake, Nextflow, or script entrypoints for reproducible execution.
- `notebooks/`: exploratory notebooks and review notebooks. Notebooks are never the source of truth for catalog products or scientific claims.

## Phase Boundaries

- Phase 0 may add structure, manifests, documentation, citation policy, environment decisions, validation checks, and validation target curation.
- Phase 1 may add RXTE ingestion, burst detection, targeted oscillation search, candidate scoring, control intervals, and catalog writes.
- Later-phase work must not appear in these directories until the roadmap phase is explicitly advanced.

## Data Rules

- Do not commit downloaded HEASARC data, mission event files, processed event tables, generated spectra, generated light curves, database files, or dashboard artifacts.
- Commit only small manifests, schemas, synthetic fixtures, documentation, and code.
- Every future data-producing command must record enough provenance to connect outputs back to source manifests, raw products, software versions, screening settings, and search configuration.
