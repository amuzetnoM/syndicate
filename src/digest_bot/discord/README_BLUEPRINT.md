Syndicate Discord Bot — Blueprint

This blueprint contains a production-minded scaffold for the Discord bot powering operational notifications and light LLM interactions.

Quick start (dev)
------------------
1. Install digest bot requirements: `pip install -r src/digest_bot/requirements.txt`
2. Copy `.env.example` to `.env` and set `DISCORD_BOT_TOKEN` and `DISCORD_OPS_CHANNEL_ID`.
3. Run: `python -m digest_bot.discord.bot_base` (development run; does not auto-post to channels unless configured).

Design principles
-----------------
- Safety-first: the bot never publishes raw LLM outputs. All results go through `llm sanitizer` paths.
- Minimal privileges: run with only necessary intents and role checks for ops commands.
- Observability: metrics for command usage, errors, and background task outcomes.

Command Codex (Phase 1)
-----------------------
Public / low-privilege:
- `/digest quick [period=24h]` — short daily digest posted in channel (public).
- `/status` — quick health check (worker, queue length, recent corrections).

Operator (role: operators):
- `/digest full [period=24h] [mode=short|full]` — full-data digest (summary + link to full Notion/Gist). Posts message + thread, attaches `Approve`/`Flag`/`Re-run` buttons.
- `/headstate` — one-line headstate and 1–3 short plan items.
- `/sanitizer audits [limit]` — show recent sanitizer audits.
- `/flagged list [limit]` — list flagged tasks.
- `/task rerun <task_id>` — re-enqueue task for processing.
- `/approve <task_id>` — approve flagged content; requires sanitized numbers and creates an audit record.

Admin:
- `/moderation warn|mute|kick|ban <user> <reason>` — moderation actions (audit logged).
- `/policy set <policy-file>` — update policy rules (dry-run option available).

Files of interest
-----------------
- `bot_base.py`: orchestrator and lifecycle manager
- `cogs/`: modular features (reporting, moderation, sanitizer alerts, digest_workflow, pins)
- `utils.py`: shared helpers for metrics and notifier
- `CODex.md`: command reference and examples (new)
- `BLUEPRINT_ARCHITECTURE.md`: design doc

Notes
-----
This is a blueprint and intentionally conservative; full production rollout must include secrets management, an approval testing plan, and a careful permission audit before enabling message content intents.