# Ingest Bot Blueprint

> **Short Research Note:** This skeleton is the starting point for an ingest engine. Runtime keys and data directories are ignored via `.gitignore`; keep secrets out of the repository and use `.env` or a secrets manager.

## Goals
- Provide a separate ingest service (not part of the main `run.py` loop) that can:
  - Poll or subscribe to realtime data sources (FRED, Rapid API feeds, MarketFlow, TradingEconomics, and yfinance fallback).
  - Normalize data into a canonical time-series schema and write to `data/ingest/<source>/`.
  - Maintain a small local index / manifest with last_ingest_timestamp per source.
  - Emit Prometheus metrics (ingest_latency_seconds, ingest_success_total, ingest_failures_total) for monitoring.

## Components
- adapters/ — source-specific adapters (e.g., `fred.py`, `rapid.py`, `marketflow.py`, `tradingeconomics.py`, `yfinance_adapter.py`). Each exports a simple `fetch_since(timestamp)` function that returns a list of records.
- orchestrator.py — schedules and runs adapter fetches, handles backoff and retries, writes manifests, and updates metrics.
- pipeline/ — normalization helpers and a small writer (`write_ingest_records(source, records, dest_dir)`).

## Operational notes
- The ingest bot should run as a separate systemd service (e.g., `syndicate-ingest.service`) or as a lightweight container.
- Secrets/API keys should be provided via host environment variables or a secrets manager; do NOT commit keys to the repo.
- Keep ingests idempotent: include source-provided IDs or timestamps and check the manifest before writing duplicates.

## Minimal Initial Scope (Skeleton)
- Add adapter skeletons for FRED, Rapid, MarketFlow, TradingEconomics, and yfinance (fallback).
- Add a single orchestrator that can be invoked via CLI or systemd timer to perform a one-shot ingest.
- Add tests that validate the manifest and writer behavior using sample fixture data.

## Future roadmap
- Add a streaming mode (webhooks or WebSocket) for high-frequency sources.
- Implement vectorization export (Parquet + embeddings) for downstream LLM usage.
- Add optional integration with a small local vectorstore (FAISS) and export helper for training pipelines (outside core scope).