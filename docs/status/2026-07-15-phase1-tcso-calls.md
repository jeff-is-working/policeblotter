# Status - 2026-07-15 - Phase 1: TCSO 911 calls + accessible site

## Summary
Initial build of the Thurston County police blotter civic-transparency project.
Phase 1 (TCSO 911 calls-for-service) is complete end to end and validated against
live data (286 real records ingested). Static GitHub Pages site + JSON-in-repo
storage + daily GitHub Actions ingestion. Repo target: `jeff-is-working/policeblotter`
(public).

## Done
- `ingest/schema.py` - normalized `Record`, Trust & Safety guards: `strip_media`
  (no mugshots), `strip_names` (no name field), `redact_address` (block-level).
- `ingest/sources/tcso_calls.py` - UTF-16 `calls.csv` decode/parse/normalize.
- `ingest/store.py` - partitioned `data/<source>/<YYYY-MM>.json`, dedup by id,
  `index.json` builder.
- `ingest/run.py` - runner: fetch, archive raw, normalize, store (per-source isolation).
- `site/` - accessible (WCAG 2.2 AA) static frontend, day + location filters only,
  `noindex` + disallow-all `robots.txt`.
- `.github/workflows/ingest.yml` - daily cron ingest + Pages deploy.
- Governance: `DATA-POLICY.md`, `ACCESSIBILITY.md`, takedown + a11y issue templates,
  repo `CLAUDE.md`, `README.md`, MIT `LICENSE`, `pyproject.toml`.
- Tests: 21 passing (schema, tcso_calls, store). Live pipeline verified: 286 records.

## Blocked / pending
- **Remote repo not yet created**: GitHub API was intermittently unreachable
  (i/o timeouts) during this session. Everything is committed locally on `main`
  (commit `2cb91d6`). When connectivity returns, run:
  ```bash
  cd ~/Local/Projects/github/policeblotter
  gh repo create jeff-is-working/policeblotter --public --source=. --remote=origin \
    --description "Aggregated public police call & jail booking records for Thurston County, WA" --push
  ```
  Then enable Pages (Settings > Pages > Source: GitHub Actions) and file the work
  item below as a GitHub issue.

## Work item (file as GitHub issue - Phase 1 backfill + Phase 2)
Title: **Aggregate + host Thurston County police call logs & jail bookings**
Acceptance criteria:
- [x] TCSO calls ingested daily, normalized, deduped, stored as JSON
- [x] No mugshots, no name field, block-level location, noindex
- [x] Accessible site with day + location filtering, tests passing
- [ ] Pages deployed and public URL live
- [ ] Phase 2 sources: TCSO ArcGIS, TCSO jail roster, Nisqually (EIS), CentralSquare
      P2C (headless Playwright)

## Next (Phase 2)
1. `tcso_arcgis.py` - query `map.co.thurston.wa.us/arcgis/rest/services` crime layer (JSON).
2. `tcso_jail.py` - ASP roster; name-gated, enumerate by letter; strip names on store.
3. `nisqually.py` - EIS Web Jail Viewer over HTTP:81; **skip mugshot detail fetch**.
4. `p2c.py` - Playwright headless against `tcrlerms.policetocitizen.com/DailyBulletin`
   (F5 WAF); throttle hard.
5. Add axe-core to Pages build; fail CI on a11y violations.
