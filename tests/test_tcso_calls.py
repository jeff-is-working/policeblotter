"""Tests for the TCSO calls.csv source (UTF-16 daily snapshot)."""

from ingest.sources import tcso_calls

_CSV = (
    "Date,Time,Sequence Number,Nature of Incident,Address,City\r\n"
    "07/14/2026,1:05:00 PM,26-000123,THEFT,184xx Old Hwy 99 Sw,Tumwater\r\n"
    "07/14/2026,11:47:00 PM,26-000124,WELFARE CHECK,52xx Martin Way E,Lacey\r\n"
)


def _utf16(text: str) -> bytes:
    return text.encode("utf-16")


def test_decode_utf16():
    assert tcso_calls.decode(_utf16(_CSV)).startswith("Date,Time")
    assert "\x00" not in tcso_calls.decode(_utf16(_CSV))


def test_decode_handles_plain_utf8():
    assert tcso_calls.decode(_CSV.encode("utf-8")).startswith("Date,Time")


def test_parse_yields_calls():
    recs = tcso_calls.parse(_utf16(_CSV))
    assert len(recs) == 2
    r = recs[0]
    assert r.type == "call"
    assert r.source == "tcso-calls"
    assert r.nature == "THEFT"
    assert r.city == "Tumwater"
    assert r.case_number == "26-000123"
    assert r.datetime == "2026-07-14T13:05:00"
    assert r.location_block == "184xx Old Hwy 99 Sw"


def test_parse_second_row_time():
    recs = tcso_calls.parse(_utf16(_CSV))
    assert recs[1].datetime == "2026-07-14T23:47:00"


def test_records_carry_no_name_or_media():
    recs = tcso_calls.parse(_utf16(_CSV))
    d = recs[0].to_dict()
    assert "name" not in d
    assert not any("mug" in k.lower() or "photo" in k.lower() for k in d)


def test_parse_skips_blank_rows():
    csv_with_blank = _CSV + ",,,,,\r\n"
    recs = tcso_calls.parse(_utf16(csv_with_blank))
    assert len(recs) == 2
