"""Thurston County Sheriff corrections roster (current in-custody).

The roster search at bureau-corrections-roster-search.asp returns the FULL current
roster on any query (mod=second POST), as a list of per-inmate detail links
(mod=third&idnum=...). Each detail page lists that inmate's charges as repeating
COURT / CAUSE NUMBER / CHARGE / BAIL / ARREST DATE blocks. There are no mugshots
on this site.

Per project constraints we keep ONLY charge, cause number, and arrest date - one
Record per charge. The inmate name on the detail page is never extracted or stored.
"""

from __future__ import annotations

import html as _html
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime

from ingest import schema

SOURCE = "tcso-jail"
AGENCY = "Thurston County Sheriff"
BASE = "https://www.co.thurston.wa.us/cm/sheriff/bureau-corrections-roster-search.asp"
LIST_URL = f"{BASE}?mod=second"
UA = "policeblotter-civic-transparency/0.1 (+https://github.com/jeff-is-working/policeblotter)"
THROTTLE_SECONDS = 0.4  # be polite to the county ASP host
MAX_INMATES = 1000      # safety backstop

_TAG = re.compile(r"<[^>]+>")
_IDNUM = re.compile(r"mod=third&idnum=(\w+)", re.I)
_CHARGE_BLOCK = re.compile(
    r"CAUSE NUMBER:\s*(?P<cause>\S+).*?"
    r"CHARGE:\s*(?P<charge>.+?)\s*BAIL:.*?"
    r"ARREST DATE:\s*(?P<date>\d{1,2}/\d{1,2}/\d{4})",
    re.S | re.I,
)


def _clean(page_html: str) -> str:
    text = _html.unescape(page_html.replace("&nbsp;", " "))
    text = _TAG.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_roster(list_html: str) -> list[str]:
    """Return the ordered, de-duplicated list of inmate idnums from the roster."""
    seen: dict[str, None] = {}
    for idnum in _IDNUM.findall(list_html):
        seen.setdefault(idnum, None)
    return list(seen)


def _iso(date_s: str) -> str:
    try:
        return datetime.strptime(date_s, "%m/%d/%Y").isoformat()
    except ValueError:
        return ""


def parse_detail(detail_html: str) -> list[schema.Record]:
    """Parse one inmate detail page into one Record per charge (name never read)."""
    text = _clean(detail_html)
    records: list[schema.Record] = []
    for m in _CHARGE_BLOCK.finditer(text):
        charge = m.group("charge").strip()
        cause = m.group("cause").strip()
        records.append(
            schema.Record(
                source=SOURCE,
                agency=AGENCY,
                type="booking",
                datetime=_iso(m.group("date")),
                nature=charge,
                location_block="",
                city="",
                case_number=cause,
                raw_hash=schema.raw_hash((cause, charge, m.group("date"))),
            )
        )
    return records


def _default_get(url: str, data: bytes | None = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 known gov host
        return resp.read().decode("utf-8", errors="replace")


def fetch(get=_default_get, sleep=time.sleep) -> list[schema.Record]:
    """Fetch the full roster, then each inmate's charges. Throttled and capped.

    ``get`` is injectable for testing; it is called as get(url) for detail pages
    and get(LIST_URL, data=...) for the roster POST.
    """
    roster_html = get(LIST_URL, data=urllib.parse.urlencode({"searchstring": "a"}).encode())
    idnums = parse_roster(roster_html)[:MAX_INMATES]
    records: list[schema.Record] = []
    for i, idnum in enumerate(idnums):
        try:
            detail = get(f"{BASE}?mod=third&idnum={idnum}")
            records.extend(parse_detail(detail))
        except Exception:  # noqa: BLE001 - one bad inmate page must not abort the run
            continue
        if i + 1 < len(idnums):
            sleep(THROTTLE_SECONDS)
    return records
