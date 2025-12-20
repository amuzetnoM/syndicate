"""Writer helpers for ingest bot

Provides atomic write helpers and manifest updates for idempotent ingestion.
"""
import json
from pathlib import Path
from typing import List, Dict

DATA_ROOT = Path("data/ingest")


def write_ingest_records(source: str, records: List[Dict]):
    """Atomically write records for `source` into `data/ingest/<source>/`.

    Writes a JSONL file and updates manifest.json with `last_ingest_timestamp`.
    """
    if not records:
        return
    dest = DATA_ROOT / source
    dest.mkdir(parents=True, exist_ok=True)
    # Simple writer for skeleton: append to a daily file
    filename = dest / ("ingest_" + records[0].get("timestamp", "unknown")[:10] + ".jsonl")
    tmp = filename.with_suffix(".jsonl.tmp")
    with tmp.open("a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    tmp.replace(filename)

    # Update manifest
    manifest = dest / "manifest.json"
    m = {}
    if manifest.exists():
        m = json.loads(manifest.read_text())
    m["last_ingest_timestamp"] = records[-1].get("timestamp")
    manifest.write_text(json.dumps(m, indent=2))
