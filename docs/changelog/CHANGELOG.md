# ACTIVE DEVELOPMENT


[![Version](https://img.shields.io/badge/version-3.7.0-blue.svg)](https://github.com/amuzetnoM/syndicate/releases)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/) &nbsp;
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) &nbsp;
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://ghcr.io/amuzetnom/syndicate)

All notable changes to Syndicate are documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---


## [3.7.0] - 2025-12-25

### Modern Web UI — Production-ready dashboard with real-time updates

### Added
- **Web UI System** - Complete Flask-based web interface for Syndicate
  - Real-time dashboard with live market metrics (Gold, Silver, GSR, Market Bias)
  - Interactive chart viewer with tab-based asset switching (Gold, Silver, DXY, VIX)
  - AI journal display with markdown formatting
  - System health monitoring (reports, tasks, win rate)
  - Task management with status badges
  - WebSocket integration for live updates without page refresh
  - Responsive mobile-first design with dark theme and gold accents
  
- **Web UI Components** (`web_ui/`)
  - `app.py` - Flask application with RESTful API and WebSocket handlers
  - `templates/index.html` - Beautiful responsive dashboard page
  - `static/css/style.css` - Professional design system (695 LOC)
  - `static/js/dashboard.js` - Real-time client with auto-refresh
  - `start.py` - Quick launcher script
  - `install.sh` - One-click installation script
  
- **Documentation**
  - `web_ui/README.md` - Quick start guide
  - `web_ui/DOCS.md` - Comprehensive technical documentation
  - `web_ui/DESIGN.md` - Design system reference with color palette and components
  - `web_ui/PREVIEW.md` - Visual mockups and examples
  - `web_ui/PROJECT_SUMMARY.md` - Complete project overview

- **API Endpoints**
  - `GET /api/status` - System health and period info
  - `GET /api/metrics` - Real-time market data with calculated GSR
  - `GET /api/journal` - Today's AI-generated analysis
  - `GET /api/tasks` - Pending/ready/scheduled tasks
  - `GET /api/charts` - Available chart metadata
  - `GET /api/memory` - Cortex memory state
  - `GET /api/toggles` - Feature toggle states
  - `POST /api/toggles/<feature>` - Toggle features (notion, tasks, insights)

- **Dependencies** - Added Flask ecosystem to `requirements.txt`
  - Flask 3.0+ for web framework
  - Flask-SocketIO 5.3+ for WebSocket support
  - python-socketio 5.10+ for client/server
  - eventlet 0.35+ for async server

- **Optional Dependency Group** - Added `webui` extra in `pyproject.toml`
  ```bash
  pip install -e ".[webui]"
  ```

### Changed
- Updated `requirements.txt` with web UI dependencies
- Bumped version from 3.6.1 to 3.7.0 in `pyproject.toml`
- Updated Dockerfile version label to 3.7.0
- Improved CI workflows - removed duplicate `ci.yml`, enhanced `python-ci.yml` robustness

### Technical Details
- **Backend**: Flask with WebSocket support, RESTful API design
- **Frontend**: Vanilla JavaScript with Socket.IO client, no framework dependencies
- **Design**: Dark theme (#0a0e1a) with gold accents (#f59e0b), Inter font family
- **Architecture**: Single-page application with real-time updates, mobile-responsive grid layout
- **Security**: Environment-based secrets, CORS configuration, input validation
- **Deployment**: systemd service, Nginx reverse proxy, HTTPS support documented

### Quick Start
```bash
bash web_ui/install.sh      # Install dependencies
python web_ui/start.py      # Start server on port 5000
# Open http://localhost:5000
```

### Notes
- Web UI is production-ready with comprehensive documentation
- All existing functionality remains unchanged - this is a pure addition
- Optional feature - system works identically without web UI
- Total: 1,685 lines of production code, ~78KB across 15 files


## [3.6.1] - 2025-12-24

### Discord digest & Notion safety — Formatting, dedupe, and safe dry-run

### Added
- Overhauled Discord digest formatting with concise embeds and plaintext fallback.
- Admin preview and interactive commands: `!preview_digest`, `!recent_sends`, `!clear_fingerprint`, `!resend_daily`.
- `scripts/discord_preview.py` for local embed/plaintext previews and safe dev sends.
- DB table `discord_messages` for dedupe and rate-limit tracking; record and query recent sends.
- Global Notion publish toggle via `DISABLE_NOTION_PUBLISH` env var and CLI `--no-notion` flag for `scripts/notion_publisher.py`.

### Changed
- Digest writer templates include `publish_to_discord: false` opt-out in frontmatter and `publish_to_notion: false` remains set for digest outputs.
- Notion sync now respects global disable and will run in dry-run mode when toggled off.
- Added fingerprint-based dedupe for Discord sends; admin controls to clear or resend messages.

### Tested
- Ran end-to-end dry-run cycle: executor (dry-run), Notion sync in safe no-notion mode, daily report dry-run, and embed preview output.

### Notes
- Please verify webhooks and operator roles before enabling wet Notion publishes or live Discord sends.




### 🔬 Focus: Ingest Engine 

- **Short:** An ingest engine prototype to collect and normalize streaming/real-time data from multiple providers (FRED, Rapid, MarketFlow, TradingEconomics, yfinance/mplfinance) and persist the latest outputs independently of the main analysis loop.
- **Goal:** Produce canonical, timestamp-normalized time series and lightweight vectorized artifacts suitable for downstream ML/LLM research. This is an exploratory research component; production-grade model training is out-of-scope for Syndicate core.
- **Status:** Initial blueprint and plans drafted; development pending prioritization.
---

# Changelog and Release History

.


---

## [3.6.0] - 2025-12-20

### Subscription & Alerting — Blueprint & Observability

### Added
- Subscription and alerting system for Discord: users can subscribe to `sanitizer`, `queue`, and `digests` topics and receive direct alerts for on-call triage.
- Automated per-topic alerting background worker that notifies subscribers when thresholds are exceeded.
- Operators role and permission hardening: added lightweight `operators` role and tightened channel permission overwrites for digests and bot logs.
- Systemd timer and service for automated daily LLM reports (`syndicate-daily-llm-report.timer` / `.service`).
- Grafana dashboard JSON for LLM observability and helper scripts to programmatically deploy the dashboard if Grafana credentials are configured.

### Changed
- Improved release notes style and structure for recent releases (3.5.x) to improve readability and consistency.

### Security & Operations
- Sensitive tokens are not committed to the repository; ensure tokens remain stored in Vault or host `.env` with restricted access.



## [3.5.3] - 2025-12-20

### Sanitizer & Observability — Sanity enforcement and audit

Patch Summary: Sanity enforcement, observability, and worker hardening.

Key fixes and improvements:
- Prevented fabricated numeric values in LLM-generated reports by adding a canonical-values block to prompts and a sanitizer that enforces reported numeric values against those canonical values.
- Added a **sanitizer audit trail** (`llm_sanitizer_audit` table) to persist correction records for review and post-incident analysis.
- Exposed Prometheus metrics for LLM operations: `gost_llm_queue_length`, `gost_llm_worker_running`, `gost_llm_tasks_processing`, and `gost_llm_sanitizer_corrections_total`.
- Added Prometheus alert rules (`deploy/prometheus/syndicate_llm_rules.yml`) for queue growth, worker health, and sanitizer corrections.
- Implemented automatic task flagging when sanitizer corrections exceed the configured threshold (`LLM_SANITIZER_FLAG_THRESHOLD`).
- Added integration and unit tests to cover the worker flow and sanitizer audit behavior to prevent regressions.
- Documentation: added `docs/observability/llm_metrics.md` describing metrics and recommended alert routing.
- Misc: improved DB initialization to avoid migration-time issues detected during development.

## v[3.5.1] Patch [2025-12-18]

Patch Summary: Production hardening, deterministic per-run chart generation, Notion daemon env-loading, and documentation updates.

Key fixes and improvements:
- **Chart generation semantics:** Charts are now generated once per analysis run and subsequent chart calls in the same run will be skipped only if they were already produced during that run. This prevents stale on-disk charts from previous runs being treated as fresh while avoiding duplicate generation within a single loop.
- **`--force` behavior neutralized for charts:** The legacy force flag no longer overrides on-disk mtimes for chart caching. The flag is retained for CLI compatibility but is inert with respect to chart caching. Recommend avoiding relying on `--force` to bypass cache in production.
- **Executor daemon environment loading:** The detached executor now loads the repository `.env` on startup (best-effort) so `NOTION_API_KEY`, `GEMINI_API_KEY`, and other keys are available to the worker process.
- **Notion publishing reliability:** Removed test Notion DB variable and fixed lifecycle registration so Notion keys are loaded from `.env` by the daemon.
- **Indicator & plotting hardening:** Continued improvements to indicator normalization (`safe_indicator_series`) and headless plotting defaults to ensure reliable offline runs.
- **Docs & changelog:** Updated documentation and changelog to reflect the behavioral changes and recommended operator actions

## [v3.5.0] Release [(2025-12-14)]


Summary: Feature Toggles, Pipeline Audit, and Draft Deduplication — focused on operational control and Notion sync reliability.

Key highlights:
- **Feature Toggles:** Runtime controls for Notion publishing, task execution, and insights; persisted in `system_config` with CLI helpers such as `--toggle` and `--show-toggles`.
- **Pipeline Audit Tool:** `scripts/pipeline_audit.py` provides comprehensive diagnostics and safe cleanup (`--cleanup`/`--execute`) for orphaned database records and pipeline health.
- **Draft Deduplication:** UPSERT-backed `register_document()` prevents duplicate drafts, enforces publish-only sync, and tracks version changes on content updates.
- **Reliability fixes:** Important fixes include path normalization for Notion syncs, improved frontmatter error handling, and AI action type validation.

See the "Added", "Fixed", and "Changed" sections below for full details.

#### Added
- **Feature Toggles System**
  - Runtime toggles for Notion publishing, task execution, and insights extraction
  - `--toggle notion --disable/--enable` CLI commands
  - `--show-toggles` to display current toggle states
  - Stored in `system_config` table for persistence across restarts
  - Methods: `is_notion_publishing_enabled()`, `set_notion_publishing_enabled()`, etc.

- **Pipeline Audit Tool** (`scripts/pipeline_audit.py`)
  - Comprehensive diagnostic for entire pipeline health
  - Audits: database integrity, frontmatter, insights, task execution, Notion sync, schedules
  - `--cleanup` flag to remove orphan records (files deleted but DB entries remain)
  - `--execute` flag to actually perform cleanup (dry-run by default)

- **Draft Deduplication**
  - Enhanced `register_document()` with UPSERT logic
  - Prevents duplicate draft entries for same file path
  - Status downgrade protection (published → draft blocked)
  - Version increment tracking on content changes

#### Fixed
- **Publishing Duplicates** (ROOT CAUSE)
  - Path normalization bug caused same file to be stored as both relative and absolute paths
  - All sync functions now use `Path.resolve()` for consistent absolute paths
  - Affects: `is_file_synced()`, `record_notion_sync()`, `get_notion_page_for_file()`, `clear_sync_for_file()`

- **Silent Error Bypass in Daemon**
  - Bare `except: pass` was syncing unready documents to Notion
  - Now properly skips and logs files with frontmatter parse errors

- **Invalid Action Types from AI**
  - AI prompt was generating compound types like "research|monitoring"
  - Fixed prompt to explicitly list valid action types
  - Added `VALID_ACTION_TYPES` validation and normalization in `insights_engine.py`

#### Changed
- **Pre-Market Type Naming**
  - Updated from `premarket` to `Pre-Market` for consistency with Notion
  - Affects: `frontmatter.py`, `notion_publisher.py` type patterns and mappings

- **Notion Sync Path Handling**
  - `sync_file()` now uses `Path.resolve()` for deduplication consistency

#### Maintenance
- Cleaned 61 orphan database records (45 notion_sync + 16 document_lifecycle)
- Applied frontmatter to files missing YAML headers

## [3.4.0] - 2025-12-13

### Standalone Executor & Docker — Task Executor daemon and services

### Added
- **Standalone Task Executor Daemon** (`scripts/executor_daemon.py`)
  - Independent worker process for task execution
  - Survives main daemon restarts and graceful shutdowns
  - Orphan recovery on startup (reclaims stuck in-progress tasks)
  - Signal handling (SIGTERM, SIGINT, SIGHUP) for graceful shutdown
  - Heartbeat tracking and health monitoring
  - Quota-aware execution with exponential backoff
  - Multiple execution modes: `--daemon`, `--once`, `--recover-orphans`, `--health`, `--spawn`
  - **Dry-run mode** (`--dry-run`) for testing without actual execution
  - **Task limits** (`--max-tasks N`) for controlled batch execution

- **Docker Compose Executor Service**
  - New `executor` service in docker-compose.yml
  - Runs independently alongside main `gost` service
  - Shares data volume for SQLite database access
  - Health check via `--health` command
  - Resource limits: 1 CPU, 1GB memory

- **Hybrid Execution Model**
  - Multiprocess spawn capability for detached execution
  - Threading fallback for environments without process isolation
  - Environment variable `GOST_DETACHED_EXECUTOR=1` to enable detached mode
  - `spawn_executor_daemon()` function in run.py for programmatic spawning

- **Systemd Service Template** (`scripts/systemd/syndicate-executor.service`)
  - Production-ready systemd unit file
  - Automatic restart on failure with configurable backoff
  - Resource limits (CPU quota, memory max)
  - Security hardening (NoNewPrivileges, ProtectSystem, PrivateTmp)
  - Journal integration for logging

### Changed
- **Docker Architecture** (BREAKING)
  - Main `gost` service now sets `GOST_DETACHED_EXECUTOR=1` by default
  - Task execution delegated to separate `executor` container
  - Both containers share `gost_data` and `gost_output` volumes
  - Main daemon depends on executor service startup

- **Task Execution Architecture**
  - Main daemon can now delegate task execution to detached executor
  - Inline execution remains as fallback when executor unavailable
  - Graceful degradation: if spawn fails, continues with blocking execution

### Deprecated
- **Inline Task Executor** (`scripts/task_executor.py`)
  - Marked as deprecated for production use (docstring notice)
  - Maintained for backward compatibility and development/testing
  - Users should migrate to `scripts/executor_daemon.py`

---

## [3.3.1] - 2025-12-13

### Fixed
- **Docker Container Robustness**
  - Removed hardcoded GHCR image reference to ensure local builds are always used
  - Fixed `NOTION_TOKEN` → `NOTION_API_KEY` environment variable naming (was causing API failures)
  - Added missing `IMGBB_API_KEY` environment variable to container
  - Added `MPLCONFIGDIR=/tmp/matplotlib` to prevent matplotlib permission errors in container
  - Removed read-only `cortex_memory.json` mount that caused lock file conflicts

- **Cortex Memory Persistence**
  - Relocated `MEMORY_FILE` and `LOCK_FILE` to `/app/data/` directory
  - Files now persist correctly in Docker volume instead of container filesystem
  - Added `DATA_DIR` property to Config for consistent data path handling
  - Automatic directory creation for data paths

- **Single Run Mode (`--once` flag)**
  - Fixed `--once` argument being parsed but never executed
  - Now correctly runs single analysis cycle with all post-analysis tasks
  - Proper exit after completion (no more falling into daemon mode)

- **File Organizer Stability**
  - Added `FILE_INDEX` skip logic to prevent recursive filename explosion
  - Prevents "[Errno 36] File name too long" errors from repeated date appending
  - Case-insensitive check covers all FILE_INDEX variations

### Changed
- Updated dev container environment to match production configuration
- Docker Compose now consistent across all service definitions

---

## [3.3.0] - 2025-12-06

### Added
- **Multi-Provider LLM System**
  - Three-tier fallback chain: Gemini → Ollama → llama.cpp
  - Automatic provider switching on quota errors, rate limits, or failures
  - `LLM_PROVIDER` env var to force specific provider (`gemini`, `ollama`, `local`)
  - `PREFER_LOCAL_LLM=1` for local-first mode (no cloud calls)

- **Ollama Integration**
  - Full Ollama server support via REST API
  - `OllamaLLM` class in `scripts/local_llm.py`
  - `OllamaProvider` class in `main.py`
  - `OLLAMA_HOST` and `OLLAMA_MODEL` environment variables
  - Auto-detection of running Ollama server
  - Compatible with all Ollama models (llama3.2, mistral, phi3, etc.)

- **Enhanced Local LLM (llama.cpp)**
  - Full GPU acceleration via `LOCAL_LLM_GPU_LAYERS` (-1=all, 0=CPU)
  - Environment variable configuration for all settings
  - Auto-discovery of GGUF models in models/ directory
  - Auto-download of recommended models (`LOCAL_LLM_AUTO_DOWNLOAD=1`)
  - Configurable context window (`LOCAL_LLM_CONTEXT=4096`)
  - Model download CLI: `python scripts/local_llm.py --download mistral-7b`

- **Comprehensive LLM Documentation**
  - New `docs/LLM_PROVIDERS.md` - complete provider guide
  - Quick start for each provider (Gemini, Ollama, llama.cpp)
  - GPU configuration and VRAM requirements
  - Offline/air-gapped usage instructions
  - Troubleshooting guide

- **Document Lifecycle Management System**
  - New `document_lifecycle` SQLite table for tracking document states
  - Lifecycle states: `draft` → `in_progress` → `review` → `published` → `archived`
  - Only `published` documents are synced to Notion (drafts remain private)
  - `status` field added to YAML frontmatter (default: `draft`)

- **Lifecycle CLI Commands**
  - `--lifecycle list` - List all documents by status
  - `--lifecycle list --show-status <status>` - Filter by specific status
  - `--lifecycle status --file <path>` - Show status of specific file
  - `--lifecycle promote --file <path>` - Promote to next status
  - `--lifecycle publish --file <path>` - Mark as published (Notion-ready)
  - `--lifecycle draft --file <path>` - Reset to draft status

- **Frontmatter Lifecycle Functions**
  - `get_document_status()` - Read status from frontmatter
  - `set_document_status()` - Update status in frontmatter
  - `promote_status()` - Advance to next lifecycle stage
  - `is_published()` / `is_draft()` - Status check helpers

- **Database Lifecycle Methods**
  - `get_document_status()` - Query document state
  - `register_document()` - Add new document to lifecycle tracking
  - `update_document_status()` - Change document state
  - `get_documents_by_status()` - List documents by state
  - `get_unpublished_documents()` - Find documents not yet published

### Changed
- Notion publisher now checks document lifecycle status before sync
- Non-published documents are skipped with informative message
- Frontmatter `generate_frontmatter()` includes `status` field by default
- **Notion Sync Exclusions**: ACT files (`_act-`, `act-`), file indexes, monitor/calc/code documents excluded from sync

### Fixed
- Bare `except` clauses replaced with `except Exception` (E722)
- Added E402 to ruff ignore list (module import order in notion_publisher)
- Fixed frontmatter date parsing (dates no longer parsed as integers)
- Pre-market documents now properly tagged with AI markers for Notion sync

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
  - Syndicate Overview with system health panels
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

[3.1.0]: https://github.com/amuzetnoM/syndicate/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/amuzetnoM/syndicate/compare/v2.1.0...v3.0.0
[2.1.0]: https://github.com/amuzetnoM/syndicate/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/amuzetnoM/syndicate/compare/v1.5.0...v2.0.0
[1.5.0]: https://github.com/amuzetnoM/syndicate/compare/v1.0.0...v1.5.0
[1.0.0]: https://github.com/amuzetnoM/syndicate/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/amuzetnoM/syndicate/releases/tag/v0.1.0
