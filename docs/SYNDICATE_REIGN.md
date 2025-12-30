# SYNDICATE REIGN
## The Complete System Reference

> **Source of Truth** | Last Updated: 2025-12-30
> VM Name: `syndicate` | Codename: **Reign**

---

## 🏗️ INFRASTRUCTURE

### Hardware - Google Cloud VM
| Specification | Value |
|--------------|-------|
| **Instance Name** | `syndicate` |
| **Zone** | `us-east1-b` |
| **Machine Type** | `e2-standard-2` |
| **vCPUs** | 2 |
| **Memory** | 8 GB |
| **Storage** | 20 GB SSD |
| **OS** | Debian 12 (Bookworm) |
| **IP Type** | Ephemeral (External) |

### Access
```bash
# SSH Access
gcloud compute ssh ali_shakil_backup_gmail_com@syndicate --zone=us-east1-b

# File Transfer
gcloud compute scp <local> ali_shakil_backup_gmail_com@syndicate:<remote> --zone=us-east1-b
```

---

## 🐍 SOFTWARE ENVIRONMENT

### Python Stack
| Component | Version/Path |
|-----------|-------------|
| **Runtime** | Python 3.12 (Miniforge) |
| **Environment** | `~/miniforge3/envs/syndicate` |
| **Interpreter** | `~/miniforge3/envs/syndicate/bin/python` |
| **Pip** | `~/miniforge3/envs/syndicate/bin/pip` |

### Key Dependencies
- `discord.py` - Bot framework
- `llama-cpp-python` - Local LLM inference
- `notion-client` - Notion API
- `aiohttp` - Async HTTP
- `feedparser` - RSS parsing

---

## 📁 DIRECTORY STRUCTURE

```
/home/ali_shakil_backup_gmail_com/
├── miniforge3/                    # Conda environment manager
│   └── envs/syndicate/            # Python 3.12 environment
├── syndicate/                     # PROJECT ROOT
│   ├── .env                       # Secrets (API keys, tokens)
│   ├── run.py                     # Main daemon entry point
│   ├── db_manager.py              # Database interface
│   ├── config.py                  # Configuration
│   │
│   ├── data/
│   │   └── syndicate.db           # SQLite database
│   │
│   ├── output/                    # Generated content
│   │   ├── reports/               # Analysis reports
│   │   │   ├── premarket/         # Pre-market plans
│   │   │   ├── catalysts/         # Live catalysts
│   │   │   ├── economic/          # Economic calendars
│   │   │   ├── analysis/          # Technical analysis
│   │   │   └── institutional/     # Institutional data
│   │   ├── digests/               # Daily digests
│   │   ├── journals/              # Trading journals
│   │   └── research/              # Research documents
│   │
│   ├── scripts/                   # Utility scripts
│   │   ├── syndicate_sentinel.py  # Watchdog service
│   │   ├── scheduled_publisher.py # Discord scheduler
│   │   ├── journal_reviser.py     # End-of-day revision
│   │   ├── notion_publisher.py    # Notion sync
│   │   ├── llm_worker.py          # LLM task processor
│   │   └── local_llm.py           # Local model interface
│   │
│   ├── src/digest_bot/            # Discord bot
│   │   ├── discord/
│   │   │   ├── bot.py             # Main bot
│   │   │   ├── content_router.py  # Channel routing
│   │   │   ├── self_guide.py      # Server blueprints
│   │   │   └── cogs/              # Bot extensions
│   │   └── llm/                   # LLM providers
│   │
│   └── deploy/systemd/normalized/ # Service definitions
│
└── .cache/syndicate/models/       # AI Models
    └── Phi-3-mini-4k-instruct-q4.gguf  # Local LLM
```

---

## 🤖 AI SYSTEM

### Local LLM - Phi-3 Mini
| Property | Value |
|----------|-------|
| **Model** | Phi-3 Mini 4K Instruct |
| **Quantization** | Q4 (4-bit) |
| **Size** | ~2.3 GB |
| **Context** | 4096 tokens |
| **Backend** | llama.cpp (CPU) |
| **Path** | `~/.cache/syndicate/models/Phi-3-mini-4k-instruct-q4.gguf` |

### AI Policy
```
Priority: LOCAL → Ollama → Gemini (cloud fallback)
Default: LLM_PROVIDER=local
```

### AI Capabilities
- **Document Generation**: Pre-market, journals, reports
- **Content Summarization**: Daily digests
- **Journal Revision**: End-of-day news contextualization
- **Response Generation**: Discord mentions (future)

---

## ⚙️ SYSTEMD SERVICES

### Core Services (Always Running)
| Service | Purpose | Status |
|---------|---------|--------|
| `syndicate-daemon` | Main analysis daemon (240min cycles) | ✅ Enabled |
| `syndicate-executor` | LLM task processor | ✅ Enabled |
| `syndicate-discord` | Discord bot | ✅ Enabled |
| `syndicate-sentinel` | Watchdog/self-healing | ✅ Enabled |

### Scheduled Timers
| Timer | Time (UTC+5) | Purpose |
|-------|-------------|---------|
| `syndicate-publish-morning` | 7:00 AM | Premarket, catalysts, calendar |
| `syndicate-publish-journal` | 12:00 PM | Initial journal |
| `syndicate-publish-digest` | 5:00 PM | Comprehensive digest |
| `syndicate-revise-journal` | 10:00 PM | Revised journal with news |
| `syndicate-health` | Hourly | Health check |
| `syndicate-cleanup` | Daily | Database maintenance |

### Management Commands
```bash
# Status check
sudo systemctl status syndicate-*

# View logs
sudo journalctl -u syndicate-daemon -n 100 --no-pager

# Restart service
sudo systemctl restart syndicate-discord

# List timers
sudo systemctl list-timers | grep syndicate
```

---

## 💬 DISCORD INTEGRATION

### Server: SYNDICATE
| Property | Value |
|----------|-------|
| **Server ID** | `1452021841706090539` |
| **Bot Name** | Gost |
| **Bot ID** | `1452017439276531855` |

### Channel Structure
```
📊 MARKET INTELLIGENCE
├── #🚨-alerts           → Catalysts, market alerts
├── #📊-daily-digests    → Comprehensive summaries
├── #📈-premarket-plans  → Morning analysis
├── #📔-trading-journal  → Journal entries
├── #📚-research-journal → Research, economic data
└── #📈-day-charts       → Visualizations

💬 COMMUNITY
├── #💬-market-discussion → Community chat
├── #📋-bot-commands      → User commands
└── #📚-resources         → Learning materials

⚙️ ADMIN
├── #📋-admin-commands   → System/AI control
├── #🔧-service          → Dev backdoor, AI tunnel
├── #📥-reports          → LLM reports, audits
└── #🤖-bot-logs         → System logs
```

### Publishing Schedule (UTC+5)
| Time | Content | Channel |
|------|---------|---------|
| 7:00 AM | Pre-market, Catalysts | `#📈-premarket-plans`, `#🚨-alerts` |
| 12:00 PM | Initial Journal | `#📔-trading-journal` |
| 5:00 PM | Daily Digest | `#📊-daily-digests` |
| 10:00 PM | Revised Journal | `#📔-trading-journal` |

---

## 🗄️ DATABASE

### Location
```
~/syndicate/data/syndicate.db (SQLite)
```

### Key Tables
| Table | Purpose |
|-------|---------|
| `llm_tasks` | LLM processing queue |
| `notion_sync` | Notion sync history |
| `document_lifecycle` | Document status tracking |
| `system_config` | Runtime configuration |
| `journals` | Trading journal entries |
| `reports` | Generated reports |

### Common Queries
```bash
# Check stuck tasks
python scripts/check_status.py

# Reset stuck tasks
python scripts/reset_stuck.py

# Check Notion status
python -c "from db_manager import db; print(db.is_notion_publishing_enabled())"
```

---

## 🔐 SECRETS & CONFIGURATION

### Environment File: `~/syndicate/.env`

| Key | Purpose |
|-----|---------|
| `LLM_PROVIDER` | AI provider (local/ollama/gemini) |
| `LOCAL_LLM_MODEL` | Path to GGUF model |
| `DISCORD_BOT_TOKEN` | Bot authentication |
| `DISCORD_APP_ID` | Application ID |
| `NOTION_API_KEY` | Notion integration |
| `NOTION_DATABASE_ID` | Target database |
| `NEWSAPI_KEY` | News fetching |
| `GEMINI_API_KEY` | Cloud AI fallback |

---

## 🛡️ SELF-HEALING (Sentinel)

### Features
- **Service Monitoring**: Restarts failed services
- **Stuck Task Recovery**: Resets tasks stuck >60 min
- **Reboot Persistence**: Auto-starts on boot
- **Resource Monitoring**: Tracks memory usage

### Logs
```bash
# Systemd logs
sudo journalctl -u syndicate-sentinel -n 50

# File log
cat ~/sentinel.log
```

---

## 📊 MONITORING

### Quick Health Check
```bash
# All services status
sudo systemctl status syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel

# Active timers
sudo systemctl list-timers | grep syndicate

# Memory usage
free -h

# Disk usage
df -h
```

### Discord Channels
- System logs → `#🤖-bot-logs`
- Reports → `#📥-reports`
- Dev access → `#🔧-service`

---

## 🚨 EMERGENCY PROCEDURES

### Service Down
```bash
sudo systemctl restart syndicate-daemon syndicate-executor syndicate-discord
```

### Tasks Stuck
```bash
cd ~/syndicate && python scripts/reset_stuck.py
```

### Full Recovery
```bash
# Stop all
sudo systemctl stop syndicate-*

# Restart all
sudo systemctl start syndicate-daemon syndicate-executor syndicate-discord syndicate-sentinel
```

### VM Reboot
```bash
# Via gcloud
gcloud compute instances reset syndicate --zone=us-east1-b
```

---

## 📞 INTEGRATION POINTS

### External APIs
| Service | Purpose | Key Variable |
|---------|---------|--------------|
| Discord | Bot, webhooks | `DISCORD_BOT_TOKEN` |
| Notion | Document sync | `NOTION_API_KEY` |
| NewsAPI | News fetching | `NEWSAPI_KEY` |
| Gemini | AI fallback | `GEMINI_API_KEY` |
| Alpha Vantage | Market data | `ALPHAVANTAGE_API_KEY` |

---

## 🔄 DEPLOYMENT

### From Local to VM
```bash
# Sync code
gcloud compute scp -r gold_standard/* ali_shakil_backup_gmail_com@syndicate:syndicate/ --zone=us-east1-b

# Update services
gcloud compute ssh ali_shakil_backup_gmail_com@syndicate --zone=us-east1-b --command="sudo systemctl daemon-reload && sudo systemctl restart syndicate-daemon syndicate-discord"
```

---

*This document is the canonical reference for Syndicate Reign. Keep it updated.*
