# Gold Standard

> Quantitative Trading Analysis System

A quantitative analysis system that combines financial market data, technical indicators, and Google Gemini AI to generate trading reports focused on gold and related assets.

## Features

- Multi-Asset Analysis: Gold, Silver, DXY (Dollar Index), US 10Y Yield, VIX, and S&P 500
- Technical Indicators: RSI, ADX, ATR, SMA (50 & 200) via pandas_ta
- Intermarket Correlations: Gold/Silver Ratio analysis and simple divergence detection
- AI-Powered Insights: Uses Google Gemini (configured via google-generativeai) for natural-language analysis
- Self-Reflection Memory: Persists past predictions and grades performance (win/loss/streaks)
- Automated Charts: Generates candlestick charts with SMA overlays (mplfinance)
- Scheduled Execution: Default run every 4 hours (configurable via Config)
- Markdown Reports: Outputs a dated markdown journal per run
- Graceful Shutdown: Ctrl+C (SIGINT) and SIGTERM handled for clean termination
- Structured Logging: Console and file logging (output/gold_standard.log)
- Thread-Safe Memory: FileLock protects cortex_memory.json from concurrent access

## Installation

1. Clone or download this repository.
2. Create a virtual environment and activate it:

    PowerShell (Windows)
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

    Bash (Linux / macOS)
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Set your Gemini API key as an environment variable before running:

PowerShell (Windows)
```powershell
$env:GEMINI_API_KEY = "your-api-key-here"
```

Bash (Linux / macOS)
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Get your API key from Google AI Studio or your Google Cloud/GenAI console.

### Configurable Parameters (defaults reflect main.py)

The `Config` dataclass in main.py exposes these defaults:

- GEMINI_API_KEY: from environment (required)
- GEMINI_MODEL: `gemini-1.5-pro-latest`
- DATA_PERIOD: `1y`
- DATA_INTERVAL: `1d`
- CHART_CANDLE_COUNT: 100
- MAX_HISTORY_ENTRIES: 5
- MAX_CHART_AGE_DAYS: 7
- ADX_TREND_THRESHOLD: 25.0
- GSR_HIGH_THRESHOLD: 85.0
- GSR_LOW_THRESHOLD: 75.0
- VIX_HIGH_THRESHOLD: 20.0
- RSI_OVERBOUGHT: 70.0
- RSI_OVERSOLD: 30.0
- RUN_INTERVAL_HOURS: 4

Adjust these values directly in main.py or extend the Config class as needed.

## Usage

Run the main program:

```bash
python main.py
```

High-level flow per cycle:

1. Validate GEMINI_API_KEY
2. Fetch market data (yfinance) for tracked assets
3. Compute indicators (RSI, ADX, ATR, SMA50, SMA200)
4. Grade previous prediction using cortex_memory.json
5. Generate charts into output/charts/
6. Query Gemini AI for analysis (google-generativeai)
7. Write a markdown journal to output/Journal_YYYY-MM-DD.md
8. Repeat on schedule (default 4 hours) until shutdown

Press Ctrl+C to shutdown gracefully.

## Output Structure

```
gold_standard/
├── main.py
├── requirements.txt
├── cortex_memory.json       # AI memory with prediction history & win rate
├── cortex_memory.lock       # File lock for concurrent access safety
└── output/
     ├── gold_standard.log    # Application logs
     ├── charts/
     │   ├── GOLD.png
     │   ├── SILVER.png
     │   ├── DXY.png
     │   ├── YIELD.png
     │   ├── VIX.png
     │   └── SPX.png
     └── Journal_YYYY-MM-DD.md
```

Report notes:
- Journal filename is `Journal_YYYY-MM-DD.md` (uses current date).
- The report saved by main.py includes a markdown analysis (AI text) and image links to charts in `charts/`.

## Dependencies

Key packages used (listed in requirements.txt):

- yfinance — market data
- pandas — data manipulation
- pandas_ta — technical indicators (RSI, SMA, ATR, ADX)
- mplfinance — candlestick charting
- google-generativeai — Gemini integration (genai.GenerativeModel)
- schedule — periodic execution
- colorama — terminal coloring
- filelock — thread-safe file locking
- (standard library logging, json, datetime, signal, etc.)

## Architecture

The application is implemented in three primary modules inside main.py:

1. Cortex (Memory & Reflection)
    - Loads and persists `cortex_memory.json` under file lock.
    - Records history entries, win/loss streaks, totals, and last bias/price.
    - Grades previous predictions against the current gold price.

2. QuantEngine (Data & Charts)
    - Fetches asset data using yfinance with a primary and backup ticker.
    - Computes RSI, SMA(50/200), ATR, and ADX via pandas_ta.
    - Generates candlestick charts with SMA overlays (mplfinance).
    - Cleans up chart images older than MAX_CHART_AGE_DAYS.

3. Strategist (AI Analysis)
    - Builds an analysis prompt that includes memory, telemetry, ratios, and news.
    - Calls Google Gemini (google-generativeai) to produce natural-language analysis.
    - Extracts a trading bias (BULLISH / BEARISH / NEUTRAL) from the AI response.
    - The configured model is `gemini-1.5-pro-latest`.

## Notes and Implementation Details

- The program validates the GEMINI_API_KEY and configures the GenAI client:
  genai.configure(api_key=...) and model = genai.GenerativeModel(config.GEMINI_MODEL)
- The strategist expects GOLD data; if absent, the cycle aborts.
- Memory grading requires a prior recorded bias and price to compute win/loss.
- Charts and logs are written to the `output/` directory, created automatically.
- The scheduler uses `schedule.every(RUN_INTERVAL_HOURS).hours.do(execute, ...)`.
- File locking with `filelock.FileLock` prevents concurrent memory corruption.

## License

MIT
