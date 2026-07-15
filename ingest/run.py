"""Ingestion entrypoint. Fetches selected sources, normalizes, archives, stores.

Sources are matched to their own upstream refresh cadence by the scheduler
(see .github/workflows/ingest.yml), so this runner takes a source selection:

    python -m ingest.run                       # all sources
    python -m ingest.run --sources tcso-calls  # just one
    python -m ingest.run --sources tcso-calls,nisqually-jail

Deploys never call this - the Pages deploy is a separate workflow. Each source is
isolated: one failing does not abort the others. Exit 0 if any source ingested.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ingest import store
from ingest.sources import nisqually, tcso_calls, tcso_jail

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
UA = "policeblotter-civic-transparency/0.1 (+https://github.com/jeff-is-working/policeblotter)"

# Rolling look-back for date-range sources; dedup handles the daily overlap.
BOOKING_LOOKBACK_DAYS = 14


def _fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 known https gov host
        return resp.read()


def _archive_raw(source: str, raw: bytes, suffix: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out = RAW_DIR / source / f"{stamp}.{suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)


def _ingest_tcso_calls() -> list:
    raw = _fetch(tcso_calls.URL)
    _archive_raw(tcso_calls.SOURCE, raw, "csv")
    return tcso_calls.parse(raw)


def _ingest_nisqually() -> list:
    today = datetime.now(timezone.utc)
    date_from = (today - timedelta(days=BOOKING_LOOKBACK_DAYS)).strftime("%m/%d/%Y")
    date_to = today.strftime("%m/%d/%Y")
    return nisqually.fetch(date_from, date_to)


def _ingest_tcso_jail() -> list:
    return tcso_jail.fetch()


# Registry: source id -> callable returning a list of normalized Records.
SOURCES = {
    tcso_calls.SOURCE: _ingest_tcso_calls,
    nisqually.SOURCE: _ingest_nisqually,
    tcso_jail.SOURCE: _ingest_tcso_jail,
}


def run(sources: list[str] | None = None) -> int:
    selected = sources or list(SOURCES)
    successes = 0
    for name in selected:
        runner = SOURCES.get(name)
        if runner is None:
            print(f"[ERROR] unknown source: {name}", file=sys.stderr)
            continue
        try:
            recs = runner()
            summary = store.write_records(recs, DATA_DIR)
            print(f"[OK] {name}: {summary['new']} new / {summary['written']} fetched")
            successes += 1
        except Exception as exc:  # noqa: BLE001 - isolate per-source failure
            print(f"[ERROR] {name}: {exc}", file=sys.stderr)

    if successes == 0:
        print("[ERROR] no sources ingested", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Thurston County police records.")
    parser.add_argument(
        "--sources",
        help=f"comma-separated source ids (default: all). Available: {', '.join(SOURCES)}",
    )
    args = parser.parse_args(argv)
    sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    return run(sources)


if __name__ == "__main__":
    raise SystemExit(main())
