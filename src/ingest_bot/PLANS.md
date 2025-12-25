# Ingest Bot Plans (skeleton)

Short-term checklist:
- [ ] Create `adapters/` skeleton with placeholder `fetch_since()` functions.
- [ ] Implement `pipeline/writer.py` that atomically writes batches to `data/ingest/<source>/YYYYMMDD.csv` and updates a `manifest.json` with `last_ingest_timestamp`.
- [ ] Create CLI entry `python -m ingest_bot.orchestrator --once --source fred` for one-shot ingest runs.
- [ ] Add unit tests to `tests/test_ingest_bot.py` for manifest behavior and writer atomicity.
- [ ] Add `syndicate-ingest.service` systemd unit template and a one-shot timer for daily ingestion.

Long-term/optional:
- Streaming mode and webhook handlers for push-based sources.
- Vectorization + export for LLM training pipeline (Parquet + FAISS export).
- Metrics & alerting integration into existing Prometheus stack.
