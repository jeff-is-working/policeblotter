"""Parser tests for Nisqually bookings (fixture-driven, no network)."""

from pathlib import Path

from ingest.sources import nisqually

FIXTURE = (Path(__file__).parent / "fixtures" / "nisqually_results.html").read_text()


def test_parses_two_bookings():
    recs = nisqually.parse_results(FIXTURE)
    assert len(recs) == 2
    assert {r.case_number for r in recs} == {"26004834", "26004833"}


def test_booking_fields_are_date_and_number_only():
    recs = nisqually.parse_results(FIXTURE)
    r = next(r for r in recs if r.case_number == "26004834")
    assert r.type == "booking"
    assert r.agency == "Nisqually Jail"
    assert r.city == "Nisqually"
    assert r.datetime == "2026-07-14T00:00:00"


def test_names_race_sex_never_appear_in_output():
    recs = nisqually.parse_results(FIXTURE)
    blob = repr([r.to_dict() for r in recs]).lower()
    for leaked in ("testone", "testtwo", "jane", "doe", "middlename", "race", "sex"):
        assert leaked not in blob, f"{leaked!r} leaked into normalized output"


def test_no_name_or_media_keys():
    recs = nisqually.parse_results(FIXTURE)
    for r in recs:
        d = r.to_dict()
        assert "name" not in d
        assert not any("mug" in k.lower() or "photo" in k.lower() for k in d)


def test_pagination_row_not_treated_as_booking():
    recs = nisqually.parse_results(FIXTURE)
    # The "1 2 3 4 5 > >>" pager row must not become a record.
    assert all(r.case_number.isdigit() and len(r.case_number) >= 6 for r in recs)
