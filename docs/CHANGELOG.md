# Changelog

All notable changes to Gold Standard are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.2.2] - 2025-12-04

### Added
- **Complete Docker Suite**
  - Multi-stage `Dockerfile` with builder/runtime/development stages
  - Non-root user security (`goldstandard` user)
  - Health check with database connectivity validation
  - Support for `linux/amd64` and `linux/arm64` platforms

- **Docker Compose Stack**
  - Full monitoring stack: Prometheus, Grafana, Alertmanager
  - Optional logging stack: Loki + Promtail (profile: logging)
  - Optional host metrics: cAdvisor, Node Exporter (profile: monitoring)
  - Development container with live code mounting (profile: dev)
  - Persistent volumes for data, metrics, and dashboards

- **Prometheus Metrics Endpoint**
  - `scripts/metrics_server.py` - Standalone metrics exporter
  - Metrics: tasks_ready, tasks_scheduled, stuck_tasks, completions, failures
  - Application uptime and last execution timestamp
  - `/metrics` and `/health` HTTP endpoints

- **Pre-configured Grafana Dashboard**
  - Gold Standard Overview with system health panels
  - CPU/Memory usage graphs
  - Task execution rate charts
  - Duration percentile tracking (p50, p95, p99)

- **Alert Rules**
  - GoldStandardDown - Application unreachable
  - StuckTasksDetected - Tasks stuck > 10 minutes
  - HighFailureRate - Task failure rate > 10%
  - HighDiskUsage, ContainerRestarting alerts

- **GitHub Actions Docker Workflow**
  - Automated build on release and version tags
  - Multi-platform builds (amd64 + arm64)
  - Security scanning with Trivy
  - Push to GitHub Container Registry (ghcr.io)
  - Build attestation and SBOM generation

### Changed
- Added `.dockerignore` for optimized builds
- All project files now have SIRIUS Alpha branding headers

### Documentation
- `docker/README.md` - Complete Docker deployment guide
- Architecture diagrams for containerized deployment
- Alertmanager configuration templates (Slack, email, webhooks)

---

## [3.2.1] - 2025-12-04

### Added
- **Natural Language Date Extraction**
  - `_extract_scheduled_date()` method in InsightsExtractor
  - Parses dates from task descriptions: "Dec 18", "December 18", "Jan 10th", "2025-12-25"
  - Automatic year rollover logic (past dates schedule to next year)
  - Default 9 AM execution time for scheduled tasks

- **Execution State Machine**
  - `claim_action()` - Atomic task claiming to prevent duplicate execution across processes
  - `release_action()` - Release tasks back to pending state for retry
  - `get_execution_context()` - Comprehensive state info for monitoring and debugging
  - Worker ID tracking in task metadata

- **System Health Monitoring**
  - `get_system_health()` method in DatabaseManager
  - Real-time metrics: ready_now, scheduled_future, stuck_in_progress counts
  - 24-hour execution statistics: total, success, avg_time_ms
  - Schedule tracker status overview

- **Self-Healing Recovery**
  - Enhanced startup recovery detects and resets stuck tasks
  - Automatic release of failed tasks back to pending for retry
  - Exponential backoff with retry count tracking in database
  - `retry_count` and `last_error` columns in action_insights table

- **Documentation Overhaul**
  - ARCHITECTURE.md: Full scheduling system documentation with state diagrams
  - GUIDE.md: User-facing scheduling guide with examples and tables
  - index_docs.html: New "Intelligent Scheduling" sidebar section with feature cards
  - index.html: Highlighted scheduling and self-healing features

### Changed
- Daemon now uses atomic claim/release pattern for race-condition-free execution
- Task execution logs success/fail counts with emoji indicators
- Health check runs before each execution cycle with automatic stuck task recovery
- Clear separation between "ready now" and "scheduled future" tasks

### Fixed
- Tasks with future dates (e.g., "Dec 18 FOMC") now properly wait until scheduled time
- Race conditions when multiple daemon processes run simultaneously
- Stuck tasks from previous crashes now automatically recover on startup

### Removed
- Temporary debugging scripts: `check_dec18.py`, `check_tasks.py`, `update_task_schedules.py`
- Cleaned `__pycache__` directories

---

## [3.2.0] - 2025-12-04

### Added
- **Intelligent Scheduling System**
  - New `schedule_tracker` table in database for frequency-based task execution
  - `should_run_task()` and `mark_task_run()` methods in DBManager
  - Configurable schedules: daily (journal), weekly (economic, institutional, task execution), monthly, yearly
  - Prevents redundant Notion publishing cycles during daemon loops

- **Notion Sync Deduplication**
  - New `notion_sync` table tracks file_path, file_hash, notion_page_id
  - Content hashing with SHA-256 to skip unchanged files
  - `is_file_synced()` and `record_notion_sync()` methods
  - `get_file_hash()` for deterministic content comparison

- **Persistent Task Execution**
  - Exponential backoff retry logic (30s to 10min, max 10 retries)
  - Automatic quota error detection and waiting
  - Processes ALL pending tasks (no limits)
  - Auto-publishes task artifacts to Notion database

- **Comprehensive File Tagging**
  - Expanded TYPE_PATTERNS covering all file organizer categories
  - New KEYWORD_PATTERNS for Fed, FOMC, CPI, NFP, PCE, etc.
  - Enhanced TICKER_PATTERNS (GOLD, SILVER, DXY, VIX, SPY, TLT, GDX, etc.)
  - DOC_TYPE_EMOJIS mapping for visual distinction in Notion

- **Rich Notion Formatting Enhancements**
  - Expanded SECTION_EMOJIS (economic, institutional, research, premarket, etc.)
  - Comprehensive emoji_map and color_map in `_add_header_callout()`
  - Support for: analysis, economic, institutional, notes, announcements, charts

### Changed
- Updated `run.py` daemon to use schedule-based task triggering
- Task executor now loads ALL pending actions from database (no limit)
- Notion publisher respects daily sync schedule to prevent duplication
- Version bump to 3.2.0

### Fixed
- Massive duplication issue when daemon loop force-published on every cycle
- Task executor losing queued actions between daemon restarts
- Incomplete file type coverage causing missed Notion uploads

---

## [3.1.0] - 2025-12-03

### Added
- **Rich Notion Formatting**
  - New `scripts/notion_formatter.py` with enhanced block generation
  - Header callouts with document type and bias indicators
  - Table of contents for longer documents
  - Section headers with contextual icons
  - Color-coded bullet points (green=bullish, red=bearish, yellow=neutral)
  - Proper table rendering with column headers
  - Visual dividers and professional styling

- **Smart Chart Integration**
  - New `scripts/chart_publisher.py` for image hosting
  - Auto-detects ticker mentions in reports (GOLD, SILVER, SPX, VIX, DXY, YIELD)
  - Uploads charts to imgbb (free 32MB/month)
  - Embeds relevant charts in "Related Charts" section
  - File hash caching to avoid re-uploading unchanged charts

- **Usage & Cleanup Management**
  - New `scripts/cleanup_manager.py` for retention policies
  - Tracks imgbb and Notion API usage
  - Monthly counter reset
  - Configurable retention: 30 days (charts), 90 days (Notion), 180 days (local)
  - Dry-run mode for safe preview
  - Warns when approaching free-tier limits

- **Notion Integration**
  - Automatic publishing of all reports to Notion database
  - New `scripts/notion_publisher.py` with full markdown-to-blocks conversion
  - Supports tables, code blocks, headers, lists, and callouts
  - Configurable via `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `IMGBB_API_KEY`

- **Frontmatter System**
  - YAML metadata headers for all generated reports
  - New `scripts/frontmatter.py` with intelligent type detection
  - Auto-extracts tags from content (tickers, keywords)
  - Journal-specific metadata: bias extraction, gold price
  - Report categorization: journal, premarket, catalyst, institutional, technical, economic

- **Documentation Site Redesign**
  - Complete overhaul of `docs/index.html`
  - Professional SVG icons replacing emojis
  - Glass morphism UI with gold accent theming
  - Animated background with floating orbs and parallax effects
  - Notion workspace quick-link in navigation and hero

### Changed
- Updated `README.md` with chart integration and cleanup commands
- Updated `GUIDE.md` with frontmatter and Notion sections
- Updated `ARCHITECTURE.md` with new module documentation
- Simplified `.env` and `.env.template` formatting
- Version bump to 3.1.0

### Fixed
- Notion API property mapping (title vs Name)
- Output path resolution in notion_publisher.py
- Removed residual frontmatter code from economic_calendar.py
- Moved test_init_cortex.py to tests/ folder

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
