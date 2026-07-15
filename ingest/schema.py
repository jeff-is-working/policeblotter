"""Normalized record schema and Trust & Safety enforcement.

Every source is normalized into a single flat record. Two hard rules from the
project constraints are enforced HERE so no source can bypass them:

  1. No mugshots / photos ever enter the data. `strip_media` drops any field
     whose name looks like an image/photo/mugshot before a record is built.
  2. No name index. The normalized `Record` has no `name` field at all, so the
     public data files are physically incapable of being searched by person.

See ACCESSIBILITY.md and the project constraints memory for the why.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

# Substrings that mark a field as media we must never store.
_MEDIA_MARKERS = ("mugshot", "mug_shot", "photo", "image", "img", "picture", "booking_photo")
# Substrings that mark a field as a person name we must never store/index.
_NAME_MARKERS = ("name", "firstname", "lastname", "middlename", "fname", "lname", "offender", "inmate")

_NON_NAME_ALLOW = ("nature", "filename", "agencyname")  # fields containing "name" that are NOT person names


def strip_media(record: dict) -> dict:
    """Return a copy of ``record`` with any image/mugshot-like field removed."""
    return {
        k: v
        for k, v in record.items()
        if not any(marker in k.lower() for marker in _MEDIA_MARKERS)
    }


def strip_names(record: dict) -> dict:
    """Return a copy of ``record`` with any person-name field removed.

    Guards the no-name-search rule: names never reach the normalized store.
    """
    out = {}
    for k, v in record.items():
        low = k.lower()
        if any(allow in low for allow in _NON_NAME_ALLOW):
            out[k] = v
            continue
        if any(marker in low for marker in _NAME_MARKERS):
            continue
        out[k] = v
    return out


RECORD_TYPES = ("call", "booking")


@dataclass(frozen=True)
class Record:
    """A single normalized incident (call for service) or jail booking.

    Deliberately has NO name field. Locations are block-level only.
    """

    source: str            # short source id, e.g. "tcso-calls"
    agency: str            # human agency label, e.g. "Thurston County Sheriff"
    type: str              # "call" | "booking"
    datetime: str          # ISO-8601, e.g. "2026-07-14T13:05:00"
    nature: str = ""       # nature of incident / charge description
    location_block: str = ""  # block-level, redacted address (no house number)
    city: str = ""
    case_number: str = ""
    raw_hash: str = ""     # sha256 of the source row, for provenance/dedup
    id: str = field(default="")

    def __post_init__(self) -> None:
        if self.type not in RECORD_TYPES:
            raise ValueError(f"type must be one of {RECORD_TYPES}, got {self.type!r}")
        object.__setattr__(self, "id", self.id or compute_id(self))

    def to_dict(self) -> dict:
        return asdict(self)


def raw_hash(row: object) -> str:
    """Stable sha256 of a source row (any stringifiable object)."""
    return hashlib.sha256(repr(row).encode("utf-8")).hexdigest()


def compute_id(record: Record) -> str:
    """Deterministic id from the identifying fields (for dedup across polls)."""
    key = "|".join(
        [record.source, record.type, record.datetime, record.case_number, record.nature, record.location_block]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# A house number is a leading digit run followed by whitespace. An already
# block-redacted value like "184xx" has the digits followed by "x", so it
# will not match and passes through unchanged.
_HOUSE_NUMBER = re.compile(r"^\s*(\d+)(?=\s)")


def redact_address(address: str) -> str:
    """Block-redact a street address: 18432 Old Hwy 99 -> 184xx Old Hwy 99.

    Sources that already block-redact pass through unchanged.
    """
    if not address:
        return ""

    def _block(match: re.Match) -> str:
        num = match.group(1)
        if len(num) <= 2:
            return num
        return num[:-2] + "xx"

    return _HOUSE_NUMBER.sub(_block, address.strip())
