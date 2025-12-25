# Discord Integration — Setup & Ops

This document describes how to create a Discord application, install the bot into a guild, create a webhook, and run the bot under systemd in staging or production.

Prerequisites
- A Discord account with sufficient permissions in the target server (Manage Server / Manage Webhooks / Manage Roles)
- `DISCORD_BOT_TOKEN` and `DISCORD_OPS_CHANNEL_ID` (or a webhook URL for notifications)

1) Create the application & bot
- Go to https://discord.com/developers/applications → New Application
- App Settings → "Bot" → Add Bot → copy the **Bot Token** and store it securely (use Vault for production)
- Under Bot settings: enable **SERVER MEMBERS INTENT** and **MESSAGE CONTENT INTENT** only if required. Keep message content disabled unless strictly needed.

2) Invite the bot to server
- OAuth2 → URL Generator
  - Scopes: `bot`, `applications.commands`
  - Bot permissions: `Send Messages`, `Manage Webhooks`, `Manage Roles` (if you want self-guiding role setup — otherwise use an admin to create roles)
- Copy invite URL and open it in browser to add the bot to the server.

3) Create ops channel & role
- Create a private channel `#ops-livestream` or `📊-daily-digests` and a role named `operators`.
- Invite initial operators and ensure the bot can read/send messages and create webhooks in this channel.

4) Create a webhook (optional)
- Manual: Channel Settings -> Integrations -> Create Webhook -> copy webhook URL
- Programmatic: run `DISCORD_BOT_TOKEN=<token> python scripts/create_discord_webhook.py --channel-id <channel_id>`
  - This requires the bot to have Manage Webhooks permission in the channel.

5) Configure environment
- Create `.env` in repo root (or better, use Vault):
  - DISCORD_BOT_TOKEN=...
  - DISCORD_OPS_CHANNEL_ID=1234567890
  - DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
  - DISCORD_ENABLE_DAILY_REPORT=1
  - DISCORD_ENABLE_MESSAGE_CONTENT=0

6) Run in dev
- Activate venv: `source /home/adam/worxpace/.venv/bin/activate`
- Run bot: `python -m digest_bot.discord.bot_base`
- Watch logs and ensure bot registers commands and posts to configured channel.

Status: blueprint applied
- The ServerBlueprint was applied to the guild **Syndicate** (ID: `1452021841706090539`).
- Channels created (sample): `📊-daily-digests` (ops channel), `🚨-alerts`, `📈-premarket-plans`, `📔-trading-journal`, `💬-market-discussion`, `🤖-bot-logs`, `📋-admin-commands`.
- A webhook was created in the ops channel and `DISCORD_OPS_CHANNEL_ID` and `DISCORD_WEBHOOK_URL` were written to your local `.env` file.
- The systemd service `syndicate-discord-bot.service` has been installed and started on this VM; check its status with: `sudo systemctl status syndicate-discord-bot.service`.

7) Smoke tests
- Run `python -m digest_bot.daily_report` (with `PYTHONPATH=src`) to post a test digest via the webhook, or use `/digest quick` and `/digest full` in the ops channel (operator role required for the latter).

7) Systemd (staging/production)
- Use `deploy/systemd/syndicate-discord-bot.service.example` as a template.
- Copy it to `/etc/systemd/system/syndicate-discord-bot.service`, update `User` and `WorkingDirectory`, and ensure `.env` is readable by the service.
- `sudo systemctl daemon-reload && sudo systemctl enable --now syndicate-discord-bot.service`

8) Smoke tests
- `/digest quick` (public) and `/digest full` (operators) should be available; run them in the ops channel.
- Verify `Approve` / `Flag` / `Re-run` buttons function and that entries appear in `bot_audit` table.

9) Monitoring & Alerts
- Hook the bot logs into existing monitoring (systemd + journald). Add a Prometheus exporter if more granular metrics required.

10) Safety notes
- Keep `DISCORD_BOT_TOKEN` secret (Vault recommended). For automated deploys, inject it from secure secrets source.
- Do not enable MESSAGE_CONTENT unless necessary; prefer slash commands and ephemeral responses.

If you want, I can proceed to: (A) run the bot locally with your token to verify the full flow, or (B) prepare the staging VM systemd unit and test run for you. Tell me which to do next.