"""Tests for the normalized schema and Trust & Safety guards."""

import pytest

from ingest import schema


def test_strip_media_removes_mugshot_and_photo_fields():
    row = {"BookingNumber": "23001086", "Mugshot": "http://x/img.jpg", "photo_url": "y", "name": "Doe"}
    out = schema.strip_media(row)
    assert "Mugshot" not in out
    assert "photo_url" not in out
    assert out["BookingNumber"] == "23001086"


def test_strip_names_removes_person_name_fields():
    row = {"FirstName": "Jane", "LastName": "Doe", "MiddleName": "Q", "nature": "THEFT", "city": "Lacey"}
    out = schema.strip_names(row)
    assert "FirstName" not in out
    assert "LastName" not in out
    assert "MiddleName" not in out
    # "nature" and "city" survive; "nature" contains no person name despite... it doesn't, but guard the allowlist too
    assert out["nature"] == "THEFT"
    assert out["city"] == "Lacey"


def test_strip_names_keeps_nature_and_agencyname():
    row = {"AgencyName": "Lacey PD", "nature": "DUI", "OffenderName": "x"}
    out = schema.strip_names(row)
    assert out["AgencyName"] == "Lacey PD"
    assert out["nature"] == "DUI"
    assert "OffenderName" not in out


def test_record_has_no_name_attribute():
    rec = schema.Record(source="s", agency="a", type="call", datetime="2026-07-14T00:00:00")
    assert not hasattr(rec, "name")
    assert "name" not in rec.to_dict()


def test_record_rejects_bad_type():
    with pytest.raises(ValueError):
        schema.Record(source="s", agency="a", type="arrest", datetime="2026-07-14T00:00:00")


def test_record_id_is_stable_and_deterministic():
    kwargs = dict(source="tcso-calls", agency="TCSO", type="call",
                  datetime="2026-07-14T13:05:00", case_number="26-1234", nature="THEFT")
    a = schema.Record(**kwargs)
    b = schema.Record(**kwargs)
    assert a.id == b.id
    assert len(a.id) == 16


def test_redact_address_blocks_house_number():
    assert schema.redact_address("18432 Old Hwy 99 SW") == "184xx Old Hwy 99 SW"


def test_redact_address_passthrough_already_redacted():
    assert schema.redact_address("184xx Old Hwy 99 Sw") == "184xx Old Hwy 99 Sw"


def test_redact_address_short_number_untouched():
    assert schema.redact_address("12 Main St") == "12 Main St"


def test_redact_address_empty():
    assert schema.redact_address("") == ""
