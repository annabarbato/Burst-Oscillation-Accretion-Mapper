# Burst-Oscillation Accretion Mapper

Burst-Oscillation Accretion Mapper is a planned, selection-function-corrected pipeline for discovering and interpreting thermonuclear burst oscillations in neutron-star low-mass X-ray binaries.

The project is intentionally framed around burst oscillations near neutron-star spin frequencies, not generic 500 Hz to 1 kHz peak finding or kHz QPO searches. Its core scientific question is whether accretion state and burst ignition conditions affect oscillation detectability, amplitude, burst phase, harmonic content, and frequency drift after controlling for sensitivity.

## Current Status

Phase 0 is closed. The repository contains the architecture, roadmap, environment notes, source/reference manifests, RXTE/PCA validation targets, and manifest validation checks needed to ground the RXTE validation MVP.

Phase 1 implementation scaffolding is in place for RXTE/PCA validation: event products, light curves, burst detection summaries, MINBAR timing matches, targeted oscillation search, conservative candidate scoring, controls, development catalog rows, and validation-run gates. Real RXTE FITS parsing and HEASoft execution remain an operational follow-up once local raw products and tool availability are confirmed.

## Key Documents

- [Architecture](docs/architecture.md): technical architecture, scientific framing, pipeline modules, data products, storage model, candidate classes, and inference layer.
- [Roadmap](docs/roadmap.md): phase-by-phase build plan and acceptance criteria.
- [Phase 0 status](docs/phase-0-status.md): closed Phase 0 gate and selected RXTE/PCA validation set.
- [Phase 1 status](docs/phase-1-status.md): current RXTE validation MVP implementation status and explicit deferrals.
- [Repository structure](docs/repository-structure.md): proposed directories and ownership boundaries.
- [Environment strategy](docs/environment.md): local scientific tooling plan and packaging path.
- [Source citation policy](docs/source-citation-policy.md): rules for dated mission, catalog, software, and literature claims.
- [Manifest guide](data/manifests/README.md): CSV schema and curation workflow for Phase 0 manifests.

## Phase 0 Validation Set

The initial RXTE/PCA validation seed includes exact ObsIDs and MINBAR burst links for:

- 4U 1636-536, secure 581 Hz recovery target.
- 4U 1728-34, secure 363 Hz recovery target.
- 4U 1728-34, expected non-detection control.
- 4U 1702-429, probable near-330 Hz recovery target for Phase 1 review.
- KS 1731-260, probable near-524 Hz recovery target for Phase 1 review.

These rows live in [observations.csv](data/manifests/observations.csv) and [validation_targets.csv](data/manifests/validation_targets.csv).

## Repository Layout

```text
docs/                 Architecture, roadmap, environment, and status docs.
data/manifests/       Tracked CSV manifests and reference index.
src/                  Phase 1 Python package modules.
tests/                Manifest checks and lightweight unit tests.
```

Generated science products, raw event files, and local catalogs stay outside git; tracked code and manifests preserve the reproducible shape of the validation run.

## Validate Manifests

Run the manifest check with:

```powershell
python tests\validate_manifests.py
```

The validator checks manifest schemas, source and observation references, RXTE/PCA-only Phase 0/1 targets, required references, and basic field constraints.

Run the Python test suite with:

```powershell
python -m pytest
```

## Data Policy

Mission event files, calibrated products, FITS files, Parquet/HDF5 outputs, SQLite/PostgreSQL exports, plots, and other generated science products should not be committed. Track durable metadata and provenance in manifests, then keep raw and processed products under ignored local data paths.

