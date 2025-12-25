# Digest Bot — Architecture

> Lightweight local AI summarizer for Syndicate daily outputs.

---

## 1. Overview

Digest Bot is a standalone module that reads the day's analysis outputs (pre-market plan, daily journal) plus the most recent weekly report, then generates a concise actionable summary using a local LLM. It is designed for:

- **Multi-provider LLM** — local llama.cpp (default) with Ollama as optional alternative; zero cloud dependency.
- **Robust gating** — only produces output when all required inputs are present.
- **Extensibility** — Discord CLI bot integration for server management, moderation, and AI-powered insights.

---

## 2. Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Syndicate Output                      │
│  output/                                                         │
│   ├── journals/YYYY-MM-DD_daily_journal.md                       │
│   ├── pre_market/YYYY-MM-DD_pre_market.md                        │
│   └── weekly/YYYY-Www_weekly_rundown.md                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Digest Bot                               │
│  src/digest_bot/                                                 │
│   ├── __init__.py                                                │
│   ├── __main__.py          # CLI entry point                     │
│   ├── config.py            # Paths, polling intervals, env vars  │
│   ├── file_gate.py         # Input presence & date validation    │
│   ├── summarizer.py        # LLM prompt builder & caller         │
│   ├── writer.py            # Digest output writer                │
│   └── discord/             # Future: Discord bot integration     │
│        ├── __init__.py                                           │
│        └── bot.py                                                │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Digest Output                             │
│  output/digests/YYYY-MM-DD_digest.md                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

1. **Scheduler** (systemd timer / cron / manual) invokes `python -m digest_bot`.
2. **Config** loads paths, polling settings, LLM provider preference from env / `.env`.
3. **File Gate** checks (strict dating):
    - Pre-market file dated **exactly** for the target day (filename date = target; optional frontmatter date = target).
    - Daily journal dated **exactly** for the target day (same rules).
    - Latest weekly report within lookback window (default 14 days).
4. If **all gates pass** → proceed. If **any gate fails** → log status, sleep, retry (configurable retries & interval).
5. **Summarizer** reads the three documents, builds prompt, calls local LLM.
6. **Writer** saves digest to `output/digests/YYYY-MM-DD_digest.md`.
7. (Future) **Discord** posts digest to configured channel.

---

## 4. Gate Logic (Detailed)

| Gate | Condition | Behavior on Fail |
|------|-----------|------------------|
| `journal_for_target` | Filename date == target AND (if present) frontmatter date == target | Skip file; continue search; fail gate if none |
| `premarket_for_target` | Filename date == target AND (if present) frontmatter date == target | Skip file; continue search; fail gate if none |
| `weekly_recent` | Latest weekly within `WEEKLY_LOOKBACK_DAYS` (default 14) | Wait & retry |
| `digest_not_exists` | Target-date digest not already written | Exit success (idempotent) |

Selection rules:
- File names must encode the date (YYYY-MM-DD) and be an exact match for the run date.
- If frontmatter contains `date:`, it **must** equal the target date; mismatches are rejected.
- Older or newer files in the same folder are ignored—no cross-day leakage.
- Weekly reports remain “latest within lookback” so the newest available is used.
- Every rejected candidate is logged with the reason (filename/frontmatter mismatch) to aid ops triage.

Retry strategy:
- `RETRY_INTERVAL_SEC` (default 300 = 5 min)
- `MAX_RETRIES` (default 48 → covers 4 hours window)
- After max retries, exit with status 1 and log warning.

---

## 5. LLM Integration

Digest Bot supports multiple local LLM providers via a pluggable abstraction layer.

### Provider Priority

| Priority | Provider | Notes |
|----------|----------|-------|
| 1 (default) | llama.cpp (GGUF) | On-device inference; CPU or GPU-accelerated via `llama-cpp-python` |
| 2 (optional) | Ollama | Local server mode; easy model management; GPU-accelerated |

### Provider Selection

```
LLM_PROVIDER=local       # llama.cpp (default)
LLM_PROVIDER=ollama      # Use Ollama server
```

### llama.cpp Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOCAL_LLM_MODEL` | `models/mistral-7b.gguf` | Path to GGUF model |
| `LOCAL_LLM_GPU_LAYERS` | `0` | GPU layers (0 = CPU, -1 = all) |
| `LOCAL_LLM_CONTEXT` | `4096` | Context window size |
| `LOCAL_LLM_THREADS` | `0` | CPU threads (0 = auto) |

### Ollama Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral` | Model name |

Prompt template (≈300 word cap):

```
You are a concise financial analyst.
Given the following three documents from today's Syndicate analysis:

--- PRE-MARKET PLAN ---
{pre_market_content}

--- DAILY JOURNAL ---
{journal_content}

--- WEEKLY REPORT (latest) ---
{weekly_content}

Produce a SHORT digest (max 300 words) with:
1. **Key Takeaways** (3-5 bullets)
2. **Actionable Next Steps** (2-3 bullets)
3. **Rationale** (1-2 sentences explaining your reasoning)

Be direct. No filler.
```

---

## 6. Output Format

`output/digests/YYYY-MM-DD_digest.md`:

```markdown
# Daily Digest — YYYY-MM-DD

## Key Takeaways
- …

## Actionable Next Steps
- …

## Rationale
…

---
_Generated by Digest Bot at HH:MM UTC_
```

---

## 7. Extension: Discord AI CLI Bot

A full-featured Discord bot with AI-powered server management, moderation, and self-refactoring capabilities.

### 7.1 Directory Structure

```
src/digest_bot/discord/
├── __init__.py
├── bot.py                 # Bot setup, event loop, lifecycle
├── commands/
│   ├── __init__.py
│   ├── digest.py          # /digest commands
│   ├── structure.py       # Channel/category management
│   ├── moderation.py      # Mod actions, escalation
│   ├── roles.py           # Role intelligence
│   ├── health.py          # Activity monitoring
│   └── knowledge.py       # Summaries, living docs
├── services/
│   ├── __init__.py
│   ├── gate_keeper.py     # Spam/raid detection
│   ├── activity_tracker.py# Engagement metrics
│   ├── refactor_engine.py # Self-refactoring logic
│   └── scheduler.py       # Timed actions
└── models/
    ├── __init__.py
    └── server_state.py    # Server state persistence
```

### 7.2 Capability Matrix

#### 🧱 Structural Management

| Capability | Description |
|------------|-------------|
| Create / delete channels | Programmatic channel lifecycle |
| Create / modify categories | Organize server structure |
| Rename channels based on usage | AI-suggested naming |
| Archive dead channels | Move inactive channels to archive |
| Reorder server layout | Optimize channel order by activity |
| Enforce naming conventions | Auto-rename violations |

#### 🛡 Moderation & Hygiene

| Capability | Description |
|------------|-------------|
| Detect spam / raids | Pattern recognition, rate limiting |
| Auto-timeout / kick / ban | Escalating response based on severity |
| Escalation logic | Warn → mute → kick → ban pipeline |
| Lock threads | Freeze heated discussions |
| Enforce slow-mode dynamically | Adjust based on message velocity |

#### 👥 Role & Permission Intelligence

| Capability | Description |
|------------|-------------|
| Auto-assign roles based on behavior | Activity-based promotion |
| Adjust permissions dynamically | Context-aware access control |
| Detect privilege abuse | Flag unusual permission usage |
| Create temporary roles | Time-boxed access grants |

#### 📊 Activity & Health Monitoring

| Capability | Description |
|------------|-------------|
| Track engagement decay | Per-channel activity trends |
| Detect dead zones | Identify unused channels |
| Recommend consolidation | Suggest merging low-activity channels |
| Generate weekly health reports | Server vitals summary |

#### 🧠 Knowledge & Memory

| Capability | Description |
|------------|-------------|
| Summarize channels | AI-generated channel summaries |
| Maintain living docs | Auto-update documentation channels |
| Auto-update pinned messages | Keep pins current |
| Detect repeated questions | FAQ detection and response |

#### 🔄 Self-Refactoring (Autonomous)

| Capability | Description |
|------------|-------------|
| Suggest structural changes | AI proposes server improvements |
| Simulate changes before applying | Dry-run mode with impact preview |
| Apply during low-activity windows | Schedule changes for off-peak |
| Roll back if engagement drops | Auto-revert harmful changes |

### 7.3 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Bot authentication token |
| `DISCORD_GUILD_ID` | Yes | Target server ID |
| `DISCORD_DIGEST_CHANNEL_ID` | No | Channel for digest posts |
| `DISCORD_LOG_CHANNEL_ID` | No | Channel for bot action logs |
| `DISCORD_ADMIN_ROLE_ID` | No | Role that can manage bot |
| `DISCORD_AUTO_REFACTOR` | No | Enable self-refactoring (default: false) |

### 7.4 Command Reference

| Command | Description |
|---------|-------------|
| `/digest [date]` | Fetch digest (latest or specific date) |
| `/health` | Generate server health report |
| `/summarize #channel` | Summarize channel content |
| `/suggest` | Get AI structural recommendations |
| `/simulate <action>` | Preview change impact |
| `/apply <action>` | Execute approved change |
| `/rollback` | Revert last structural change |

---

## 8. Error Handling

| Scenario | Handling |
|----------|----------|
| LLM timeout | Retry up to 3 times with exponential backoff |
| LLM returns empty | Log error, do not write digest, exit 1 |
| File read error | Log, treat as gate fail, retry |
| Disk full on write | Log critical, exit 1 |

---

## 9. Logging

- Logs to `output/digests/digest_bot.log` (rotating, 5 MB max, 3 backups).
- Levels: DEBUG (gate checks), INFO (success), WARNING (retries), ERROR (failures).

---

## 10. Security & Performance

- **Minimal network** — llama.cpp: zero network; Ollama: localhost only.
- **Discord bot** — outbound HTTPS to Discord API only.
- Prompt token budget: ~4k tokens input, ~500 tokens output.
- Single-threaded digest; Discord bot uses async event loop.
- Safe to run via systemd with `flock` (digest) or as long-running service (Discord).

---

_Last updated: 2025-12-15_
