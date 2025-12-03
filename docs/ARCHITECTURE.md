# Gold Standard — System Architecture (Enhanced)

## Purpose
This document summarizes the system architecture, design rationale, and operational conventions for Gold Standard. It is an actionable reference for contributors, maintainers, and operators — covering module responsibilities, data flow, persistence, concurrency, testing, and deployment.

## Design principles
- Single responsibility per module; clear public APIs for integration.
- Robustness: graceful fallbacks (NumPy implementations) when optional deps unavailable.
- Reproducibility: deterministic runs, pinned environments (Python 3.12).
- Observability: structured logging, health metrics, and CI tests.
- Minimal privileges: file locking and transactional DB operations to prevent corruption.

## High-level overview
Gold Standard is a Precious Metals Intelligence System that combines market data ingestion, technical analysis, regime/strategy synthesis, memory/persistence, and optional AI-enhanced insights. Primary concerns:
- Reliable data retrieval (yfinance + fallbacks)
- Deterministic TA with fallbacks (pandas_ta → NumPy)
- Persistent memory and graded predictions for simulation and backtesting
- Lightweight GUI and CLI for operators

ASCII data flow:
```
[yfinance / fetchers] -> QuantEngine -> Strategist -> Cortex (memory)
                           |               ^
                           v               |
                       reports & charts     |
                           v               |
                       db_manager.sqlite <- run/gui -> user
                                   ^
                                   +-- scripts/ (scheduler, split_reports)
```

## Core modules (3‑module design)

| Module   | Class       | Responsibility |
|----------|-------------|----------------|
| Memory   | Cortex      | Persistent memory; prediction grading; trade simulation; file locking; upserts to SQLite |
| Data     | QuantEngine | Market data fetchers; data normalization; TA indicators (pandas_ta with fallbacks); chart generation; CSV/JSON export |
| Strategy | Strategist  | Regime detection; bias synthesis; signal scoring; optional AI augmentation (Gemini) |

Key design notes:
- Each module exposes a small public API surface, documented in docstrings and validated by unit tests.
- Side effects (file/DB writes, network) centralized to facilitate testing and mocking.

## Entry points and responsibilities

| File | Purpose |
|------|---------|
| main.py | Core analysis pipeline, orchestrates modules for end-to-end runs |
| run.py  | CLI wrapper and scheduler integration (daemon mode, `--daemon`) |
| gui.py  | Tkinter dashboard for exploration, journaling, and manual runs |
| db_manager.py | Database access layer with migration helpers and transactional APIs |

Operational behavior:
- `run.py` provides a "Run All" mode used by schedulers and CI integration tests.
- `gui.py` auto-activates virtualenv via `ensure_venv()` and reexecutes under venv Python.

## Assets & configuration

ASSETS map (canonical):
```py
ASSETS = {
    'GOLD':   {'p': 'GC=F',   'b': 'GLD'},
    'SILVER': {'p': 'SI=F',   'b': 'SLV'},
    'DXY':    {'p': 'DX-Y.NYB','b': 'UUP'},
    'YIELD':  {'p': '^TNX',   'b': 'IEF'},
    'VIX':    {'p': '^VIX',   'b': '^VIX'},
    'SPX':    {'p': '^GSPC',  'b': 'SPY'}
}
```

Config conventions:
- Use a single `config.yaml` or environment variables (`.env`) for credentials and toggles (e.g., AI_ENABLED=false).
- Keep secrets out of repo; tests that require `.env` should provide fixtures or mocking.

Example config snippet:
```yaml
python_version: 3.12
assets:
  - GOLD
  - SILVER
ai:
  enabled: true
  provider: gemini
db:
  path: ./data/gold_standard.sqlite
logging:
  level: INFO
```

## Database schema (SQLite) & migration
Primary tables:

- journals: daily analysis journals
  - id INTEGER PK
  - date TEXT (ISO)
  - content TEXT
  - bias TEXT
  - gold_price REAL, silver_price REAL, gsr REAL
  - ai_enabled INTEGER
  - created_at, updated_at TIMESTAMP

- reports: aggregated reports
  - id, report_type, period, content, summary, ai_enabled, created_at

- analysis_snapshots: technical data per asset/time
  - id, date, asset, price, rsi, sma_50, sma_200, atr, adx, trend, raw_data

- premarket_plans: premarket plans
  - id, date, content, bias, catalysts, ai_enabled, created_at

- trades: simulated trades
  - id, trade_id, direction, asset, entry_price, exit_price, stop_loss, take_profit
  - status, result, pnl, pnl_pct, entry_date, exit_date, notes, created_at

- **entity_insights** (NEW): extracted entities from reports
  - id, entity_name, entity_type, context, relevance_score
  - source_report, extracted_at, metadata

- **action_insights** (NEW): actionable tasks from reports
  - id, action_id (unique), action_type, title, description
  - priority, status, source_report, source_context
  - deadline, result, created_at, completed_at, metadata

- **task_execution_log** (NEW): task execution audit trail
  - id, action_id, success, result_data, execution_time_ms
  - error_message, artifacts, executed_at

- **system_config** (NEW): runtime configuration storage
  - id, key (unique), value, description, updated_at

Provide migrations via simple SQL files or a lightweight migration helper in `db_manager.py`. Example DDL:
```sql
CREATE TABLE IF NOT EXISTS journals (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  asset TEXT NOT NULL,
  bias TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Concurrency & integrity:
- All DB writes performed inside transactions.
- File-level locking provided by `filelock` when Cortex reads/writes memory files; prevents concurrent corruption across processes.

## Technical analysis & fallbacks
- Primary TA library: pandas_ta (fast, expressive). Fallbacks implemented in pure NumPy when pandas_ta or numba are unavailable.
- Indicator implementations include SMA, EMA, RSI, MACD, ATR, plus custom regime detectors.
- Unit tests verify parity between pandas_ta outputs and NumPy fallbacks for key indicators.

## AI Integration
- Optional, toggled via config (`--no-ai` to disable).
- Adapter pattern abstracts provider (Gemini adapter).
- All prompts and AI outputs treated as advisory — any AI result is post-processed and persisted with versioned prompt metadata.

## Scripts (scripts/)
- split_reports.py: generates weekly/monthly/yearly reports and pushes snapshots into DB.
- pre_market.py: generates pre-market plans for trading day.
- live_analysis.py: produces intraday watchlists and categorizations.
- economic_calendar.py: maintains Fed/ECB/NFP/CPI calendar via scraping; run periodically.
- **insights_engine.py**: Extracts entity and action insights from generated reports. Powers autonomous task execution.
- **task_executor.py**: Executes action insights (research, data fetch, monitoring, calculations) before next cycle.
- **file_organizer.py**: Intelligently organizes, categorizes, dates, and archives reports and charts.

## Insights & Task Execution System

Gold Standard features a fully autonomous intelligence pipeline that extracts insights from generated reports and executes actionable tasks without manual intervention.

### Entity Insights
- Extracts named entities from reports: institutions (Fed, ECB, CME), indicators (CPI, RSI), assets, events, persons
- Pattern-based extraction with relevance scoring
- Stored in `entity_insights` table for historical analysis

### Action Insights  
- Identifies actionable tasks from report content:
  - **research**: Topics requiring further investigation
  - **data_fetch**: COT data, ETF flows, yields to retrieve
  - **news_scan**: Headlines to monitor
  - **calculation**: Position sizing, risk/reward ratios
  - **monitoring**: Price levels, breakout/breakdown alerts
  - **code_task**: Custom analysis code generation
- Priority-based queue (critical → high → medium → low)
- Deadline calculation based on priority

### Task Executor
- Processes action queue before next analysis cycle
- AI-powered research and news analysis via Gemini
- Data fetching via yfinance for real-time market data
- Results saved to `output/research/` with full audit trail
- Execution logged to `task_execution_log` table

### Daemon Cycle Flow
```
1. Run analysis (reports, charts)
2. Extract entity insights → save to DB
3. Extract action insights → save to DB  
4. Execute pending tasks (up to 10 per cycle)
5. Log execution results
6. Organize files (categorize, archive)
7. Sleep until next interval (default: 1 minute)
```

## File Organization System (NEW)

### Auto-Categorization
Files are categorized by content patterns:
- journals, premarket, weekly, monthly, yearly
- catalysts, institutional, analysis, economic
- research (task outputs), charts

### Naming Convention
Files renamed to: `{Category}_{YYYY-MM-DD}.{ext}`
Examples:
- `Journal_2025-12-03.md`
- `PreMarket_2025-12-03.md`
- `Weekly_W49_2025-12-03.md`
- `InstMatrix_2025-12-03.md`

### Archive Policy
- Files older than 7 days automatically archived
- Archive structure: `archive/{reports|charts}/{year}/{month}/`
- File index maintained at `output/FILE_INDEX.md`

## Testing & CI
- Test suite: pytest (total historically 33 tests — ensure updated counts).
- Key test files:
  - test_core.py (bias extraction)
  - test_gemini.py (AI adapter; loads .env in CI with safeguards)
  - test_split_reports.py
  - test_ta_fallback.py (fallback parity)
- CI pipeline:
  - lint (ruff) → test (pytest) → integration
  - Enforce Python 3.12 in CI runners

## Observability & UX
- Structured JSON logs (timed, level, module).
- GUI: dark theme, gold accents, date picker, live status indicators, journaling UI.
- Exportable charts (PNG/SVG) and CSV/JSON for reproducibility.

## Deployment & Operations
- Runtime: Python 3.12; prefer pinned dependencies via poetry/requirements.txt.
- Deployment modes:
  - Local interactive (gui.py)
  - Headless scheduled runs (run.py --daemon)
  - CI/integration for nightly reports
- Backups: periodic snapshot exports of key DB tables (reports, analysis_snapshots, trades).

## Extensibility & Contribution points
- Add new assets: update ASSETS map and provide ticker validation in QuantEngine.
- Add TA indicators: implement in indicators/ with tests comparing fallback implementations.
- Add AI providers: implement new adapter conforming to Strategist.ai_adapter interface.

## Vector Studio Integration
Gold Standard includes a companion high-performance vector database and AI training platform (`../vector_database/`) for semantic search and future AI training:

**Purpose:**
- Store embeddings of charts, reports, and journals
- Enable RAG (Retrieval Augmented Generation) for AI queries
- Build training datasets for custom models

**Architecture:**
- C++20 with SIMD optimization (AVX2/AVX-512)
- HNSW index for fast approximate nearest neighbor search
- ONNX Runtime for local embeddings (no cloud API costs)
- Text model: all-MiniLM-L6-v2 (384→512 dim)
- Image model: CLIP ViT-B/32 (512 dim)

**Build Requirements:**
- CMake 3.20+
- Visual Studio 2022 (or Build Tools)
- Ninja (optional, for faster builds)

**Setup:**
```powershell
cd ../vector_database
.\scripts\build.ps1 -AutoInstall  # Installs missing deps
python scripts\download_models.py --download
```

**Integration Points:**
- `pyvdb` Python bindings for direct use from Gold Standard
- CLI tool `vdb_cli` for manual operations
- Memory-mapped storage for efficient large-scale data

## Troubleshooting
- "pandas_ta missing": system falls back to NumPy; check logs for performance impact.
- "DB locked": ensure filelock is operational and only one long-running write is executing; avoid networked filesystems for SQLite.
- "Tests failing in CI": confirm Python 3.12 runner and that .env secrets are supplied via CI secrets (test_gemini).
- "CMake not found": run `winget install Kitware.CMake` or use `build.ps1 -AutoInstall`
- "Visual Studio not found": run `winget install Microsoft.VisualStudio.2022.BuildTools`

## Recent changes (session highlights)
- **Daemon interval reduced to 1 minute** (configurable via --interval-min)
- **Entity Insights extraction** - auto-identifies key entities in reports
- **Action Insights extraction** - identifies actionable tasks from reports
- **Task Executor** - autonomously executes pending tasks before next cycle
- **File Organizer** - intelligent categorization, dating, and archiving
- **New DB tables**: entity_insights, action_insights, task_execution_log, system_config
- CI pinned to Python 3.12
- Auto-venv activation added
- Improved test .env handling
- TA fallback parity tests added
- UI polish: sharper corners, glass effects, Geist font
- Vector Studio project added for semantic search and RAG
- Automated dependency installation via winget

## Quick reference: file map
- main.py, run.py, gui.py, db_manager.py
- core/: Cortex, QuantEngine, Strategist implementations
- scripts/: split_reports.py, pre_market.py, live_analysis.py, economic_calendar.py, **insights_engine.py**, **task_executor.py**, **file_organizer.py**
- tests/: test_*.py
- docs/: ARCHITECTURE.md, GUIDE.md, index.html (sample outputs)
- ../vector_database/: Vector Studio - C++ vector database for embeddings

Contact / Ownership: See repository root CODEOWNERS for module maintainers.

Keep this file current when structural or schema changes occur — especially when adding new tables, assets, or toggles that affect persistence or analysis outputs.
