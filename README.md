# Gold Standard

> Quantitative Analysis Pipeline for Precious Metals Intelligence

An end-to-end system combining financial market data, technical indicators, and Google Gemini AI to generate structured trading reports focused on gold and related intermarket assets.

---

![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/status-active-success?style=flat-square)

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
- [Troubleshooting](#troubleshooting)
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
| **No-AI Mode** | Run data analysis without API calls for testing or offline use |

---

## Quick Start

### Automated Setup (Recommended)

**Windows PowerShell:**
```powershell
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

# Create virtual environment
python -m venv .venv

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

The unified CLI (`run.py`) provides both interactive and command-line modes.

#### Interactive Mode

```powershell
python run.py
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

#### Command-Line Mode

| Command | Description |
|---------|-------------|
| `python run.py --mode daily` | Run daily journal with AI |
| `python run.py --mode weekly` | Generate weekly rundown |
| `python run.py --mode monthly` | Generate monthly report |
| `python run.py --mode yearly` | Generate yearly report |
| `python run.py --mode daily --no-ai` | Run without AI calls |
| `python run.py --help` | Show all options |

### GUI Dashboard

```powershell
python gui.py
```

The GUI provides:

- **Mode Selection** - Radio buttons for Daily, Weekly, Monthly, Yearly
- **No AI Toggle** - Skip Gemini API calls for offline testing
- **Live Console** - Real-time progress output with timestamps
- **Results Dashboard** with four tabs:
  - **Charts** - Gallery of generated chart images (click to view full size)
  - **Reports** - List of markdown reports (double-click to preview)
  - **Preview** - Full content viewer for selected reports
  - **Journal** - Cortex memory stats and latest daily journal content

---

## Architecture

The system is organized into three primary modules:

```
+------------------+     +------------------+     +------------------+
|      Cortex      |     |   QuantEngine    |     |   Strategist     |
|------------------|     |------------------|     |------------------|
| - Memory JSON    |     | - yfinance data  |     | - Prompt builder |
| - Win/Loss track |<--->| - RSI, SMA, ATR  |<--->| - Gemini API     |
| - Predictions    |     | - mplfinance     |     | - Bias extract   |
+------------------+     +------------------+     +------------------+
```

### Cortex (Memory and Reflection)

- Persists predictions, win/loss records, and streaks to `cortex_memory.json`
- Grades past predictions against current prices
- Thread-safe with file locking via `filelock`
- Maintains history for performance tracking

### QuantEngine (Data and Charts)

- Fetches OHLC data via yfinance with primary/backup tickers
- Computes RSI, SMA, ATR, ADX with safe fallbacks for Python 3.14+
- Generates candlestick charts with mplfinance
- Handles missing data gracefully with NaN protection

### Strategist (AI Analysis)

- Builds structured prompts from quant data and memory context
- Queries Google Gemini for natural language analysis
- Extracts trading bias (BULLISH/BEARISH/NEUTRAL)
- Graceful fallback when AI is unavailable

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes* | Google Gemini API key (*not needed with `--no-ai`) |

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
├── setup.ps1                 # Automated setup (Windows PowerShell)
├── setup.sh                  # Automated setup (Unix/macOS/Linux)
├── run.py                    # Unified CLI entry point
├── gui.py                    # GUI dashboard application
├── main.py                   # Core pipeline (Cortex, QuantEngine, Strategist)
├── cortex_memory.json        # Persistent memory (auto-created)
├── cortex_memory.template.json
├── .env                      # API key (create from .env.template)
├── .env.template
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── scripts/
│   ├── split_reports.py      # Weekly/monthly/yearly report generator
│   ├── init_cortex.py        # Initialize memory from template
│   ├── get_gold_price.py     # Quick gold price check utility
│   ├── list_gemini_models.py # List available Gemini models
│   └── prevent_secrets.py    # Pre-commit secret detection hook
├── tests/
│   ├── test_core.py          # Core pipeline tests
│   ├── test_split_reports.py # Report generation tests
│   └── test_ta_fallback.py   # Technical analysis fallback tests
└── output/
    ├── gold_standard.log     # Application logs
    ├── Journal_YYYY-MM-DD.md # Daily journal reports
    ├── charts/               # Generated chart images
    │   ├── GOLD.png
    │   ├── SILVER.png
    │   ├── DXY.png
    │   ├── YIELD.png
    │   ├── VIX.png
    │   ├── SPX.png
    │   └── *_WEEK.png        # Weekly interval charts
    └── reports/              # Periodic reports
        ├── weekly_rundown_YYYY-MM-DD.md
        ├── monthly_yearly_report_YYYY-MM-DD.md
        └── charts/           # Report-specific charts
```

---

## Development

### Running Tests

```powershell
pip install -r requirements-dev.txt
pytest
pytest --cov=. --cov-report=html  # With coverage
```

### Pre-commit Hooks

```powershell
pre-commit install
pre-commit run --all-files
```

### Code Quality

The project uses:
- `pytest` for testing
- `pre-commit` for git hooks
- Custom secret detection via `scripts/prevent_secrets.py`

### Project Files

| File | Purpose |
|------|---------|
| `run.py` | Unified CLI with interactive menu and command-line flags |
| `gui.py` | Tkinter GUI dashboard with dark theme |
| `main.py` | Core pipeline (Cortex, QuantEngine, Strategist classes) |
| `scripts/split_reports.py` | Weekly/monthly/yearly report generator |
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
| `pandas_ta import error` | Safe fallbacks are built-in; works on Python 3.14+ |
| `yfinance rate limit` | Wait a few minutes; the system uses backup tickers |
| `Unicode errors in console` | Fixed in latest version; uses ASCII-only output |
| `Charts not generating` | Check `output/charts/` folder; ensure matplotlib is installed |

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

For detailed technical documentation, indicator explanations, and extension guidance, see [BOOKLET.md](BOOKLET.md).

---

<p align="center">
<strong>Gold Standard</strong> - Quantitative Analysis for Precious Metals
</p>
