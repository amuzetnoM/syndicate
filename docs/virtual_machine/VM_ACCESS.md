# VM Access Notes (odyssey)

**Date:** 2025-12-19

## Summary
- Project: `artifact-virtual` (display name: ARTIFACT VIRTUAL)
- VM: `odyssey`
- Zone: `europe-west9-b`
- External IP: `34.155.169.168`

## Updates 
1. Installed Google Cloud SDK on the host (already done earlier).
2. Performed device-flow login as `ali.shakil.backup@gmail.com` to create a service account.
3. Created a service account: `vm-access-sa@artifact-virtual.iam.gserviceaccount.com`.
4. Granted roles:
   - `roles/compute.instanceAdmin.v1` (to manage instance metadata)
   - `roles/iam.serviceAccountUser` (so the SA can operate with the compute service account where required)
5. Created a service-account JSON key and saved to: `/home/adam/sa-key.json`.
6. Activated the service account for gcloud: `gcloud auth activate-service-account --key-file=/home/adam/sa-key.json`.
7. Generated an SSH keypair on the host (ed25519):
   - Private: `/home/adam/.ssh/id_ed25519_gce` (600)
   - Public: `/home/adam/.ssh/id_ed25519_gce.pub`
8. Appended the public key to the instance `odyssey` metadata (username: `ali`):
   - Added entry: `ali:<ssh-ed25519 PUBLIC KEY>`
9. Confirmed SSH access works: `ssh -i /home/adam/.ssh/id_ed25519_gce ali@34.155.169.168` — succeeded.

## Commands to run (replay) 
- `gcloud auth login --no-launch-browser`
- `gcloud projects add-iam-policy-binding artifact-virtual --member=serviceAccount:vm-access-sa@artifact-virtual.iam.gserviceaccount.com --role=roles/iam.serviceAccountUser`
- `ssh-keygen -t ed25519 -f /home/adam/.ssh/id_ed25519_gce -N "" -C "ali"`
- `gcloud compute instances add-metadata odyssey --zone=europe-west9-b --project=artifact-virtual --metadata-from-file ssh-keys=/tmp/sshkeys_artifact.txt`
- `ssh -i /home/adam/.ssh/id_ed25519_gce -o IdentitiesOnly=yes ali@34.155.169.168`

## Security notes 
- The service-account key is stored at `/home/adam/sa-key.json`. This is sensitive—rotate or delete it when not required. To delete:
  - `gcloud iam service-accounts keys delete <KEY_ID> --iam-account=vm-access-sa@artifact-virtual.iam.gserviceaccount.com`
  - Or delete the service account if not needed: `gcloud iam service-accounts delete vm-access-sa@artifact-virtual.iam.gserviceaccount.com`
- If you prefer OS Login and centralized IAM-based access, we can enable `enable-oslogin` and grant the required `roles/compute.osLogin` / `roles/compute.osAdminLogin` roles instead.



# Actions Log

## Authentication
*2025-12-19*
- **Service account key** removed from IAM and local file shredded: `/home/adam/sa-key.json` was deleted.
- **Service account** `vm-access-sa@artifact-virtual.iam.gserviceaccount.com` was deleted.
- **SSH access** confirmed: `ssh -i /home/adam/.ssh/id_ed25519_gce ali@34.155.169.168` — user `ali` has passwordless sudo (is in `google-sudoers` group).
- **VM packages installed/checked** on `odyssey` (via sudo):
  - `git` present (2.39.5).
  - Installed: `python3-pip` (pip3), `docker.io` (Docker engine), `docker-compose-plugin` (Compose V2 plugin).
  - `ali` was added to the `docker` group and Docker service enabled.

## Automation & healthchecks
- A daily healthcheck is installed and enabled via systemd timer: `gold-standard-healthcheck.timer` → `gold-standard-healthcheck.service`.
- The runner script is `/opt/gold_standard_health_check.sh` (installed and executable) which calls `scripts/health_check.py` and performs a basic restart of the `gold-standard-run-once.service` on failure and triggers Discord alerts via `scripts/notifier.py` (if `DISCORD_WEBHOOK_URL` is set in `.env`).
- You can run the healthcheck manually: `sudo /opt/gold_standard_health_check.sh` and inspect logs with `journalctl -u gold-standard-healthcheck.service -n 200 --no-pager`.
- A new daily LLM-operations report generator was added: `src/digest_bot/daily_report.py`.
  - Usage (dry-run): `python -m digest_bot.daily_report --dry-run` — prints a markdown summary of queue length, sanitizer corrections, flagged tasks and recent errors.
  - Send to Discord: ensure `DISCORD_WEBHOOK_URL` is set in `.env` (or pass `--webhook <url>`), then run: `python -m digest_bot.daily_report`.
  - Install as a systemd timer (example):

```ini
# /etc/systemd/system/gold-standard-daily-llm-report.service
[Unit]
Description=Gold Standard daily LLM operations report

[Service]
Type=oneshot
User=ali
WorkingDirectory=/home/ali/worxpace/gold_standard
ExecStart=/usr/bin/env python -m digest_bot.daily_report

# /etc/systemd/system/gold-standard-daily-llm-report.timer
[Unit]
Description=Run Gold Standard daily LLM operations report daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

- You can test sending with a single run: `sudo systemctl start gold-standard-daily-llm-report.service` and inspect the logs with `journalctl -u gold-standard-daily-llm-report.service -n 200 --no-pager`.

## Discord webhook setup (quick)

If you want the Gold Standard system to post alerts to Discord, create a webhook in a channel (Server Settings → Integrations → Webhooks → New Webhook) and copy the webhook URL.

A helper script is provided to validate and persist the webhook and Notion credentials:

- Test and persist a Discord webhook into the project `.env` (and optionally to systemd units):

```bash
# Test and persist webhook to .env (will attempt to send a test message)
python scripts/discord_setup.py --webhook "https://discord.com/api/webhooks/..." 

# Persist into systemd units (requires sudo)
python scripts/discord_setup.py --webhook "https://discord.com/api/webhooks/..." --persist-systemd --services gold-standard-llm-worker.service,gold-standard-premarket-watcher.service
```

- Persist Notion credentials to `.env`:

```bash
python scripts/discord_setup.py --notion-api "<NOTION_TOKEN>" --notion-db "<DATABASE_ID>"
```

- If you prefer to manually edit `.env`, add the following lines (project root):

```ini
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
NOTION_API_KEY=secret_xxx
NOTION_DATABASE_ID=xxx-xxxx-...
```

- After updating systemd drop-in files, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gold-standard-llm-worker.service gold-standard-premarket-watcher.service
```

- The helper is a convenience to avoid editing systemd files directly; use it if you want the systemd units to inherit the env var automatically.

- We added a smoke-test CI workflow (`.github/workflows/smoke.yml`): set `SMOKE_NOTION_API_KEY` and `SMOKE_NOTION_DATABASE_ID` in GitHub Secrets to enable weekly smoke publishes.
- **Host tools**: `git`, `docker`, `docker-compose`, `python3`, and `gcc` are already installed and ready.

## Notion publishing status
- Notion connection: **OK** (test connection successful with configured `NOTION_API_KEY` and `NOTION_DATABASE_ID`).
- Publishing: **Partial** — I attempted to force-publish a generated report but the Notion API returned a 400 error ("Status is expected to be status."). I implemented code fallbacks to retry with different property encodings and a minimal payload, and also confirmed creating a minimal page (title only) works.
- **Action required**: please **share the Notion database** ("Precious Metals Complex") with your Notion integration (the integration linked to `NOTION_API_KEY`) from the Notion UI (Share → Invite → select the integration). This will ensure the integration has the correct permissions and let me re-run the publishing process end-to-end.

### VM Verification Checklist

A short verification checklist has been added to help you confirm the VM is healthy and ready to run the full Gold Standard stack unattended. See `VM_VERIFICATION_CHECKLIST.md` for a comprehensive, operator-friendly list of checks and commands (disk, services, timers, backups, metrics, and recovery steps).

Inline quick checks:
- [ ] Boot & systemd health (`sudo journalctl -b --no-pager | tail -n 200`)
- [ ] Disk usage (`df -h /` / `df -i /`)
- [ ] LLM worker (`systemctl status gold-standard-llm-worker.service`)
- [ ] Discord bot (`systemctl status gold-standard-discord-bot.service`)
- [ ] Daily report timer (`systemctl status gold-standard-daily-llm-report.timer`)

### Notes & recommendations
- The service account has been removed, so future metadata or IAM changes will require an owner or another admin account (e.g., `ali.shakil.backup@gmail.com`) or re-creation of an admin SA.
- For long-term multi-user management, consider enabling **OS Login** and granting IAM-based SSH roles (`roles/compute.osLogin` or `roles/compute.osAdminLogin`).