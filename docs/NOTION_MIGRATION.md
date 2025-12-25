# Notion Migration & Operational guide
>  2025-09-03 

This document covers the migration steps and operational hardening we've implemented to support Notion's 2025-09-03 multi-source databases.

## Key changes
- The Notion API now supports multiple *data sources* per database. Many operations must use `data_source_id` instead of `database_id`.
- The publisher now performs a discovery step and prefers `data_source_id` when creating pages and querying content.

## What we changed in the project
- `scripts/notion_publisher.py`
  - Added `data_source` discovery via `GET /v1/databases/:database_id` and `GET /v1/data_sources/:data_source_id`.
  - Uses `parent:{type: 'data_source_id', data_source_id: ...}` for page creation when available.
  - Uses data_source query endpoint when available and falls back gracefully.
  - Added more robust retries with structured logging, jitter, and alerts on terminal failure.
- Tests added: discovery, property mapping, data_source queries, webhook parsing, notifier alerts.
- Healthcheck: `scripts/health_check.py` + wrapper and systemd timer to run daily and perform basic self-healing.
- Notifier: `scripts/notifier.py` to send Discord webhook alerts (config: `DISCORD_WEBHOOK_URL`).

## How to operate
1. Ensure your integration token (NOTION_API_KEY) belongs to the same workspace as the database and the integration is *shared* with the database (Share → Invite → Integration).
2. If you want to pin a `data_source_id` (for deterministic behavior), add `NOTION_DATA_SOURCE_ID` to the project `.env`.
3. To test connection:
   - `cd /mnt/disk/syndicate`
   - `set -a && source .env && set +a && . .venv/bin/activate && python scripts/notion_publisher.py --test`
4. To force a publish for a file:
   - `python scripts/notion_publisher.py --file output/reports/journals/Journal_YYYY-MM-DD.md --force`

## Healthchecks & Alerting
- A healthcheck runs daily via systemd timer: `syndicate-healthcheck.timer` → `syndicate-healthcheck.service`.
- On failure, the healthcheck will attempt a basic restart of the run-once service and send an alert to Discord using `DISCORD_WEBHOOK_URL`.

## Next steps & recommendations
- We added extensive tests and CI; merge requests should include tests for any Notion interactions.
- We should consider a weekly smoke-test that performs a lightweight publish to a dedicated test data source.
- Consider adding automated remediation for missing packages or environment drifts (e.g. run ephemeral `pip install --upgrade -r requirements.txt` traffic guard) — needs approval.

---


