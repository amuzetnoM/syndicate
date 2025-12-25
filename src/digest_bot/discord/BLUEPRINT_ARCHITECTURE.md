# Syndicate — Discord Bot Blueprint (Architecture)

Overview
--------
This document captures the architecture and design rationale for a first-of-its-kind, state-of-the-art Discord integration for Syndicate. The bot is designed to be an operational control-plane and a lightweight assistant for day-to-day monitoring, incident alerts, digest publishing, and constrained LLM-powered interactions.

Goals
-----
- Operational visibility: post daily LLM reports, sanitizer alerts, and queue health to an ops channel.
- Human-in-the-loop: provide commands to fetch recent sanitizer audits, flag/unflag tasks, and re-run a generation.
- Safety-first: never post raw LLM-generated content without sanitizer checks; allow operators to accept or reject content.
- Extensibility: modular Cog-based architecture (discord.py) so features are pluggable and testable.
- Metrics & health: expose internal metrics via Prometheus client and readiness endpoints.
- Security: least privilege tokens, secure storage for webhook tokens and ephemeral secrets, rate limiting, and role-based command controls.

Core Components
---------------
- Bot core: `bot_base.py` — initialize the `discord.Bot` (slash + message commands), lifecycle management, metrics, graceful shutdown.
- Cogs:
  - `cogs.reporting` — create and send daily digest posts on demand, view last report, and schedule ad-hoc runs.
  - `cogs.sanitizer_alerts` — listen for sanitizer audit events and post compact summaries, allow triage commands.
  - `cogs.moderation` — role-restricted commands for operators: view flagged tasks, re-run, or mark as resolved.
  - `cogs.pins` — utilities to pin and manage recent chart messages and enforce pin limits (auto-unpin older charts).
  - `cogs.resources` — publish changelog, docs, and pinned command guide into `📚-resources`.
  - `cogs.llm_integration` — run short LLM queries with enforced ICU (inspection) and sanitized results.
- Utilities:
  - `utils.metrics` — Prometheus gauges/counters integrated with `syndicate/metrics` pipeline.
  - `utils.notifier` — wrapper to send messages to Discord webhooks and internal channels.

Operational patterns
--------------------
- Use slash commands for interactive ops and message-based low-noise notifications for alerts.
- Background task loop: sends daily report, watches sanitizer counters, and alerts if thresholds breached.
- Circuit breaker and retry policies when calling external services (Ollama, Notion, Google GenAI).
- Audit logging: every moderator action is written to the DB (or audit log) with user, timestamp, and justification.

Security & deployment
---------------------
- Bot token stored in a secrets manager (.env for staging, Vault/KMS for production).
- Use minimal scopes for bot (gateway intents minimized; only enable MESSAGE_CONTENT if required and justified).
- Systemd unit sample and containerization recommended (Dockerfile + process supervisor).

Testing & CI
------------
- Unit tests: validate Cog registration, configuration parsing, and command permission checks using mocked Discord objects.
- Integration smoke: run in a staging channel with a test bot token for sanity verification.

Roadmap
-------
1. Phase 1 — Full Data Digest & Approval Workflow (MVP)
   - `/digest full` (operators only): generates a full-data digest (summary + bias, rationale, headstate, KPIs, flagged items) posted as a short Discord message with an attached thread and a link to a full Notion/Gist for deeper inspection.
   - **Interactive approval buttons**: `Approve`, `Flag`, `Re-run` attached to digest message. Approve triggers an audit entry and optional Notion publish (via operator confirm); Flag marks the task for manual review; Re-run enqueues a rerun via `llm_tasks`.
   - **Audit trail**: every operator action (approve/flag/rerun) is recorded in a DB `bot_audit` table with user, action, details, and timestamp.
   - **Safety rules**: sanitized numeric enforcement required before any Approve action completes.
2. Phase 2 — Subscriptions & Policy Engine
   - Topic subscriptions (gold/macros), policy-driven automations (queue/backlog thresholds), and scheduled incident workflows.
3. Phase 3 — Explainable signals & gamification
   - Signal citations, rationale expansion, operator leaderboards, and simulations.

Operational details for Phase 1
-------------------------------
- Message flow: digest posted to ops channel → bot starts thread → operators take action using buttons → bot logs action and, on approval, publishes to Notion (or other configured sinks).
- Size handling: short digest in chat (<=2k chars), full digest as Notion page or file upload; message shows a compact summary and link.
- Deployment & safety: token storage in Vault, staging enablement in a private ops channel first, and operator role gating for approval commands.

Testing & rollout
------------------
- Unit tests for command handlers and audit logging, integration smoke on staging, and manual operator-run trials for 1–2 weeks before wider roll-out.
