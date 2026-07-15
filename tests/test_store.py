"""Tests for the partitioned JSON store and dedup behavior."""

import json

from ingest import schema, store


def _rec(seq, month="07", nature="THEFT"):
    return schema.Record(
        source="tcso-calls", agency="TCSO", type="call",
        datetime=f"2026-{month}-14T13:05:00", nature=nature, case_number=seq,
    )


def test_write_creates_partition_file(tmp_path):
    summary = store.write_records([_rec("26-1"), _rec("26-2")], tmp_path)
    part = tmp_path / "tcso-calls" / "2026-07.json"
    assert part.exists()
    rows = json.loads(part.read_text())
    assert len(rows) == 2
    assert summary["new"] == 2


def test_dedup_across_runs(tmp_path):
    store.write_records([_rec("26-1")], tmp_path)
    summary = store.write_records([_rec("26-1"), _rec("26-9")], tmp_path)
    rows = json.loads((tmp_path / "tcso-calls" / "2026-07.json").read_text())
    assert len(rows) == 2  # 26-1 not duplicated
    assert summary["new"] == 1


def test_partitions_split_by_month(tmp_path):
    store.write_records([_rec("26-1", month="07"), _rec("26-2", month="08")], tmp_path)
    assert (tmp_path / "tcso-calls" / "2026-07.json").exists()
    assert (tmp_path / "tcso-calls" / "2026-08.json").exists()


def test_index_written(tmp_path):
    store.write_records([_rec("26-1")], tmp_path)
    index = json.loads((tmp_path / "index.json").read_text())
    assert "tcso-calls" in index
    assert index["tcso-calls"][0]["count"] == 1


def test_stored_rows_have_no_name_or_media(tmp_path):
    store.write_records([_rec("26-1")], tmp_path)
    rows = json.loads((tmp_path / "tcso-calls" / "2026-07.json").read_text())
    for r in rows:
        assert "name" not in r
        assert not any("mug" in k.lower() or "photo" in k.lower() for k in r)
