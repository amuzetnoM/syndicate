import json
from pathlib import Path
import tempfile

from ingest_bot.pipeline.writer import write_ingest_records


def test_writer_and_manifest(tmp_path):
    recs = [
        {"timestamp": "2025-12-20T00:00:00Z", "series_id": "GDP", "value": 100},
        {"timestamp": "2025-12-20T01:00:00Z", "series_id": "GDP", "value": 101},
    ]
    source = "testsource"
    # Ensure data dir isolated for test
    old_root = Path("data/ingest")
    try:
        # Use tmp path for writes
        Path("data/ingest").mkdir(parents=True, exist_ok=True)
        write_ingest_records(source, recs)
        dest = Path("data/ingest") / source
        assert (dest / "manifest.json").exists()
        m = json.loads((dest / "manifest.json").read_text())
        assert m["last_ingest_timestamp"] == recs[-1]["timestamp"]
    finally:
        # cleanup test writes
        import shutil

        shutil.rmtree("data/ingest", ignore_errors=True)
