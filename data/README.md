# Data Directory

This directory is for small, tracked metadata inputs and local untracked science products.

Tracked in Git:

- `manifests/`: small CSV manifests used to seed source metadata, validation targets, references, and reproducibility inputs.
- Future tiny synthetic fixtures may be added only when needed for tests.

Not tracked in Git:

- Raw mission data from HEASARC or other archives.
- Processed event products.
- Generated light curves, spectra, power spectra, dynamic spectra, injection/recovery products, database files, and dashboard artifacts.

Large local products should follow the storage architecture in `docs/architecture.md` and must carry provenance. Phase 0 does not implement data ingestion.

