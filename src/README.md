# Source Package

This directory contains the Phase 1 Python package skeleton.

The current package exports only version metadata. It does not define a stable public science API yet; implementation modules should mature behind the roadmap-aligned internal boundaries before anything is advertised as reusable.

Expected Phase 1 modules should align with the conceptual interfaces in `docs/architecture.md`:

- Ingest backend.
- Burst detector.
- Oscillation searcher.
- Candidate scorer.
- Catalog writer.

Do not add NICER backend code, injection/recovery code, inference models, or dashboard code before the roadmap phase is explicitly advanced.
