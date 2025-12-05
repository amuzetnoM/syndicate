```
   _________ _________ _________ _________ ____ ____ ____ ____
  ||       |||       |||       |||       |||G |||O |||L |||D ||
  ||_______|||_______|||_______|||_______|||__|||__|||__|||__||
  |/_______\|/_______\|/_______\|/_______\|/__\|/__\|/__\|/__\|
   _________ ____ ____ ____ ____ ____ ____ ____ ____
  ||       |||S |||T |||A |||N |||D |||A |||R |||D ||
  ||_______|||__|||__|||__|||__|||__|||__|||__|||__||
  |/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|


```

# Gold Standard
*version 3.2.2* [[CHANGELOG]](docs/CHANGELOG.md)

![FUCK IT · SHIP IT](https://img.shields.io/badge/FUCK%20IT-SHIP%20IT-2f2f2f?style=for-the-badge&labelColor=6f42c1&logoColor=white)

> **Precious Metals Intelligence Complex**
> A System for Quantitative Analysis

A comprehensive end-to-end system combining real-time market data, technical indicators, economic calendar intelligence, and Google Gemini AI to generate structured trading reports for gold and intermarket assets.

---

<p align="center">

<!-- CI Status -->
[![CI](https://img.shields.io/github/actions/workflow/status/amuzetnoM/gold_standard/python-ci.yml?branch=main&style=for-the-badge&logo=github&logoColor=white&label=CI)](https://github.com/amuzetnoM/gold_standard/actions/workflows/python-ci.yml)
[![Tests](https://img.shields.io/badge/tests-33%20passing-success?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/amuzetnoM/gold_standard/actions)
[![Coverage](https://img.shields.io/codecov/c/github/amuzetnoM/gold_standard?style=for-the-badge&logo=codecov&logoColor=white)](https://codecov.io/gh/amuzetnoM/gold_standard)

<!-- Tech Stack -->
[![Python](https://img.shields.io/badge/python-3.10--3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)


<!-- Meta -->
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)](#)

</p>

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Output Samples](#output-samples)
- [Economic Calendar](#economic-calendar)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Output Structure](#output-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Daemon** | Runs continuously, executing analysis every minute (configurable) |
| **Intelligent Scheduling** | Frequency-based task execution: daily/weekly/monthly/yearly cycles |
| **Notion Deduplication** | Content hashing prevents duplicate uploads; tracks sync state |
| **Auto Venv Activation** | Scripts automatically detect and activate virtual environment |
| **Multi-Asset Analysis** | Gold, Silver, Dollar Index (DXY), US 10Y Yield, VIX, S&P 500 |
| **Technical Indicators** | RSI, ADX, ATR, SMA (50/200) with pandas_ta + numba acceleration |
| **Intermarket Correlations** | Gold/Silver ratio analysis and divergence detection |
| **AI-Powered Insights** | Google Gemini integration for natural-language analysis |
| **Entity Insights** | Auto-extracts key entities (Fed, ECB, institutions) from reports |
| **Action Insights** | Identifies actionable tasks (research, monitoring, calculations) |
| **Task Executor** | Autonomously executes action insights with retry logic and quota handling |
| **Economic Calendar** | Self-maintaining calendar with Fed, ECB, NFP, CPI events and gold impact analysis |
| **Live Analysis Suite** | Catalyst watchlist, institutional matrix, 1Y/3M analysis reports |
| **Database Storage** | SQLite persistence for all reports, insights, tasks, and sync tracking |
| **Persistent Memory** | Cortex system tracks predictions, grades performance, maintains win/loss streaks |
| **Automated Charts** | Candlestick charts with SMA overlays via mplfinance |
| **Multiple Report Types** | Daily journals, pre-market plans, weekly rundowns, monthly/yearly reports |
| **Intelligent File Organization** | Auto-categorizes, dates, and archives reports (>7 days) |
| **YAML Frontmatter** | Auto-generates metadata headers for categorization and tagging |
| **Notion Integration** | Automatic publishing to Notion database with type/tag mapping |
| **Rich Notion Formatting** | Enhanced pages with callouts, colors, tables, TOC, and section emojis |
| **Comprehensive Tagging** | Auto-extracts tickers, keywords (Fed, CPI, FOMC) for complete coverage |
| **Smart Chart Integration** | Auto-detects tickers and embeds relevant charts in Notion pages |
| **Usage Management** | Tracks API usage, caches uploads, manages free-tier limits |
| **Dual Interface** | Command-line CLI and graphical GUI dashboard |
| **No-AI Mode** | Run data analysis without API calls for testing or offline use |

---

## Quick Start

### Requirements

- **Python 3.10 - 3.13** (Python 3.14+ not supported due to numba dependency)
- Windows, macOS, or Linux
- Google Gemini API key (free tier available)

### Automated Setup (Recommended)

**Windows PowerShell:**
```powershell
# Install Python 3.12 if needed
winget install Python.Python.3.12

.\setup.ps1
```

**Unix/macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Create and activate a virtual environment
- Install all dependencies
- Create `.env` from template
- Initialize Cortex memory
- Create output directories

After setup, edit `.env` and add your `GEMINI_API_KEY`.

### Manual Setup

#### 1. Clone and Setup Environment

```powershell
git clone https://github.com/amuzetnoM/gold_standard.git
cd gold_standard

# Create virtual environment (use Python 3.12 for best compatibility)
py -3.12 -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Unix/macOS)
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Optional: for tests and pre-commit
```

#### 2. Configure API Key

```powershell
# Copy template and add your Gemini API key
Copy-Item .env.template .env
# Edit .env and set GEMINI_API_KEY=your-key-here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

#### 3. Initialize Cortex Memory (Optional)

```powershell
python scripts/init_cortex.py
```

This creates `cortex_memory.json` from the template. The system will auto-create it on first run if missing.

#### 4. Run

```powershell
# Quick test (no AI)
python run.py --mode daily --no-ai

# Full run with AI
python run.py --mode daily

# Or launch the GUI
python gui.py
```

---

## Usage

### CLI Interface

The unified CLI (`run.py`) runs as an autonomous daemon by default with 1-minute cycles.

#### Autonomous Daemon Mode (Default)

```powershell
# Start autonomous daemon - runs analysis every 1 minute
python run.py

# Custom interval in minutes (5 minutes)
python run.py --interval-min 5

# Legacy hours-based interval (2 hours)
python run.py --interval 2

# Daemon without AI
python run.py --no-ai
```

Press **Ctrl+C** to gracefully shutdown the daemon.

#### Single Run Mode

```powershell
# Run once and exit
python run.py --once

# Run all analysis once
python run.py --run

# Quick daily journal only
python run.py --daily
```

#### Interactive Menu Mode

```powershell
python run.py --interactive
```

Displays a menu:

```
========================================
      GOLD STANDARD - Analysis Suite
========================================

Select analysis mode:

  [1] Daily Journal   - Full daily analysis with AI-generated thesis
  [2] Weekly Rundown  - Short-horizon tactical overview
  [3] Monthly Report  - Monthly aggregated performance + AI outlook
  [4] Yearly Report   - Year-over-year analysis + AI forecast

  [0] Exit

Enter choice (0-4):
```

#### Command Reference

| Command | Description |
|---------|-------------|
| `python run.py` | **Autonomous daemon** - runs every 1 minute (default) |
| `python run.py --interval-min 5` | Daemon with 5-minute interval |
| `python run.py --interval 2` | Daemon with 2-hour interval (legacy) |
| `python run.py --once` | Single run and exit |
| `python run.py --run` | Run all analysis once |
| `python run.py --daily` | Quick daily journal only |
| `python run.py --interactive` | Interactive menu mode |
| `python run.py --status` | Show system status |
| `python run.py --no-ai` | Run without Gemini API |
| `python run.py --help` | Show all options |

### GUI Dashboard

```powershell
python gui.py
```

The GUI provides:

- **Run All** - Execute complete analysis suite
- **Start Daemon** - Launch autonomous mode (runs every minute)
- **Quick Daily** - Fast daily journal update
- **Pre-Market** - Generate trading blueprint
- **No AI Toggle** - Skip Gemini API calls for offline testing
- **Live Console** - Real-time progress output with timestamps
- **Results Dashboard** with four tabs:
  - **Journals** - Browse journals by date with content preview
  - **Charts** - Gallery of generated chart images
  - **Reports** - List of all generated reports
  - **Trades** - Trade simulation history and stats

---

## Output Samples

### 📊 Generated Charts

The system generates professional candlestick charts with technical overlays:

| Asset | Chart |
|-------|-------|
| Gold (GC=F) | ![Gold Chart](docs/images/GOLD.png) |
| Silver (SI=F) | ![Silver Chart](docs/images/SILVER.png) |
| Dollar Index | ![DXY Chart](docs/images/DXY.png) |
| 10Y Yield | ![Yield Chart](docs/images/YIELD.png) |
| VIX | ![VIX Chart](docs/images/VIX.png) |
| S&P 500 | ![SPX Chart](docs/images/SPX.png) |

---

### 📋 Daily Journal Sample

The AI-generated daily journal includes comprehensive market analysis:

```markdown

## Date: December 01, 2025

## 1. Market Context
The macro environment is exhibiting classic "risk-on" characteristics with a
significant dovish tilt. The DXY's continued weakness (below 200SMA and in a
strong downtrend) and suppressed yields suggest the market is pricing in a
less restrictive Federal Reserve policy...

## 2. Asset-Specific Analysis
Gold has experienced a significant impulsive move, gaining +3.98% to reach $4254.9.
Price is firmly above its 200-day simple moving average, a long-term bullish signal.

**Trend Strength:** ADX reading of -1385.42, flagged as **CHOPPY/RANGING**
**Momentum:** RSI at **72.36**, entering overbought territory

## 4. Strategic Thesis
**Bias:** **NEUTRAL**
The primary thesis is that Gold's recent parabolic advance has pushed it into
a short-term overbought condition...

## 6. Scenario Probability Matrix
| Scenario | Price Target | Probability | Key Drivers |
|----------|-------------|-------------|-------------|
| Bull Case | $4450+ | 30% | DXY collapse continues, momentum traders pile in |
| Base Case | $4180 - $4280 | 55% | Price consolidates, digesting recent gains |
| Bear Case | <$4120 | 15% | Sharp reversal as overbought triggers profit-taking |
```

---

### 📈 Catalyst Watchlist Sample

Live market catalysts with HTML-formatted tables:

```markdown
# Live Catalyst Watchlist
> Generated: 2025-12-01 | Gold: $4,254.90 | DXY: 103.00 | VIX: 17.00 | 10Y: 4.30%

## Market Condition Summary

| Indicator | Current | Status | Gold Impact |
|-----------|---------|--------|-------------|
| VIX (Volatility) | 17.00 | NORMAL | Neutral |
| 10Y Yield | 4.30% | MODERATE | Neutral |
| DXY (Dollar) | 103.00 | Moderate | Neutral |

## Active Catalyst Matrix

| # | Event / Catalyst | What to Monitor | Impact |
|---|------------------|-----------------|--------|
| 1 | **Fed Policy & Interest Rates** | FOMC decisions, rate guidance | Bullish: Rate cuts → Rally |
| 2 | **U.S. Inflation Data** | CPI, PPI, PCE prints | Bullish: High inflation → Hedge demand |
| 3 | **Employment & Labor Market** | NFP, unemployment, wages | Bullish: Weak jobs → Rate cuts |
```

---

### 🏦 Institutional Matrix Sample

Tracks institutional and central bank positioning:

```markdown
# Institutional Activity Matrix
> Generated: 2025-12-01

## Central Bank Activity

| Central Bank | Recent Action | YTD Purchases | Gold Impact |
|--------------|---------------|---------------|-------------|
| 🇨🇳 PBOC (China) | +10t | +180t | Bullish - Largest buyer |
| 🇷🇺 Bank of Russia | +5t | +60t | Bullish - Strategic reserves |
| 🇹🇷 TCMB (Turkey) | +8t | +120t | Bullish - De-dollarization |
| 🇮🇳 RBI (India) | +3t | +45t | Bullish - Diversification |

## ETF Flow Tracking

| ETF | Weekly Flow | Monthly Flow | Signal |
|-----|-------------|--------------|--------|
| GLD | +$250M | +$1.2B | Bullish - Institutional accumulation |
| IAU | +$80M | +$350M | Bullish - Retail inflows |
```

---

## Economic Calendar

### 📅 Self-Maintaining Economic Calendar

The system includes a comprehensive economic calendar that automatically updates with each run:

**Features:**
- ✅ Auto-updates each system run
- ✅ December 2025 & January 2026 events pre-loaded
- ✅ Covers all major catalysts:
  - 🔴 **HIGH**: FOMC, NFP, CPI, Core CPI, PCE, GDP, ISM PMI
  - 🟡 **MED**: ADP, JOLTS, PPI, Retail Sales, Housing
  - 🟢 **LOW**: Beige Book, Fed Speeches, Trade Balance
- ✅ Real forecasts and previous values
- ✅ Gold impact analysis for each event

### Calendar Sample Output

```markdown
# Gold Standard Economic Calendar
> Generated: 2025-12-01 | Self-Maintaining | Auto-Updated Each Run

## This Week's Events

| Date | Time (ET) | Event | Impact | Forecast | Previous | Gold Impact |
|------|-----------|-------|--------|----------|----------|-------------|
| Tue Dec 02 | 10:00 | 🇺🇸 ISM Manufacturing PMI | 🔴 HIGH | 48.0 | 46.5 | Below 50 = Bullish |
| Wed Dec 03 | 10:00 | 🇺🇸 JOLTS Job Openings | 🟡 MED | 7.5M | 7.4M | Falling = Bullish |
| Thu Dec 04 | 10:00 | 🇺🇸 ISM Services PMI | 🔴 HIGH | 55.5 | 56.0 | Weakness = Bullish |
| Fri Dec 05 | 08:30 | 🇺🇸 Unemployment Rate | 🔴 HIGH | 4.2% | 4.1% | Rising = Bullish |
| Sat Dec 06 | 08:30 | 🇺🇸 Nonfarm Payrolls (NFP) | 🔴 HIGH | 200K | 12K | Weak = Bullish |

## Key Upcoming Events

### 🔴 HIGH IMPACT
- **Dec 11**: CPI YoY - Hot = Bullish (inflation hedge)
- **Dec 12**: ECB Rate Decision - Cut = EUR weak = Bearish short-term
- **Dec 18**: FOMC Decision - Dovish = Bullish
- **Jan 10**: NFP - Employment health check
- **Jan 15**: CPI YoY - Inflation trajectory

### Central Bank Meetings
| Bank | Date | Current Rate | Expectation |
|------|------|--------------|-------------|
| 🇺🇸 Fed (FOMC) | Dec 18 | 4.50% | Hold/Cut 25bp |
| 🇪🇺 ECB | Dec 12 | 3.25% | Cut 25bp |
| 🇯🇵 BOJ | Dec 19 | 0.25% | Hold |
| 🇬🇧 BOE | Dec 19 | 4.75% | Hold |
```

### Run the Calendar

```powershell
# Standalone calendar generation
python scripts/economic_calendar.py

# Or as part of daily analysis (auto-integrated)
python run.py --daily
```

---

## Architecture

The system is organized into modular components:

```
+------------------+     +------------------+     +------------------+
|      Cortex      |     |   QuantEngine    |     |   Strategist     |
|------------------|     |------------------|     |------------------|
| - Memory JSON    |     | - yfinance data  |     | - Prompt builder |
| - Win/Loss track |<--->| - RSI, SMA, ATR  |<--->| - Gemini API     |
| - Predictions    |     | - mplfinance     |     | - Bias extract   |
+------------------+     +------------------+     +------------------+
         |                       |                        |
         v                       v                        v
+------------------+     +------------------+     +------------------+
|   DBManager      |     |  LiveAnalyzer    |     | EconomicCalendar |
|------------------|     |------------------|     |------------------|
| - SQLite storage |     | - Catalyst watch |     | - Fed/ECB/BOJ    |
| - Report queries |     | - Inst. matrix   |     | - NFP/CPI/GDP    |
| - History access |     | - 1Y/3M analysis |     | - Gold impact    |
+------------------+     +------------------+     +------------------+
```

### Core Modules

| Module | File | Purpose |
|--------|------|---------|
| **Cortex** | `main.py` | Memory persistence, prediction tracking, performance grading |
| **QuantEngine** | `main.py` | Market data fetching, technical indicators, chart generation |
| **Strategist** | `main.py` | AI prompt building, Gemini API integration, bias extraction |
| **DBManager** | `db_manager.py` | SQLite database for report storage and historical queries |
| **LiveAnalyzer** | `scripts/live_analysis.py` | Live analysis suite with catalyst/matrix/period reports |
| **EconomicCalendar** | `scripts/economic_calendar.py` | Self-maintaining economic event calendar |
| **Frontmatter** | `scripts/frontmatter.py` | YAML metadata generator for reports |
| **NotionPublisher** | `scripts/notion_publisher.py` | Syncs reports to Notion database |
| **NotionFormatter** | `scripts/notion_formatter.py` | Rich Notion blocks with callouts, colors, tables |
| **ChartPublisher** | `scripts/chart_publisher.py` | Uploads charts to imgbb, smart ticker detection |
| **CleanupManager** | `scripts/cleanup_manager.py` | Usage tracking, retention policies, limit management |

---

## Notion Integration

Gold Standard can automatically publish reports to a Notion database with **rich formatting** and **embedded charts**.

### Features

| Feature | Description |
|---------|-------------|
| **Rich Formatting** | Callouts, colored text, tables, TOC, section emojis |
| **Smart Charts** | Auto-detects tickers mentioned and embeds relevant charts |
| **Usage Management** | Tracks imgbb/Notion usage, caches uploads, warns on limits |
| **Auto-Categorization** | Types reports by filename pattern |
| **Tag Extraction** | Extracts tickers and keywords as tags |

### Setup

1. **Create a Notion Integration**
   - Go to [Notion My Integrations](https://www.notion.so/my-integrations)
   - Create a new integration, copy the API key (starts with `ntn_`)

2. **Create/Share Database**
   - Create a Notion database (or use existing)
   - Click Share → Invite your integration
   - Copy the database ID from the URL: `notion.so/{database_id}?v=...`

3. **Get imgbb API Key (for charts)**
   - Go to [imgbb API](https://api.imgbb.com/) - free 32MB/month
   - Sign up and copy your API key

4. **Configure Environment**
   ```env
   NOTION_API_KEY=ntn_xxxxxxxxxxxxx
   NOTION_DATABASE_ID=your-database-id
   IMGBB_API_KEY=your-imgbb-key
   ```

### Document Types

Reports are automatically categorized:

| Pattern | Notion Type |
|---------|-------------|
| `Journal_*` | journal |
| `catalysts_*`, `research_*` | research |
| `1y_*`, `3m_*`, `weekly_*`, `monthly_*` | reports |
| `inst_matrix_*`, `*_insights_*` | insights |
| `premarket_*`, `economic_calendar_*` | articles |
| `*chart*` | charts |
| Default | notes |

### Manual Publishing

```powershell
# Test connection
python scripts/notion_publisher.py --test

# Publish single file (with auto-charts)
python scripts/notion_publisher.py --file output/reports/journals/Journal_2025-12-03.md

# Sync all outputs
python scripts/notion_publisher.py --sync-all

# List published pages
python scripts/notion_publisher.py --list
```

### Chart Management

```powershell
# Upload all charts to imgbb
python scripts/chart_publisher.py --upload-all

# Detect which charts a file needs
python scripts/chart_publisher.py --detect output/reports/journals/Journal_2025-12-03.md

# List cached chart URLs
python scripts/chart_publisher.py --list
```

### Usage & Cleanup

```powershell
# Check usage status
python scripts/cleanup_manager.py --status

# Clean old chart cache (default: 30 days)
python scripts/cleanup_manager.py --cleanup-charts

# Preview cleanup of old reports
python scripts/cleanup_manager.py --cleanup-all

# Actually archive old content
python scripts/cleanup_manager.py --cleanup-all --execute
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google Gemini API key (*not needed with `--no-ai`) |
| `NOTION_API_KEY` | No | Notion integration API key (for auto-publishing) |
| `NOTION_DATABASE_ID` | No | Notion database ID to publish reports to |
| `IMGBB_API_KEY` | No | imgbb API key for chart hosting (free: 32MB/month) |

### Config Class Parameters (main.py)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `GEMINI_MODEL` | `models/gemini-pro-latest` | Gemini model identifier |
| `DATA_PERIOD` | `1y` | Historical data lookback |
| `DATA_INTERVAL` | `1d` | Data interval (daily) |
| `CHART_CANDLE_COUNT` | `100` | Candles displayed on charts |
| `ADX_TREND_THRESHOLD` | `25.0` | ADX level for trend detection |
| `RSI_OVERBOUGHT` | `70.0` | RSI overbought threshold |
| `RSI_OVERSOLD` | `30.0` | RSI oversold threshold |

### Tracked Assets

| Asset | Primary Ticker | Backup Ticker |
|-------|----------------|---------------|
| Gold | GC=F | GLD |
| Silver | SI=F | SLV |
| DXY | DX-Y.NYB | UUP |
| 10Y Yield | ^TNX | - |
| VIX | ^VIX | - |
| S&P 500 | ^GSPC | SPY |

---

## Output Structure

```
gold_standard/
├── run.py                    # Unified CLI entry point
├── gui.py                    # GUI dashboard application
├── main.py                   # Core pipeline (Cortex, QuantEngine, Strategist)
├── db_manager.py             # SQLite database manager
├── cortex_memory.json        # Persistent memory (auto-created)
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
│
├── scripts/
│   ├── live_analysis.py      # Live analysis suite (catalysts, matrix, periods)
│   ├── economic_calendar.py  # Self-maintaining economic calendar
│   ├── pre_market.py         # Pre-market plan generator
│   ├── split_reports.py      # Weekly/monthly/yearly report generator
│   ├── frontmatter.py        # YAML frontmatter generator for reports
│   ├── notion_publisher.py   # Notion database sync and publishing
│   ├── notion_formatter.py   # Rich Notion formatting (callouts, colors, tables)
│   ├── chart_publisher.py    # Image hosting and smart chart detection
│   ├── cleanup_manager.py    # Usage tracking and retention management
│   ├── file_organizer.py     # Auto-categorizes and archives reports
│   ├── insights_engine.py    # Entity and action insight extraction
│   ├── task_executor.py      # Autonomous task execution
│   ├── init_cortex.py        # Initialize memory from template
│   ├── get_gold_price.py     # Quick gold price check utility
│   ├── list_gemini_models.py # List available Gemini models
│   └── prevent_secrets.py    # Pre-commit secret detection hook
│
├── data/
│   └── gold_standard.db      # SQLite database for report storage
│
├── tests/
│   ├── test_core.py          # Core pipeline tests (bias extraction)
│   ├── test_gemini.py        # Gemini AI integration tests
│   ├── test_split_reports.py # Report generation tests
│   └── test_ta_fallback.py   # Technical analysis fallback tests
│
└── output/
    ├── gold_standard.log     # Application logs
    ├── Journal_YYYY-MM-DD.md # Daily journal reports
    │
    ├── charts/               # Generated chart images
    │   ├── GOLD.png
    │   ├── SILVER.png
    │   ├── DXY.png
    │   ├── YIELD.png
    │   ├── VIX.png
    │   └── SPX.png
    │
    └── reports/              # All generated reports
        ├── catalysts_YYYY-MM-DD.md          # Catalyst watchlist
        ├── inst_matrix_YYYY-MM-DD.md        # Institutional matrix
        ├── 1y_YYYY-MM-DD.md                 # 1-year analysis
        ├── 3m_YYYY-MM-DD.md                 # 3-month analysis
        ├── economic_calendar_YYYY-MM-DD.md  # Economic calendar
        ├── premarket_YYYY-MM-DD.md          # Pre-market plan
        ├── weekly_rundown_YYYY-MM-DD.md     # Weekly summary
        └── monthly_yearly_report_YYYY-MM-DD.md
```

---

## Development

### Running Tests

```powershell
pip install -r requirements-dev.txt
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html  # With coverage
```

**Test Results:**
```
tests/test_core.py (2 tests)                    PASSED
tests/test_gemini.py (23 tests)                 PASSED
tests/test_split_reports.py (2 tests)           PASSED
tests/test_ta_fallback.py (2 tests)             PASSED

================================ 29 passed ================================
```

### Pre-commit Hooks

```powershell
pre-commit install
pre-commit run --all-files
```

### Code Quality

The project uses:
- **Ruff** - Fast Python linter and formatter
- **Bandit** - Security vulnerability scanner
- **pytest** - Testing framework (29 tests passing)
- **pre-commit** - Git hooks for code quality
- **detect-secrets** - Prevent secrets from being committed
- **GitHub Actions CI** - Lint, test, and integration checks

### Project Files

| File | Purpose |
|------|---------|
| `run.py` | Unified CLI with interactive menu and command-line flags |
| `gui.py` | Tkinter GUI dashboard with dark theme |
| `main.py` | Core pipeline (Cortex, QuantEngine, Strategist classes) |
| `db_manager.py` | SQLite database manager for report persistence |
| `scripts/live_analysis.py` | Live analysis suite with HTML table formatting |
| `scripts/economic_calendar.py` | Self-maintaining economic event calendar |
| `scripts/pre_market.py` | Pre-market plan generator |
| `scripts/split_reports.py` | Weekly/monthly/yearly report generator |
| `scripts/frontmatter.py` | YAML frontmatter generator for reports |
| `scripts/notion_publisher.py` | Notion database sync and publishing |
| `scripts/notion_formatter.py` | Rich Notion blocks (callouts, colors, tables, TOC) |
| `scripts/chart_publisher.py` | imgbb upload, smart ticker detection, caching |
| `scripts/cleanup_manager.py` | Usage tracking, retention policies, limit warnings |
| `scripts/file_organizer.py` | Auto-categorizes, dates, and archives reports |
| `scripts/insights_engine.py` | Entity and action insight extraction |
| `scripts/task_executor.py` | Autonomous task execution from insights |
| `scripts/init_cortex.py` | Initialize memory from template |
| `scripts/get_gold_price.py` | Quick gold price utility |
| `scripts/list_gemini_models.py` | List available Gemini models |
| `scripts/prevent_secrets.py` | Pre-commit secret detection |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `GEMINI_API_KEY not set` | Create `.env` file with your API key or use `--no-ai` |
| `numba not supported` | Use Python 3.10-3.13. Install with `winget install Python.Python.3.12` |
| `pandas_ta import error` | Ensure Python 3.10-3.13 is used; numba required for pandas_ta |
| `yfinance rate limit` | Wait a few minutes; the system uses backup tickers |
| `Unicode errors in console` | Fixed in latest version; uses ASCII-only output |
| `Charts not generating` | Check `output/charts/` folder; ensure matplotlib is installed |
| `Database locked` | Close other instances; SQLite allows single writer |

### Logs

Check `output/gold_standard.log` for detailed execution logs.

### No-AI Mode

For testing without API calls:

```powershell
python run.py --mode daily --no-ai
python gui.py  # Then check "No AI" checkbox
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Documentation

For detailed technical documentation, indicator explanations, and extension guidance, see [docs/GUIDE.md](docs/GUIDE.md).

---

<p align="center">
<strong>Gold Standard</strong> — Precious Metals Intelligence Complex
<br/>
<em>Quantitative Analysis • AI Insights • Economic Calendar • Live Reports</em>
</p>
