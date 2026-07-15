# policeblotter - repo working notes

Public GitHub repo (org: `jeff-is-working`). Civic-transparency site aggregating
Thurston County, WA police call logs + jail bookings. Static GitHub Pages site +
JSON data committed to the repo; ingestion runs in GitHub Actions on a daily cron.

## Non-negotiable Trust & Safety rules (enforced in `ingest/schema.py`)
- No mugshots ever ingested/stored/displayed.
- Public search is DAY + LOCATION only. No name field anywhere in normalized data.
- Site is `noindex` + disallow-all `robots.txt`. Never add a name search.

See DATA-POLICY.md and ACCESSIBILITY.md. Accessibility = WCAG 2.2 AA, first-class.

## Workflow
Plan -> GitHub issue with acceptance criteria -> TDD (pytest first) -> validate ->
status file in `docs/status/`. Run `python -m pytest -q` before every commit.

## Structure
- `ingest/` schema, sources/, store, run
- `site/` static frontend
- `data/` normalized JSON partitions + raw/ archive
