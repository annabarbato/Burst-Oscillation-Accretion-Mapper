# Environment Decision

Last updated: 2026-05-24

This document records the Phase 0 environment decision from `docs/roadmap.md`. It defines how development should prepare for RXTE/PCA validation first, while leaving container packaging and full dependency pinning for later roadmap phases.

## Decision

Use a two-layer local environment:

1. Mission tools installed outside the repository.
2. Python project environment inside or beside the repository.

HEASoft, NICERDAS, CALDB, and any mission-specific shell initialization should be treated as external scientific infrastructure. The repository should record how to detect and report those versions, but it should not vendor mission tools or calibration files.

Python dependencies should be introduced only when the first code skeleton is added. Until then, Phase 0 remains documentation, manifest, and curation work.

## Mission Tool Layer

Install and initialize mission tools outside this repository:

- HEASoft for FITS-oriented high-energy astrophysics tools, barycentering, mission utilities, and XSPEC availability.
- NICERDAS through the supported HEASoft distribution when NICER work begins.
- HEASARC CALDB outside the repository, either local or remotely configured.

Version and configuration values that future pipeline runs must capture:

- `HEADAS` path or equivalent HEASoft initialization state.
- HEASoft version.
- NICERDAS version when NICER products are processed.
- CALDB path, remote/local mode, and mission calibration version.
- Mission task names and parameters used for screening, extraction, barycentering, and spectra.

Phase 0 does not require these tools to be installed before committing manifests and documentation. Phase 1 RXTE validation will require HEASoft availability before ingestion or barycentering code can be considered complete.

## Python Layer

Use a local Python environment for project code once implementation begins:

- Prefer a project-local virtual environment named `.venv` or an equivalent named Conda environment.
- Keep the environment reproducible through tracked configuration once Python code is added.
- Do not add broad scientific dependencies before code uses them.
- Start with minimal developer dependencies for linting, formatting, tests, and manifest validation.
- Add analysis dependencies in the phase that first requires them.

Expected dependency timing:

- Phase 0: no runtime Python package required; optional local tools only.
- Early Phase 1: Astropy, NumPy, SciPy, pandas or polars, PyArrow, pytest, and FITS/event I/O support as implementation requires.
- Phase 1 timing validation: Stingray once event-based oscillation search code begins.
- Phase 2: simulation and injection/recovery dependencies.
- Phase 3: NICERDAS-aware wrappers and NICER-specific dependencies.
- Phase 4: PyMC or Stan for hierarchical inference.
- Phase 5: dashboard framework only after released catalog tables exist.

## Container Strategy

Do not build Docker or Apptainer packaging in Phase 0.

Container packaging should wait until the RXTE validation MVP has real commands to preserve. The first container target should package a reproducible Phase 1 RXTE validation run, not an empty scaffold.

Future container requirements:

- Document HEASoft/NICERDAS licensing and distribution constraints before packaging.
- Keep CALDB data external or mounted unless a tiny test calibration fixture is explicitly approved.
- Preserve exact pipeline, Python, HEASoft, NICERDAS, CALDB, and OS versions in release metadata.

## Local Data And Secrets

- Do not commit raw HEASARC data, processed event files, generated products, database files, local CALDB mirrors, virtual environments, notebooks with bulky outputs, or credentials.
- Use manifests and provenance files to describe external data products instead of committing them.
- Keep any access tokens, archive credentials, or local paths out of tracked files.

## Phase Gate

Phase 0 is satisfied for environment strategy when:

- The repository has a documented local environment decision.
- Official HEASoft, NICERDAS, and CALDB sources are tracked in `data/manifests/references.csv`.
- The docs clearly state that HEASoft/NICERDAS installation is external and that containers are deferred.

Phase 1 may add executable environment files when the first RXTE ingestion and validation code is introduced.

## Reference Notes

Mission-tool and calibration source claims in this document were checked on
2026-05-24 against sources tracked in `data/manifests/references.csv`:

- `heasoft_docs`: HEASoft mission-tool documentation.
- `nicer_analysis_docs`: NICERDAS and NICER analysis documentation.
- `caldb_docs`: HEASARC CALDB documentation.
