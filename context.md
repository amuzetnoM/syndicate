# Syndicate — Local Development

Purpose
-------
This document captures the full, current operational and developer context for the Syndicate repository and the local machine ("this computer") that is used as the authoritative runner for testing and production-like execution.

Read this file first when returning to this machine or when another operator takes over; it is intended to provide the necessary commands, file locations, service names, and outstanding items to get the system back into the same working state described here.

Keep this file up-to-date when making any operational change (services, timers, secrets, or architecture).

---

Repository
----------
- Path: /home/adam/worxpace/syndicate
- Branch: main (HEAD == origin/main at commit bbc2923a36e841a23e5d20701827de076975f14d at time of writing)
- Important files:
  - `pyproject.toml` — project metadata and versioning
  - `src/` — main Python package
  - `src/digest_bot/` — Discord bot and automation code
  - `docs/virtual_machine/VM_ACCESS.md` — VM access notes and quick checks
  - `docs/virtual_machine/VM_VERIFICATION_CHECKLIST.md` — operator checklist
  - `deploy/systemd/` — systemd unit and timer templates
  - `.env` — runtime environment variables (sensitive; file stored locally and not committed to VCS)

Environment
-----------
- Python virtualenv: /home/adam/.venv
- Use venv python with: `/home/adam/.venv/bin/python` and `pip` commands using that interpreter.
- To run tests: `/home/adam/.venv/bin/pytest -q`
- Local packages are installed in editable mode for development: `pip install -e .`

Key Services (systemd)
----------------------
Service names and behaviour (configured to start on boot):
- `syndicate-discord-bot.service` — runs bot: `python -m digest_bot.discord.bot`
  - Unit file: `/etc/systemd/system/syndicate-discord-bot.service`
  - WorkingDirectory: `/home/adam/worxpace/syndicate`
  - Env: `EnvironmentFile=/home/adam/worxpace/syndicate/.env`
- `syndicate-llm-worker.service` — worker daemon (`scripts/llm_worker.py`)
- `syndicate-daily-llm-report.timer` & `.service` — runs daily summary & posts to ops webhook
- `syndicate-monitor.service` — monitoring agent (added to ensure services remain active and enabled)

All core services are enabled and should be set to `Restart=on-failure` so they come back on their own.

Runtime secrets
---------------
- `.env` holds runtime secrets used by services (Discord tokens, Notion keys, webhook URLs, LLM provider keys). Keep it permissioned to `600` and owned by `adam`.
- Do not commit `.env` to the repo.

Discord integration notes
-------------------------
- Bot token set via `DISCORD_BOT_TOKEN` in `.env`.
- Recommended workflow: rely on slash commands when `DISCORD_ENABLE_MESSAGE_CONTENT=0` for safer deployment.
- The bot supports a ServerBlueprint that auto-creates roles & channels; important channels created:
  - `📚-resources` — changelog & pinned commands
  - `🔧-service` — private service channel for operators
  - `📊-daily-digests`, `🚨-alerts`, `🤖-bot-logs`, `📋-admin-commands`

Monitoring & self-healing
-------------------------
- `syndicate-monitor.service` runs a Python script (`scripts/service_monitor.py`) that:
  - Periodically checks the status of the core services (`syndicate-discord-bot.service`, `syndicate-llm-worker.service`, `syndicate-daily-llm-report.timer`),
  - Restarts any service that is inactive, and ensures they are enabled to start on boot,
  - Logs actions to systemd journal and to `/var/log/syndicate/service_monitor.log`.

Usage & common operations
------------------------
- Start/stop/restart a service:
  - `sudo systemctl restart syndicate-discord-bot.service`
  - `sudo systemctl status syndicate-llm-worker.service`
- View logs (recent):
  - `sudo journalctl -u syndicate-discord-bot.service -n 200 --no-pager`
- Run a dry-run of the daily report:
  - `/home/adam/.venv/bin/python -m digest_bot.daily_report --dry-run`
- Create `🔧-service` channel via helper (if missing):
  - `/home/adam/.venv/bin/python scripts/discord_create_service_channel.py`

Known issues & troubleshooting notes
-----------------------------------
- Ollama timeouts: Local Ollama calls can timeout if models are missing or server is unresponsive — check `OLLAMA_HOST` and model presence.
- Discord privileged intents: If you need message-content intents, enable them in the Discord developer portal and set `DISCORD_ENABLE_MESSAGE_CONTENT=1` in `.env`.
- healthcheck/retry services: `syndicate-healthcheck.service` and retry service were intentionally left disabled until their helper scripts are installed.

Change log (operational summary)
--------------------------------
- v3.6.0 release prepared locally; package installed in editable mode and tests run: `114 passed, 3 skipped`.
- Added `ResourcesCog` and `PinsCog` to manage changelog publishing and pinned charts.
- Blueprint expanded with `🔧-service` channel and corresponding helper script.
- Created monitor agent service and enabled core services to start at boot.

If you need to move the authoritative runner to a different machine:
1. Ensure the target host has the same repository state (`git clone` or `git pull origin main`).
2. Copy the `.env` file securely (do not check into git). Ensure file ownership and mode `600`.
3. Install Python deps in a venv and `pip install -e .`.
4. Copy systemd unit files: `deploy/systemd/*` to `/etc/systemd/system/` and `sudo systemctl daemon-reload`.

> **Note:** Running `./setup.sh` will attempt to copy `deploy/systemd/*` into `/etc/systemd/system/` and **enable & start** `syndicate-monitor.service` (and other core units) automatically on the first run when systemd is present; this operation requires `sudo` access.

5. Enable and start services: `sudo systemctl enable --now syndicate-discord-bot.service syndicate-llm-worker.service && sudo systemctl enable --now syndicate-daily-llm-report.timer syndicate-monitor.service`.
6. Verify with `sudo systemctl status` and `sudo journalctl -u <service>`.

Contact & ownership
-------------------
- Current operator: `adam` (local username). Keep this person as the first contact for emergency actions.

---

This document is generated and should be maintained as the canonical context for this machine and this repository. If anything important changes (services, secret locations, hostnames, expected behaviours), update this file immediately and commit the change.
