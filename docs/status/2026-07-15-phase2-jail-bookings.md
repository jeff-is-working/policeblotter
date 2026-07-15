# Status - 2026-07-15 - Phase 2: Nisqually + TCSO jail bookings

## Summary
Added two jail-booking sources. Both verified live and ingested. Every source was
probed live before coding, which corrected several wrong assumptions from recon.

## Verification corrections (recon vs reality)
- **TCSO ArcGIS crime layer**: does NOT exist as a public REST service. Dropped;
  `calls.csv` already covers TCSO incidents.
- **Nisqually**: not a JS/WAF problem - the search just requires `Status=IN CUSTODY`.
  Works over plain HTTP with `&page=N` pagination. No browser needed.
- **TCSO roster**: any query returns the FULL current roster (288 inmates) in one
  request; no A-Z surname enumeration needed. One detail page per inmate for charges.

## Done
- `ingest/sources/nisqually.py` - in-custody bookings by date range over plain HTTP,
  paginated. Keeps ONLY booking number + booking date. Live: 269 bookings / 43 days.
- `ingest/sources/tcso_jail.py` - roster -> per-inmate charge detail. One Record per
  charge (charge text + cause number + arrest date). Throttled 0.4s, per-inmate
  failure isolation, 1000-inmate cap. Live: 908 charge-records.
- Both wired into `ingest/run.py` (rolling 14-day window for Nisqually; full roster
  for TCSO). Per-source try/except isolation preserved.
- 6 new tests (11 total for Phase 2 sources); full suite 35 passing.
- Names, race, sex, and mugshots are never fetched or stored (enforced in parsers +
  schema guards; tests assert no leakage).

## Notable
- **No Playwright dependency after all** - both Phase 2 sources use plain HTTP.
  Playwright is installed in the local `.venv` and reserved for the future P2C work.
- Booking records have no location, so the site's location filter is a no-op for
  them; the date filter works. Acceptable.
- TCSO jail records partition by ARREST month (charges carry arrest date), so history
  spans back to 2023 for long-held inmates. Expected.

## Data seeded (committed)
- nisqually-jail: 269 | tcso-calls: 286 | tcso-jail: 908

## Next
- **P2C city PDs** (Lacey/Olympia/Tumwater): the one remaining source, needs headless
  Playwright against `tcrlerms.policetocitizen.com/DailyBulletin` (F5 WAF). This will
  add the CI browser dependency. Weigh ToS before enabling.
- Consider optional charge enrichment for Nisqually (detail pages have charges but also
  mugshots; would require fetch-but-drop-image). Deferred.
- Add axe-core to the Pages build.
