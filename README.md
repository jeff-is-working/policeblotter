# Thurston County Police Blotter

A civic-transparency site that aggregates **public** police call-for-service and
jail booking records for Thurston County, Washington, and serves them as a static,
accessible website backed by JSON data files committed to this repository.

## What this is (and is not)

This project publishes aggregate public-records data to make local law-enforcement
activity easier for residents to see. It is built with deliberate Trust & Safety
guardrails:

- **No mugshots** are ever collected, stored, or displayed.
- **Search is by day and location only.** There is no name search, and the data
  files contain no person-name field.
- **Not search-indexed.** The site ships `noindex` and a disallow-all `robots.txt`
  so it cannot become, or be scraped into, a person-lookup tool.
- People appearing in booking records are **presumed innocent** unless convicted.

See [ACCESSIBILITY.md](ACCESSIBILITY.md) and [DATA-POLICY.md](DATA-POLICY.md).

## Data sources

| Source | Coverage | Status |
|--------|----------|--------|
| TCSO 911 calls (`calls.csv`) | Sheriff calls for service, countywide | **Live (Phase 1)** |
| TCSO ArcGIS crime layer | Sheriff incidents | Planned (Phase 2) |
| TCSO jail roster | Current inmates | Planned (Phase 2) |
| Nisqually jail (EIS Web Jail Viewer) | Bookings (no mugshots) | Planned (Phase 2) |
| CentralSquare P2C | Lacey / Olympia / Tumwater PDs | Planned (Phase 2, headless) |

The TCSO calls feed is a **same-day snapshot with no server-side history**, so the
pipeline polls it daily and accumulates history in-repo via git.

## Architecture

```
GitHub Actions (daily cron)
  -> ingest.run  fetch + normalize + archive raw
  -> store       merge/dedup into data/<source>/<YYYY-MM>.json
  -> commit data back to repo
  -> build + deploy static site to GitHub Pages
```

No backend server. Storage is JSON files under `data/`.

## Layout

- `ingest/` - Python ingestion (schema, sources, store, runner)
- `site/` - static GitHub Pages frontend
- `data/` - normalized JSON partitions + `raw/` provenance archive
- `tests/` - pytest suite (run: `python -m pytest -q`)

## Local development

```bash
pip install -e .[test]
python -m pytest -q          # run the tests
python -m ingest.run         # fetch live data into ./data
```
