"""Tests for source selection in the runner (no network; registry stubbed)."""

from ingest import run


def test_main_parses_source_selection(monkeypatch):
    called = {}
    monkeypatch.setattr(run, "run", lambda sources: called.setdefault("sources", sources) or 0)

    run.main(["--sources", "tcso-calls, nisqually-jail"])
    assert called["sources"] == ["tcso-calls", "nisqually-jail"]


def test_main_defaults_to_all(monkeypatch):
    called = {}
    monkeypatch.setattr(run, "run", lambda sources: called.setdefault("sources", sources) or 0)
    run.main([])
    assert called["sources"] is None  # None => all sources


def test_run_only_invokes_selected_sources(monkeypatch, tmp_path):
    invoked = []
    monkeypatch.setattr(run, "SOURCES", {
        "a": lambda: invoked.append("a") or [],
        "b": lambda: invoked.append("b") or [],
    })
    monkeypatch.setattr(run.store, "write_records", lambda recs, d: {"new": 0, "written": 0})
    rc = run.run(["a"])
    assert invoked == ["a"]
    assert rc == 0


def test_run_unknown_source_is_error(monkeypatch):
    monkeypatch.setattr(run, "SOURCES", {"a": lambda: []})
    rc = run.run(["does-not-exist"])
    assert rc == 1  # nothing ingested


def test_run_isolates_failing_source(monkeypatch):
    def boom():
        raise RuntimeError("down")

    monkeypatch.setattr(run, "SOURCES", {"a": boom, "b": lambda: []})
    monkeypatch.setattr(run.store, "write_records", lambda recs, d: {"new": 0, "written": 0})
    rc = run.run(["a", "b"])
    assert rc == 0  # b still succeeded
