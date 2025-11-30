# Gold Standard — Technical Booklet & Educational Guide

This booklet is an educational companion to the Gold Standard project and is intended for developers and quants interested in understanding the mathematical foundations, the design choices, and suggested extension points.

Sections:
- Indicator explanations: RSI, ATR, ADX, SMA
- Gold/Silver ratio rationale
- Memory grading logic
- AI prompt design and best practices
- Implementation details & code walk-through
- Testing and validation guidance
- Deployment and operation tips

---

Indicator explanations
----------------------
1) RSI (Relative Strength Index)
   - Definition: RSI = 100 - (100 / (1 + RS)), where RS is the average of gains divided by average of losses over a lookback period (default 14 days).
   - Use: Identify overbought (typically >70) and oversold (typically <30) conditions.
   - Calculation (sample code):
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

2) ATR (Average True Range)
   - Definition: ATR measures volatility and is typically a smoothed moving average of the True Range (TR), which is the greatest of:
     - current high - current low
     - absolute value of current high - previous close
     - absolute value of current low - previous close
   - Use: Position sizing, stop loss width determination (often multiplied by some factor, e.g., 2x ATR).
   - Calculation (sample code):
     ```python
     def atr(high, low, close, length=14):
         prev_close = close.shift(1)
         tr1 = high - low
         tr2 = (high - prev_close).abs()
         tr3 = (low - prev_close).abs()
         tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
         return tr.rolling(window=length, min_periods=length).mean()
     ```

3) ADX (Average Directional Index)
   - Definition: The ADX is derived from the DMI (Directional Movement Index) composed of +DI and -DI. ADX measures trend strength without showing direction; values >25 often indicate a strong trend.
   - Use: Distinguish trending markets from ranging markets.
   - Notes on Calculation: ADX relies on +DI and -DI which themselves are smoothed moving averages of directional movement (+DM/-DM) divided by ATR. The final ADX is typically a smoothed moving average of the DX value.
   - Sketch (pseudo-code):
     ```python
     up_move = high.diff()
     down_move = low.diff() * -1
     plus_dm = np.where(up_move>down_move & up_move>0, up_move, 0)
     minus_dm = np.where(down_move>up_move & down_move>0, down_move, 0)
     # Smooth plus_dm, minus_dm using Wilder averaging (exponential smoothing with alpha=1/period)
     plus_di = (plus_dm_smooth / atr) * 100
     minus_di = (minus_dm_smooth / atr) * 100
     dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
     adx = dx.rolling(window=period).mean()
     ```

4) SMA (Simple Moving Average)
   - Use: Trend identification and crossovers (SMA 50/200 are common for longer-term regime identification).

Gold/Silver Ratio (GSR)
------------------------
- Definition: gold price / silver price.
- Rationale: As both metals often move together, the relative ratio can indicate relative value opportunities (i.e., Silver cheap relative to Gold). Historically, GSR varying above or below certain thresholds indicates potential rotation benefits.

Memory grading logic
---------------------
- The `Cortex` module stores the last prediction (bias) and price; once a new price is fetched, the system compares the new price to the previously recorded price; if the bias direction was correct, it logs a WIN; otherwise, a LOSS.
- Historical entries are kept bounded to `MAX_HISTORY_ENTRIES` for memory budgeting.

AI prompt design & best practices
---------------------------------
The `Strategist` builds a strict prompt to constrain model outputs and make parsing deterministic. The prompt includes:

- System instructions and identity to set the context and role of the model.
- Memory context (performance history) to enable self-reflection and improvement.
- Quant telemetry and intermarket ratios (price, RSI, ADX, ATR, regime) and recent headlines.
- Threshold values and an explicit output format (Markdown or JSON) so downstream code can extract values reliably.

Practical tips:

- Ask for a JSON response schema when programmatic integration is required. This reduces parsing errors and allows safe deserialization.
- If JSON output is requested, insist on a `json` code block to ensure the model returns machine-readable content.
- If Markdown output is chosen, require a clearly labeled `Bias` field, and instruct the model to use one of the canonical tokens: `BULLISH`, `BEARISH`, or `NEUTRAL`.
- Include example outputs in the prompt to demonstrate the expected formatting.

Example JSON schema (recommended):
```json
{
  "bias": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0.0,
  "entry": 0.0,
  "stop": 0.0,
  "take_profit": 0.0,
  "rationale": "..."
}
```

If JSON is not feasible, require the model to include the expected keys in a labeled Markdown section.

Implementation details & code walk-through
-----------------------------------------
- `main.py` houses the entire pipeline for simplicity, but you may split into `cortex.py`, `quant.py`, and `strategist.py` for maintainability.
- Key functions and logic paths are documented with inline comments.

Testing & validation guidance
Unit tests should cover:
  - ADX & ATR fallback computations to ensure their values are sane

  Integration tests and recommendations:
  - Use a fixed, deterministic dataset in `tests/fixtures/` to validate that indicators and charts are reproducible
  - Add a `tests/test_quantengine.py` that validates outputs for a small, known dataset saved under `tests/data/` and checks key indicators against expected ranges

  Example of a simple test for ATR:
  ```python
  def test_atr_known_values():
    df = pd.read_csv('tests/data/gold_sample.csv')
    result = quant_engine._compute_indicators(df)
    # assert result['ATR'].iloc[-1] == pytest.approx(5.23, rel=0.01)
  ```
  - Bias extraction for different AI outputs
  - Memory grading for edge cases (zero previous price, unchanged price, etc.)
  - Data pipeline handling for short/no data (fallback to backup tickers)
  - ADX & ATR fallback computations to ensure their values are sane

  Additional Testing Guidance
  --------------------------
  - Use synthetic datasets: build a small CSV dataset with known values and expected indicator outputs (especially for ADX/ATR/RSi). Keep fixtures under `tests/data/` to validate indicator computations over time.
  - Add integration tests that run a full `execute()` cycle with `--no-ai` and mock `yfinance` to return deterministic OHLC data.
  - Create a test to validate journal output: ensure that the `Journal_YYYY-MM-DD.md` contains the expected Markdown sections and that chart references exist.

  Worked Example: Serialized AI Output
  -----------------------------------
  For reliable downstream logic, prefer JSON output. If the model returns a JSON object, you can safely parse for the `bias` field and additional numeric items like `entry`, `stop`, and `take_profit`. A robust parse should validate types and ranges.

  Prompt Variants
  ---------------
  - Minimal structured prompt: ask the model for a succinct `Bias` field with a one-line rationale.
  - Structured JSON prompt: ask the model for a JSON object with specific keys.

  Example minimal prompt snippet:
  ```
  Provide a single-line bias labeled 'Bias:' followed by BULLISH, BEARISH, or NEUTRAL and a two-sentence rationale.
  ```

  Example JSON prompt snippet:
  ```
  Return a JSON object with keys 'bias', 'confidence', 'entry', 'stop', 'take_profit', 'rationale'.
  ``` 


CI & deployment
----------------
- CI should run with Python 3.11.
- Include steps for ensuring `pandas_ta` and `numba` are properly installed in CI if you require numeric parity with production.
- Consider containerizing your pipeline into a small Alpine or Debian-based image pinned to Python 3.11 and run a single process scheduling job.

Operational notes
------------------
- Rotate Gemini keys and any secrets used for third-party APIs.
- Disable AI in low-cost or test environments with `--no-ai` for faster runs.

Appendix: Where to start extending
----------------------------------
- Add new assets in the `ASSETS` dictionary in `main.py`.
- Add new signals to `QuantEngine._fetch` and chart to `QuantEngine._chart`.
- Add unit tests for any new signal calculations and backtest your logic with historical candle data before placing any trades.

---

This booklet aims to be a developer-first resource. If you'd like, I can produce a slide deck or an HTML book for human consumption.

