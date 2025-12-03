#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__            
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____   
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \  
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/ 
#
# Gold Standard - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Pre-Market Plan Generator
Generates daily pre-market trading plans with strategic bias, risk triggers,
event calendars, and trade management blueprints.
"""
import os
import sys
import argparse
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import Config, setup_logging, Cortex, QuantEngine, Strategist, ASSETS
import google.generativeai as genai


def get_week_info() -> Dict[str, Any]:
    """Get current week information."""
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    month_name = today.strftime('%B')
    year = today.year
    weekday = today.strftime('%A')
    
    return {
        'date': today,
        'weekday': weekday,
        'week_num': week_num,
        'month': month_name,
        'year': year,
        'formatted': today.strftime('%B %d, %Y')
    }


def build_premarket_prompt(
    config: Config,
    data: Dict[str, Any],
    news: List[str],
    cortex: Cortex,
    week_info: Dict[str, Any]
) -> str:
    """Build the pre-market plan AI prompt."""
    
    gold_data = data.get('GOLD', {})
    gold_price = gold_data.get('price', 0)
    gold_atr = gold_data.get('atr', 0) or 0
    gold_rsi = gold_data.get('rsi', 50)
    gold_adx = gold_data.get('adx', 0)
    
    # Calculate key levels
    atr_stop_width = float(gold_atr) * 2
    suggested_sl = gold_price - atr_stop_width if gold_price else 0
    support_zone_low = gold_price - (atr_stop_width * 1.5) if gold_price else 0
    support_zone_high = gold_price - atr_stop_width if gold_price else 0
    
    # Get regime
    regime = "TRENDING" if gold_adx and gold_adx > config.ADX_TREND_THRESHOLD else "RANGE-BOUND"
    
    # Format data summary
    data_lines = []
    for key, values in data.items():
        if key == 'RATIOS' or not isinstance(values, dict):
            continue
        price = values.get('price', 'N/A')
        change = values.get('change', 0)
        rsi = values.get('rsi', 'N/A')
        data_lines.append(f"* {key}: ${price} ({change:+.2f}%) | RSI: {rsi}")
    
    # Get trade summary
    trade_summary = cortex.get_trade_summary()
    active_trades = cortex.get_active_trades()
    
    active_trades_text = "No active positions."
    if active_trades:
        lines = []
        for t in active_trades:
            lines.append(
                f"* #{t['id']} {t['direction']} @ ${t['entry_price']:.2f} | "
                f"SL: ${t['stop_loss']:.2f} | Unrealized: ${t.get('unrealized_pnl', 0):.2f}"
            )
        active_trades_text = "\n".join(lines)
    
    gsr = data.get('RATIOS', {}).get('GSR', 'N/A')
    vix = data.get('VIX', {}).get('price', 'N/A')
    
    return f"""
You are "Gold Standard" - an elite quantitative trading algorithm.
Generate a comprehensive PRE-MARKET PLAN for {week_info['weekday']}, {week_info['formatted']}.

=== CURRENT MARKET STATE ===
{chr(10).join(data_lines)}

Intermarket:
* Gold/Silver Ratio: {gsr}
* VIX: {vix}
* Current Regime: {regime} (ADX: {gold_adx})

=== ACTIVE POSITIONS ===
{active_trades_text}

Performance: {trade_summary['wins']}W / {trade_summary['losses']}L | Win Rate: {trade_summary['win_rate']:.1f}% | Total PnL: ${trade_summary['total_pnl']:.2f}

=== RECENT NEWS ===
{chr(10).join(['* ' + n for n in news[:5]]) if news else "No significant headlines."}

=== GENERATE PRE-MARKET PLAN ===

# Pre-Market Plan
## Week {week_info['week_num']}, {week_info['month']} {week_info['year']}
### {week_info['weekday']}, {week_info['formatted']}

---

## 1. Strategic Bias
* **Overall Bias:** [BULLISH / BEARISH / NEUTRAL] - Accumulate on Dips / Fade Rallies / Stay Flat
* **Rationale:** Brief explanation of the current macro setup
* **Target Continuation:** Next price target based on institutional forecasts

## 2. Key Risk & Invalidation Triggers

Provide a table:
| Metric | Bullish Outcome (Action: Accumulate/Hold) | Bearish Outcome (Action: Risk Reduction) |
|--------|-------------------------------------------|------------------------------------------|
| Economic Data | What would be bullish | What would be bearish |
| Fed/Central Bank | Dovish signals | Hawkish signals |
| DXY/Yields | Dollar weakness | Dollar strength |
| Gold Price | Key support levels to hold | Key breakdown levels |

## 3. Critical Events Calendar

List any known economic events for today/this week:
| Date | Time (ET) | Event | Relevance to Gold Thesis |
|------|-----------|-------|--------------------------|
| ... | ... | ... | ... |

(If no specific events known, note that and suggest monitoring economic calendars)

## 4. Trade Management Blueprint

| Component | Trade Idea | Risk Management |
|-----------|------------|-----------------|
| Direction | LONG / SHORT / FLAT | Entry discipline notes |
| Entry Zone | ${support_zone_low:.0f} - ${support_zone_high:.0f} | Staggered entry strategy |
| Stop Loss | ${suggested_sl:.0f} (2x ATR) | Hard stop, no exceptions |
| Initial Targets | List 2-3 price targets | Partial exit strategy |
| Intraday Notes | Key times/events to watch | Risk reduction before data |

## 5. Key Levels to Watch

* **Immediate Resistance:** $X,XXX
* **Major Resistance:** $X,XXX
* **Immediate Support:** $X,XXX
* **Major Support (Invalidation):** $X,XXX
* **Stop Loss Floor:** ${suggested_sl:.0f}

## 6. Session Strategy

Provide specific guidance for:
* **Asian Session:** Expectations and key levels
* **London Session:** Key windows and potential moves
* **NY Session:** Data releases and volatility windows

## 7. Contingency Plans

* **If bullish thesis plays out:** Trailing stop strategy, target extensions
* **If bearish reversal occurs:** When to cut, when to add to short
* **If choppy/range-bound:** Avoid overtrading, wait for clarity

---
*Pre-Market Plan generated by Gold Standard*
"""


def generate_premarket(
    config: Config,
    logger,
    model=None,
    dry_run: bool = False,
    no_ai: bool = False
) -> str:
    """Generate the pre-market plan."""
    logger.info("Generating Pre-Market Plan...")
    
    week_info = get_week_info()
    reports_dir = os.path.join(config.OUTPUT_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    # Initialize components
    cortex = Cortex(config, logger)
    quant = QuantEngine(config, logger)
    
    # Fetch data
    data = quant.get_data()
    if not data:
        logger.warning("Data fetch failed - generating skeleton report")
        data = {}
    
    # Update trade prices
    if 'GOLD' in data:
        gold_price = data['GOLD']['price']
        triggered = cortex.update_trade_prices({'GOLD': gold_price})
        for trade in triggered:
            cortex.close_trade(trade['id'], gold_price, trade.get('exit_reason', 'AUTO'))
    
    # Build report
    md = []
    filename = f"premarket_{week_info['date']}.md"
    report_path = os.path.join(reports_dir, filename)
    
    if not no_ai and model is not None:
        prompt = build_premarket_prompt(config, data, quant.news, cortex, week_info)
        try:
            response = model.generate_content(prompt)
            md.append(response.text)
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            md.append(_generate_skeleton_premarket(data, week_info, cortex))
    else:
        md.append(_generate_skeleton_premarket(data, week_info, cortex))
    
    # Add charts reference
    md.append("\n\n---\n\n## Reference Charts\n")
    md.append("![Gold](../charts/GOLD.png)\n")
    md.append("![DXY](../charts/DXY.png)\n")
    
    if not dry_run:
        content = "\n".join(md)
        
        # Note: Frontmatter is applied as FINAL step in run.py
        # after all file organization is complete
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Pre-Market Plan written to {report_path}")
    else:
        logger.info(f"[DRY-RUN] Would write to {report_path}")
    
    return report_path


def _generate_skeleton_premarket(
    data: Dict[str, Any],
    week_info: Dict[str, Any],
    cortex: Cortex
) -> str:
    """Generate skeleton pre-market plan without AI."""
    gold_data = data.get('GOLD', {})
    gold_price = gold_data.get('price', 'N/A')
    gold_atr = gold_data.get('atr', 0) or 50
    
    trade_summary = cortex.get_trade_summary()
    
    return f"""# Pre-Market Plan
## Week {week_info['week_num']}, {week_info['month']} {week_info['year']}
### {week_info['weekday']}, {week_info['formatted']}

---

## 1. Strategic Bias
* **Overall Bias:** [PENDING AI ANALYSIS]
* **Current Gold Price:** ${gold_price}
* **ATR (14):** ${gold_atr:.2f}

## 2. Key Risk & Invalidation Triggers

| Metric | Bullish Outcome | Bearish Outcome |
|--------|-----------------|-----------------|
| Economic Data | Below consensus | Above consensus |
| Fed Speak | Dovish tone | Hawkish tone |
| DXY/Yields | Weakness | Strength |
| Gold Price | Holds support | Breaks support |

## 3. Trade Management Blueprint

| Component | Specification |
|-----------|---------------|
| Direction | [PENDING] |
| Entry Zone | [Calculate from ATR] |
| Stop Loss | ${float(gold_price) - (float(gold_atr) * 2) if gold_price != 'N/A' else 'N/A':.0f} |

## 4. Performance Summary

* Wins: {trade_summary['wins']}
* Losses: {trade_summary['losses']}
* Win Rate: {trade_summary['win_rate']:.1f}%
* Total PnL: ${trade_summary['total_pnl']:.2f}
* Active Positions: {trade_summary['active_positions']}

---

*[NO AI MODE] - Run with AI enabled for full analysis*
"""


def main():
    parser = argparse.ArgumentParser(description="Pre-Market Plan Generator")
    parser.add_argument('--dry-run', action='store_true', help='Do not write files')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI generation')
    parser.add_argument('--gemini-key', default=None, help='Override API key')
    parser.add_argument('--log-level', default='INFO')
    args = parser.parse_args()
    
    config = Config()
    if args.gemini_key:
        config.GEMINI_API_KEY = args.gemini_key
    
    logger = setup_logging(config)
    logger.setLevel(getattr(logger, args.log_level.upper(), 'INFO'))
    
    # Configure AI
    model_obj = None
    if not args.no_ai:
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            model_obj = genai.GenerativeModel(config.GEMINI_MODEL)
            logger.info(f"Configured Gemini model: {config.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            model_obj = None
    
    generate_premarket(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai)


if __name__ == '__main__':
    main()
