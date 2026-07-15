"""Tests for the LOCAL-ONLY full booking pipeline (names/demographics, no mugshots)."""

import json
import subprocess
from pathlib import Path

from ingest import full_schema, private_store
from ingest.sources import nisqually, tcso_jail

FX = Path(__file__).parent / "fixtures"
NQ_DETAIL = (FX / "nisqually_detail.html").read_text()
TCSO_DETAIL = (FX / "tcso_detail.html").read_text()


# --- Nisqually full parse ---

def test_nisqually_full_captures_name_and_demographics():
    b = nisqually.parse_detail_full(NQ_DETAIL)
    assert b.booking_number == "26004834"
    assert b.name_full == "TESTONE TESTTWO"
    assert b.age == "33"
    assert b.sex == "M"
    assert b.race == "P"
    assert b.booking_date == "2026-07-14T00:00:00"
    assert b.arrest_agency == "WA DOC"
    assert b.custody_status == "IN CUSTODY"
    assert any("DOCVIOL" in c.charge for c in b.charges)


# --- TCSO full parse ---

def test_tcso_full_captures_name_and_charges():
    b = tcso_jail.parse_detail_full(TCSO_DETAIL, idnum="Z0072311")
    assert b.booking_number == "Z0072311"
    assert b.name_full == "TESTALPHA TESTBETA TESTGAMMA"
    assert len(b.charges) == 2
    c = b.charges[0]
    assert c.court == "SUPERIOR COURT"
    assert c.cause_number == "2410006934"
    assert c.bail.startswith("$")


def test_tcso_ids_are_unique_per_idnum():
    a = tcso_jail.parse_detail_full(TCSO_DETAIL, idnum="Z0072311")
    b = tcso_jail.parse_detail_full(TCSO_DETAIL, idnum="Z0066825")
    assert a.id != b.id  # no collision despite no booking number on the page


# --- mugshot exclusion (structural + defensive) ---

def test_full_booking_never_emits_media_field():
    raw = {"booking_number": "1", "mugshot": "http://x/pic.jpg", "photo_url": "y", "name_full": "X"}
    b = full_schema.from_raw("nisqually-jail", "Nisqually Jail", raw)
    d = b.to_dict()
    assert not any("mug" in k.lower() or "photo" in k.lower() or "image" in k.lower() for k in d)
    assert "mugshot" not in json.dumps(d).lower()


# --- private store writes to gitignored dir ---

def test_private_store_writes_partitioned(tmp_path):
    b = nisqually.parse_detail_full(NQ_DETAIL)
    summary = private_store.write_bookings([b], tmp_path)
    part = tmp_path / "nisqually-jail" / "2026-07.json"
    assert part.exists()
    rows = json.loads(part.read_text())
    assert rows[0]["name_full"] == "TESTONE TESTTWO"
    assert summary["updated"] == 1


def test_private_store_newest_wins(tmp_path):
    b = nisqually.parse_detail_full(NQ_DETAIL)
    private_store.write_bookings([b], tmp_path)
    private_store.write_bookings([b], tmp_path)  # same id again
    rows = json.loads((tmp_path / "nisqually-jail" / "2026-07.json").read_text())
    assert len(rows) == 1  # deduped by id


# --- the critical safety guard ---

def test_private_data_dir_is_gitignored():
    repo = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["git", "check-ignore", "private-data/nisqually-jail/2026-07.json"],
        cwd=repo, capture_output=True, text=True,
    )
    assert result.returncode == 0, "private-data/ MUST be gitignored so names never reach the public repo"


def test_public_record_still_has_no_name():
    # Regression: the public schema used by the GitHub pipeline stays name-free.
    from ingest import schema
    rec = schema.Record(source="s", agency="a", type="booking", datetime="2026-07-14T00:00:00")
    assert "name" not in rec.to_dict()
