# Pipelines

This directory is reserved for reproducible execution entrypoints.

Current Phase 1 runner:

- `run_phase1_real_validation.py`: local RXTE/PCA real-data validation runner.
  It reads ignored products under `data/raw/`, writes ignored SQLite/JSON
  products under `data/products/phase1_real_validation/`, and evaluates the
  Phase 1 validation gate. It mirrors required RXTE orbit products when absent,
  runs HEASoft `barycorr` through the configured local/WSL HEASoft environment,
  records GoodXenon pairing status, scores real and synthetic controls, and
  writes validation recovery status separate from conservative catalog class.
  It does not perform Phase 2 injection/recovery.

Future contents may include:

- Snakemake or Nextflow workflow definitions.
- Thin command wrappers for ingestion, burst detection, oscillation search, injection/recovery, inference, and catalog export.
- Configuration examples for local and release runs.

Phase 0 does not implement pipeline execution. Add workflow files only when the roadmap phase owns the underlying behavior.
