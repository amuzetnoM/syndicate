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
  - asset TEXT
  - bias TEXT
  - notes TEXT
  - created_at TIMESTAMP

- reports: aggregated reports
  - id, period_start, period_end, type, summary, payload (JSON)

- analysis_snapshots: technical data per asset/time
  - id, asset, ts, indicators (JSON), prices (JSON)

- premaket_plans: premarket plans
  - id, date, plan (JSON), author

- trades: simulated trades
  - id, asset, entry_ts, exit_ts, entry_price, exit_price, pnl, metadata (JSON)

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

## Troubleshooting
- "pandas_ta missing": system falls back to NumPy; check logs for performance impact.
- "DB locked": ensure filelock is operational and only one long-running write is executing; avoid networked filesystems for SQLite.
- "Tests failing in CI": confirm Python 3.12 runner and that .env secrets are supplied via CI secrets (test_gemini).

## Recent changes (session highlights)
- CI pinned to Python 3.12
- Auto-venv activation added
- Improved test .env handling
- TA fallback parity tests added
- UI polish: sharper corners, glass effects, Geist font

## Quick reference: file map
- main.py, run.py, gui.py, db_manager.py
- core/: Cortex, QuantEngine, Strategist implementations
- scripts/: split_reports.py, pre_market.py, live_analysis.py, economic_calendar.py
- tests/: test_*.py
- docs/: ARCHITECTURE.md, GUIDE.md, index.html (sample outputs)

Contact / Ownership: See repository root CODEOWNERS for module maintainers.

Keep this file current when structural or schema changes occur — especially when adding new tables, assets, or toggles that affect persistence or analysis outputs.
