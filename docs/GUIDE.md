# Gold Standard Technical Booklet

> Educational Guide and Technical Reference

This booklet provides in-depth documentation of the mathematical foundations, design decisions, and extension patterns for the Gold Standard quantitative analysis system.

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
10. [Testing Guidelines](#testing-guidelines)
11. [Deployment Notes](#deployment-notes)
12. [Extension Patterns](#extension-patterns)

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

The `db_manager.py` module provides SQLite persistence for all reports.

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
```

### Benefits

- Persistent storage across runs
- Historical analysis queries
- Performance tracking over time
- Data export capabilities

---

## Testing Guidelines

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
CMD ["python", "run.py", "--mode", "daily"]
```

### Scheduling

For automated runs, use system scheduler:

```bash
# Cron (Unix) - Daily at 8 AM
0 8 * * * cd /path/to/gold_standard && python run.py --mode daily

# Task Scheduler (Windows) - Similar configuration
```

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
| `gui.py` | GUI dashboard application |
| `main.py` | Core pipeline and modules |
| `db_manager.py` | SQLite database manager |
| `scripts/live_analysis.py` | Live analysis suite |
| `scripts/economic_calendar.py` | Economic calendar system |
| `scripts/pre_market.py` | Pre-market plan generator |
| `scripts/split_reports.py` | Specialized report generator |
| `scripts/init_cortex.py` | Memory initialization |
| `scripts/prevent_secrets.py` | Pre-commit secret detection |
| `cortex_memory.json` | Persistent memory (auto-created) |
| `cortex_memory.template.json` | Safe template for new users |

---

## License

MIT
