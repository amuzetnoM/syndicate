#!/usr/bin/env python3
import os
import sys
import re
import json
from dotenv import load_dotenv
import time
import signal
import logging
from logging.handlers import RotatingFileHandler
import datetime
import filelock
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import schedule
import argparse
import pandas as pd
try:
    import pandas_ta as ta
except Exception:
    # Fallback implementations for environments where pandas_ta or its optional
    # dependencies (like numba) are unavailable (e.g., Python 3.14).
    import pandas as _pd

    class _FallbackTA:
        @staticmethod
        def sma(series, length=50):
            return series.rolling(window=length).mean()

        @staticmethod
        def rsi(series, length=14):
            delta = series.diff()
            up = delta.clip(lower=0)
            down = -delta.clip(upper=0)
            ma_up = up.rolling(window=length, min_periods=length).mean()
            ma_down = down.rolling(window=length, min_periods=length).mean()
            rs = ma_up / ma_down
            return 100 - (100 / (1 + rs))

        @staticmethod
        def atr(high, low, close, length=14):
            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=length, min_periods=length).mean()

        @staticmethod
        def adx(high, low, close, length=14):
                # Basic ADX implementation compatible with pandas Series input (fallback).
                try:
                    prev_close = close.shift(1)
                    tr1 = high - low
                    tr2 = (high - prev_close).abs()
                    tr3 = (low - prev_close).abs()
                    tr = _pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                    atr = tr.rolling(window=length, min_periods=length).mean()

                    up_move = high.diff()
                    down_move = -low.diff()
                    # Use where to avoid setting dtype incompatible warnings
                    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
                    minus_dm = (-down_move).where((down_move > up_move) & (down_move > 0), 0.0)

                    plus_di = (plus_dm.rolling(window=length, min_periods=length).sum() / atr) * 100
                    minus_di = (minus_dm.rolling(window=length, min_periods=length).sum() / atr) * 100

                    dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
                    adx = dx.rolling(window=length, min_periods=length).mean()

                    df = _pd.concat([adx.rename(f'ADX_{length}'), plus_di.rename(f'DMP_{length}'), minus_di.rename(f'DMN_{length}')], axis=1)
                    return df
                except Exception:
                    return None

    ta = _FallbackTA()
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
    # Read API key from environment; do not hardcode secrets
    GEMINI_API_KEY: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    # Use an available model name from Google GenAI model list.
    # Default will work for the current API: 'models/gemini-pro-latest'
    GEMINI_MODEL: str = "models/gemini-pro-latest"
    
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
    
    # Scheduling - NEW: Minutes-based for high-frequency operation
    # Default to 1-minute cycles for real-time intelligence
    RUN_INTERVAL_MINUTES: int = 1
    RUN_INTERVAL_HOURS: int = 0  # Legacy support - set to 0 when using minutes
    
    # Insights & Task Execution
    ENABLE_INSIGHTS_EXTRACTION: bool = True
    ENABLE_TASK_EXECUTION: bool = True
    MAX_TASKS_PER_CYCLE: int = 10
    
    # File Organization
    ENABLE_AUTO_ORGANIZE: bool = True
    ARCHIVE_DAYS_THRESHOLD: int = 7


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
    
    # File handler for detailed logs (rotating)
    log_file = os.path.join(config.OUTPUT_DIR, "gold_standard.log")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


def strip_emojis(text: str) -> str:
    """Remove common emoji characters from a text string.
    This uses Unicode ranges for emoji and other symbols and removes them.
    """
    try:
        import re
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols etc
            "\U00002600-\U000026FF"  # Misc symbols
            "\U00002700-\U000027BF"  # Dingbats
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)
    except Exception:
        # Fallback: naive filter keeping ascii and basic punctuation
        return ''.join(ch for ch in text if ord(ch) < 10000)


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
# MODULE 1: MEMORY & REFLECTION (CORTEX)
# ==========================================
class Cortex:
    """
    Advanced persistent memory system for the Gold Standard algo.
    Tracks predictions, grades performance, and manages hypothetical trade positions.
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
            # Prediction tracking
            "history": [],
            "win_streak": 0,
            "loss_streak": 0,
            "total_wins": 0,
            "total_losses": 0,
            "last_bias": None,
            "last_price_gold": 0.0,
            "last_update": None,
            # Trade simulation
            "active_trades": [],
            "closed_trades": [],
            "total_pnl": 0.0,
            "trade_count": 0,
            # Strategic context
            "current_regime": "UNKNOWN",
            "confidence_level": 0.5,
            "invalidation_triggers": [],
            "key_levels": {
                "support": [],
                "resistance": [],
                "stop_loss": None,
                "take_profit": []
            }
        }
        
        try:
            template_path = os.path.join(self.config.BASE_DIR, 'cortex_memory.template.json')
            with self.lock:
                if not os.path.exists(self.config.MEMORY_FILE) and os.path.exists(template_path):
                    with open(template_path, 'r', encoding='utf-8') as t:
                        template_content = t.read()
                    with open(self.config.MEMORY_FILE, 'w', encoding='utf-8') as f:
                        f.write(template_content)
                    self.logger.debug(f"Initialized memory file from template: {self.config.MEMORY_FILE}")

                if os.path.exists(self.config.MEMORY_FILE):
                    with open(self.config.MEMORY_FILE, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        return {**default_memory, **loaded}
        except filelock.Timeout:
            self.logger.error("Could not acquire memory file lock (timeout)")
        except json.JSONDecodeError as e:
            self.logger.error(f"Memory file corrupted: {e}. Starting fresh.")
        except Exception as e:
            self.logger.error(f"Error loading memory: {e}")
        
        return default_memory

    def _save_memory(self) -> bool:
        """Persist memory to JSON file."""
        try:
            with self.lock:
                with open(self.config.MEMORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.memory, f, indent=4)
            return True
        except filelock.Timeout:
            self.logger.error("Could not acquire memory file lock for writing")
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
        return False

    def update_memory(self, bias: str, current_gold_price: float, 
                     regime: str = None, confidence: float = None,
                     key_levels: Dict = None) -> None:
        """Save current state for the next run to judge."""
        self.memory["last_bias"] = bias
        self.memory["last_price_gold"] = current_gold_price
        self.memory["last_update"] = datetime.datetime.now().isoformat()
        
        if regime:
            self.memory["current_regime"] = regime
        if confidence is not None:
            self.memory["confidence_level"] = confidence
        if key_levels:
            self.memory["key_levels"].update(key_levels)
        
        self._save_memory()
        self.logger.debug(f"Memory updated: bias={bias}, price={current_gold_price}")

    # ------------------------------------------
    # Trade Simulation System
    # ------------------------------------------
    def open_trade(self, direction: str, entry_price: float, 
                   stop_loss: float, take_profit: List[float],
                   size: float = 1.0, rationale: str = "") -> Dict:
        """
        Open a hypothetical trade position.
        Direction: LONG or SHORT
        """
        trade = {
            "id": self.memory.get("trade_count", 0) + 1,
            "direction": direction.upper(),
            "entry_price": entry_price,
            "entry_time": datetime.datetime.now().isoformat(),
            "stop_loss": stop_loss,
            "take_profit": take_profit if isinstance(take_profit, list) else [take_profit],
            "size": size,
            "rationale": rationale,
            "status": "OPEN",
            "current_price": entry_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "partial_exits": [],
            "trailing_stop": None
        }
        
        self.memory["active_trades"].append(trade)
        self.memory["trade_count"] = trade["id"]
        self._save_memory()
        
        self.logger.info(f"[TRADE] Opened {direction} @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: {take_profit}")
        return trade

    def update_trade_prices(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Update all active trades with current prices.
        Returns list of any trades that hit SL or TP.
        """
        gold_price = current_prices.get('GOLD', 0)
        if not gold_price:
            return []
        
        triggered_trades = []
        
        for trade in self.memory.get("active_trades", []):
            if trade["status"] != "OPEN":
                continue
            
            trade["current_price"] = gold_price
            entry = trade["entry_price"]
            direction = trade["direction"]
            
            # Calculate unrealized PnL
            if direction == "LONG":
                pnl = (gold_price - entry) * trade["size"]
                pnl_pct = ((gold_price - entry) / entry) * 100
            else:  # SHORT
                pnl = (entry - gold_price) * trade["size"]
                pnl_pct = ((entry - gold_price) / entry) * 100
            
            trade["unrealized_pnl"] = round(pnl, 2)
            trade["unrealized_pnl_pct"] = round(pnl_pct, 2)
            
            # Check stop loss
            if direction == "LONG" and gold_price <= trade["stop_loss"]:
                trade["exit_reason"] = "STOP_LOSS"
                triggered_trades.append(trade)
            elif direction == "SHORT" and gold_price >= trade["stop_loss"]:
                trade["exit_reason"] = "STOP_LOSS"
                triggered_trades.append(trade)
            
            # Check take profits (first target)
            if trade["take_profit"]:
                first_tp = trade["take_profit"][0]
                if direction == "LONG" and gold_price >= first_tp:
                    trade["exit_reason"] = "TAKE_PROFIT"
                    triggered_trades.append(trade)
                elif direction == "SHORT" and gold_price <= first_tp:
                    trade["exit_reason"] = "TAKE_PROFIT"
                    triggered_trades.append(trade)
        
        self._save_memory()
        return triggered_trades

    def close_trade(self, trade_id: int, exit_price: float, 
                    reason: str = "MANUAL") -> Optional[Dict]:
        """Close an active trade and record results."""
        for i, trade in enumerate(self.memory.get("active_trades", [])):
            if trade["id"] == trade_id:
                # Calculate final PnL
                entry = trade["entry_price"]
                direction = trade["direction"]
                
                if direction == "LONG":
                    pnl = (exit_price - entry) * trade["size"]
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl = (entry - exit_price) * trade["size"]
                    pnl_pct = ((entry - exit_price) / entry) * 100
                
                # Update trade record
                trade["status"] = "CLOSED"
                trade["exit_price"] = exit_price
                trade["exit_time"] = datetime.datetime.now().isoformat()
                trade["exit_reason"] = reason
                trade["realized_pnl"] = round(pnl, 2)
                trade["realized_pnl_pct"] = round(pnl_pct, 2)
                trade["result"] = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
                
                # Move to closed trades
                self.memory["active_trades"].pop(i)
                self.memory["closed_trades"].append(trade)
                self.memory["total_pnl"] = round(
                    self.memory.get("total_pnl", 0) + pnl, 2
                )
                
                # Update win/loss stats
                if trade["result"] == "WIN":
                    self.memory["total_wins"] = self.memory.get("total_wins", 0) + 1
                    self.memory["win_streak"] = self.memory.get("win_streak", 0) + 1
                    self.memory["loss_streak"] = 0
                elif trade["result"] == "LOSS":
                    self.memory["total_losses"] = self.memory.get("total_losses", 0) + 1
                    self.memory["loss_streak"] = self.memory.get("loss_streak", 0) + 1
                    self.memory["win_streak"] = 0
                
                self._save_memory()
                self.logger.info(
                    f"[TRADE] Closed #{trade_id} @ ${exit_price:.2f} | "
                    f"PnL: ${pnl:.2f} ({pnl_pct:+.2f}%) | {trade['result']}"
                )
                return trade
        
        return None

    def update_trailing_stop(self, trade_id: int, new_stop: float) -> bool:
        """Update trailing stop for an active trade."""
        for trade in self.memory.get("active_trades", []):
            if trade["id"] == trade_id:
                old_stop = trade["stop_loss"]
                trade["stop_loss"] = new_stop
                trade["trailing_stop"] = new_stop
                self._save_memory()
                self.logger.info(f"[TRADE] Updated SL for #{trade_id}: ${old_stop:.2f} -> ${new_stop:.2f}")
                return True
        return False

    def get_active_trades(self) -> List[Dict]:
        """Get all active trade positions."""
        return self.memory.get("active_trades", [])

    def get_trade_summary(self) -> Dict:
        """Get trading performance summary."""
        closed = self.memory.get("closed_trades", [])
        active = self.memory.get("active_trades", [])
        
        total_trades = len(closed)
        wins = sum(1 for t in closed if t.get("result") == "WIN")
        losses = sum(1 for t in closed if t.get("result") == "LOSS")
        
        return {
            "total_trades": total_trades,
            "active_positions": len(active),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / total_trades * 100) if total_trades > 0 else 0,
            "total_pnl": self.memory.get("total_pnl", 0),
            "win_streak": self.memory.get("win_streak", 0),
            "loss_streak": self.memory.get("loss_streak", 0)
        }

    # ------------------------------------------
    # Legacy Performance Grading
    # ------------------------------------------

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
        # Production mode: using ASSETS defined in the source configuration

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Fetch and process data for all tracked assets."""
        self.logger.info("Engaging Quant Engine - fetching market data...")
        self.logger.info(f"[SYSTEM] Engaging Quant Engine...")
        
        snapshot: Dict[str, Any] = {}
        self.news = []
        
        # Ensure charts directory exists
        os.makedirs(self.config.CHARTS_DIR, exist_ok=True)
        
        # Clean up old charts
        self._cleanup_old_charts()
        
        # Fetch data for each asset
        for key, conf in ASSETS.items():
            conf = ASSETS[key]
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
        # Production path: fetch from yfinance only

        for ticker in [primary, backup]:
            try:
                self.logger.debug(f"Fetching data for {ticker}")
                df = yf.download(
                    ticker,
                    period=self.config.DATA_PERIOD,
                    interval=self.config.DATA_INTERVAL,
                    progress=False,
                    multi_level_index=False,
                    auto_adjust=True
                )
                
                if df.empty:
                    self.logger.debug(f"No data returned for {ticker}")
                    continue
                
                # Validate minimal columns exist
                required_columns = ['Open', 'High', 'Low', 'Close']
                if not all(col in df.columns for col in required_columns):
                    self.logger.warning(f"Missing required OHLC columns for {ticker}: {df.columns}")
                    continue

                # Ensure index is timezone-aware or normalized
                df.index = pd.to_datetime(df.index)

                # Calculate technical indicators safely with fallbacks
                def safe_indicator_series(name, func, *fargs, **fkwargs):
                    try:
                        out = func(*fargs, **fkwargs)
                        # If a DataFrame or Series make sure it aligns with index
                        if out is None:
                            return None
                        if isinstance(out, pd.Series):
                            s = out
                        else:
                            s = pd.Series(out, index=df.index)
                        if len(s) != len(df):
                            self.logger.warning(f"Indicator {name} returned {len(s)} values for {ticker} but df has {len(df)} index; ignoring {name}")
                            return None
                        return s
                    except Exception as e:
                        self.logger.warning(f"Safe indicator {name} failed for {ticker}: {e}")
                        return None

                # Compute indicators with backoff to fallback implementations
                try:
                    # RSI
                    rsi_series = safe_indicator_series('RSI', ta.rsi, df['Close'], length=14)
                    if rsi_series is None:
                        # fallback computation
                        delta = df['Close'].diff()
                        up = delta.clip(lower=0)
                        down = -delta.clip(upper=0)
                        ma_up = up.rolling(window=14, min_periods=14).mean()
                        ma_down = down.rolling(window=14, min_periods=14).mean()
                        rs = ma_up / ma_down
                        rsi_series = 100 - (100 / (1 + rs))
                except Exception as e:
                    self.logger.warning(f"RSI computation failed for {ticker}: {e}")
                    rsi_series = None

                try:
                    sma200 = safe_indicator_series('SMA_200', ta.sma, df['Close'], length=200)
                    if sma200 is None:
                        # fallback SMA using pandas rolling mean
                        sma200 = df['Close'].rolling(window=200, min_periods=1).mean()
                except Exception as e:
                    self.logger.warning(f"SMA_200 computation failed for {ticker}: {e}")
                    # fallback SMA using pandas rolling mean
                    try:
                        sma200 = df['Close'].rolling(window=200, min_periods=1).mean()
                    except Exception:
                        sma200 = None

                try:
                    sma50 = safe_indicator_series('SMA_50', ta.sma, df['Close'], length=50)
                    if sma50 is None:
                        # fallback SMA using pandas rolling mean
                        sma50 = df['Close'].rolling(window=50, min_periods=1).mean()
                except Exception as e:
                    self.logger.warning(f"SMA_50 computation failed for {ticker}: {e}")
                    # fallback SMA using pandas rolling mean
                    try:
                        sma50 = df['Close'].rolling(window=50, min_periods=1).mean()
                    except Exception:
                        sma50 = None

                try:
                    atr_series = safe_indicator_series('ATR', ta.atr, df['High'], df['Low'], df['Close'], length=14)
                    if atr_series is None:
                        # fallback ATR as rolling mean of TR
                        prev_close = df['Close'].shift(1)
                        tr1 = df['High'] - df['Low']
                        tr2 = (df['High'] - prev_close).abs()
                        tr3 = (df['Low'] - prev_close).abs()
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr_series = tr.rolling(window=14, min_periods=14).mean()
                except Exception as e:
                    self.logger.warning(f"ATR computation failed for {ticker}: {e}")
                    atr_series = None

                # ADX returns DataFrame with multiple columns. Wrap safely.
                try:
                    adx_df = None
                    raw_adx = None
                    try:
                        raw_adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                    except Exception:
                        raw_adx = None
                    if raw_adx is not None:
                        if isinstance(raw_adx, pd.DataFrame):
                            adx_df = raw_adx
                        else:
                            # if series, no
                            adx_df = None
                    if adx_df is None:
                        # fallback ADX
                        prev_close = df['Close'].shift(1)
                        tr1 = df['High'] - df['Low']
                        tr2 = (df['High'] - prev_close).abs()
                        tr3 = (df['Low'] - prev_close).abs()
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        atr = tr.rolling(window=14, min_periods=14).mean()
                        up_move = df['High'].diff()
                        down_move = -df['Low'].diff()
                        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
                        minus_dm = (-down_move).where((down_move > up_move) & (down_move > 0), 0.0)
                        plus_di = (plus_dm.rolling(window=14, min_periods=14).sum() / atr) * 100
                        minus_di = (minus_dm.rolling(window=14, min_periods=14).sum() / atr) * 100
                        dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
                        adx_ser = dx.rolling(window=14, min_periods=14).mean()
                        adx_df = pd.DataFrame({f'ADX_14': adx_ser, f'DMP_14': plus_di, f'DMN_14': minus_di})
                except Exception as e:
                    self.logger.warning(f"ADX computation failed for {ticker}: {e}")
                    adx_df = None

                # Assign computed indicators if present
                if rsi_series is not None:
                    df['RSI'] = rsi_series
                if sma200 is not None:
                    df['SMA_200'] = sma200
                if sma50 is not None:
                    df['SMA_50'] = sma50
                if atr_series is not None:
                    df['ATR'] = atr_series
                if adx_df is not None:
                    df = pd.concat([df, adx_df], axis=1)

                # Only drop rows based on missing OHLC data — keep indicator NaNs to avoid dropping datasets
                df_clean = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
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
            # Prefer columns if precomputed by _fetch; else compute safely
            def safe_sma(series, length):
                try:
                    out = None
                    # Try using ta if available
                    out = ta.sma(series, length)
                    if out is None:
                        raise Exception('ta.sma returned None')
                    if isinstance(out, pd.Series):
                        s = out
                    else:
                        s = pd.Series(out, index=series.index)
                    if len(s) != len(series):
                        raise Exception('sma length mismatch')
                    return s
                except Exception:
                    # fallback to pandas rolling mean
                    try:
                        return series.rolling(window=length, min_periods=length).mean()
                    except Exception:
                        return None

            if 'SMA_50' in df.columns:
                sma50 = df['SMA_50']
            else:
                sma50 = safe_sma(df['Close'], 50)
            if 'SMA_200' in df.columns:
                sma200 = df['SMA_200']
            else:
                sma200 = safe_sma(df['Close'], 200)
            
            # Slice the dataframe to the candle count to plot; additionally slice addplot series to match length
            plot_df = df.tail(self.config.CHART_CANDLE_COUNT)
            apds = []
            sma50_plot = None
            sma200_plot = None
            if sma50 is not None:
                sma50_plot = sma50.reindex(plot_df.index)
            if sma200 is not None:
                sma200_plot = sma200.reindex(plot_df.index)
            if sma50_plot is not None and hasattr(sma50_plot, 'isna') and not sma50_plot.isna().all():
                apds.append(mpf.make_addplot(sma50_plot, color='orange', width=1))
            if sma200_plot is not None and hasattr(sma200_plot, 'isna') and not sma200_plot.isna().all():
                apds.append(mpf.make_addplot(sma200_plot, color='blue', width=1))
            
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
            mpf.plot(plot_df, **plot_kwargs)
            # ensure chart was actually written
            ok = False
            try:
                if os.path.exists(chart_path) and os.path.getsize(chart_path) > 2048:
                    ok = True
            except Exception:
                ok = False

            if not ok:
                self.logger.warning(f"Chart generated but verification failed (size too small or missing): {chart_path}")
            else:
                self.logger.info(f"Chart generated and verified: {chart_path}")
            
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
    Generates sophisticated trading insights matching institutional-grade analysis.
    """
    
    def __init__(
        self,
        config: Config,
        logger: logging.Logger,
        data: Dict[str, Any],
        news: List[str],
        memory_log: str,
        model: Optional[Any] = None,
        cortex: Optional['Cortex'] = None,
    ):
        self.config = config
        self.logger = logger
        self.data = data
        self.news = news
        self.memory = memory_log
        self.model = model
        self.cortex = cortex

    def think(self) -> Tuple[str, str]:
        """Generate AI analysis and extract trading bias."""
        self.logger.info("AI Strategist analyzing correlations & volatility...")
        
        if 'GOLD' not in self.data:
            self.logger.error("Gold data missing - cannot generate analysis")
            return "Error: Gold data unavailable", "NEUTRAL"
        
        gsr = self.data.get('RATIOS', {}).get('GSR', 'N/A')
        vix_data = self.data.get('VIX', {})
        vix_price = vix_data.get('price', 'N/A')
        
        data_dump = self._format_data_summary()
        prompt = self._build_prompt(gsr, vix_price, data_dump)
        
        try:
            if not self.model:
                raise RuntimeError("AI model not available")
            response = self.model.generate_content(prompt)
            response_text = response.text
            
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
            change = values.get('change', 0)
            rsi = values.get('rsi', 'N/A')
            adx = values.get('adx', 'N/A')
            regime = values.get('regime', 'N/A')
            atr = values.get('atr', 'N/A')
            sma200 = values.get('sma200', 'N/A')
            
            trend_vs_sma = ""
            if price != 'N/A' and sma200 and sma200 != 'N/A':
                if price > sma200:
                    trend_vs_sma = "ABOVE 200SMA"
                else:
                    trend_vs_sma = "BELOW 200SMA"
            
            lines.append(
                f"* {key}: ${price} ({change:+.2f}%) | RSI: {rsi} | ADX: {adx} ({regime}) | ATR: ${atr} | {trend_vs_sma}"
            )
        
        return "\n".join(lines)

    def _get_active_trades_context(self) -> str:
        """Format active trades for AI context."""
        if not self.cortex:
            return "No active positions."
        
        trades = self.cortex.get_active_trades()
        if not trades:
            return "No active positions."
        
        lines = ["Current Active Positions:"]
        for t in trades:
            lines.append(
                f"* Trade #{t['id']}: {t['direction']} @ ${t['entry_price']:.2f} | "
                f"SL: ${t['stop_loss']:.2f} | TP: {t['take_profit']} | "
                f"Unrealized: ${t.get('unrealized_pnl', 0):.2f} ({t.get('unrealized_pnl_pct', 0):+.2f}%)"
            )
        return "\n".join(lines)

    def _build_prompt(self, gsr: Any, vix_price: Any, data_dump: str) -> str:
        """Build sophisticated AI analysis prompt matching institutional style."""
        gold_data = self.data.get('GOLD', {})
        gold_price = gold_data.get('price', 0)
        gold_atr = gold_data.get('atr', 0) or 0
        gold_rsi = gold_data.get('rsi', 50)
        gold_adx = gold_data.get('adx', 0)
        
        atr_stop_width = float(gold_atr) * 2
        suggested_sl = gold_price - atr_stop_width if gold_price else 0
        suggested_tp1 = gold_price + (atr_stop_width * 1.5) if gold_price else 0
        suggested_tp2 = gold_price + (atr_stop_width * 3) if gold_price else 0
        
        # Determine regime
        regime = "TRENDING" if gold_adx and gold_adx > self.config.ADX_TREND_THRESHOLD else "RANGE-BOUND/CHOPPY"
        
        # Get active trades context
        trades_context = self._get_active_trades_context()
        
        return f"""
You are "Gold Standard" - an elite quantitative trading algorithm operating for a sophisticated hedge fund.
Your analysis must be precise, actionable, and reflect deep market understanding.

=== SYSTEM STATE ===
Performance Memory:
{self.memory}

Active Positions:
{trades_context}

=== MARKET TELEMETRY ===
{data_dump}

Intermarket Ratios:
* Gold/Silver Ratio (GSR): {gsr} (>85 = Silver undervalued; <75 = Gold undervalued)
* VIX (Fear Gauge): {vix_price} (>20 = Elevated volatility/risk-off; <15 = Complacency)

Current Regime Detection: {regime} (ADX: {gold_adx})

=== NEWS CONTEXT ===
{chr(10).join(['* ' + n for n in self.news[:5]]) if self.news else "No significant headlines."}

=== ANALYSIS FRAMEWORK ===

Generate a comprehensive trading journal following this EXACT structure:

## Date: {datetime.date.today().strftime('%B %d, %Y')}

---

## 1. Market Context
Analyze the broader macro environment:
* Fed policy expectations and rate probabilities
* Dollar dynamics and their impact on commodities
* Global liquidity conditions and risk appetite
* Key macro themes driving precious metals

## 2. Asset-Specific Analysis
For Gold and the metals complex:
* Current price action and technical structure
* Trend strength (use ADX: {gold_adx})
* Momentum readings (RSI: {gold_rsi})
* Key support/resistance zones
* Intermarket correlations (GSR, DXY relationship)

## 3. Sentiment Summary
* Institutional positioning (infer from price action)
* Safe-haven demand dynamics
* Market pulse (bullish/bearish/neutral sentiment)

## 4. Strategic Thesis
**Bias:** **[BULLISH/BEARISH/NEUTRAL]** (Choose ONE and make it bold)

Provide clear rationale with:
* Primary thesis (1-2 sentences)
* Supporting factors (bullet points)
* Invalidation conditions (what would change your view)

## 5. Setup Scan & Trade Idea

| Component | Specification |
|-----------|---------------|
| Direction | LONG / SHORT / FLAT |
| Entry Zone | Price range for entry |
| Stop Loss | ${suggested_sl:.2f} (2x ATR: ${atr_stop_width:.2f}) |
| Target 1 | ${suggested_tp1:.2f} (1.5R) |
| Target 2 | ${suggested_tp2:.2f} (3R) |
| Position Sizing | Based on ATR volatility |

Entry Conditions:
* List specific conditions that must be met

## 6. Scenario Probability Matrix

| Scenario | Price Target | Probability | Key Drivers |
|----------|-------------|-------------|-------------|
| Bull Case | $X,XXX | XX% | List drivers |
| Base Case | $X,XXX | XX% | List drivers |
| Bear Case | $X,XXX | XX% | List drivers |

## 7. Risk Management
* Key levels to watch
* Trailing stop strategy
* Position adjustment triggers

## 8. Algo Self-Reflection
* Previous call assessment (from memory)
* Lessons learned
* Confidence calibration

---
*Generated by Gold Standard Quant Engine*
"""

    def _extract_bias(self, text: str) -> str:
        """Extract trading bias from AI response using robust parsing."""
        text_upper = text.upper()
        
        bias_patterns = [
            r'\*\*BIAS[:\*\s]*\*?\*?\s*\*?\*?(BULLISH|BEARISH|NEUTRAL)',
            r'BIAS[:\s]+\*?\*?(BULLISH|BEARISH|NEUTRAL)',
            r'\*\*(BULLISH|BEARISH|NEUTRAL)\*\*',
            r'DIRECTION[:\s]+(LONG|SHORT|FLAT)',
        ]
        
        for pattern in bias_patterns:
            match = re.search(pattern, text_upper)
            if match:
                result = match.group(1)
                if result == "LONG":
                    return "BULLISH"
                elif result == "SHORT":
                    return "BEARISH"
                elif result == "FLAT":
                    return "NEUTRAL"
                return result
        
        bullish_count = text_upper.count("BULLISH") + text_upper.count("LONG")
        bearish_count = text_upper.count("BEARISH") + text_upper.count("SHORT")
        neutral_count = text_upper.count("NEUTRAL") + text_upper.count("FLAT")
        
        if bullish_count > bearish_count and bullish_count > neutral_count:
            return "BULLISH"
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            return "BEARISH"
        
        return "NEUTRAL"


# ==========================================
# EXECUTION LOOP
# ==========================================
def execute(config: Config, logger: logging.Logger, model: Optional[Any] = None, dry_run: bool = False, no_ai: bool = False) -> bool:
    """
    Execute one analysis cycle.
    Returns True on success, False on failure.
    """
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
        return False
    
    # Validate gold data exists
    if 'GOLD' not in data:
        logger.error("Gold data missing - aborting cycle")
        return False
    
    gold_price = data['GOLD']['price']
    
    # 2. Grade Past Performance
    last_result = cortex.grade_performance(gold_price)
    logger.info(f"[MEMORY] Last Run Result: {last_result}")
    
    # 3. Update active trades with current prices
    triggered = cortex.update_trade_prices({'GOLD': gold_price})
    for trade in triggered:
        logger.info(f"[TRADE] Auto-closed: #{trade['id']} - {trade.get('exit_reason', 'TRIGGERED')}")
        cortex.close_trade(trade['id'], gold_price, trade.get('exit_reason', 'AUTO'))

    # 4. AI Analysis
    memory_context = cortex.get_formatted_history()
    report = ""
    new_bias = "NEUTRAL"

    if no_ai:
        logger.info("No-AI mode enabled; skipping AI analysis")
        report = "[NO AI MODE] - AI analysis skipped by CLI option."
        new_bias = "NEUTRAL"
    else:
        strat = Strategist(config, logger, data, quant.news, memory_context, model=model, cortex=cortex)
        report, new_bias = strat.think()
    
    # 5. Save Bias to Memory (unless dry-run)
    if not dry_run:
        cortex.update_memory(new_bias, gold_price)
    else:
        logger.info("Dry-run mode: memory not updated")
    
    # Remove any existing today's journal so a fresh one can be created
    try:
        fname = os.path.join(config.OUTPUT_DIR, f"Journal_{datetime.date.today()}.md")
        if os.path.exists(fname):
            os.remove(fname)
            logger.info(f"Deleted previous journal: {fname}")
    except Exception as e:
        logger.warning(f"Failed deleting previous journal: {e}")

    # 6. Write Report
    report_filename = f"Journal_{datetime.date.today()}.md"
    report_path = os.path.join(config.OUTPUT_DIR, report_filename)
    
    if dry_run:
        logger.info(f"Dry-run mode: skipping report write to {report_path}")
        return True

    try:
        # Clean non-ASCII / emoji characters from report before saving
        safe_report = strip_emojis(report)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(safe_report)
            f.write("\n\n---\n\n## Charts\n\n")
            f.write("![Gold](charts/GOLD.png)\n\n")
            f.write("![Silver](charts/SILVER.png)\n\n")
            f.write("![VIX](charts/VIX.png)\n")
        
        logger.info(f"Report generated: {report_path}")
        
        # Save to database for organized storage
        try:
            from db_manager import get_db, JournalEntry
            db = get_db()
            
            # Get silver price and GSR for database
            silver_price = data.get('SILVER', {}).get('price', 0)
            gsr = gold_price / silver_price if silver_price > 0 else 0
            
            entry = JournalEntry(
                date=str(datetime.date.today()),
                content=safe_report,
                bias=new_bias,
                gold_price=gold_price,
                silver_price=silver_price,
                gsr=gsr,
                ai_enabled=not no_ai
            )
            db.save_journal(entry, overwrite=True)
            logger.info(f"[DATABASE] Journal saved for {datetime.date.today()}")
        except ImportError:
            logger.debug("Database module not available, skipping DB save")
        except Exception as db_err:
            logger.warning(f"Failed to save to database: {db_err}")
        
        # Run live analysis if AI enabled (catalysts, institutional matrix, horizon reports)
        if not no_ai and model:
            try:
                from scripts.live_analysis import LiveAnalyzer
                analyzer = LiveAnalyzer(config, logger, model)
                logger.info("[LIVE] Running live analysis suite...")
                
                # Generate all live reports
                reports_generated = analyzer.run_full_analysis(
                    gold_price=gold_price,
                    silver_price=data.get('SILVER', {}).get('price', 0),
                    current_bias=new_bias
                )
                
                for report_name, report_path in reports_generated.items():
                    logger.info(f"[LIVE] Generated: {report_name} -> {report_path}")
                    
            except ImportError as ie:
                logger.debug(f"Live analysis module not available: {ie}")
            except Exception as la_err:
                logger.warning(f"Live analysis failed: {la_err}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error writing report: {e}", exc_info=True)
        return False


def main() -> None:
    """Main entry point with graceful shutdown handling."""
    global shutdown_requested

    # Load environment from .env (optional)
    load_dotenv()
    
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Gold Standard Quant Analysis")
    parser.add_argument('--once', action='store_true', help='Run one cycle and exit')
    parser.add_argument('--dry-run', action='store_true', help='Run without writing memory/report')
    parser.add_argument('--no-ai', action='store_true', help='Do not call AI, produce a skeleton report')
    parser.add_argument('--interval', type=int, default=None, help='Override run interval hours')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    parser.add_argument('--gemini-key', default=None, help='Override GEMINI API key via CLI (not recommended)')
    # Production mode: the tool uses the configured ASSETS in the source code
    args = parser.parse_args()

    # Initialize colorama
    init(autoreset=True)
    
    # Load configuration
    config = Config()
    if args.interval:
        config.RUN_INTERVAL_HOURS = args.interval
    
    # Setup logging
    logger = setup_logging(config)
    # Adjust log level from CLI
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))
    
    # Validate API key unless --no-ai is set
    if not args.no_ai:
        if args.gemini_key:
            config.GEMINI_API_KEY = args.gemini_key
        if not config.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY environment variable not set and no CLI key provided!")
            logger.error("Please set GEMINI_API_KEY environment variable or provide --gemini-key.")
            logger.warning("Example: $env:GEMINI_API_KEY = 'your-api-key-here' or use --gemini-key option")
            sys.exit(1)
    
    # Configure Gemini (unless --no-ai)
    model_obj = None
    if not args.no_ai:
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            model_obj = genai.GenerativeModel(config.GEMINI_MODEL)
            logger.info(f"Gemini AI configured with model: {config.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini AI: {e}")
            sys.exit(1)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("GOLD STANDARD SYSTEM ONLINE")
    logger.info(f"Run interval: {config.RUN_INTERVAL_HOURS} hours")
    logger.info("Press Ctrl+C to shutdown gracefully")
    
    # Execute immediately
    execute(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai)

    # If --once, we exit now
    if args.once:
        logger.info("Run-once mode specified -- exiting")
        return

    # Schedule recurring execution
    schedule.every(config.RUN_INTERVAL_HOURS).hours.do(execute, config, logger, model_obj, args.dry_run, args.no_ai)
    
    # Main loop with graceful shutdown
    while not shutdown_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)
    
    logger.info("Graceful shutdown complete")


if __name__ == "__main__":
    main()
