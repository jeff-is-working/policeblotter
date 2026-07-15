"""Ingestion entrypoint. Fetches each source, normalizes, archives raw, stores.

Run by GitHub Actions on a schedule (see .github/workflows/ingest.yml) and
locally with:  python -m ingest.run

Exit codes: 0 = at least one source ingested; non-zero = total failure.
Each source is isolated: one source failing does not abort the others.
"""

from __future__ import annotations

import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ingest import store
from ingest.sources import tcso_calls

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
UA = "policeblotter-civic-transparency/0.1 (+https://github.com/jeff-is-working/policeblotter)"


def _fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (known https gov host)
        return resp.read()


def _archive_raw(source: str, raw: bytes, stamp: str, suffix: str) -> None:
    out = RAW_DIR / source / f"{stamp}.{suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)


def run() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    successes = 0

    # --- TCSO 911 calls (daily snapshot CSV) ---
    try:
        raw = _fetch(tcso_calls.URL)
        _archive_raw(tcso_calls.SOURCE, raw, stamp, "csv")
        recs = tcso_calls.parse(raw)
        summary = store.write_records(recs, DATA_DIR)
        print(f"[OK] {tcso_calls.SOURCE}: {summary['new']} new / {summary['written']} fetched")
        successes += 1
    except Exception as exc:  # noqa: BLE001 - isolate per-source failure
        print(f"[ERROR] {tcso_calls.SOURCE}: {exc}", file=sys.stderr)

    # Phase 2 sources (tcso_arcgis, tcso_jail, nisqually, p2c) plug in here.

    if successes == 0:
        print("[ERROR] no sources ingested", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
