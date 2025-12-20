# Discord Bot Command Codex — Phase 1

This file is a concise reference for commands exposed by the Discord bot during Phase 1.

Slash commands (recommended)
----------------------------
- /digest quick [period=24h]
  - Public summary of recent data.
  - Example: `/digest quick period=24h`

- /digest full [period=24h] [mode=short|full]
  - Operator-only; posts a short summary in-channel + opens a thread containing a link to the full Notion/Gist. Attaches interactive buttons: Approve, Flag, Re-run.
  - Example: `/digest full period=24h mode=short`

- /headstate
  - Operator-only; returns a 1–3 line headstate and short plan.

- /sanitizer audits [limit]
  - Show recent sanitizer audit records (operators).

- /flagged list [limit]
  - List flagged tasks and their IDs (operators).

- /task rerun <task_id>
  - Re-enqueue an existing task for processing (operators).

- /approve <task_id>
  - Approve flagged content (operators). Requires the task to be sanitized (no sanitizer corrections) and will create an audit record. If sanitizer corrections exist, approval is blocked and the audit will note the failed attempt.

Moderation commands (admin-only)
---------------------------------
- /moderation warn <user> <reason>
- /moderation mute <user> <duration>
- /moderation kick <user> <reason>
- /moderation ban <user> <reason>

Notes
-----
- All operator actions are recorded in `bot_audit` for transparency.
- The UI interaction (Approve/Flag/Re-run) is intentionally lightweight to reduce friction and promote rapid triage.
