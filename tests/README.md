# Tests

This directory is reserved for automated tests and small fixtures.

Expected early test areas:

- Manifest parsing and validation.
- Time-window and GTI handling.
- Synthetic event fixtures with known burst envelopes.
- Targeted oscillation-search fixtures once Phase 1 begins.

Large mission data products must not be committed as fixtures. Use tiny synthetic data or documented external-data skips.

## Current Checks

Run the Phase 0 manifest validation check with:

```powershell
python tests/validate_manifests.py
```

The check uses only the Python standard library and validates tracked CSV schemas, required fields, references, source IDs, observation rows, RXTE-only validation scope, numeric coordinates, and expected oscillation frequencies.
