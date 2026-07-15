"""Tests for the TCSO corrections roster source (fixture-driven, no network)."""

from pathlib import Path

from ingest.sources import tcso_jail

FX = Path(__file__).parent / "fixtures"
LIST_HTML = (FX / "tcso_roster_list.html").read_text()
DETAIL_HTML = (FX / "tcso_detail.html").read_text()


def test_parse_roster_dedupes_idnums():
    ids = tcso_jail.parse_roster(LIST_HTML)
    assert ids == ["Z0072311", "Z0066825"]  # order preserved, dup collapsed


def test_parse_detail_one_record_per_charge():
    recs = tcso_jail.parse_detail(DETAIL_HTML)
    assert len(recs) == 2
    natures = {r.nature for r in recs}
    assert "ATTEMPTED MURDER 1ST DEGREE" in natures
    assert "THEFT OF MOTOR VEHICLE" in natures


def test_parse_detail_fields():
    rec = tcso_jail.parse_detail(DETAIL_HTML)[0]
    assert rec.type == "booking"
    assert rec.agency == "Thurston County Sheriff"
    assert rec.case_number == "2410006934"
    assert rec.datetime == "2024-01-21T00:00:00"


def test_detail_never_leaks_name():
    recs = tcso_jail.parse_detail(DETAIL_HTML)
    blob = repr([r.to_dict() for r in recs]).lower()
    for leaked in ("testalpha", "testbeta", "testgamma", "name"):
        assert leaked not in blob, f"{leaked!r} leaked into normalized output"


def test_fetch_orchestrates_list_then_details():
    calls = []

    def fake_get(url, data=None):
        calls.append(url)
        return LIST_HTML if "mod=second" in url else DETAIL_HTML

    recs = tcso_jail.fetch(get=fake_get, sleep=lambda s: None)
    # 2 unique inmates x 2 charges each = 4 records
    assert len(recs) == 4
    assert any("mod=second" in u for u in calls)
    assert sum("mod=third" in u for u in calls) == 2


def test_fetch_isolates_bad_detail_page():
    def flaky_get(url, data=None):
        if "mod=second" in url:
            return LIST_HTML
        if "Z0066825" in url:
            raise RuntimeError("boom")
        return DETAIL_HTML

    recs = tcso_jail.fetch(get=flaky_get, sleep=lambda s: None)
    assert len(recs) == 2  # only the healthy inmate's charges
