# LLM Worker Metrics & Alerts

This document describes the Prometheus metrics and recommended alerting for the LLM queue and worker.

## Metrics added

- `gost_llm_queue_length` (Gauge): Number of pending LLM tasks in the SQLite queue (`llm_tasks` table).
- `gost_llm_worker_running` (Gauge): Worker running flag (1 running, 0 stopped).
- `gost_llm_tasks_processing` (Gauge): Number of tasks currently processing in a worker cycle.
- `gost_llm_sanitizer_corrections_total` (Counter): Total number of price/number corrections made by the sanitizer.

All metrics are served at the project's metrics server (default port `8000`), alongside `/healthz` and `/readyz` endpoints.

## Recommended Alert Rules

We added `deploy/prometheus/syndicate_llm_rules.yml` with the following alerts:

- `GoldStandardLLMQueueGrowing`: triggers when `gost_llm_queue_length > 10` for 5m.
- `GoldStandardLLMWorkerDown`: triggers when `gost_llm_worker_running == 0` for 2m.
- `GoldStandardLLMSanitizerCorrections`: triggers when `gost_llm_sanitizer_corrections_total > 0` (warning) — indicates the sanitizer corrected numbers and audit logs should be checked.

## Operational Notes

- The LLM sanitizer enforces canonical numeric values present in the prompt ("CANONICAL VALUES (DO NOT INVENT NUMBERS)") and replaces mismatched numeric mentions.

- Config knobs:
  - `LLM_SANITIZER_FLAG_THRESHOLD` (int, default=2): Number of corrections that cause a report to be flagged for manual review.
  - `LLM_ASYNC_QUEUE` (bool): When set, pre-market and insights tasks are enqueued and processed by the worker.

- Corrections are auditable in the `llm_sanitizer_audit` table; when corrections exceed the configured threshold (`LLM_SANITIZER_FLAG_THRESHOLD`, default `2`), the worker flags the task with status `flagged` for manual review and writes `sanitizer_flagged: true` to the report frontmatter.

- Alert routing recommendations: route `GoldStandardLLMWorkerDown` and `GoldStandardLLMQueueGrowing` to PagerDuty or other high priority channels; route `GoldStandardLLMSanitizerCorrections` to a Slack/Discord channel for on-call triage.
## Next steps

- Add Alertmanager routing rules and a silence policy for known maintenance windows.
- Add a Grafana dashboard panel showing queue length, sanitizer corrections, and worker processing count.

- Consider enabling the daily LLM operations report (see `src/digest_bot/daily_report.py`) to post a concise daily summary to a Discord/Slack channel so the team can spot trends without opening Grafana. Use `DISCORD_WEBHOOK_URL` env var or a systemd timer to schedule runs.
