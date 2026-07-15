"""Nisqually Jail bookings (EIS Web Jail Viewer).

The viewer is an ASP.NET MVC app on HTTP-only port 81. The search rejects a query
that omits the ``Status`` filter (it redirects back to the form), but a plain HTTP
GET that includes ``Status=IN CUSTODY`` and a booking DATE RANGE works and paginates
via ``&page=N`` - no browser required. The date range fits our day-based model.

Per project constraints we keep ONLY the booking number and booking date. Names,
race, sex, and mugshots (detail-page only) are never fetched or stored. Detail
pages are deliberately not requested because they carry mugshots.
"""

from __future__ import annotations

import html as _html
import re
import urllib.parse
import urllib.request
from datetime import datetime

from ingest import schema

SOURCE = "nisqually-jail"
AGENCY = "Nisqually Jail"
HOST = "http://nit-pscapp.nisqually-nsn.gov:81"
FORM_URL = f"{HOST}/Home/BookingSearchQuery"
RESULT_URL = f"{HOST}/Home/BookingSearchResult"
UA = "policeblotter-civic-transparency/0.1 (+https://github.com/jeff-is-working/policeblotter)"
MAX_PAGES = 50  # safety backstop against a runaway pager

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_DATE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
_BOOKING = re.compile(r"^\d{6,}$")


def _text(cell: str) -> str:
    return _html.unescape(_TAG.sub("", cell)).strip()


def _iso(date_s: str) -> str:
    try:
        return datetime.strptime(date_s, "%m/%d/%Y").isoformat()
    except ValueError:
        return ""


def _header_index(rows: list[str]) -> dict[str, int]:
    """Map lowercased header label -> column index from the first header row."""
    for row in rows:
        cells = [_text(c).lower() for c in _CELL.findall(row)]
        if any("booking" in c for c in cells):
            return {label: i for i, label in enumerate(cells)}
    return {}


def parse_results(page_html: str) -> list[schema.Record]:
    """Parse a BookingSearchResult page into booking Records (date + number only)."""
    rows = _ROW.findall(page_html)
    header = _header_index(rows)
    num_idx = next((i for lbl, i in header.items() if "booking #" in lbl or lbl == "booking"), 1)
    date_idx = next((i for lbl, i in header.items() if "booking date" in lbl), 7)

    records: list[schema.Record] = []
    for row in rows:
        cells = _CELL.findall(row)
        if len(cells) <= max(num_idx, date_idx):
            continue  # header or pagination row
        booking = _text(cells[num_idx])
        if not _BOOKING.match(booking):
            continue  # not a data row
        date_cell = _text(cells[date_idx])
        m = _DATE.search(date_cell)
        booking_date = _iso(m.group(1)) if m else ""
        records.append(
            schema.Record(
                source=SOURCE,
                agency=AGENCY,
                type="booking",
                datetime=booking_date,
                nature="Booking",
                location_block="",
                city="Nisqually",
                case_number=booking,
                raw_hash=schema.raw_hash(booking),
            )
        )
    return records


def detail_url(booking_number: str) -> str:
    return f"{HOST}/Home/BookingSearchDetail?BookingNumber={booking_number}"


_LABEL_STOP = r"(?=[A-Z][A-Za-z .#/]*:|Personal Description|Charges:|Arrest Information|$)"


def _field(text: str, label: str) -> str:
    m = re.search(re.escape(label) + r":\s*" + r"(.*?)\s*" + _LABEL_STOP, text)
    return m.group(1).strip() if m else ""


def parse_detail_full(detail_html: str):
    """Parse a Nisqually detail page into a FullBooking (LOCAL-ONLY, has name).

    Imported lazily so the public pipeline never pulls the full schema.
    """
    from ingest import full_schema

    text = _text(detail_html.replace("</strong>", " ").replace("<strong>", " "))
    name_full = ""
    # The name is the capitalized token(s) immediately before the custody status,
    # e.g. "TESTONE TESTTWO IN CUSTODY as of 07/15/26". Anchor on the status to avoid
    # grabbing repeated "Booking Search Detail" nav/heading text.
    m = re.search(
        r".*Booking Search Detail\s+(.+?)\s+"
        r"(?:IN CUSTODY|OUT OF CUSTODY|RELEASED)\s+as of",
        text, re.S,
    )
    if m:
        name_full = re.sub(r"\s+", " ", m.group(1)).strip()
    status = "IN CUSTODY" if "IN CUSTODY" in text else ("RELEASED" if "RELEASED" in text else "")
    parts = name_full.split()
    charges = []
    for viol, level in re.findall(r"Violation:\s*(.*?)\s*(?:Level:\s*(\w*)|Add\. Desc|Arrest Information|$)", text):
        viol = viol.strip()
        if viol:
            charges.append(full_schema.Charge(charge=viol, level=(level or "").strip()))
    raw = {
        "booking_number": _field(text, "Booking Number"),
        "inmate_id": _field(text, "Inmate ID"),
        "name_full": name_full,
        "name_first": parts[0] if parts else "",
        "name_last": " ".join(parts[1:]) if len(parts) > 1 else "",
        "booking_date": _iso_any(_field(text, "Booking Date")),
        "arrest_date": _iso_any(_field(text, "Arrest Date")),
        "release_date": _iso_any(_field(text, "Released")),
        "sched_release": _iso_any(_field(text, "Sched. Release")),
        "custody_status": status,
        "age": _field(text, "Age"),
        "sex": _field(text, "Sex"),
        "race": _field(text, "Race"),
        "arrest_agency": _field(text, "Arrest Agency"),
    }
    return full_schema.from_raw(SOURCE, AGENCY, raw, charges)


def _iso_any(date_s: str) -> str:
    date_s = date_s.strip()
    return _iso(date_s) if re.match(r"\d{1,2}/\d{1,2}/\d{4}", date_s) else ""


def _result_url(date_from: str, date_to: str, page: int) -> str:
    params = {
        "LastName": "", "FirstName": "",
        "BookingFrom": date_from, "BookingTo": date_to,
        "ReleaseFrom": "", "ReleaseTo": "",
        "Status": "IN CUSTODY", "ValidSearch": "",
        "page": str(page),
    }
    return f"{RESULT_URL}?{urllib.parse.urlencode(params)}"


def _default_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 known gov host
        return resp.read().decode("utf-8", errors="replace")


def fetch(date_from: str, date_to: str, get=_default_get) -> list[schema.Record]:
    """Fetch all in-custody bookings in [date_from, date_to] (MM/DD/YYYY).

    Pages through ``&page=N`` until a page yields no new booking numbers. ``get``
    is injectable for testing. Records are deduped by id in the store upstream.
    """
    records: list[schema.Record] = []
    seen: set[str] = set()
    for page in range(1, MAX_PAGES + 1):
        page_recs = parse_results(get(_result_url(date_from, date_to, page)))
        fresh = [r for r in page_recs if r.case_number not in seen]
        if not fresh:
            break  # empty page or fully-repeated page => end of results
        for r in fresh:
            seen.add(r.case_number)
        records.extend(fresh)
    return records
