# Digest Bot

> Lightweight robot summarizer for Syndicate daily outputs.

---

## What It Does

Digest Bot monitors the `output/` tree for today's **pre-market plan** and **daily journal**. Once both are present (and a recent **weekly report** exists), it invokes a local LLM to produce a concise, actionable digest saved to `output/digests/`.

Key features:

- **Multi-provider LLM** — local llama.cpp (default) or Ollama; zero cloud dependency.
- **Robust gating** — strict same-day matching (filename and optional frontmatter), retries until ready, and logs skipped candidates.
- **Idempotent** — skips if today's digest already exists.
- **Database fallback** — reads from SQLite if files not found.
- **Atomic writes** — temp file + rename for safe file operations.
- **Discord AI Bot** — full server management, moderation, and self-refactoring capabilities (planned).

---

## Installation

```bash
# From syndicate root
cd src/digest_bot
pip install -r requirements.txt

# If using llama.cpp (default)
pip install llama-cpp-python

# If using Ollama, ensure server is running
# ollama serve
```

---

## Quick Start

```bash
# From syndicate root, with venv active
python -m digest_bot                     # run with defaults
python -m digest_bot run                 # same as above
python -m digest_bot run --dry-run       # preview without saving
python -m digest_bot run --wait          # wait for inputs (retry loop)
python -m digest_bot run --date 2025-01-15  # specific date
python -m digest_bot check               # verify configuration
python -m digest_bot history             # list recent digests
python -m digest_bot cleanup --keep 30   # remove old digests
```

---

## CLI Commands

### `run` (default)

Generate a daily digest:

```bash
python -m digest_bot run [OPTIONS]

Options:
  -d, --date DATE     Target date (YYYY-MM-DD), default: today
  -n, --dry-run       Don't write output, just print
  -w, --wait          Wait for all inputs to be ready
  --overwrite         Overwrite existing digest
```

### `check`

Validate configuration and environment:

```bash
python -m digest_bot check
```

### `history`

List recent digests:

```bash
python -m digest_bot history --limit 10
```

### `cleanup`

Remove old digest files:

```bash
python -m digest_bot cleanup --keep 30 --dry-run
```

---

## Configuration

Set via environment variables or `.env` file in `syndicate/`:

### LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `local` | `local` (llama.cpp) or `ollama` |
| `LOCAL_LLM_MODEL` | `models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` | Path to GGUF model |
| `LOCAL_LLM_GPU_LAYERS` | `0` | GPU layers (0 = CPU, -1 = all) |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `LLM_MAX_TOKENS` | `768` | Max output tokens |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral` | Ollama model name |

### Path Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `output` | Base output directory |
| `REPORTS_DIR` | `output/reports` | Root for report folders |
| `JOURNALS_DIR` | `output/reports/journals` | Daily journal location |
| `PRE_MARKET_DIR` | `output/reports/premarket` | Pre-market plan location |
| `WEEKLY_DIR` | `output/reports/weekly` | Weekly report location |
| `DIGEST_OUTPUT_DIR` | `output/digests` | Digest output directory |
| `DATABASE_PATH` | `data/syndicate.db` | SQLite database path |
| `DIGEST_LOG_FILE` | `output/digests/digest_bot.log` | Log file path |

### Gate Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRY_INTERVAL_SEC` | `300` | Seconds between retries |
| `MAX_RETRIES` | `48` | Max retry attempts |
| `MAX_STALENESS_DAYS` | `1` | Max age for journal/premarket |
| `WEEKLY_LOOKBACK_DAYS` | `14` | Lookback window for weekly |
| `MIN_FILE_SIZE` | `100` | Minimum bytes to treat as valid |
| `USE_DATABASE_FALLBACK` | `1` | Enable SQLite fallback |

---

## Directory Structure

```
src/digest_bot/
├── __init__.py           # Package exports
├── __main__.py           # CLI entry point (Click-based)
├── config.py             # Configuration management
├── file_gate.py          # Input document retrieval
├── summarizer.py         # LLM prompt building & generation
├── writer.py             # Atomic file output
├── requirements.txt      # Dependencies
├── llm/                  # LLM provider abstraction
│   ├── __init__.py       # Provider exports
│   ├── base.py           # Abstract interface + dataclasses
│   ├── llamacpp.py       # llama-cpp-python implementation
│   ├── ollama.py         # Ollama HTTP API implementation
│   └── factory.py        # Provider factory + singleton
└── docs/
    ├── ARCHITECTURE.md   # Component design
    └── PLAN.md           # Implementation roadmap
```

---

## File Patterns

The digest bot looks for files with these naming patterns (filename date must equal the target date; if frontmatter contains `date:`, it must also match):

| Type | Pattern | Example |
|------|---------|---------|
| Journal | `Journal_YYYY-MM-DD.md` | `Journal_2025-01-15.md` |
| Pre-market | `premarket_YYYY-MM-DD.md` | `premarket_2025-01-15.md` |
| Weekly | `weekly_rundown_YYYY-MM-DD.md` | `weekly_rundown_2025-01-12.md` |
| Digest (output) | `digest_YYYY-MM-DD.md` | `digest_2025-01-15.md` |

Files are searched in `output/reports/` directory.

---

## Digest Output

Generated digests follow this structure (shortened for brevity):

```markdown
---
title: "Daily Digest - 2025-01-15"
generated: "2025-01-15T14:30:00"
provider: "llamacpp"
model: "mistral-7b"
tokens_used: 342

# 📊 Daily Digest — 2025-01-15

## Key Takeaways
- Gold tested $2,700 resistance as expected
- Dollar weakness continues to support metals
- Technical breakout above 50 DMA confirmed

## Actionable Next Steps
- Watch for pullback to $2,680 support for long entry
- Set alerts at $2,700 and $2,720 resistance levels

## Rationale
Pre-market analysis correctly identified key levels...
```

---

## Programmatic Usage

```python
from datetime import date

from digest_bot import Config, FileGate, Summarizer, DigestWriter

# Load configuration (env is read inside Config)
config = Config()

# Check for inputs
gate = FileGate(config)
status = gate.check_all_gates(date.today())

if status.all_inputs_ready:
    with Summarizer(config) as summarizer:
        result = summarizer.generate(status)

    if result.success:
        writer = DigestWriter(config)
        write_result = writer.write(result)
        print(f"Digest saved: {write_result.path}")
```

---

## Testing

```bash
# From syndicate root
pytest tests/test_digest_bot.py -v

# With coverage
pytest tests/test_digest_bot.py --cov=src/digest_bot
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — component diagram, data flow, gate logic.
- [Implementation Plan](docs/PLAN.md) — phased roadmap, milestones, testing.
- [Changelog](CHANGELOG.md) — release history and major changes.

---

## Roadmap

| Phase | Status |
|-------|--------|
| Architecture & planning | ✅ |
| Core scaffold | ✅ |
| LLM abstraction layer | ✅ |
| File gate logic | ✅ |
| Summarizer + writer | ✅ |
| CLI + logging | ✅ |
| Tests | ✅ |
| Systemd deployment | 🔜 |
| Discord core + commands | 🔜 |
| Discord services + self-refactoring | 🔜 |

---

## License

MIT — see project root LICENSE.
