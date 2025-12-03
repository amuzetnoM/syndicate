# Changelog

All notable changes to Gold Standard are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] - 2025-12-03

### Added
- **Notion Integration**
  - Automatic publishing of all reports to Notion database
  - New `scripts/notion_publisher.py` with full markdown-to-blocks conversion
  - Supports tables, code blocks, headers, lists, and callouts
  - Configurable via `NOTION_API_KEY` and `NOTION_DATABASE_ID` environment variables

- **Frontmatter System**
  - YAML metadata headers for all generated reports
  - New `scripts/frontmatter.py` with intelligent type detection
  - Auto-extracts tags from content (tickers, keywords)
  - Journal-specific metadata: bias extraction, gold price
  - Report categorization: journal, premarket, catalyst, institutional, technical, economic

- **Publishing Pipeline**
  - Notion sync integrated into `run.py` as Step 5
  - Frontmatter applied automatically after report generation

- **Documentation Site Redesign**
  - Complete overhaul of `docs/index.html`
  - Glass morphism UI with gold accent theming
  - Animated background with floating orbs and parallax effects
  - Notion workspace quick-link in navigation and hero
  - Bold uppercase "GOLD STANDARD" branding

### Changed
- Updated `README.md` with Notion integration instructions
- Updated `GUIDE.md` with frontmatter and Notion sections
- Updated `ARCHITECTURE.md` with new module documentation
- Simplified `.env` and `.env.template` formatting

### Fixed
- Notion API property mapping (title vs Name)
- Output path resolution in notion_publisher.py
- Removed residual frontmatter code from economic_calendar.py

---

## [3.0.0] - 2025-12-03

### Added
- **Autonomous Task Execution System**
  - InsightsEngine extracts entity and action insights from generated reports
  - TaskExecutor processes action queue before each analysis cycle
  - Six action types: research, data_fetch, news_scan, calculation, monitoring, code_task
  - Priority-based task queue (critical → high → medium → low)
  - Full audit trail with execution logging

- **Intelligent File Organization**
  - FileOrganizer with automatic categorization (journals, premarket, weekly, analysis, charts, etc.)
  - Standardized naming with dates (e.g., `Journal_2025-12-03.md`)
  - Auto-archiving of files older than 7 days
  - File index with searchable metadata

- **1-Minute Daemon Intervals**
  - Reduced default daemon interval from 4 hours to 1 minute
  - Configurable via `--interval-min` CLI argument
  - Integrated insights extraction and task execution into daemon cycle

- **Modern GUI v3**
  - Complete redesign with dual-pane architecture
  - Left pane: Charts grid with click-to-analyze, analysis panel, metrics, console
  - Right pane: AI Workspace with journal, reasoning/rationale, task queue, execution log
  - Premium dark theme with gold accents
  - Real-time status indicators and task tracking

- **Database Enhancements**
  - New tables: `entity_insights`, `action_insights`, `task_execution_log`, `system_config`
  - Methods for insights persistence and retrieval
  - Task status tracking and execution logging

- **Comprehensive Test Suite**
  - `test_insights.py` with 12 test cases for entity/action extraction
  - `test_file_organizer.py` with 15 test cases for file management
  - All 33 tests passing

### Changed
- Updated `run.py` with minute-based daemon cycle
- Enhanced `db_manager.py` with ~15 new methods
- Updated `main.py` Config with new feature flags

### Documentation
- Updated README.md with new features
- Updated ARCHITECTURE.md with insights/task system documentation
- Created this CHANGELOG.md

---

## [2.1.0] - 2025-12-01

### Added
- Vector Studio integration for semantic search
- Android MVP blueprints and wireframes
- Comprehensive architecture documentation (`docs/ARCHITECTURE.md`)
- Live API test instructions

### Changed
- Enhanced CI/CD pipeline with linting and integration jobs
- Updated documentation structure

---

## [2.0.0] - 2025-11-28

### Added
- **Autonomous Daemon Mode**
  - Periodic analysis execution with `--daemon` flag
  - 4-hour default intervals (now superseded by 1-minute in v3.0)
  
- **Database Manager**
  - SQLite persistence for all reports, journals, predictions
  - Cortex memory integration
  - Historical data retrieval

- **GUI Dashboard v2**
  - Date-wise journal browsing
  - Chart viewing tabs
  - Daemon control buttons
  - Console output display

- **Live Analysis Module**
  - Real-time gold market insights
  - Catalyst watchlist generation
  - Institutional matrix analysis

### Changed
- Virtual environment auto-detection and activation
- Enhanced SMA computation with pandas fallback

---

## [1.5.0] - 2025-11-25

### Added
- Pre-market plan generation
- Interactive menu in `run.py`
- Split reports generator (weekly, monthly, yearly)

### Changed
- Unified CLI entry point
- Enhanced report generation modes

---

## [1.0.0] - 2025-11-20

### Added
- **Core Analysis Engine**
  - Multi-asset analysis: Gold, Silver, DXY, VIX, 10Y Yield, S&P 500
  - Technical indicators: RSI, ADX, ATR, SMA (50/200) via pandas_ta
  - Intermarket correlations and Gold/Silver ratio analysis

- **Google Gemini Integration**
  - AI-powered natural language analysis
  - Gemini 2.0 Flash model support

- **Report Generation**
  - Daily journals with market summary
  - 1Y and 3M horizon analysis
  - Catalyst reports
  - Economic calendar integration

- **Automated Charts**
  - Candlestick charts with SMA overlays
  - Generated via mplfinance

- **Cortex Memory System**
  - Prediction tracking
  - Performance grading
  - Win/loss streak maintenance

- **Basic GUI**
  - Report generation interface
  - Mode selection (full, daily, journal-only)

- **Setup Scripts**
  - Windows PowerShell setup (`setup.ps1`)
  - Unix bash setup (`setup.sh`)
  - Environment initialization

---

## [0.1.0] - 2025-11-15

### Added
- Initial project structure
- Basic gold price fetching via yfinance
- README and project documentation
- MIT License
- GitHub Actions CI workflow

---

[3.1.0]: https://github.com/amuzetnoM/gold_standard/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/amuzetnoM/gold_standard/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/amuzetnoM/gold_standard/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/amuzetnoM/gold_standard/compare/v1.5.0...v2.0.0
[1.5.0]: https://github.com/amuzetnoM/gold_standard/compare/v1.0.0...v1.5.0
[1.0.0]: https://github.com/amuzetnoM/gold_standard/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/amuzetnoM/gold_standard/releases/tag/v0.1.0
