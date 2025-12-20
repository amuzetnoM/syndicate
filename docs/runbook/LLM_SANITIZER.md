# LLM Sanitizer Runbook

This runbook details what to do when the LLM sanitizer flags or corrects generated reports.

## Detection

- Alerts to watch:
  - `GoldStandardLLMSanitizerCorrections` (warning): Sanitizer made corrections to generated reports.
  - `GoldStandardLLMQueueGrowing` (page): Queue backlog is increasing.
  - `GoldStandardLLMWorkerDown` (page): Worker process is down.

- Inspect Prometheus metrics:
  - `gost_llm_sanitizer_corrections_total` (counter)
  - `gost_llm_queue_length` (gauge)
  - `gost_llm_worker_running` (gauge)

## Investigation Steps

1. Query audit records:

   sqlite3 data/gold_standard.db "SELECT id, task_id, corrections, notes, created_at FROM llm_sanitizer_audit ORDER BY created_at DESC LIMIT 20;"

   Review `notes` to see what replacements were made.

2. Check `llm_tasks` table to find flagged tasks:

   sqlite3 data/gold_standard.db "SELECT id, document_path, status, attempts, response FROM llm_tasks WHERE status = 'flagged' ORDER BY id DESC LIMIT 20;"

3. Inspect the flagged report on disk (path in `document_path`) — frontmatter will have `sanitizer_flagged: true` when flagged.

## Remediation

- If corrections are minor (e.g., one numeric rounding fix):
  - Update document if necessary and clear the `flagged` status manually in DB or re-run the worker after verification.

- If corrections indicate a systemic issue (e.g., LLM hallucinating prices):
  - Disable AI generation temporarily by setting `LLM_ASYNC_QUEUE=0` or using `--no-ai` flags in run commands.
  - Investigate upstream data feed (QuantEngine/yfinance) to ensure canonical values are correct.
  - Consider increasing `LLM_SANITIZER_FLAG_THRESHOLD` temporarily if false-positives are observed.

## Postmortem & Notifications

- If a `flagged` task corresponds to a published Notion page, treat it as a potential content incident: follow standard incident response, notify stakeholders, and re-publish corrected content.
- For repeated sanitizer corrections, consider adding a Discord/Slack alert (planned after release).

## Config & Tuning

- `LLM_SANITIZER_FLAG_THRESHOLD` (env var): default 2 — number of corrections that trigger automatic flagging.
- `LLM_ASYNC_QUEUE` (env var): when enabled, tasks are enqueued and processed by worker. For urgent mitigation, disable to force manual generation.

---

This runbook should be updated if sanitization behavior or thresholds change.
