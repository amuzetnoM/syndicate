# Setup Guide

This setup guide provides concise, actionable steps to install, configure, and run the Syndicate project. It mirrors the project conventions used in `README.md` and focuses specifically on getting a system instance running reliably (development and production).

## 1. Overview

Syndicate is an end-to-end system for quantitative analysis of precious metals and intermarket assets. The system is designed to run autonomously with intelligent scheduling, multi-provider LLM fallback, and robust monitoring.

This guide covers:
- Requirements
- Automated and manual setup
- Environment configuration (`.env` keys)
- Systemd automation and timers
- Docker Compose and data storage best practices

## 2. Requirements

- Python: 3.10 — 3.13 (3.12 recommended)
- Git
- Docker & Docker Compose (for containerized services)
- On Linux production hosts: `systemd`

Optional but recommended:
- `winget` (Windows) for installing Python easily
- `mplfinance`, `numba`, and scientific dependencies (installed via `requirements.txt`)

## 3. Automated Setup (recommended)

The repository includes convenient scripts to automate the environment setup.

Windows (PowerShell):

```powershell
# If needed, install Python (example)
winget install Python.Python.3.12

# Run the setup script
.\setup.ps1
```

Unix / macOS / Linux:

```bash
chmod +x setup.sh
./setup.sh
```

What the setup scripts do:
- Create and (where supported) activate a Python virtual environment
- Install dependencies from `requirements.txt` and `requirements-dev.txt`
- Copy `.env.template` to `.env` (if present) and prompt for secret values
- Initialize `cortex_memory.json` (Cortex memory)
- Create expected output directories and initial config files

After automated setup, open `.env` and add the required keys (below).

## 4. Manual Setup (if you prefer control)

1. Clone and enter the repo:

```bash
git clone https://github.com/amuzetnoM/syndicate.git
cd syndicate
```

2. Create a virtual environment and activate it (example using Python 3.12):

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Unix / macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional: for tests and dev tools
```

4. Create `.env` from template and populate secrets:

```bash
cp .env.template .env
# Edit .env and add API keys
```

5. (Optional) Initialize Cortex memory:

```bash
python scripts/init_cortex.py
```

6. Quick run to validate installation:

```bash
# Run one-off (no AI)
python run.py --once --no-ai
```

## Environment Secrets Checklist

Copy `.env.template` to `.env` and populate required secrets. Do NOT commit `.env` to source control.

Core keys (from `.env.template`):

- `GEMINI_API_KEY` — Google Gemini API key (required for cloud LLM features).
- `NOTION_API_KEY` — Notion API key (for publishing reports).
- `NOTION_DATABASE_ID` — Notion database identifier to post pages.
- `IMGBB_API_KEY` — Image hosting API key (used to host chart images).

Optional / advanced keys:
- `LLM_PROVIDER` — Force provider (`gemini`, `ollama`, `local`).
- `PREFER_LOCAL_LLM` — Set to `1` to prefer local models and skip cloud calls.
- `OLLAMA_HOST` / `OLLAMA_MODEL` — Ollama server host and model name for local LLM option.
- `LOCAL_LLM_MODEL` and GPU/threads controls — For llama.cpp / GGUF setups.

Deployment notes:
- Systemd services may read `/path/to/.env` via `EnvironmentFile=`; ensure the service's path matches where `.env` is stored (e.g., `/mnt/newdisk/syndicate/syndicate_config/.env`).
- For Docker Compose, you can set `env_file: .env` in the Compose file or export variables in the shell that launches Compose.

Security checklist:
- Keep `.env` readable only to the service account (e.g., `chmod 600 .env`).
- Use a secrets manager (HashiCorp Vault, AWS Secrets Manager) for production where possible.
- Remove keys from shells or CI logs after use.


## 6. Systemd automation (production Linux)

The project ships with a set of `systemd` units and timers used to schedule and run tasks.

6.1 `syndicate-compose.service`
- Purpose: Manage the Docker Compose stack (monitoring + logging profiles).
- Typical settings: Requires `docker.service` and `network-online.target`; runs as `root`.
- Behavior: Start on boot, restart on failure (with short delay).

6.2 `syndicate-daily.service` + `syndicate-daily.timer`
- Purpose: Trigger the daily analysis run.
- Service example command: `/usr/bin/flock -n /tmp/syndicate.lock /home/ali_shakil_backup/codex.sh run`
  - `flock` ensures single concurrent run.
- Timer: `OnCalendar=daily` with a randomized `RandomizedDelaySec` up to 30m to avoid collisions.
- Logging: writes output to configured log path (example `/home/ali_shakil_backup/syndicate_config/run.log`).

6.3 `syndicate-weekly-cleanup.service` + `syndicate-weekly-cleanup.timer`
- Purpose: Weekly cleanup tasks for logs, temporary files, or DB maintenance.
- Example command: `/usr/local/bin/syndicate-weekly-cleanup.sh`
- Timer: weekly trigger (e.g., 1am Sunday).

Notes:
- Adjust users, paths, and logging locations to match your host environment.
- Use `systemctl enable --now` to enable services and timers.

## 7. Docker Compose & Data Storage

Syndicate uses Docker Compose to host the monitoring stack and optional containerized services. Important operational requirement:

High-importance: Do NOT store Docker data on the system root filesystem. Use a dedicated data disk and bind mounts.

Recommended approach in `docker-compose.yml`:

```yaml
services:
  gost:
    image: gost:latest
    volumes:
      - ./docker-data/gost_data:/app/data
      - ./docker-data/gost_output:/app/output
      - ./cortex_memory.json:/app/cortex_memory.json:ro

# Monitoring stack uses similar bind mounts for Prometheus/Grafana/Loki
```

Why bind mounts?
- Bind mounts ensure persistent data lives on a chosen data disk (e.g., `/mnt/data/docker-data`) instead of a small root partition.
- This avoids unexpected disk-full failures and simplifies backups.

Volume management checklist:
- Create a dedicated data directory on a separate disk, e.g. `/data/syndicate/docker-data` or a Windows drive.
- Update the Compose file or `.env` (if Compose references paths) to point to the dedicated directory.
- Ensure file system permissions allow the Docker user or service to read/write.

## 8. Docker Compose Services (summary)

The stack commonly includes:
- `gost` — main Syndicate application
- `prometheus`, `grafana` — metrics collection & dashboards
- `alertmanager` — alerting
- `node-exporter`, `cadvisor` — host / container metrics
- `loki`, `promtail` — log aggregation & collection
- `gost-dev` — development container (optional)

## 9. Running the System

Development / Interactive:

```bash
# In venv
python run.py --interactive
```

Autonomous daemon (recommended in production via systemd):

```bash
python run.py
# or use systemd timer/service as documented above
```

Daily/weekly automation is best handled via the provided systemd units and timers. Use `flock` or equivalent to avoid overlapping runs.

## 10. Logging & Monitoring

- Logs from autonomous runs are written to configured paths (see systemd service `StandardOutput`/`StandardError` settings).
- The Docker monitoring stack (Prometheus/Grafana/Loki) provides visibility into resource usage, metrics, and logs.

## 11. Troubleshooting

- Virtualenv activation issues: ensure you're using the correct Python executable matching the venv.
- Missing API keys: check `.env` and that variables are exported for systemd services.
- Disk full errors: verify Compose bind mounts point to the dedicated data disk.
- Systemd service failures: inspect `journalctl -u <service>` for startup logs.

## 12. Where to find more

Full project documentation, architecture diagrams, usage examples, and advanced topics are in the main README: [README.md](README.md).
For code-level details, inspect `src/`, `scripts/`, and `docker/` in the repository.
