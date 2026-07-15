"""FULL booking schema for the LOCAL-ONLY private pipeline.

Unlike ingest.schema.Record (name-free, for the public GitHub Pages site), this
schema retains names and demographics. It is written ONLY to the gitignored
private-data/ directory and must never be committed to the public repo.

Mugshots are still structurally excluded: there is no image field, and
``from_raw`` runs strip_media so an image URL can never be carried in.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

from ingest.schema import strip_media


@dataclass
class Charge:
    charge: str = ""
    court: str = ""
    cause_number: str = ""
    bail: str = ""
    level: str = ""
    arrest_date: str = ""  # ISO


@dataclass
class FullBooking:
    source: str
    agency: str
    booking_number: str = ""
    inmate_id: str = ""
    name_first: str = ""
    name_middle: str = ""
    name_last: str = ""
    name_full: str = ""
    booking_date: str = ""     # ISO
    arrest_date: str = ""      # ISO
    release_date: str = ""     # ISO
    sched_release: str = ""    # ISO
    custody_status: str = ""
    age: str = ""
    sex: str = ""
    race: str = ""
    arrest_agency: str = ""
    charges: list = field(default_factory=list)  # list[Charge]
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = booking_id(self.source, self.booking_number)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Defensive: never emit any image/mugshot-like key even if one sneaks in.
        return strip_media(d)


def booking_id(source: str, booking_number: str) -> str:
    return hashlib.sha256(f"{source}|{booking_number}".encode()).hexdigest()[:16]


def from_raw(source: str, agency: str, raw: dict, charges: list | None = None) -> FullBooking:
    """Build a FullBooking from a raw label->value dict, dropping any media field."""
    clean = strip_media(raw)
    return FullBooking(
        source=source,
        agency=agency,
        booking_number=clean.get("booking_number", ""),
        inmate_id=clean.get("inmate_id", ""),
        name_first=clean.get("name_first", ""),
        name_middle=clean.get("name_middle", ""),
        name_last=clean.get("name_last", ""),
        name_full=clean.get("name_full", ""),
        booking_date=clean.get("booking_date", ""),
        arrest_date=clean.get("arrest_date", ""),
        release_date=clean.get("release_date", ""),
        sched_release=clean.get("sched_release", ""),
        custody_status=clean.get("custody_status", ""),
        age=clean.get("age", ""),
        sex=clean.get("sex", ""),
        race=clean.get("race", ""),
        arrest_agency=clean.get("arrest_agency", ""),
        charges=charges or [],
    )
