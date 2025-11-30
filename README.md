# Gold Standard

> Quantitative Analysis Pipeline for Precious Metals Intelligence

An end-to-end system combining financial market data, technical indicators, and Google Gemini AI to generate structured trading reports focused on gold and related intermarket assets.

---

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/amuzetnoM/gold_standard/actions/workflows/python-ci.yml/badge.svg)
![Codecov](https://img.shields.io/codecov/c/gh/amuzetnoM/gold_standard)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI Interface](#cli-interface)
  - [GUI Dashboard](#gui-dashboard)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Output Structure](#output-structure)
- [Development](#development)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Asset Analysis** | Gold, Silver, Dollar Index (DXY), US 10Y Yield, VIX, S&P 500 |
| **Technical Indicators** | RSI, ADX, ATR, SMA (50/200) with pandas_ta and fallback implementations |
| **Intermarket Correlations** | Gold/Silver ratio analysis and divergence detection |
| **AI-Powered Insights** | Google Gemini integration for natural-language analysis |
| **Persistent Memory** | Cortex system tracks predictions, grades performance, maintains win/loss streaks |
| **Automated Charts** | Candlestick charts with SMA overlays via mplfinance |
| **Multiple Report Types** | Daily journals, weekly rundowns, monthly/yearly reports |
| **Dual Interface** | Command-line CLI and graphical GUI dashboard |

---

## Quick Start

### 1. Clone and Setup Environment

```bash
git clone https://github.com/amuzetnoM/gold_standard.git
cd gold_standard

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Unix/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for tests and pre-commit
```

### 2. Configure API Key

```bash
# Copy template and add your Gemini API key
cp .env.template .env
# Edit .env and set GEMINI_API_KEY=your-key-here
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Run

```bash
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

The unified CLI (`run.py`) provides both interactive and command-line modes.

#### Interactive Mode

```bash
python run.py
```

Displays a menu:

```
  [1] Daily Journal   -  Full daily analysis with AI-generated thesis
  [2] Weekly Rundown  -  Short-horizon tactical overview for the weekend
  [3] Monthly Report  -  Monthly aggregated performance tables + AI outlook
  [4] Yearly Report   -  Year-over-year analysis + AI forecast

  [0] Exit
```

#### Command-Line Mode

| Command | Description |
|---------|-------------|
| `python run.py --mode daily` | Run daily journal |
| `python run.py --mode weekly` | Generate weekly rundown |
| `python run.py --mode monthly` | Generate monthly report |
| `python run.py --mode yearly` | Generate yearly report |
| `python run.py --mode daily --no-ai` | Run without AI |

### GUI Dashboard

```bash
python gui.py
```

The GUI provides:

- **Mode Selection** - Radio buttons for Daily, Weekly, Monthly, Yearly
- **No AI Toggle** - Skip Gemini API calls
- **Live Console** - Real-time progress output
- **Results Dashboard** with four tabs:
  - **Charts** - Gallery of generated chart images
  - **Reports** - List of markdown reports with double-click preview
  - **Preview** - Full content viewer for selected reports
  - **Journal** - Persistent Cortex memory with performance stats and prediction history

---

## Architecture

The system is organized into three primary modules:

### Cortex (Memory and Reflection)

- Persists predictions, win/loss records, and streaks to `cortex_memory.json`
- Grades past predictions against current prices
- Thread-safe with file locking

### QuantEngine (Data and Charts)

- Fetches OHLC data via yfinance with primary/backup tickers
- Computes RSI, SMA, ATR, ADX with safe fallbacks
- Generates candlestick charts with mplfinance

### Strategist (AI Analysis)

- Builds structured prompts from quant data and memory
- Queries Google Gemini for analysis
- Extracts trading bias (BULLISH/BEARISH/NEUTRAL)

---

## Configuration

Key parameters in `main.py` Config class:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `GEMINI_MODEL` | `models/gemini-pro-latest` | Gemini model to use |
| `DATA_PERIOD` | `1y` | Historical data period |
| `DATA_INTERVAL` | `1d` | Data interval |
| `CHART_CANDLE_COUNT` | `100` | Candles to display |
| `ADX_TREND_THRESHOLD` | `25.0` | ADX threshold for trending |
| `RSI_OVERBOUGHT` | `70.0` | RSI overbought level |
| `RSI_OVERSOLD` | `30.0` | RSI oversold level |

---

## Output Structure

```
gold_standard/
├── run.py                    # Unified CLI entry point
├── gui.py                    # GUI dashboard
├── main.py                   # Core pipeline
├── cortex_memory.json        # Persistent memory (auto-created)
├── scripts/
│   └── split_reports.py      # Weekly/monthly/yearly generator
└── output/
    ├── gold_standard.log     # Application logs
    ├── Journal_YYYY-MM-DD.md # Daily journal
    ├── charts/               # Generated charts
    │   ├── GOLD.png
    │   ├── SILVER.png
    │   ├── DXY.png
    │   ├── YIELD.png
    │   ├── VIX.png
    │   └── SPX.png
    └── reports/              # Weekly/monthly/yearly reports
        └── charts/
```

---

## Development

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

### Project Files

| File | Purpose |
|------|---------|
| `run.py` | Unified CLI with interactive menu |
| `gui.py` | GUI dashboard with results viewer |
| `main.py` | Core pipeline (Cortex, QuantEngine, Strategist) |
| `scripts/split_reports.py` | Weekly/monthly/yearly report generator |
| `scripts/init_cortex.py` | Initialize memory from template |
| `scripts/prevent_secrets.py` | Pre-commit secret detection |

---

## License

MIT

---

For detailed technical documentation, indicator explanations, and extension guidance, see [BOOKLET.md](BOOKLET.md).
