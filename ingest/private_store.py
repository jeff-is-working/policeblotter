"""LOCAL-ONLY store for FULL booking data (names/demographics).

Writes to a gitignored directory (default: private-data/) so it can never reach
the public repo. Partitioned by source + booking month, deduped by booking id.
On each write the newest version of a booking replaces the prior one (custody
status and charges change over time), unlike the public store which is append-only.
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DIR = Path("private-data")


def _month(booking) -> str:
    d = booking.booking_date or booking.arrest_date or ""
    return d[:7] if len(d) >= 7 else "unknown"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def write_bookings(bookings: list, data_dir: str | Path = DEFAULT_DIR) -> dict:
    """Merge FullBooking objects into private-data/<source>/<YYYY-MM>.json."""
    data_dir = Path(data_dir)
    buckets: dict[tuple[str, str], list] = {}
    for b in bookings:
        buckets.setdefault((b.source, _month(b)), []).append(b)

    updated = 0
    for (source, month), items in sorted(buckets.items()):
        path = data_dir / source / f"{month}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = _load(path)
        for b in items:
            existing[b.id] = b.to_dict()  # newest wins
            updated += 1
        merged = sorted(existing.values(), key=lambda r: (r.get("booking_date", ""), r.get("id", "")))
        path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"written": len(bookings), "updated": updated}
