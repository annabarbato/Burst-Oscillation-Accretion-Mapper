# Source Citation Policy

Last updated: 2026-05-24

This policy satisfies the Phase 0 roadmap requirement for citation and source tracking. It applies to documentation, manifests, future catalog rows, validation target curation, and any scientific or instrument claim in this repository.

## Goals

- Make every scientific claim traceable to a source.
- Separate current mission status from stable instrument or catalog descriptions.
- Prevent guessed source metadata from entering manifests.
- Preserve enough context for future provenance tables and paper references.

## Source Of Truth

Use `data/manifests/references.csv` as the tracked index of project references.

Use inline links in Markdown when they improve readability, but every durable project claim should also be representable by a reference row. Manifest rows may cite URLs directly during early Phase 0, but later curation should prefer stable `ref_id` values from `references.csv`.

## Reference Categories

Use these categories in `references.csv`:

- `mission_status`: time-sensitive mission operations pages, pause notices, archive availability, or current caveats.
- `instrument_spec`: mission or instrument pages used for energy range, time resolution, detector description, or calibration context.
- `catalog`: MINBAR, SIMBAD, HEASARC tables, VizieR tables, or other structured external catalogs.
- `software_doc`: package or tool documentation such as Stingray, HEASoft, NICERDAS, or XSPEC references.
- `literature`: papers, proceedings, preprints, or NASA technical records used for burst oscillation frequencies, detections, ephemerides, methods, or source properties.
- `ephemeris`: source-specific timing or orbital ephemerides. Use this when a paper is specifically authoritative for a correction, not just general source context.

## Required Fields

Every reference row must include:

- `ref_id`: stable lower snake case identifier.
- `category`: one of the approved categories.
- `title`: short human-readable title.
- `url`: authoritative URL when available.
- `checked_date`: date the source was checked in `YYYY-MM-DD` format.
- `authoritative_for`: concise description of what the source supports.

Use blank fields instead of guessed values for DOI, bibcode, version, or notes.

## Current Claims

Current or operational claims must include a checked date in the text or nearby source note. Examples:

- NICER observation status.
- Archive availability.
- Tool or calibration recommendations.
- Mission pages that may change over time.

Stable historical or literature claims still need references, but do not need to be phrased as current status unless the claim can change.

## Manifest Rules

- Do not add source coordinates without a coordinate reference.
- Do not add known spin or burst-oscillation frequencies without a literature or catalog reference.
- Do not add RXTE validation targets without a source row and a validation reference.
- Do not add binary ephemerides without noting the authoritative source and any validity caveat.
- Use notes for uncertainty and missing information rather than filling guessed values.

## Documentation Rules

- Architecture and roadmap claims should cite primary or authoritative sources where practical.
- If a source is used to justify implementation order, validation strategy, mission status, catalog size, or timing capability, add or reuse a `references.csv` row.
- If a claim is not supported by the existing architecture, roadmap, or reference index, update the relevant doc before implementation.

## Review Checklist

Before adding or changing a claim, check:

- Is this claim current, historical, instrument-specific, catalog-specific, or literature-specific?
- Does a reference row already exist?
- Does the claim need a `checked_date` because it may change?
- Is the source authoritative enough for the claim?
- Does the claim affect the roadmap phase, validation target selection, or acceptance criteria?

