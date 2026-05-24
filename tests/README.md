# Tests

This directory is reserved for automated tests and small fixtures.

Expected early test areas:

- Poisson excess scoring and conservative interval grouping on synthetic light curves.
- No-download archive planning for selected RXTE/PCA raw products.
- HEASoft/CALDB environment snapshot behavior without running mission tools.
- Local raw-product inventory and checksum behavior.
- RXTE/PCA detector-selection and barycenter provenance configuration.
- RXTE/PCA ingestion preflight behavior before FITS parsing.
- Manifest parsing and validation.
- Phase 1 manifest access for selected RXTE/PCA validation ObsIDs.
- GTI-corrected light-curve binning and baseline estimation on synthetic events.
- In-memory event product slicing on synthetic events.
- Time-window and GTI handling with half-open event intervals.
- Synthetic event fixtures with known burst envelopes.
- Targeted oscillation-search fixtures once Phase 1 begins.

Large mission data products must not be committed as fixtures. Use tiny synthetic data or documented external-data skips.

## Current Checks

Run the manifest validation check with:

```powershell
python tests\validate_manifests.py
```

The check uses only the Python standard library and validates tracked CSV schemas, required fields, references, source IDs, observation rows, RXTE-only validation scope, numeric coordinates, and expected oscillation frequencies.

Run the Python test suite with:

```powershell
python -m pytest
```

The initial Phase 1 test suite is intentionally small and verifies that the package skeleton imports cleanly before RXTE-specific implementation begins.
