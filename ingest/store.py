"""Partitioned JSON storage for normalized records.

Records are written to ``data/<source>/<YYYY-MM>.json`` and merged on each run,
deduped by ``Record.id``. This lets a daily GitHub Actions run accumulate history
in-repo (git is the archive) from sources that only publish a same-day snapshot.

A top-level ``data/index.json`` summarizes available partitions for the site.
"""

from __future__ import annotations

import json
from pathlib import Path

from ingest import schema


def _partition_key(record: schema.Record) -> tuple[str, str]:
    month = record.datetime[:7] if len(record.datetime) >= 7 else "unknown"
    return record.source, month


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_records(records: list[schema.Record], data_dir: str | Path) -> dict:
    """Merge ``records`` into partitioned JSON files under ``data_dir``.

    Returns a summary: {"written": int, "new": int, "partitions": [...]}.
    Existing records with the same id are preserved (not duplicated); genuinely
    new records are added. Media/name fields can never appear because Record has
    no such fields, but we defensively strip on the way out too.
    """
    data_dir = Path(data_dir)
    buckets: dict[tuple[str, str], list[schema.Record]] = {}
    for rec in records:
        buckets.setdefault(_partition_key(rec), []).append(rec)

    total_new = 0
    partitions: list[str] = []
    for (source, month), recs in sorted(buckets.items()):
        path = data_dir / source / f"{month}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = {r["id"]: r for r in _load(path)}
        before = len(existing)
        for rec in recs:
            row = schema.strip_names(schema.strip_media(rec.to_dict()))
            existing.setdefault(row["id"], row)
        merged = sorted(existing.values(), key=lambda r: (r.get("datetime", ""), r.get("id", "")))
        path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        total_new += len(existing) - before
        partitions.append(f"{source}/{month}")

    _write_index(data_dir)
    return {"written": len(records), "new": total_new, "partitions": partitions}


def _write_index(data_dir: Path) -> None:
    """Rebuild data/index.json from the partition files on disk."""
    index: dict[str, list[dict]] = {}
    for source_dir in sorted(p for p in data_dir.iterdir() if p.is_dir() and p.name != "raw"):
        parts = []
        for pf in sorted(source_dir.glob("*.json")):
            rows = _load(pf)
            parts.append({"month": pf.stem, "count": len(rows), "path": f"{source_dir.name}/{pf.name}"})
        if parts:
            index[source_dir.name] = parts
    (data_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
