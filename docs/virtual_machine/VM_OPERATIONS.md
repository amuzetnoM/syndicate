# Syndicate VM Operations Manual

> **Last Updated:** 2025-12-30

This document provides a comprehensive, granular overview of the Syndicate VM operations, environment, and management procedures.

---

## Quick Reference

| Item | Value |
|------|-------|
| **VM Name** | `syndicate` |
| **Zone** | `us-east1-b` |
| **Machine Type** | `e2-standard-2` (8GB RAM, 2 vCPU) |
| **OS** | Debian 12 |
| **User** | `ali_shakil_backup_gmail_com` |
| **Python** | 3.12 (Miniforge) |
| **Project Root** | `/home/ali_shakil_backup_gmail_com/syndicate` |

---

## Directory Structure

```
/home/ali_shakil_backup_gmail_com/
├── miniforge3/                    # Conda environment manager
│   └── envs/syndicate/            # Python 3.12 environment
├── syndicate/                     # Main project directory
│   ├── .env                       # Environment variables (secrets)
│   ├── run.py                     # Main daemon entry point
│   ├── data/syndicate.db          # SQLite database
│   ├── output/                    # Generated reports
│   │   ├── reports/               # Organized by type
│   │   ├── digests/               # Daily digests
│   │   └── research/              # Research documents
│   ├── scripts/                   # Utility scripts
│   │   ├── syndicate_sentinel.py  # Watchdog service
│   │   ├── notion_publisher.py    # Notion sync
│   │   └── llm_worker.py          # LLM task processor
│   ├── src/digest_bot/            # Discord bot
│   └── deploy/systemd/normalized/ # Service definitions
└── .cache/syndicate/models/       # LLM model files
    └── Phi-3-mini-4k-instruct-q4.gguf
```

---

## Systemd Services

### Core Services

| Service | Description | Status |
|---------|-------------|--------|
| `syndicate-daemon.service` | Main analysis daemon (240min cycles) | ✅ Enabled |
| `syndicate-executor.service` | LLM task executor | ✅ Enabled |
| `syndicate-discord.service` | Discord bot | ✅ Enabled |
| `syndicate-sentinel.service` | Self-healing watchdog | ✅ Enabled |

### Management Commands

```bash
# Check all services
sudo systemctl status syndicate-*

# View recent logs
sudo journalctl -u syndicate-daemon -n 100 --no-pager

# Restart a service
sudo systemctl restart syndicate-discord

# Follow logs in real-time
sudo journalctl -u syndicate-sentinel -f
```

---

## Environment Configuration

The `.env` file contains all secrets and configuration:

```bash
# View current config (redacted)
cat ~/syndicate/.env | grep -v KEY | grep -v TOKEN

# Required variables:
LLM_PROVIDER=local
LOCAL_LLM_MODEL=/home/ali_shakil_backup_gmail_com/.cache/syndicate/models/Phi-3-mini-4k-instruct-q4.gguf
DISCORD_BOT_TOKEN=<valid_token>
DISCORD_APP_ID=<app_id>
NOTION_API_KEY=<notion_key>
NOTION_DATABASE_ID=<database_id>
```

---

## Database Operations

### Location
```
~/syndicate/data/syndicate.db
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `llm_tasks` | LLM processing queue |
| `notion_sync` | Notion sync history |
| `document_lifecycle` | Document status tracking |
| `system_config` | Runtime configuration |

### Common Queries

```bash
# Check stuck tasks
cd ~/syndicate && ~/miniforge3/envs/syndicate/bin/python scripts/check_status.py

# Reset stuck tasks
cd ~/syndicate && ~/miniforge3/envs/syndicate/bin/python scripts/reset_stuck.py

# Check Notion publishing status
cd ~/syndicate && ~/miniforge3/envs/syndicate/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/syndicate.db')
c = conn.cursor()
c.execute(\"SELECT value FROM system_config WHERE key='notion_publishing_enabled'\")
print('Notion publishing:', c.fetchone())
"
```

---

## LLM Configuration

### Model Details
- **Model:** Phi-3 Mini 4K Instruct (Q4 quantized)
- **Size:** ~2.3 GB
- **Context:** 4096 tokens
- **Inference:** CPU-only (llama.cpp backend)

### Fallback Chain
1. **Local** (Phi-3 via llama.cpp) - Primary
2. **Ollama** (if configured) - Fallback
3. **Gemini** (if API key set) - Cloud fallback

---

## Sentinel Watchdog

The Sentinel service (`syndicate_sentinel.py`) provides:

1. **Service Monitoring** - Checks and restarts failed services
2. **Stuck Task Recovery** - Resets tasks stuck for >60 minutes
3. **Resource Monitoring** - Logs memory usage
4. **Boot Persistence** - Starts automatically on VM boot

### Logs
```bash
# Sentinel logs
sudo journalctl -u syndicate-sentinel -n 50

# Sentinel file log
cat ~/sentinel.log
```

---

## Maintenance Procedures

### Daily Health Check
```bash
# Quick status check
sudo systemctl status syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# Check for stuck tasks
cd ~/syndicate && ~/miniforge3/envs/syndicate/bin/python scripts/check_status.py
```

### Manual Analysis Run
```bash
cd ~/syndicate
~/miniforge3/envs/syndicate/bin/python run.py --once
```

### Force Notion Sync
```bash
cd ~/syndicate
~/miniforge3/envs/syndicate/bin/python scripts/publish_unsynced_to_notion.py --force
```

---

## SSH Access

```bash
# From local machine
gcloud compute ssh ali_shakil_backup_gmail_com@syndicate --zone=us-east1-b

# File transfer
gcloud compute scp localfile.txt ali_shakil_backup_gmail_com@syndicate:~/syndicate/ --zone=us-east1-b
```

---

## Troubleshooting

### Service Won't Start
1. Check logs: `sudo journalctl -u <service> -n 100`
2. Verify `.env` exists and has correct permissions
3. Check Python environment: `~/miniforge3/envs/syndicate/bin/python --version`

### LLM Not Responding
1. Check model exists: `ls -lh ~/.cache/syndicate/models/`
2. Check memory: `free -h`
3. Look for OOM in logs: `dmesg | grep -i oom`

### Notion Sync Failing
1. Verify API key is valid in Notion settings
2. Ensure integration is shared with target database
3. Check publishing is enabled: Query `system_config` table

---

## Contact

For emergencies or escalations, check the Discord `🔧-service` channel.
