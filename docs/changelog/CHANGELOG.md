# ACTIVE DEVELOPMENT

[![Version](https://img.shields.io/badge/version-3.5.0-blue.svg)](https://github.com/amuzetnoM/gold_standard/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://ghcr.io/amuzetnom/gold_standard)

All notable changes to Gold Standard are documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

### HIGHLIGHTS

##### Version [3.5.0] Released

> 2025-12-14

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

---


## Engineering Roadmap

[![Target](https://img.shields.io/badge/target-v3.6.0-blue.svg)]()
[![Priority](https://img.shields.io/badge/priority-production_hardening-critical.svg)]()

We are actively researching and implementing the next generation of Gold Standard's infrastructure. The following initiatives represent our current engineering focus, driven by real-world production insights gathered from VM deployments and continuous operation cycles. Each area has been identified through systematic analysis of operational patterns, failure modes, and scalability requirements.

---

## Focus

### Observability Infrastructure Expansion

**Current State:** The existing Prometheus and Grafana stack provides solid infrastructure metrics, but application-level visibility remains fragmented across multiple log files.

**Active Research:**

We are investigating unified observability patterns that consolidate application telemetry with infrastructure metrics. The goal is to establish a single-pane monitoring experience where operators can correlate application behavior with system performance in real-time.

| Initiative | Phase | Objective |
|------------|-------|-----------|
| Log Aggregation Pipeline | `RESEARCH` | Route `run.log` and `cleanup.log` through Loki into Grafana dashboards with structured parsing |
| Alert Rule Engineering | `DESIGN` | Develop Alertmanager configurations for container health, disk utilization, and API connectivity |
| Quota Proximity Detection | `PROTOTYPE` | Instrument LLM providers to emit metrics when approaching rate limits |

**Target Alerts Under Development:**
- Container restart frequency anomaly detection
- Disk space threshold warnings for persistent volumes
- API endpoint health degradation (yfinance, Gemini, Notion, ImgBB)
- LLM token consumption velocity tracking

---

### Intelligent API Orchestration Layer

**Current State:** The multi-provider LLM fallback chain (Gemini, Ollama, llama.cpp) operates on a fixed priority basis. Provider selection is reactive rather than adaptive.

**Active Research:**

We are exploring dynamic provider orchestration that learns from runtime performance characteristics. This involves tracking latency, success rates, and quota consumption across providers to make intelligent routing decisions.

| Initiative | Phase | Objective |
|------------|-------|-----------|
| Adaptive Fallback Engine | `DESIGN` | Implement performance-weighted provider selection with automatic promotion and demotion |
| Quota Ledger System | `RESEARCH` | Build internal tracking for API consumption across all external services |
| Preemptive Rate Limiting | `PROTOTYPE` | Introduce smart delays based on quota burn rate to prevent limit exhaustion |

**Design Principles:**
- Operator notifications when fallback providers are engaged
- Graceful degradation paths for free-tier constraint management
- Provider health scoring with configurable thresholds

---

### Configuration and Deployment Architecture

**Current State:** Configuration is distributed between environment variables and hardcoded defaults. Deployment requires manual intervention for updates.

**Active Research:**

We are evaluating structured configuration management approaches that separate secrets from operational parameters. Additionally, we are designing CI/CD pipelines that enable zero-touch deployments from commit to production.

| Initiative | Phase | Objective |
|------------|-------|-----------|
| Hierarchical Config System | `DESIGN` | Implement YAML/TOML configuration layers for TA thresholds, asset definitions, and model parameters |
| Secrets Vault Integration | `RESEARCH` | Evaluate Docker secrets, HashiCorp Vault, and cloud-native secret managers for credential isolation |
| Automated Deployment Pipeline | `PLANNING` | Build GitHub Actions workflows for image builds, registry pushes, and systemd orchestration |

**Deployment Automation Targets:**
- Triggered rebuilds on code changes
- Automatic container registry synchronization
- Remote systemd service management

---

### Self-Healing and Resilience Patterns

**Current State:** Health checks verify basic container operation but do not validate application-level functionality or external dependencies.

**Active Research:**

We are developing deep health check patterns that probe actual application readiness, including database connectivity, external API reachability, and internal subsystem status. Additionally, we are evaluating error aggregation platforms for systematic issue tracking.

| Initiative | Phase | Objective |
|------------|-------|-----------|
| **Task Executor Daemon** | `✅ IMPLEMENTED` | Standalone worker with orphan recovery, graceful shutdown, and systemd integration |
| Deep Health Probes | `PROTOTYPE` | Extend healthchecks to validate database, yfinance, and LLM provider connectivity |
| Exception Telemetry | `RESEARCH` | Evaluate Sentry and Bugsnag for automatic error capture, categorization, and alerting |
| Circuit Breaker Patterns | `DESIGN` | Implement failure isolation for external service dependencies |

---

### Data Persistence and Integrity

**Current State:** SQLite database and generated reports persist on the data volume, but backup and archival processes are manual.

**Active Research:**

We are designing automated backup strategies that protect critical data without impacting operational performance. Additionally, we are refining the file organization system to handle edge cases and provide configurable behavior.

| Initiative | Phase | Objective |
|------------|-------|-----------|
| Scheduled Backup System | `DESIGN` | Implement daily incremental and weekly full SQLite backups to off-disk storage |
| Archive Lifecycle Rules | `RESEARCH` | Define configurable policies for report retention, compression, and offsite replication |
| File Organizer Hardening | `PROTOTYPE` | Enhance naming conventions, deduplication logic, and stale file detection |

**Data Protection Strategy:**
- Incremental backups during low-activity windows
- Weekly full snapshots with integrity verification
- Geographic replication for disaster recovery scenarios

---

> **Engineering Philosophy:** These initiatives represent our commitment to evolving Gold Standard into a production-grade autonomous system. Each enhancement is validated against real operational requirements and designed for minimal manual intervention. Contributions and feedback on these research areas are welcome.

---
## Chagelog and Release History

---

## [3.4.0] - 2025-12-13

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

- **Systemd Service Template** (`scripts/systemd/gold-standard-executor.service`)
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
