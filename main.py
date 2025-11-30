#!/usr/bin/env python3
import os
import sys
import re
import json
import time
import signal
import logging
import datetime
import filelock
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import schedule
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import mplfinance as mpf
import google.generativeai as genai
from colorama import Fore, Back, Style, init

# ==========================================
# CONFIGURATION
# ==========================================
@dataclass
class Config:
    """Central configuration with sensible defaults."""
    # API Configuration
    GEMINI_API_KEY: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", "AIzaSyB_AcEs6f3qxHZRnN_5OjaGHIpdy4t0_78"))
    GEMINI_MODEL: str = "gemini-1.5-pro-latest"
    
    # Filesystem paths
    BASE_DIR: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))
    
    @property
    def OUTPUT_DIR(self) -> str:
        return os.path.join(self.BASE_DIR, "output")
    
    @property
    def CHARTS_DIR(self) -> str:
        return os.path.join(self.OUTPUT_DIR, "charts")
    
    @property
    def MEMORY_FILE(self) -> str:
        return os.path.join(self.BASE_DIR, "cortex_memory.json")
    
    @property
    def LOCK_FILE(self) -> str:
        return os.path.join(self.BASE_DIR, "cortex_memory.lock")
    
    # Technical Analysis Thresholds
    ADX_TREND_THRESHOLD: float = 25.0
    GSR_HIGH_THRESHOLD: float = 85.0  # Gold/Silver ratio - Silver cheap
    GSR_LOW_THRESHOLD: float = 75.0   # Gold/Silver ratio - Gold cheap
    VIX_HIGH_THRESHOLD: float = 20.0  # High volatility threshold
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0
    
    # Data Settings
    DATA_PERIOD: str = "1y"
    DATA_INTERVAL: str = "1d"
    CHART_CANDLE_COUNT: int = 100
    MAX_HISTORY_ENTRIES: int = 5
    MAX_CHART_AGE_DAYS: int = 7
    
    # Scheduling
    RUN_INTERVAL_HOURS: int = 4


# Asset Universe Configuration
ASSETS: Dict[str, Dict[str, str]] = {
    'GOLD':   {'p': 'GC=F', 'b': 'GLD', 'name': 'Gold Futures'},
    'SILVER': {'p': 'SI=F', 'b': 'SLV', 'name': 'Silver Futures'},
    'DXY':    {'p': 'DX-Y.NYB', 'b': 'UUP', 'name': 'Dollar Index'},
    'YIELD':  {'p': '^TNX', 'b': 'IEF', 'name': 'US 10Y Yield'},
    'VIX':    {'p': '^VIX', 'b': '^VIX', 'name': 'Volatility Index'},
    'SPX':    {'p': '^GSPC', 'b': 'SPY', 'name': 'S&P 500'}
}

# Global state for graceful shutdown
shutdown_requested = False
model = None  # Will be initialized in main()

# ==========================================
# LOGGING SETUP
# ==========================================
def setup_logging(config: Config) -> logging.Logger:
    """Configure structured logging with file and console handlers."""
    logger = logging.getLogger("GoldStandard")
    logger.setLevel(logging.DEBUG)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler for detailed logs
    log_file = os.path.join(config.OUTPUT_DIR, "gold_standard.log")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# ==========================================
# SIGNAL HANDLING
# ==========================================
def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger = logging.getLogger("GoldStandard")
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True


# ==========================================
# MODULE 1: MEMORY & REFLECTION
# ==========================================
class Cortex:
    """
    Handles persistent storage of past decisions, predictions, and performance grading.
    Uses file locking to prevent corruption from concurrent access.
    """
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.lock = filelock.FileLock(config.LOCK_FILE, timeout=10)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from JSON file with file locking."""
        default_memory = {
            "history": [],
            "win_streak": 0,
            "loss_streak": 0,
            "total_wins": 0,
            "total_losses": 0,
            "last_bias": None,
            "last_price_gold": 0.0,
            "last_update": None
        }
        
        try:
            with self.lock:
                if os.path.exists(self.config.MEMORY_FILE):
                    with open(self.config.MEMORY_FILE, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        # Merge with defaults to handle missing keys
                        return {**default_memory, **loaded}
        except filelock.Timeout:
            self.logger.error("Could not acquire memory file lock (timeout)")
        except json.JSONDecodeError as e:
            self.logger.error(f"Memory file corrupted: {e}. Starting fresh.")
        except Exception as e:
            self.logger.error(f"Error loading memory: {e}")
        
        return default_memory

    def update_memory(self, bias: str, current_gold_price: float) -> None:
        """Save current state for the next run to judge."""
        self.memory["last_bias"] = bias
        self.memory["last_price_gold"] = current_gold_price
        self.memory["last_update"] = datetime.datetime.now().isoformat()
        
        try:
            with self.lock:
                with open(self.config.MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.memory, f, indent=4)
            self.logger.debug(f"Memory updated: bias={bias}, price={current_gold_price}")
        except filelock.Timeout:
            self.logger.error("Could not acquire memory file lock for writing")
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")

    def grade_performance(self, current_gold_price: float) -> str:
        """Check if the previous run's bias was correct and update statistics."""
        if not self.memory.get("last_bias") or self.memory.get("last_price_gold", 0) == 0:
            self.logger.info("No previous prediction to grade")
            return "NO HISTORY"

        prev_price = self.memory["last_price_gold"]
        bias = self.memory["last_bias"]
        delta = current_gold_price - prev_price
        delta_pct = (delta / prev_price) * 100 if prev_price else 0
        
        result = "NEUTRAL"
        if bias == "BULLISH" and delta > 0:
            result = "WIN"
            self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
            self.memory["loss_streak"] = 0
            self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
        elif bias == "BULLISH" and delta < 0:
            result = "LOSS"
            self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
            self.memory["win_streak"] = 0
            self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1
        elif bias == "BEARISH" and delta < 0:
            result = "WIN"
            self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
            self.memory["loss_streak"] = 0
            self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
        elif bias == "BEARISH" and delta > 0:
            result = "LOSS"
            self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
            self.memory["win_streak"] = 0
            self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1
        
        # Log the result
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prev_bias": bias,
            "prev_price": prev_price,
            "current_price": current_gold_price,
            "delta_pct": round(delta_pct, 2),
            "result": result
        }
        self.memory["history"].append(entry)
        
        # Keep history bounded
        max_history = self.config.MAX_HISTORY_ENTRIES
        if len(self.memory["history"]) > max_history:
            self.memory["history"] = self.memory["history"][-max_history:]
        
        self.logger.info(
            f"Performance graded: {bias} @ ${prev_price:.2f} -> ${current_gold_price:.2f} "
            f"({delta_pct:+.2f}%) = {result}"
        )
        
        return result
    
    def get_win_rate(self) -> Optional[float]:
        """Calculate win rate percentage."""
        total = self.memory.get("total_wins", 0) + self.memory.get("total_losses", 0)
        if total == 0:
            return None
        return (self.memory.get("total_wins", 0) / total) * 100
    
    def get_formatted_history(self) -> str:
        """Format history for AI context."""
        if not self.memory.get("history"):
            return "No previous predictions recorded."
        
        lines = []
        for entry in self.memory["history"]:
            if isinstance(entry, dict):
                lines.append(
                    f"- {entry.get('prev_bias', 'N/A')} @ ${entry.get('prev_price', 0):.2f} "
                    f"-> ${entry.get('current_price', 0):.2f} ({entry.get('delta_pct', 0):+.2f}%) = "
                    f"{entry.get('result', 'N/A')}"
                )
            else:
                # Legacy string format
                lines.append(f"- {entry}")
        
        win_rate = self.get_win_rate()
        stats = f"\nWin Rate: {win_rate:.1f}%" if win_rate is not None else ""
        streak_info = ""
        if self.memory.get("win_streak", 0) > 0:
            streak_info = f" | Current Win Streak: {self.memory['win_streak']}"
        elif self.memory.get("loss_streak", 0) > 0:
            streak_info = f" | Current Loss Streak: {self.memory['loss_streak']}"
        
        return "\n".join(lines) + stats + streak_info


# ==========================================
# MODULE 2: QUANT ENGINE (Data)
# ==========================================
class QuantEngine:
    """
    Handles market data fetching, technical indicator calculation, and chart generation.
    """
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.news: List[str] = []

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Fetch and process data for all tracked assets."""
        self.logger.info("Engaging Quant Engine - fetching market data...")
        print(f"{Fore.CYAN}[SYSTEM] Engaging Quant Engine...")
        
        snapshot: Dict[str, Any] = {}
        self.news = []
        
        # Ensure charts directory exists
        os.makedirs(self.config.CHARTS_DIR, exist_ok=True)
        
        # Clean up old charts
        self._cleanup_old_charts()
        
        # Fetch data for each asset
        for key, conf in ASSETS.items():
            try:
                df = self._fetch(conf['p'], conf['b'])
                if df is None or df.empty:
                    self.logger.warning(f"No data available for {key}")
                    continue
                
                latest = df.iloc[-1]
                previous = df.iloc[-2] if len(df) > 1 else latest
                
                # Safely extract values with validation
                close_price = self._safe_float(latest.get('Close'))
                prev_close = self._safe_float(previous.get('Close'))
                rsi = self._safe_float(latest.get('RSI'))
                adx = self._safe_float(latest.get('ADX_14'))
                atr = self._safe_float(latest.get('ATR'))
                sma200 = self._safe_float(latest.get('SMA_200'))
                
                if close_price is None:
                    self.logger.warning(f"Invalid close price for {key}")
                    continue
                
                # Calculate change percentage
                change_pct = 0.0
                if prev_close and prev_close != 0:
                    change_pct = ((close_price - prev_close) / prev_close) * 100
                
                # Determine market regime based on ADX
                regime = "UNKNOWN"
                if adx is not None:
                    regime = "TRENDING" if adx > self.config.ADX_TREND_THRESHOLD else "CHOPPY/RANGING"
                
                snapshot[key] = {
                    "price": round(close_price, 2),
                    "change": round(change_pct, 2),
                    "rsi": round(rsi, 2) if rsi is not None else None,
                    "adx": round(adx, 2) if adx is not None else None,
                    "atr": round(atr, 2) if atr is not None else None,
                    "regime": regime,
                    "sma200": round(sma200, 2) if sma200 is not None else None
                }
                
                # Fetch news headlines
                self._fetch_news(key, conf['p'])
                
                # Generate chart
                self._chart(key, df)
                
                self.logger.debug(f"Processed {key}: ${close_price:.2f} ({change_pct:+.2f}%)")
                
            except Exception as e:
                self.logger.error(f"Error processing {key}: {e}", exc_info=True)
                continue
        
        if not snapshot:
            self.logger.error("Failed to fetch any market data")
            return None
        
        # Calculate intermarket ratios
        if 'GOLD' in snapshot and 'SILVER' in snapshot:
            gold_price = snapshot['GOLD']['price']
            silver_price = snapshot['SILVER']['price']
            if silver_price and silver_price > 0:
                gsr = round(gold_price / silver_price, 2)
                snapshot['RATIOS'] = {'GSR': gsr}
                self.logger.info(f"Gold/Silver Ratio: {gsr}")
        
        return snapshot

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            result = float(value)
            if pd.isna(result):
                return None
            return result
        except (ValueError, TypeError):
            return None

    def _fetch(self, primary: str, backup: str) -> Optional[pd.DataFrame]:
        """Fetch market data with fallback to backup ticker."""
        for ticker in [primary, backup]:
            try:
                self.logger.debug(f"Fetching data for {ticker}")
                df = yf.download(
                    ticker,
                    period=self.config.DATA_PERIOD,
                    interval=self.config.DATA_INTERVAL,
                    progress=False,
                    multi_level_index=False
                )
                
                if df.empty:
                    self.logger.debug(f"No data returned for {ticker}")
                    continue
                
                # Calculate technical indicators
                df['RSI'] = ta.rsi(df['Close'], length=14)
                df['SMA_200'] = ta.sma(df['Close'], length=200)
                df['SMA_50'] = ta.sma(df['Close'], length=50)
                df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
                
                # ADX (Trend Strength)
                adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                if adx_df is not None:
                    df = pd.concat([df, adx_df], axis=1)
                
                df_clean = df.dropna()
                if not df_clean.empty:
                    return df_clean
                    
            except Exception as e:
                self.logger.warning(f"Error fetching {ticker}: {e}")
                continue
        
        return None

    def _fetch_news(self, asset_key: str, ticker: str) -> None:
        """Fetch latest news headline for an asset."""
        try:
            t = yf.Ticker(ticker)
            if hasattr(t, 'news') and t.news:
                headline = t.news[0].get('title', '')
                if headline:
                    self.news.append(f"{asset_key}: {headline}")
                    self.logger.debug(f"News for {asset_key}: {headline[:50]}...")
        except Exception as e:
            self.logger.debug(f"Could not fetch news for {asset_key}: {e}")

    def _chart(self, name: str, df: pd.DataFrame) -> None:
        """Generate candlestick chart with technical overlays."""
        try:
            # Prepare additional plots
            sma50 = ta.sma(df['Close'], 50)
            sma200 = ta.sma(df['Close'], 200)
            
            apds = []
            if sma50 is not None and not sma50.isna().all():
                apds.append(mpf.make_addplot(sma50, color='orange', width=1))
            if sma200 is not None and not sma200.isna().all():
                apds.append(mpf.make_addplot(sma200, color='blue', width=1))
            
            style = mpf.make_mpf_style(
                base_mpf_style='nightclouds',
                rc={'font.size': 8}
            )
            
            chart_path = os.path.join(self.config.CHARTS_DIR, f"{name}.png")
            
            plot_kwargs = {
                'type': 'candle',
                'volume': False,
                'style': style,
                'title': f"{name} Quant View",
                'savefig': chart_path
            }
            
            if apds:
                plot_kwargs['addplot'] = apds
            
            mpf.plot(df.tail(self.config.CHART_CANDLE_COUNT), **plot_kwargs)
            self.logger.debug(f"Chart generated: {chart_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating chart for {name}: {e}")

    def _cleanup_old_charts(self) -> None:
        """Remove charts older than configured age."""
        if not os.path.exists(self.config.CHARTS_DIR):
            return
        
        try:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=self.config.MAX_CHART_AGE_DAYS)
            
            for filename in os.listdir(self.config.CHARTS_DIR):
                if not filename.endswith('.png'):
                    continue
                    
                filepath = os.path.join(self.config.CHARTS_DIR, filename)
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_mtime < cutoff:
                    os.remove(filepath)
                    self.logger.debug(f"Removed old chart: {filename}")
                    
        except Exception as e:
            self.logger.warning(f"Error during chart cleanup: {e}")


# ==========================================
# MODULE 3: THE STRATEGIST (AI)
# ==========================================
class Strategist:
    """
    AI-powered market analysis using Google Gemini.
    Generates trading insights based on technical data and intermarket correlations.
    """
    
    def __init__(
        self,
        config: Config,
        logger: logging.Logger,
        data: Dict[str, Any],
        news: List[str],
        memory_log: str
    ):
        self.config = config
        self.logger = logger
        self.data = data
        self.news = news
        self.memory = memory_log

    def think(self) -> Tuple[str, str]:
        """Generate AI analysis and extract trading bias."""
        self.logger.info("AI Strategist analyzing correlations & volatility...")
        print(f"{Fore.YELLOW}[AI] Analyzing Correlations & Volatility...")
        
        # Validate required data
        if 'GOLD' not in self.data:
            self.logger.error("Gold data missing - cannot generate analysis")
            return "Error: Gold data unavailable", "NEUTRAL"
        
        # Construct the context
        gsr = self.data.get('RATIOS', {}).get('GSR', 'N/A')
        vix_data = self.data.get('VIX', {})
        vix_price = vix_data.get('price', 'N/A')
        
        # Build data summary
        data_dump = self._format_data_summary()
        
        # Generate prompt
        prompt = self._build_prompt(gsr, vix_price, data_dump)
        
        try:
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Extract bias using more robust parsing
            bias = self._extract_bias(response_text)
            
            self.logger.info(f"AI analysis complete. Bias: {bias}")
            return response_text, bias
            
        except Exception as e:
            self.logger.error(f"AI generation error: {e}", exc_info=True)
            return f"Error generating analysis: {e}", "NEUTRAL"

    def _format_data_summary(self) -> str:
        """Format asset data for AI prompt."""
        lines = []
        for key, values in self.data.items():
            if key == 'RATIOS':
                continue
            if not isinstance(values, dict):
                continue
            
            price = values.get('price', 'N/A')
            rsi = values.get('rsi', 'N/A')
            adx = values.get('adx', 'N/A')
            regime = values.get('regime', 'N/A')
            atr = values.get('atr', 'N/A')
            
            lines.append(
                f"[{key}] Price:${price} | RSI:{rsi} | ADX:{adx} ({regime}) | ATR:${atr}"
            )
        
        return "\n".join(lines)

    def _build_prompt(self, gsr: Any, vix_price: Any, data_dump: str) -> str:
        """Build the AI analysis prompt."""
        gold_atr = self.data.get('GOLD', {}).get('atr', 0) or 0
        atr_stop = float(gold_atr) * 2
        
        return f"""
        Identity: Advanced Quant Algo "Gold Standard".
        Context: You are analyzing markets for a Hedge Fund.
        
        ### 🧠 SYSTEM MEMORY (Self-Reflection):
        {self.memory}
        (If you LOST last time, be more cautious. If you WON, maintain logic).

        ### 📊 QUANT METRICS:
        Gold/Silver Ratio: {gsr} (High > {self.config.GSR_HIGH_THRESHOLD} = Silver Cheap, Low < {self.config.GSR_LOW_THRESHOLD} = Gold Cheap)
        VIX (Fear): {vix_price} (High > {self.config.VIX_HIGH_THRESHOLD} = High Volatility Risk)
        
        ### 📉 ASSET TELEMETRY:
        {data_dump}
        
        ### 📰 NEWS CONTEXT:
        {chr(10).join(self.news[:4]) if self.news else "No recent news available."}

        ### INSTRUCTIONS:
        1. **Regime Detection:** Look at ADX. If < {self.config.ADX_TREND_THRESHOLD}, declare "Range-Bound". If > {self.config.ADX_TREND_THRESHOLD}, declare "Trending".
        2. **Volatility Sizing:** Use the ATR provided to calculate Stop Loss width. (e.g., Stop = 2 * ATR).
        3. **Correlation Check:** If DXY is UP and Gold is UP, note the "Safe Haven Divergence".
        4. **Bias:** Must be BULLISH, BEARISH, or NEUTRAL.

        ### OUTPUT FORMAT (MARKDOWN):
        # 🪙 Gold Standard Quant Report
        
        ## 1. 🧠 Algo Self-Correction
        *   **Previous Call:** (Reflect on the memory provided)
        *   **Current Stance:** (Adjusted based on recent performance)

        ## 2. 🌍 Macro & Intermarket
        *   **Regime:** (Trending or Ranging based on ADX?)
        *   **Gold/Silver Ratio:** (Analysis of {gsr})
        *   **VIX/Risk:** (Impact of VIX {vix_price})

        ## 3. 🎯 Strategic Thesis
        *   **Bias:** **[BULLISH/BEARISH/NEUTRAL]** (Choose exactly one and put it in bold)
        *   **Logic:** ...

        ## 4. 📐 Precision Execution (ATR Based)
        *   **Entry Zone:** Current Price +/- volatility
        *   **Volatility Stop (2x ATR):** ${atr_stop:.2f} width
        *   **Stop Loss Level:** $...
        *   **Take Profit:** $...

        ## 5. 🔮 Scenario Probability
        (Create a Markdown Matrix Table)
        """

    def _extract_bias(self, text: str) -> str:
        """
        Extract trading bias from AI response using robust parsing.
        Prioritizes explicit bias declarations over casual mentions.
        """
        text_upper = text.upper()
        
        # Pattern for explicit bias declaration
        bias_patterns = [
            r'\*\*BIAS[:\*\s]*\*?\*?\s*\*?\*?(BULLISH|BEARISH|NEUTRAL)',
            r'BIAS[:\s]+(BULLISH|BEARISH|NEUTRAL)',
            r'\*\*(BULLISH|BEARISH|NEUTRAL)\*\*',
        ]
        
        for pattern in bias_patterns:
            match = re.search(pattern, text_upper)
            if match:
                return match.group(1)
        
        # Fallback: count occurrences but weight by context
        bullish_count = text_upper.count("BULLISH")
        bearish_count = text_upper.count("BEARISH")
        neutral_count = text_upper.count("NEUTRAL")
        
        # Only return non-neutral if there's a clear preference
        if bullish_count > bearish_count and bullish_count > neutral_count:
            return "BULLISH"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            return "BEARISH"
        
        return "NEUTRAL"


# ==========================================
# EXECUTION LOOP
# ==========================================
def execute(config: Config, logger: logging.Logger) -> bool:
    """
    Execute one analysis cycle.
    Returns True on success, False on failure.
    """
    print(f"\n{Back.BLUE}{Fore.WHITE} --- QUANT CYCLE INITIATED --- {Style.RESET_ALL}")
    logger.info("=" * 50)
    logger.info("QUANT CYCLE INITIATED")
    logger.info("=" * 50)
    
    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    # Initialize components
    cortex = Cortex(config, logger)
    quant = QuantEngine(config, logger)
    
    # 1. Get Market Data
    data = quant.get_data()
    if not data:
        logger.error("Data fetch failed - aborting cycle")
        print(f"{Fore.RED}[ERROR] Data fetch failed.")
        return False
    
    # Validate gold data exists
    if 'GOLD' not in data:
        logger.error("Gold data missing - aborting cycle")
        print(f"{Fore.RED}[ERROR] Gold data unavailable.")
        return False
    
    gold_price = data['GOLD']['price']
    
    # 2. Grade Past Performance
    last_result = cortex.grade_performance(gold_price)
    print(f"{Fore.MAGENTA}[MEMORY] Last Run Result: {last_result}")
    
    # 3. AI Analysis
    memory_context = cortex.get_formatted_history()
    strat = Strategist(config, logger, data, quant.news, memory_context)
    report, new_bias = strat.think()
    
    # 4. Save Bias to Memory
    cortex.update_memory(new_bias, gold_price)
    
    # 5. Write Report
    report_filename = f"Journal_{datetime.date.today()}.md"
    report_path = os.path.join(config.OUTPUT_DIR, report_filename)
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            f.write("\n\n---\n\n## 📈 Charts\n\n")
            f.write("![Gold](charts/GOLD.png)\n\n")
            f.write("![Silver](charts/SILVER.png)\n\n")
            f.write("![VIX](charts/VIX.png)\n")
        
        logger.info(f"Report generated: {report_path}")
        print(f"{Fore.GREEN}[SUCCESS] Quant Report Generated: {report_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing report: {e}")
        print(f"{Fore.RED}[ERROR] Failed to write report: {e}")
        return False


def main() -> None:
    """Main entry point with graceful shutdown handling."""
    global shutdown_requested, model
    
    # Initialize colorama
    init(autoreset=True)
    
    # Load configuration
    config = Config()
    
    # Setup logging
    logger = setup_logging(config)
    
    # Validate API key
    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable not set!")
        print(f"{Fore.RED}[ERROR] Please set GEMINI_API_KEY environment variable.")
        print(f"{Fore.YELLOW}Example: $env:GEMINI_API_KEY = 'your-api-key-here'")
        sys.exit(1)
    
    # Configure Gemini
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        logger.info(f"Gemini AI configured with model: {config.GEMINI_MODEL}")
    except Exception as e:
        logger.error(f"Failed to configure Gemini AI: {e}")
        sys.exit(1)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"{Fore.GREEN}GOLD STANDARD SYSTEM ONLINE")
    print(f"{Fore.CYAN}Interval: {config.RUN_INTERVAL_HOURS} hours")
    print(f"{Fore.YELLOW}Press Ctrl+C to shutdown gracefully\n")
    
    logger.info(f"System started. Run interval: {config.RUN_INTERVAL_HOURS} hours")
    
    # Execute immediately
    execute(config, logger)
    
    # Schedule recurring execution
    schedule.every(config.RUN_INTERVAL_HOURS).hours.do(execute, config, logger)
    
    # Main loop with graceful shutdown
    while not shutdown_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)
    
    logger.info("Graceful shutdown complete")
    print(f"\n{Fore.GREEN}[SHUTDOWN] Gold Standard system stopped gracefully.")


if __name__ == "__main__":
    main()
        time.sleep(60)
