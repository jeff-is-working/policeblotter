"""Fetch/pagination tests for Nisqually (injected HTTP getter, no network)."""

from pathlib import Path

from ingest.sources import nisqually

FIXTURE = (Path(__file__).parent / "fixtures" / "nisqually_results.html").read_text()
EMPTY = "<table><thead><tr><th>Booking #</th><th>Booking Date</th></tr></thead><tbody></tbody></table>"


def test_fetch_pages_until_empty():
    calls = []

    def fake_get(url):
        calls.append(url)
        # page 1 returns the fixture (2 bookings), page 2 is empty -> stop
        return FIXTURE if "page=1" in url else EMPTY

    recs = nisqually.fetch("05/01/2026", "07/15/2026", get=fake_get)
    assert len(recs) == 2
    assert any("page=1" in u for u in calls)
    assert any("page=2" in u for u in calls)
    # must not keep paging past the empty page
    assert not any("page=3" in u for u in calls)


def test_fetch_stops_on_repeated_page():
    # A server that returns the same page forever must not loop past MAX_PAGES.
    recs = nisqually.fetch("05/01/2026", "07/15/2026", get=lambda url: FIXTURE)
    assert len(recs) == 2  # deduped by booking number, stops when no fresh rows


def test_result_url_includes_status_and_dates():
    url = nisqually._result_url("05/01/2026", "07/15/2026", 1)
    assert "Status=IN+CUSTODY" in url
    assert "BookingFrom=05%2F01%2F2026" in url
    assert "page=1" in url
