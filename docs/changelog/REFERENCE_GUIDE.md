# Syndicate Technical Booklet

> Educational Guide and Technical Reference — v3.4.0 | Stable: v3.3.1

This booklet provides in-depth documentation of the mathematical foundations, design decisions, and extension patterns for the Syndicate quantitative analysis system. Version 3.4.0 introduces the standalone Task Executor Daemon with Docker containerization, building on v3.3.1's container robustness fixes, v3.3's document lifecycle management, v3.2's intelligent scheduling, Notion deduplication, persistent task execution with retry logic, and comprehensive file tagging.

---

## Table of Contents

1. [Technical Indicators](#technical-indicators)
2. [Intermarket Analysis](#intermarket-analysis)
3. [Memory and Grading System](#memory-and-grading-system)
4. [AI Prompt Engineering](#ai-prompt-engineering)
5. [Data Pipeline and Safety](#data-pipeline-and-safety)
6. [Report Types](#report-types)
7. [Live Analysis Suite](#live-analysis-suite)
8. [Economic Calendar Module](#economic-calendar-module)
9. [Database Manager](#database-manager)
10. [Intelligent Scheduling](#intelligent-scheduling)
11. [Notion Sync & Deduplication](#notion-sync--deduplication)
12. [Document Lifecycle Management](#document-lifecycle-management)
13. [Insights Engine](#insights-engine)
14. [Task Executor](#task-executor)
    - [Executor Daemon (Recommended)](#executor-daemon-recommended)
    - [Inline Executor (Legacy)](#inline-executor-legacy)
15. [File Organizer](#file-organizer)
16. [Frontmatter System](#frontmatter-system)
17. [Notion Integration](#notion-integration)
18. [Comprehensive Tagging](#comprehensive-tagging)
19. [Testing Guidelines](#testing-guidelines)
20. [Deployment Notes](#deployment-notes)
21. [Extension Patterns](#extension-patterns)

---

## Technical Indicators

### RSI (Relative Strength Index)

**Definition:** Momentum oscillator measuring speed and magnitude of price movements.

**Formula:**
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss (over N periods, default 14)
```

**Interpretation:**
- RSI > 70: Overbought condition
- RSI < 30: Oversold condition
- Divergences between RSI and price can signal reversals

**Implementation:**
```python
def rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(length, min_periods=length).mean()
    avg_loss = loss.rolling(length, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

---

### ATR (Average True Range)

**Definition:** Volatility indicator measuring the average range of price movement.

**Formula:**
```
True Range = max(
    High - Low,
    |High - Previous Close|,
    |Low - Previous Close|
)
ATR = Rolling Mean of True Range (default 14 periods)
```

**Use Cases:**
- Position sizing (larger ATR = smaller position)
- Stop loss placement (e.g., 2x ATR from entry)
- Volatility regime detection

**Implementation:**
```python
def atr(high, low, close, length=14):
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=length, min_periods=length).mean()
```

---

### ADX (Average Directional Index)

**Definition:** Trend strength indicator (not direction) derived from Directional Movement Index.

**Components:**
- +DI: Positive Directional Indicator
- -DI: Negative Directional Indicator
- ADX: Smoothed average of DX

**Interpretation:**
- ADX > 25: Strong trend present
- ADX < 20: Weak or no trend (ranging market)
- Rising ADX: Trend strengthening
- Falling ADX: Trend weakening

**Implementation Notes:**
- The system uses pandas_ta when available
- Fallback implementation uses Wilder smoothing approximation
- Fallback values may differ slightly from library implementations

---

### SMA (Simple Moving Average)

**Definition:** Arithmetic mean of prices over N periods.

**Common Periods:**
- SMA 50: Intermediate-term trend
- SMA 200: Long-term trend
- Golden Cross: SMA 50 crosses above SMA 200 (bullish)
- Death Cross: SMA 50 crosses below SMA 200 (bearish)

---

## Intermarket Analysis

### Gold/Silver Ratio (GSR)

**Definition:** Price of gold divided by price of silver.

**Interpretation:**
```
GSR > 85: Silver relatively cheap (consider silver)
GSR < 75: Gold relatively cheap (consider gold)
```

**Rationale:** Both metals move together but the ratio oscillates around historical norms. Extreme readings can indicate relative value opportunities.

### Correlation Framework

The system tracks six assets for intermarket analysis:

| Asset | Ticker | Typical Correlation to Gold |
|-------|--------|---------------------------|
| Gold | GC=F | - |
| Silver | SI=F | Strong positive |
| Dollar Index | DX-Y.NYB | Inverse |
| US 10Y Yield | ^TNX | Inverse |
| VIX | ^VIX | Positive (flight to safety) |
| S&P 500 | ^GSPC | Weak/Variable |

---

## Memory and Grading System

### Cortex Architecture

The Cortex module maintains persistent memory across runs:

```json
{
  "last_bias": "BULLISH",
  "last_price": 1960.50,
  "wins": 7,
  "losses": 3,
  "current_streak": 2,
  "streak_type": "win",
  "history": [
    {
      "date": "2025-11-30",
      "bias": "BULLISH",
      "price": 1940.00,
      "result": "WIN"
    }
  ],
  "last_run": "2025-11-30T12:00:00"
}
```

### Grading Logic

```python
def grade_performance(current_price, last_price, last_bias):
    delta = current_price - last_price

    if last_bias == "BULLISH" and delta > 0:
        return "WIN"
    elif last_bias == "BEARISH" and delta < 0:
        return "WIN"
    elif last_bias == "NEUTRAL":
        return "NEUTRAL"
    else:
        return "LOSS"
```

### File Safety

- Memory file protected by `filelock.FileLock`
- Prevents corruption from concurrent access
- Lock file: `cortex_memory.lock`

---

## AI Prompt Engineering

### Prompt Structure

The Strategist builds prompts with these components:

1. **System Context** - Role and output format instructions
2. **Memory History** - Past predictions and performance
3. **Quant Telemetry** - Current prices, indicators, regime
4. **Intermarket Data** - Ratios, correlations, divergences
5. **News Headlines** - Recent market news (when available)

### Output Format

The system expects structured output with explicit bias declaration:

```markdown
## Strategic Thesis

**Bias:** BULLISH

**Rationale:** ADX indicates strong trend, RSI not overbought,
yields declining supports gold prices...
```

### Bias Extraction

1. Regex search for explicit declarations (`Bias: BULLISH`)
2. Fallback: Count keyword occurrences
3. Default to NEUTRAL if ambiguous

### Best Practices

- Request specific output format (Markdown or JSON)
- Include example outputs in prompt
- Constrain to canonical tokens: BULLISH, BEARISH, NEUTRAL
- Validate AI response before processing

---

## Data Pipeline and Safety

### Fetch Strategy

Each asset has primary and backup tickers:

```python
ASSETS = {
    'GOLD':   {'p': 'GC=F', 'b': 'GLD'},
    'SILVER': {'p': 'SI=F', 'b': 'SLV'},
    # ...
}
```

If primary fails, backup is attempted automatically.

### Indicator Fallbacks

The system provides safe wrappers for indicator computation:

1. Attempt pandas_ta calculation
2. If error or mismatched length, use fallback
3. Fallback uses pure pandas operations
4. Log warnings but continue processing

### Data Validation

- Verify OHLC columns exist
- Only drop rows with missing OHLC (not indicator NaNs)
- Validate chart files are non-empty after generation

---

## Report Types

### Daily Journal

Generated by `main.py`, includes:
- Self-correction analysis (grading previous prediction)
- Technical indicator summary
- Intermarket analysis
- AI-generated thesis
- Embedded charts

Output: `output/Journal_YYYY-MM-DD.md`

### Weekly Rundown

Generated by `scripts/split_reports.py --mode weekly`:
- Short-horizon tactical overview
- Current asset status
- AI tactical thesis (optional)
- Weekly timeframe charts

Output: `output/reports/weekly_rundown_YYYY-MM-DD.md`

### Monthly Report

Generated by `scripts/split_reports.py --mode monthly`:
- Monthly aggregated performance tables
- Return calculations per asset
- AI outlook (optional)
- One-year charts

Output: `output/reports/monthly_yearly_report_YYYY-MM-DD.md`

### Yearly Report

Same as monthly but with yearly aggregation focus.

---

## Live Analysis Suite

The `scripts/live_analysis.py` module provides real-time analysis reports with HTML-formatted tables.

### LiveAnalyzer Class

```python
from scripts.live_analysis import LiveAnalyzer

analyzer = LiveAnalyzer()
results = analyzer.run_full_analysis()
```

### Report Types

| Report | Method | Description |
|--------|--------|-------------|
| Catalyst Watchlist | `generate_catalyst_watchlist()` | Active market catalysts with gold impact |
| Institutional Matrix | `generate_institutional_matrix()` | Central bank activity, ETF flows |
| 1Y Analysis | `generate_1y_analysis()` | One-year trend and pattern analysis |
| 3M Analysis | `generate_3m_analysis()` | Three-month tactical view |

### HTML Table Format

All tables use consistent HTML formatting:

```html
<table>
<thead>
<tr>
<th>Column 1</th>
<th>Column 2</th>
</tr>
</thead>
<tbody>
<tr>
<td>Value 1</td>
<td>Value 2</td>
</tr>
</tbody>
</table>
```

---

## Economic Calendar Module

The `scripts/economic_calendar.py` module provides a self-maintaining economic calendar system.

### Key Classes

```python
from enum import Enum

class EventImpact(Enum):
    HIGH = "HIGH"   # 🔴 FOMC, NFP, CPI, GDP
    MED = "MED"     # 🟡 ADP, JOLTS, PPI
    LOW = "LOW"     # 🟢 Beige Book, Fed Speeches
```

### EconomicCalendar Class

```python
from scripts.economic_calendar import EconomicCalendar

calendar = EconomicCalendar()
report = calendar.generate_full_calendar_report()
```

### Event Structure

Each event includes:

| Field | Description |
|-------|-------------|
| `date` | Event datetime |
| `name` | Event name (e.g., "Nonfarm Payrolls") |
| `impact` | EventImpact enum (HIGH/MED/LOW) |
| `forecast` | Expected value |
| `previous` | Prior reading |
| `gold_impact` | Directional gold analysis |
| `country` | Country flag emoji |

### Pre-loaded Events

The calendar comes with December 2025 and January 2026 events pre-loaded:

**HIGH Impact Events:**
- FOMC Rate Decision (Dec 18, Jan 29)
- Nonfarm Payrolls (Dec 6, Jan 10)
- CPI YoY/Core CPI (Dec 11, Jan 15)
- GDP (Dec 19, Jan 30)
- ISM Manufacturing/Services PMI

**Central Bank Meetings:**
- Fed (FOMC): Dec 18, Jan 29
- ECB: Dec 12, Jan 30
- BOJ: Dec 19, Jan 24
- BOE: Dec 19, Feb 6

---

## Database Manager

The `db_manager.py` module provides SQLite persistence for all reports, scheduling, and sync tracking.

### DBManager Class

```python
from db_manager import DBManager

db = DBManager()

# Save a report
db.save_journal(date="2025-12-01", content="...", bias="BULLISH")

# Query historical reports
reports = db.get_journals(limit=30)
```

### Schema

```sql
CREATE TABLE journals (
    id INTEGER PRIMARY KEY,
    date TEXT UNIQUE,
    content TEXT,
    bias TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New in v3.2: Schedule tracking
CREATE TABLE schedule_tracker (
    task_name TEXT PRIMARY KEY,
    last_run TIMESTAMP,
    frequency TEXT
);

-- New in v3.2: Notion sync tracking
CREATE TABLE notion_sync (
    file_path TEXT PRIMARY KEY,
    file_hash TEXT,
    notion_page_id TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Benefits

- Persistent storage across runs
- Historical analysis queries
- Performance tracking over time
- Data export capabilities
- Entity and action insights storage
- Task execution history
- **Schedule tracking** for frequency-based task execution
- **Notion sync tracking** for deduplication

---

## Intelligent Scheduling

Version 3.2 introduces a revolutionary intelligent task scheduling system that transforms Syndicate from a periodic runner into a sophisticated autonomous execution engine.

### Core Principles

1. **Immediate by Default**: Tasks without explicit scheduling execute immediately
2. **Natural Language Dates**: Automatic extraction of dates from task descriptions
3. **Self-Healing**: Automatic recovery from crashes, restarts, and API quota exhaustion
4. **Atomic Operations**: Race-condition-free task claiming and execution

### Task Scheduling Architecture

#### Date Extraction Engine

The system automatically parses temporal references from task descriptions:

```
Input: "Track FOMC meeting for Dec 18"
Output: scheduled_for = "2025-12-18T09:00:00"

Input: "Monitor employment data for Jan 10"
Output: scheduled_for = "2026-01-10T09:00:00"

Input: "Research gold correlation patterns"
Output: scheduled_for = NULL (execute immediately)
```

**Supported Date Formats:**
| Format | Example | Result |
|--------|---------|--------|
| Short month + day | "Dec 18" | 2025-12-18T09:00:00 |
| Full month + day | "December 18" | 2025-12-18T09:00:00 |
| With year | "Dec 18, 2025" | 2025-12-18T09:00:00 |
| Ordinal | "January 10th" | 2026-01-10T09:00:00 |
| ISO format | "2025-12-25" | 2025-12-25T09:00:00 |
| No date | Any text | NULL (immediate) |

**Year Rollover Logic:**
- If a parsed date is in the past for the current year, the system schedules for next year
- Example: "Jan 10" parsed in December 2025 → January 10, 2026

#### Execution State Machine

Tasks follow a deterministic state machine:

```
┌─────────┐    ┌────────────┐    ┌───────────┐    ┌───────────┐
│ CREATED │───▶│  PENDING   │───▶│IN_PROGRESS│───▶│ COMPLETED │
└─────────┘    └────────────┘    └───────────┘    └───────────┘
                    ▲                   │
                    │                   │ failure
                    │                   ▼
                    │              ┌─────────┐
                    └──────────────│  RETRY  │
                                   └─────────┘
                                        │ max retries
                                        ▼
                                   ┌─────────┐
                                   │ FAILED  │
                                   └─────────┘
```

#### Atomic Task Claiming

To prevent duplicate execution across multiple daemon processes:

```python
from db_manager import get_db

db = get_db()

# Atomically claim a task for execution
if db.claim_action(action_id, worker_id='worker_1'):
    try:
        # Execute the task
        result = execute_task(action)
        db.update_action_status(action_id, 'completed', result)
    except Exception as e:
        # Release back to pending for retry
        db.release_action(action_id, reason=str(e))
else:
    print("Task already claimed by another process")
```

### Ready vs Scheduled Tasks

The system distinguishes between:

| Category | Criteria | Behavior |
|----------|----------|----------|
| **Ready** | `scheduled_for IS NULL` OR `scheduled_for <= NOW` | Execute immediately |
| **Scheduled** | `scheduled_for > NOW` | Wait until scheduled time |

**Query for Ready Tasks:**
```sql
SELECT * FROM action_insights
WHERE status = 'pending'
  AND (scheduled_for IS NULL OR scheduled_for <= datetime('now'))
ORDER BY
    CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
    scheduled_for ASC NULLS FIRST,
    created_at ASC;
```

### Retry & Recovery System

#### Exponential Backoff

When API quota errors occur, the system waits with exponential backoff:

```python
INITIAL_BACKOFF = 30    # seconds
MAX_BACKOFF = 600       # 10 minutes
MAX_RETRIES = 10

# Backoff sequence: 30s → 60s → 120s → 240s → 480s → 600s → 600s...
backoff = min(INITIAL_BACKOFF * (2 ** retry_count), MAX_BACKOFF)
```

#### Quota Error Detection

```python
QUOTA_PATTERNS = [
    'quota', 'rate limit', 'too many requests',
    '429', 'resource exhausted', 'capacity', 'overloaded'
]
```

#### Crash Recovery

On daemon startup, stuck tasks are automatically recovered:

```python
# Reset tasks stuck in 'in_progress' from previous crash
reset_count = db.reset_stuck_actions(max_age_hours=24)
if reset_count > 0:
    print(f"Recovered {reset_count} stuck tasks from previous session")
```

### System Health Monitoring

```python
health = db.get_system_health()

# Example output:
{
    'timestamp': '2025-12-04T10:30:00',
    'tasks': {
        'ready_now': 56,           # Execute immediately
        'scheduled_future': 9,      # Waiting for schedule time
        'stuck_in_progress': 0      # Need recovery
    },
    'execution': {
        'last_24h_total': 150,
        'last_24h_success': 142,
        'last_24h_avg_time_ms': 2340.5
    }
}
```

### Frequency-Based Scheduling

In addition to task-level scheduling, the system supports operation-level frequency control:

| Task | Frequency | Description |
|------|-----------|-------------|
| Journal | Daily | Once per day |
| Notion Sync | Daily | Publish new/changed files |
| Insights Extraction | Daily | Extract from new reports |
| Economic Calendar | Weekly | Update calendar events |
| Institution Watchlist | Weekly | Refresh institutional analysis |
| Monthly Reports | Monthly | Generate monthly summaries |
| Yearly Reports | Yearly | Generate annual reviews |

### Schedule Tracker Methods

```python
from db_manager import DBManager

db = DBManager()

# Check if task should run
if db.should_run_task('notion_sync', frequency='daily'):
    # Execute the task
    sync_all_outputs()
    # Mark as completed
    db.mark_task_run('notion_sync')
```

### Frequency Options

- `daily`: Run once per calendar day
- `weekly`: Run once per week (7 days)
- `monthly`: Run once per month
- `yearly`: Run once per year

### Integration with Daemon

The daemon (`run.py`) uses scheduling to control post-analysis tasks:

```python
def _run_post_analysis_tasks():
    # Only run task execution weekly
    if db.should_run_task('task_execution', frequency='weekly'):
        executor.process_queue()
        db.mark_task_run('task_execution')

    # Only sync to Notion daily
    if db.should_run_task('notion_sync', frequency='daily'):
        sync_all_outputs()
        db.mark_task_run('notion_sync')
```

---

## Notion Sync & Deduplication

Version 3.2 prevents duplicate Notion pages through content-based deduplication.

### Overview

The system tracks which files have been synced to Notion and their content hashes. Files are only re-uploaded when content changes.

### Sync Tracking Methods

```python
from db_manager import DBManager

db = DBManager()

# Check if file needs sync
file_path = "output/reports/Journal_2025-12-04.md"
current_hash = db.get_file_hash(file_path)

if not db.is_file_synced(file_path, current_hash):
    # File is new or changed - publish to Notion
    result = publisher.sync_file(file_path)

    # Record the sync
    db.record_notion_sync(file_path, current_hash, result['page_id'])
```

### Content Hashing

Files are hashed using SHA-256 for deterministic comparison:

```python
def get_file_hash(self, file_path: str) -> str:
    """Generate SHA-256 hash of file contents."""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()
```

### Benefits

- **No duplicates**: Same content never uploaded twice
- **Change detection**: Only modified files are synced
- **Audit trail**: Track which Notion page corresponds to each file
- **Efficiency**: Reduces API calls and bandwidth

---

## Document Lifecycle Management

Version 3.3 introduces a document lifecycle system to control which documents are synced to Notion and prevent accidental overwrites of published content.

### Overview

The lifecycle system ensures that:
- Draft documents remain private (not synced to Notion)
- Only explicitly published documents are visible externally
- Document state is tracked in both frontmatter and database
- Status progression follows a defined workflow

### Lifecycle States

Documents progress through these states:

```
┌─────────┐    ┌─────────────┐    ┌────────┐    ┌───────────┐    ┌──────────┐
│  draft  │───▶│ in_progress │───▶│ review │───▶│ published │───▶│ archived │
└─────────┘    └─────────────┘    └────────┘    └───────────┘    └──────────┘
     │                                                │
     └────────────────────────────────────────────────┘
                    (can reset to draft)
```

| Status | Description | Notion Sync |
|--------|-------------|-------------|
| `draft` | Initial state, work in progress | **No** |
| `in_progress` | Active editing/analysis | **No** |
| `review` | Ready for final review | **No** |
| `published` | Approved for external visibility | **Yes** |
| `archived` | Historical reference | **No** |

### Frontmatter Integration

Status is stored in YAML frontmatter:

```yaml
---
type: journal
title: "Gold Analysis - December 5, 2025"
date: 2025-12-05
status: draft
generated: 2025-12-05T10:30:00
tags: [gold, xauusd, technical-analysis]
---
```

### Frontmatter Functions

```python
from scripts.frontmatter import (
    get_document_status,
    set_document_status,
    promote_status,
    is_published,
    is_draft,
    VALID_STATUSES
)

# Read status from document
content = open("Journal_2025-12-05.md").read()
status = get_document_status(content)  # Returns 'draft'

# Check status
if is_draft(content):
    print("Document is still in draft")

if is_published(content):
    print("Document is ready for Notion")

# Update status
new_content = set_document_status(content, "published", "Journal_2025-12-05.md")

# Promote to next status (draft -> in_progress -> review -> published)
new_content = promote_status(content, "Journal_2025-12-05.md")
```

### Database Schema

```sql
CREATE TABLE document_lifecycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    doc_type TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT,
    updated_at TEXT,
    published_at TEXT,
    notion_page_id TEXT,
    content_hash TEXT,
    version INTEGER DEFAULT 1,
    metadata TEXT
);

CREATE INDEX idx_doc_lifecycle_path ON document_lifecycle(file_path);
CREATE INDEX idx_doc_lifecycle_status ON document_lifecycle(status);
```

### Database Methods

```python
from db_manager import get_db

db = get_db()

# Get document status
doc = db.get_document_status("output/Journal_2025-12-05.md")
# Returns: {'file_path': '...', 'status': 'draft', 'version': 1, ...}

# Register new document
db.register_document("output/new_report.md", doc_type="journal", status="draft")

# Update status
db.update_document_status("output/Journal_2025-12-05.md", "published")

# Get all documents by status
drafts = db.get_documents_by_status("draft")
published = db.get_documents_by_status("published")

# Get unpublished documents
pending = db.get_unpublished_documents()
```

### CLI Commands

```bash
# List all documents by status
python run.py --lifecycle list

# List only draft documents
python run.py --lifecycle list --show-status draft

# Check status of specific file
python run.py --lifecycle status --file output/Journal_2025-12-05.md

# Promote to next status
python run.py --lifecycle promote --file output/Journal_2025-12-05.md

# Directly publish
python run.py --lifecycle publish --file output/Journal_2025-12-05.md

# Reset to draft
python run.py --lifecycle draft --file output/Journal_2025-12-05.md
```

### Integration with Notion Publisher

The `sync_file()` method checks lifecycle status before syncing:

```python
def sync_file(self, filepath: str, force: bool = False) -> Dict[str, str]:
    content = Path(filepath).read_text(encoding='utf-8')

    # Check lifecycle status (unless forced)
    if not force:
        status = get_document_status(content)
        if not is_published(content):
            return {
                "skipped": True,
                "reason": f"Document status is '{status}' (not published)"
            }

    # Continue with sync...
```

### Workflow Example

```python
# 1. New document is created with status: draft
generate_journal()  # Creates Journal_2025-12-05.md with status: draft

# 2. Review and edit the document
# ...

# 3. Promote when ready
run.py --lifecycle promote --file output/Journal_2025-12-05.md
# Status: draft -> in_progress

# 4. Continue promoting
run.py --lifecycle promote --file output/Journal_2025-12-05.md
# Status: in_progress -> review

run.py --lifecycle promote --file output/Journal_2025-12-05.md
# Status: review -> published

# 5. Now Notion sync will include this document
run.py --sync-all  # Journal_2025-12-05.md is now synced
```

### Best Practices

1. **Review before publishing** - Use the `review` status as a checkpoint
2. **Batch publishing** - Review all drafts, then publish in batches
3. **Archive old content** - Move outdated published docs to `archived`
4. **Force sync for testing** - `--force` remains available for CLI compatibility but should be used sparingly. Chart generation semantics were changed: charts are regenerated once per analysis run and the `--force` flag no longer overrides on-disk mtimes to force regeneration across runs. Use `--once` to run a fresh cycle and produce a complete set of charts for that run.

---

## Insights Engine

The `scripts/insights_engine.py` module extracts actionable intelligence from generated reports.

### Overview

The Insights Engine scans reports for:
- **Entity Insights**: Named entities (Fed, ECB, CME, indicators, assets)
- **Action Insights**: Research tasks, data to fetch, news to scan, calculations

### InsightsExtractor Class

```python
from scripts.insights_engine import InsightsExtractor

extractor = InsightsExtractor(config, logger, model)

# Extract from a report
entities = extractor.extract_entities(report_content, "Journal_2025-12-01.md")
actions = extractor.extract_actions(report_content, "Journal_2025-12-01.md")
```

### Entity Types

| Type | Examples |
|------|----------|
| Institution | Fed, ECB, BOJ, CME, Goldman Sachs |
| Indicator | CPI, NFP, GDP, RSI, ADX |
| Asset | Gold, Silver, DXY, VIX, S&P 500 |
| Event | FOMC Meeting, Rate Decision, OpEx |
| Person | Powell, Lagarde, Yellen |

### Action Types

| Type | Description |
|------|-------------|
| `research` | Topics requiring further investigation |
| `data_fetch` | Data to retrieve (COT, ETF flows) |
| `news_scan` | News/headlines to monitor |
| `calculation` | Math/risk calculations to perform |
| `monitoring` | Price levels or conditions to watch |

### Action Priorities

- **critical**: Requires immediate attention
- **high**: Important for current session
- **medium**: Should be addressed soon
- **low**: Background task

---

## Task Executor

Syndicate provides **two execution architectures** for processing action insights:

1. **Inline Executor** (`scripts/task_executor.py`) - Legacy blocking execution within main daemon
2. **Executor Daemon** (`scripts/executor_daemon.py`) - **Recommended** standalone worker with production hardening

### Architecture Comparison

| Feature | Inline Executor | Executor Daemon |
|---------|-----------------|-----------------|
| Lifecycle | Tied to main daemon | Independent process |
| Shutdown | Killed with daemon | Graceful drain |
| Orphan Recovery | None | Automatic on startup |
| Signal Handling | None | SIGTERM, SIGINT, SIGHUP |
| Systemd Support | No | Yes |
| Recommended For | Development | Production |

---

### Executor Daemon (Recommended)

The `scripts/executor_daemon.py` module provides a standalone, production-hardened task execution service.

#### Features

- **Independent lifecycle** - Survives main daemon restarts and graceful shutdowns
- **Orphan recovery** - Reclaims stuck `in_progress` tasks on startup
- **Signal handling** - SIGTERM/SIGINT for graceful drain, SIGHUP for config reload
- **Atomic claiming** - Prevents duplicate task execution across workers
- **Quota-aware** - Exponential backoff on rate limits
- **Health monitoring** - Heartbeat tracking, statistics, consecutive error detection

#### CLI Usage

```bash
# Run as continuous daemon (production)
python scripts/executor_daemon.py --daemon

# Drain queue and exit (CI/testing)
python scripts/executor_daemon.py --once

# Recover orphaned tasks only
python scripts/executor_daemon.py --recover-orphans

# Health check (JSON output)
python scripts/executor_daemon.py --health

# Spawn detached subprocess
python scripts/executor_daemon.py --spawn
```

#### Systemd Deployment

```bash
# Install service
sudo cp scripts/systemd/syndicate-executor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now syndicate-executor.service

# Check status
sudo systemctl status syndicate-executor

# View logs
sudo journalctl -u syndicate-executor -f
```

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOST_DETACHED_EXECUTOR` | `0` | Set to `1` to enable detached mode in run.py |
| `GOST_DATA_DIR` | `/app/data` | Data directory for executor |
| `NOTION_API_KEY` | *(none)* | Notion integration API key. The executor daemon performs a best-effort load of the repository `.env` on startup so keys defined there (e.g., `NOTION_API_KEY`, `GEMINI_API_KEY`) are available to the worker process. |

---

### Inline Executor (Legacy)

The `scripts/task_executor.py` module executes tasks within the main daemon loop.

### TaskExecutor Class

```python
from scripts.task_executor import TaskExecutor

executor = TaskExecutor(config, logger, db_manager, model)

# Execute a single action
result = executor.execute_action(action_insight)

# Process the entire queue (no limits)
executor.process_queue()
```

### Task Handlers

| Handler | Action Type | Description |
|---------|-------------|-------------|
| `_handle_research` | research | AI-powered research synthesis |
| `_handle_data_fetch` | data_fetch | Retrieve market data and COT reports |
| `_handle_news_scan` | news_scan | Scan for relevant news headlines |
| `_handle_calculation` | calculation | Execute quantitative calculations |
| `_handle_monitoring` | monitoring | Set up price level monitoring |
| `_handle_code_task` | code_task | Generate or modify code |

### Retry Logic (v3.2)

The executor uses exponential backoff for handling API quota errors:

```python
MAX_RETRIES = 10
INITIAL_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 600  # 10 minutes

def _execute_with_retry(self, action):
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(MAX_RETRIES):
        try:
            return self._execute_action(action)
        except Exception as e:
            if self._is_quota_error(e):
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
            else:
                raise
```

### Quota Error Detection

The system detects various quota error patterns:

- `429` - Rate limit exceeded
- `RESOURCE_EXHAUSTED` - API quota depleted
- `quota` - Generic quota messages
- `rate limit` - Rate limiting errors

### Auto-Publishing to Notion

Completed task artifacts are automatically published to Notion:

```python
def _publish_to_notion(self, artifact_path: str):
    """Publish task artifact to Notion database."""
    publisher = NotionPublisher()
    result = publisher.sync_file(artifact_path)
    return result
```

### Execution Flow

1. Insights Engine extracts actions from reports
2. Actions are queued with priorities
3. Task Executor processes ALL pending tasks (no limit)
4. Failed tasks retry with exponential backoff
5. Results are logged and stored in database
6. Artifacts are auto-published to Notion

---

## File Organizer

The `scripts/file_organizer.py` module provides intelligent file organization for outputs.

### Overview

Automatically organizes generated reports, charts, and exports into a structured directory hierarchy based on file type, date, and content category.

### FileOrganizer Class

```python
from scripts.file_organizer import FileOrganizer

organizer = FileOrganizer(config, logger)

# Organize all files in output directory
organizer.organize_output_directory()

# Organize a specific file
organizer.organize_file(file_path)
```

### Directory Structure

```
output/
├── journals/
│   └── 2025/
│       └── 12/
│           └── Journal_2025-12-01.md
├── reports/
│   ├── daily/
│   ├── weekly/
│   └── monthly/
├── charts/
│   ├── gold/
│   ├── silver/
│   └── intermarket/
├── exports/
│   ├── csv/
│   └── json/
└── archive/
```

### File Categories

| Category | Patterns | Destination |
|----------|----------|-------------|
| journal | `Journal_*.md` | `journals/YYYY/MM/` |
| weekly | `weekly_*.md` | `reports/weekly/` |
| monthly | `monthly_*.md` | `reports/monthly/` |
| chart | `*.png`, `*.svg` | `charts/{asset}/` |
| data | `*.csv`, `*.json` | `exports/{format}/` |

### Auto-Organization

When running in daemon mode, the File Organizer automatically processes new files:

```bash
python run.py --daemon --interval-min 240
```

---

## Frontmatter System

The `scripts/frontmatter.py` module generates YAML frontmatter metadata for all reports, enabling automated categorization and Notion integration.

### Overview

Frontmatter is applied as the **final step** after file organization, ensuring all files have proper metadata headers.

### Frontmatter Structure

```yaml
---
type: journal
title: "Journal 2025 12 03"
date: 2025-12-03
generated: 2025-12-03T21:47:56.739323
tags: [DXY, GOLD, Risk, SILVER, SPY, VIX]
bias: BULLISH
gold_price: 2650.50
---
```

### Auto-Detection

The module automatically detects document types based on filename patterns:

| Pattern | Type |
|---------|------|
| `Journal_*` | journal |
| `catalysts_*`, `research_*` | research |
| `1y_*`, `3m_*`, `weekly_*`, `monthly_*` | reports |
| `inst_matrix_*`, `*_insights_*` | insights |
| `premarket_*`, `analysis_*` | articles |
| `economic_calendar_*` | articles |
| `*chart*` | charts |
| Default | notes |

### Tag Extraction

Tags are automatically extracted from content:

- **Ticker symbols**: GOLD, SILVER, DXY, SPY, VIX, etc.
- **Keywords**: Fed, FOMC, CPI, NFP, Inflation, Bullish, Bearish

### Journal-Specific Metadata

For journal documents, additional metadata is extracted:

- **bias**: BULLISH, BEARISH, or NEUTRAL (from content analysis)
- **gold_price**: Current gold price mentioned in report

### Usage

```python
from scripts.frontmatter import add_frontmatter, has_frontmatter

# Check if content has frontmatter
if not has_frontmatter(content):
    content = add_frontmatter(content, filename)

# With custom fields
content = add_frontmatter(content, filename, custom_fields={
    'bias': 'BULLISH',
    'gold_price': 2650.50
})
```

---

## Notion Integration

The `scripts/notion_publisher.py` module syncs reports to a Notion database automatically.

### Overview

After each analysis cycle, reports are:
1. Generated and saved locally
2. Organized into directories
3. Tagged with frontmatter
4. **Published to Notion**

### Setup

1. Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share your database with the integration
3. Add credentials to `.env`:

```env
NOTION_API_KEY=ntn_xxxxxxxxxxxxx
NOTION_DATABASE_ID=your-database-id
```

### NotionPublisher Class

```python
from scripts.notion_publisher import NotionPublisher, sync_all_outputs

# Initialize publisher
publisher = NotionPublisher()

# Publish single file
result = publisher.sync_file("output/reports/journals/Journal_2025-12-03.md")
print(result['url'])  # Notion page URL

# Sync all outputs
results = sync_all_outputs()
print(f"Published: {len(results['success'])} files")
```

### Type Mapping

Documents are mapped to Notion types based on frontmatter:

| Frontmatter Type | Notion Select |
|------------------|---------------|
| journal | journal |
| research | research |
| reports | reports |
| insights | insights |
| articles | articles |
| charts | charts |
| notes | notes |

### Markdown Conversion

The publisher converts Markdown to Notion blocks:

- Headers → Heading blocks (H1-H3)
- Paragraphs → Paragraph blocks
- Lists → Bulleted/Numbered list items
- Code blocks → Code blocks with language
- Tables → Table blocks
- Blockquotes → Quote blocks

### CLI Commands

```bash
# Test connection
python scripts/notion_publisher.py --test

# Publish single file
python scripts/notion_publisher.py --file path/to/report.md

# Sync all outputs
python scripts/notion_publisher.py --sync-all

# List published pages
python scripts/notion_publisher.py --list
```

### Automatic Publishing

Publishing is integrated into the daemon workflow in `run.py`:

```
Analysis Cycle:
1. Generate reports (main.py)
2. Run live analysis (catalysts, matrix)
3. Split reports (weekly/monthly)
4. Organize files
5. Apply frontmatter
6. Publish to Notion  ← Automatic (respects daily schedule)
```

---

## Comprehensive Tagging

Version 3.2 introduces comprehensive file tagging to ensure all outputs are properly categorized and published to Notion.

### Type Patterns

Files are classified by filename patterns:

| Pattern | Type | Emoji |
|---------|------|-------|
| `Journal_*`, `journal_*`, `daily_*` | journal | 📓 |
| `premarket_*`, `pre_market_*` | premarket | 🌅 |
| `weekly_*`, `rundown_*` | reports | 📰 |
| `monthly_*` | reports | 📊 |
| `yearly_*`, `annual_*` | reports | 📈 |
| `analysis_*`, `horizon_*`, `1y_*`, `3m_*` | analysis | 🔍 |
| `catalyst*`, `watchlist*` | research | ⚡ |
| `research_*`, `calc_*`, `code_*` | research | 🔬 |
| `economic_*`, `calendar_*`, `events_*` | economic | 📅 |
| `inst_matrix*`, `institutional*`, `scenario*` | institutional | 🏦 |
| `entity_insights*`, `action_insights*` | insights | 💡 |

### Ticker Patterns

Automatically extracted from content:

```python
TICKER_PATTERNS = [
    r'\bGOLD\b', r'\bSILVER\b', r'\bDXY\b',
    r'\bVIX\b', r'\bSPY\b', r'\bSPX\b',
    r'\bTLT\b', r'\bGDX\b', r'\bGLD\b',
    r'\bSLV\b', r'\bYIELD\b', r'\bTNX\b',
]
```

### Keyword Patterns

Economic and institutional keywords for tagging:

```python
KEYWORD_PATTERNS = {
    'Fed': [r'\bFed\b', r'\bFederal Reserve\b', r'\bFOMC\b'],
    'ECB': [r'\bECB\b', r'\bEuropean Central Bank\b'],
    'CPI': [r'\bCPI\b', r'\bConsumer Price Index\b'],
    'NFP': [r'\bNFP\b', r'\bNonfarm Payrolls\b'],
    'GDP': [r'\bGDP\b', r'\bGross Domestic Product\b'],
    'PCE': [r'\bPCE\b', r'\bPersonal Consumption\b'],
    'ISM': [r'\bISM\b', r'\bPMI\b'],
    'JOLTS': [r'\bJOLTS\b', r'\bJob Openings\b'],
}
```

### Notion Formatting

Each document type gets a styled header callout:

```python
emoji_map = {
    "journal": "📓",
    "premarket": "🌅",
    "reports": "📑",
    "analysis": "🔍",
    "research": "🔬",
    "economic": "📅",
    "institutional": "🏦",
    "insights": "💡",
}

color_map = {
    "journal": "yellow_background",
    "premarket": "orange_background",
    "reports": "blue_background",
    "analysis": "purple_background",
    "economic": "green_background",
    "institutional": "blue_background",
}
```

### File Organizer Categories

All categories from `file_organizer.py` are fully covered:

| Category | Directory | Notion Type |
|----------|-----------|-------------|
| journals | `reports/journals/` | journal |
| premarket | `reports/premarket/` | premarket |
| weekly | `reports/weekly/` | reports |
| monthly | `reports/monthly/` | reports |
| yearly | `reports/yearly/` | reports |
| catalysts | `reports/catalysts/` | research |
| institutional | `reports/institutional/` | institutional |
| analysis | `reports/analysis/` | analysis |
| economic | `reports/economic/` | economic |
| research | `research/` | research |
| charts | `charts/` | charts |

---

## Testing Guidelines

### Test Suite Overview

The project includes comprehensive tests across multiple test files:

| File | Tests | Description |
|------|-------|-------------|
| `test_core.py` | 2 | Bias extraction logic |
| `test_gemini.py` | 27 | Gemini AI integration (includes 4 live API tests) |
| `test_split_reports.py` | 2 | Report generation |
| `test_ta_fallback.py` | 2 | Technical analysis fallback |
| `test_integration.py` | 1 | Integration tests for v3.0 modules |

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_gemini.py -v

# Run live API tests (requires GEMINI_API_KEY in .env)
pytest tests/test_gemini.py::TestGeminiLiveConnection -v

# Run integration tests for new modules
pytest tests/test_integration.py -v
```

### Live API Tests

Tests in `TestGeminiLiveConnection` require a valid `GEMINI_API_KEY`:

```python
class TestGeminiLiveConnection:
    def test_live_api_configuration(self, api_key):
        """Test that Gemini API can be configured with real key."""

    def test_live_model_initialization(self, api_key):
        """Test that GenerativeModel can be instantiated."""

    def test_live_simple_generation(self, api_key):
        """Test a simple content generation to verify API connectivity."""

    def test_live_strategist_analysis(self, api_key):
        """Test full Strategist analysis with live API."""
```

These tests load credentials from `.env` using `python-dotenv`.

### Unit Tests

Test individual components in isolation:

```python
# Test bias extraction
def test_extract_bias_bullish():
    text = "The outlook is BULLISH based on..."
    assert extract_bias(text) == "BULLISH"

# Test indicator fallback
def test_rsi_fallback():
    close = pd.Series([100, 101, 102, 101, 100, 99, 98, 99, 100])
    result = fallback_rsi(close, length=5)
    assert len(result) == len(close)
```

### Integration Tests

Test full pipeline with mocked data:

```python
def test_execute_no_ai(monkeypatch):
    # Mock yfinance to return deterministic data
    monkeypatch.setattr(yf, 'download', mock_download)

    # Run pipeline
    execute(config, logger, no_ai=True)

    # Verify outputs
    assert Path('output/Journal_2025-11-30.md').exists()
```

### Test Data

Keep fixtures in `tests/data/`:
- `gold_sample.csv` - Known OHLC data
- `expected_indicators.json` - Expected indicator values

---

## Deployment Notes

### Environment

- Python 3.10+ recommended
- Python 3.14 supported with fallback indicators

### Container Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "run.py", "--daemon", "--interval-min", "1"]
```

### Daemon Mode (v3.0)

The system supports autonomous background operation:

```bash
# Run with 1-minute intervals (default for v3.0)
python run.py --daemon --interval-min 240

# Legacy 4-hour intervals
python run.py --daemon --interval-hours 4

# Run once and exit
python run.py --mode daily --once
```

### Scheduling

For automated runs, use system scheduler:

```bash
# Cron (Unix) - Daemon mode with 1-minute intervals
@reboot cd /path/to/syndicate && python run.py --daemon --interval-min 240

# Single daily run at 8 AM
0 8 * * * cd /path/to/syndicate && python run.py --mode daily --once

# Task Scheduler (Windows) - Similar configuration
```

### GUI Mode

Launch the desktop dashboard:

```bash
python run.py --gui
```

Features:
- Dual-pane architecture (Data View + AI Workspace)
- Real-time chart grid with click-to-analyze
- Task queue and execution log
- Journal and rationale display

### Security

- Never commit `.env` or API keys
- Use pre-commit hooks for secret detection
- Rotate API keys if accidentally exposed
- Memory file contains run-specific data, not secrets

---

## Extension Patterns

### Adding New Assets

1. Add entry to `ASSETS` dictionary:
```python
ASSETS['PLATINUM'] = {'p': 'PL=F', 'b': 'PPLT', 'name': 'Platinum Futures'}
```

2. Update chart generation if needed
3. Add to report templates

### Adding New Indicators

1. Add computation in `QuantEngine._fetch`:
```python
df['MACD'] = ta.macd(df['Close'])['MACD_12_26_9']
```

2. Add fallback implementation
3. Include in quant telemetry for AI prompt

### Custom Report Types

1. Create new function in `split_reports.py` or `live_analysis.py`
2. Add CLI mode option in `run.py`
3. Add to GUI mode selector

### Extending Economic Calendar

Add new events in `economic_calendar.py`:

```python
def get_february_2026_events(self) -> List[EconomicEvent]:
    events = [
        EconomicEvent(
            datetime(2026, 2, 4, 8, 30),
            "Nonfarm Payrolls (NFP)",
            EventImpact.HIGH,
            "220K",
            "180K",
            "Weak = Bullish | Strong = Bearish",
            "🇺🇸"
        ),
        # ... more events
    ]
    return events
```

---

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `run.py` | Unified CLI entry point |
| `gui.py` | GUI dashboard application (v3.0) |
| `main.py` | Core pipeline and modules |
| `db_manager.py` | SQLite database manager |
| `scripts/insights_engine.py` | Entity and action extraction (v3.0) |
| `scripts/task_executor.py` | Autonomous task execution (v3.0) |
| `scripts/file_organizer.py` | Intelligent file organization (v3.0) |
| `scripts/live_analysis.py` | Live analysis suite |
| `scripts/economic_calendar.py` | Economic calendar system |
| `scripts/pre_market.py` | Pre-market plan generator |
| `scripts/split_reports.py` | Specialized report generator |
| `scripts/init_cortex.py` | Memory initialization |
| `scripts/prevent_secrets.py` | Pre-commit secret detection |
| `cortex_memory.json` | Persistent memory (auto-created) |
| `cortex_memory.template.json` | Safe template for new users |

---

## Appendix: CLI Reference

### Run Modes

```bash
# Daemon mode with 1-minute intervals (v3.0 default)
python run.py --daemon --interval-min 240

# Single execution
python run.py --mode daily --once

# GUI mode
python run.py --gui

# Interactive menu
python run.py --interactive
```

### Mode Options

| Mode | Description |
|------|-------------|
| `daily` | Full daily analysis with journal |
| `weekly` | Weekly tactical rundown |
| `monthly` | Monthly/yearly report |
| `catalyst` | Catalyst watchlist |
| `institutional` | Institutional matrix |
| `calendar` | Economic calendar |
| `premarket` | Pre-market preparation |

### Flags

| Flag | Description |
|------|-------------|
| `--daemon` | Run continuously in background |
| `--interval-min N` | Set daemon interval (minutes) |
| `--interval-hours N` | Set daemon interval (hours) |
| `--once` | Run once and exit |
| `--no-ai` | Skip AI analysis |
| `--gui` | Launch desktop dashboard |
| `--debug` | Enable debug logging |

---

## License

MIT
