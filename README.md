# Burst-Oscillation Accretion Mapper

Burst-Oscillation Accretion Mapper is a planned, selection-function-corrected pipeline for discovering and interpreting thermonuclear burst oscillations in neutron-star low-mass X-ray binaries.

The project is intentionally framed around burst oscillations near neutron-star spin frequencies, not generic 500 Hz to 1 kHz peak finding or kHz QPO searches. Its core scientific question is whether accretion state and burst ignition conditions affect oscillation detectability, amplitude, burst phase, harmonic content, and frequency drift after controlling for sensitivity.

## Current Status

Phase 0 is closed. The repository contains the architecture, roadmap, environment notes, source/reference manifests, RXTE/PCA validation targets, and manifest validation checks needed to ground the RXTE validation MVP.

Phase 1 is strictly closed out for the selected RXTE/PCA validation set. The repository now includes RXTE event/FITS and SingleBit binned readers, real orbit-file barycentric correction through HEASoft `barycorr`, explicit GoodXenon pairing status, targeted `Z_1^2` search, conservative candidate scoring, pre/post and neighboring controls, synthetic Poisson null controls, SQLite/JSON validation output, and a strict validation gate.

The Phase 1 closeout run recovered all five selected MINBAR burst windows, recovered the two strongest known-signal validation targets, kept the expected MINBAR.2206 non-detection as marginal review rather than an accepted detection, and produced no secure or probable controls across the expanded control set. Binary orbital correction remains gated on curated source ephemerides.

Phase 2 has started with the injection/recovery product contract and tiny schema fixtures. It should add sensitivity curves and amplitude upper limits before any population or accretion-state correlation claims.

Source-backed project claims are indexed in [references.csv](data/manifests/references.csv). Current or operational claims carry checked dates in the status docs; local validation results are produced by [run_phase1_real_validation.py](pipelines/run_phase1_real_validation.py) and summarized in the ignored `data/products/phase1_real_validation/summary.json` artifact.

## Key Documents

- [Architecture](docs/architecture.md): technical architecture, scientific framing, pipeline modules, data products, storage model, candidate classes, and inference layer.
- [Roadmap](docs/roadmap.md): phase-by-phase build plan and acceptance criteria.
- [Phase 0 status](docs/phase-0-status.md): closed Phase 0 gate and selected RXTE/PCA validation set.
- [Phase 1 status](docs/phase-1-status.md): current RXTE validation MVP implementation status and explicit deferrals.
- [Phase 2 status](docs/phase-2-status.md): selection-function and injection/recovery progress.
- [Phase 2 injection/recovery contract](docs/phase-2-injection-recovery-contract.md): product contract and fixture rules before broad simulation machinery.
- [Repository structure](docs/repository-structure.md): proposed directories and ownership boundaries.
- [Environment strategy](docs/environment.md): local scientific tooling plan and packaging path.
- [Source citation policy](docs/source-citation-policy.md): rules for dated mission, catalog, software, and literature claims.
- [Manifest guide](data/manifests/README.md): CSV schema and curation workflow for Phase 0 manifests.

## RXTE Validation Set

The initial RXTE/PCA validation seed includes exact ObsIDs and MINBAR burst links for:

- 4U 1636-536, secure 581 Hz recovery target: `minbar_entry_2257`, `bo_4u_1636_536_581hz`, and `bo_4u_1636_536_tail_osc_table`.
- 4U 1728-34, secure 363 Hz recovery target: `minbar_entry_2204` and `bo_4u_1728_34_363hz`.
- 4U 1728-34, expected non-detection control: `minbar_entry_2206` and `bo_4u_1728_34_363hz`.
- 4U 1702-429, probable near-330 Hz recovery target for Phase 1 review: `minbar_entry_2322` and `bo_4u_1702_429_330hz`.
- KS 1731-260, probable near-524 Hz recovery target for Phase 1 review: `minbar_entry_2431` and `bo_ks_1731_260_524hz`.

These rows live in [observations.csv](data/manifests/observations.csv) and [validation_targets.csv](data/manifests/validation_targets.csv).

## Citation Map

- RXTE/PCA validation order, instrument capability, and archive context: `rxte_pca_heasarc`, `minbar_paper`, and `minbar_home`.
- NICER/XTI status and future backend assumptions: `nicer_heasarc_status`, `nasa_nicer_status_updates`, `nicer_instrument_heasarc`, and `nicer_analysis_docs`.
- Source coordinates, aliases, and source classes: `simbad`.
- Source-level burst-oscillation frequency seeds and validation labels: the `bo_*` literature rows in [references.csv](data/manifests/references.csv).
- MINBAR burst timing and ObsID mappings: the `minbar_entry_*` catalog rows in [references.csv](data/manifests/references.csv).
- Timing and mission-tool software assumptions: `heasoft_docs`, `stingray_docs`, and `caldb_docs`.

## Repository Layout

```text
docs/                 Architecture, roadmap, environment, and status docs.
data/manifests/       Tracked CSV manifests and reference index.
pipelines/            Reproducible local validation entrypoints.
src/                  Phase 1 Python package modules.
tests/                Manifest checks and lightweight unit tests.
```

Generated science products, raw event files, and local catalogs stay outside git; tracked code and manifests preserve the reproducible shape of the validation run.

## Run Checks

Run the manifest check with:

```powershell
python tests\validate_manifests.py
```

The validator checks manifest schemas, source and observation references, RXTE/PCA-only Phase 0/1 targets, required references, and basic field constraints.

Run the Python test suite with:

```powershell
python -m pytest
```

The Phase 1 real-data validation runner is:

```powershell
python pipelines\run_phase1_real_validation.py
```

That runner expects ignored local RXTE products under `data/raw/rxte/` and HEASoft availability for `barycorr`. It writes ignored SQLite and JSON products under `data/products/phase1_real_validation/`.

## Data Policy

Mission event files, calibrated products, FITS files, Parquet/HDF5 outputs, SQLite/PostgreSQL exports, plots, and other generated science products should not be committed. Track durable metadata and provenance in manifests, then keep raw and processed products under ignored local data paths.

Local agent instruction files such as `AGENTS.md` are ignored and should remain machine-local.
