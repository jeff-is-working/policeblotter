"""LOCAL-ONLY full booking collector. Run from your laptop, never in CI.

Collects the COMPLETE public booking record (names, demographics, charges, court,
bail, dates) from both jails into the gitignored private-data/ directory. Mugshots
are never fetched-and-stored (the detail pages carry none for TCSO; Nisqually's are
dropped by the schema). This data is NOT for the public site until you gate it.

    python -m ingest.collect_full                    # both jails, 14-day window
    python -m ingest.collect_full --days 30
    python -m ingest.collect_full --sources nisqually-jail

Throttled to be polite to the source hosts. Expect several minutes per jail.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from ingest import private_store
from ingest.sources import nisqually, tcso_jail

UA = "policeblotter-civic-transparency/0.1 (+https://github.com/jeff-is-working/policeblotter)"
THROTTLE = 0.4


def _get(url: str, data: bytes | None = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 known gov hosts
        return resp.read().decode("utf-8", errors="replace")


def collect_nisqually(date_from: str, date_to: str, sleep=time.sleep) -> list:
    # Reuse the public fetch just to enumerate booking numbers in the window.
    booking_numbers = [r.case_number for r in nisqually.fetch(date_from, date_to)]
    bookings = []
    for i, bn in enumerate(booking_numbers):
        try:
            bookings.append(nisqually.parse_detail_full(_get(nisqually.detail_url(bn))))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] nisqually {bn}: {exc}", file=sys.stderr)
        if i + 1 < len(booking_numbers):
            sleep(THROTTLE)
    return bookings


def collect_tcso(sleep=time.sleep) -> list:
    roster = _get(tcso_jail.LIST_URL, data=urllib.parse.urlencode({"searchstring": "a"}).encode())
    idnums = tcso_jail.parse_roster(roster)
    bookings = []
    for i, idnum in enumerate(idnums):
        try:
            html = _get(f"{tcso_jail.BASE}?mod=third&idnum={idnum}")
            bookings.append(tcso_jail.parse_detail_full(html, idnum=idnum))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] tcso {idnum}: {exc}", file=sys.stderr)
        if i + 1 < len(idnums):
            sleep(THROTTLE)
    return bookings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect FULL booking data locally (private).")
    parser.add_argument("--days", type=int, default=14, help="Nisqually look-back window in days")
    parser.add_argument("--sources", help="comma-separated: nisqually-jail,tcso-jail (default both)")
    args = parser.parse_args(argv)
    selected = [s.strip() for s in args.sources.split(",")] if args.sources else ["nisqually-jail", "tcso-jail"]

    today = datetime.now(timezone.utc)
    date_from = (today - timedelta(days=args.days)).strftime("%m/%d/%Y")
    date_to = today.strftime("%m/%d/%Y")

    total = 0
    if "nisqually-jail" in selected:
        b = collect_nisqually(date_from, date_to)
        s = private_store.write_bookings(b)
        print(f"[OK] nisqually-jail: {s['updated']} bookings -> private-data/")
        total += s["updated"]
    if "tcso-jail" in selected:
        b = collect_tcso()
        s = private_store.write_bookings(b)
        print(f"[OK] tcso-jail: {s['updated']} bookings -> private-data/")
        total += s["updated"]
    print(f"[done] {total} full bookings written to private-data/ (gitignored)")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
