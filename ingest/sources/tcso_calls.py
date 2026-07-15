"""Thurston County Sheriff 911 calls-for-service source.

Fetches the daily snapshot CSV published at:
    https://www.co.thurston.wa.us/apps/sheriff-911-calls/calls.csv

The file is UTF-16 encoded and is OVERWRITTEN daily (no server-side history),
so the pipeline must poll daily and archive to build a record over time.
Columns: Date, Time, Sequence Number, Nature of Incident, Address, City.
No names, no dispositions - addresses are already block-redacted at source.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from ingest import schema

SOURCE = "tcso-calls"
AGENCY = "Thurston County Sheriff"
URL = "https://www.co.thurston.wa.us/apps/sheriff-911-calls/calls.csv"


def decode(raw: bytes) -> str:
    """Decode the UTF-16 CSV bytes to text, tolerating BOM and encoding drift."""
    for encoding in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        # A correct decode yields readable header text, not null-interleaved bytes.
        if "\x00" not in text:
            return text
    # Last resort: strip nulls from a latin-1 decode.
    return raw.decode("latin-1").replace("\x00", "")


def _parse_datetime(date_s: str, time_s: str) -> str:
    date_s, time_s = date_s.strip(), time_s.strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(f"{date_s} {time_s}", fmt).isoformat()
        except ValueError:
            continue
    # Fall back to date-only if the time is unparseable.
    for fmt in ("%m/%d/%Y",):
        try:
            return datetime.strptime(date_s, fmt).isoformat()
        except ValueError:
            continue
    return ""


def parse(raw: bytes) -> list[schema.Record]:
    """Parse raw CSV bytes into normalized call Records."""
    text = decode(raw)
    reader = csv.DictReader(io.StringIO(text))
    records: list[schema.Record] = []
    for row in reader:
        # Normalize whatever the header casing/spacing is into lookups.
        norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        date_s = norm.get("date", "")
        time_s = norm.get("time", "")
        nature = norm.get("nature of incident", "") or norm.get("nature", "")
        address = norm.get("address", "")
        city = norm.get("city", "")
        seq = norm.get("sequence number", "") or norm.get("sequence", "")
        if not (date_s or nature):
            continue
        records.append(
            schema.Record(
                source=SOURCE,
                agency=AGENCY,
                type="call",
                datetime=_parse_datetime(date_s, time_s),
                nature=nature,
                location_block=schema.redact_address(address),
                city=city,
                case_number=seq,
                raw_hash=schema.raw_hash(row),
            )
        )
    return records
