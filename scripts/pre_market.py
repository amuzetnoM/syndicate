#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Pre-Market Plan Generator
Generates daily pre-market trading plans with strategic bias, risk triggers,
event calendars, and trade management blueprints.
"""

import argparse
import datetime
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
from dotenv import load_dotenv

try:
    from syndicate.utils.env_loader import load_env

    load_env(PROJECT_ROOT / ".env")
except Exception:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


from main import Config, Cortex, QuantEngine, create_llm_provider, setup_logging


def get_week_info() -> Dict[str, Any]:
    """Get current week information."""
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    month_name = today.strftime("%B")
    year = today.year
    weekday = today.strftime("%A")

    return {
        "date": today,
        "weekday": weekday,
        "week_num": week_num,
        "month": month_name,
        "year": year,
        "formatted": today.strftime("%B %d, %Y"),
    }


def build_premarket_prompt(
    config: Config, data: Dict[str, Any], news: List[str], cortex: Cortex, week_info: Dict[str, Any]
) -> str:
    """Build the pre-market plan AI prompt."""

    gold_data = data.get("GOLD", {})
    gold_price = gold_data.get("price", 0)
    gold_atr = gold_data.get("atr", 0) or 0
    _gold_rsi = gold_data.get("rsi", 50)  # Reserved for future RSI-based logic
    gold_adx = gold_data.get("adx", 0)

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
        if key == "RATIOS" or not isinstance(values, dict):
            continue
        price = values.get("price", "N/A")
        change = values.get("change", 0)
        rsi = values.get("rsi", "N/A")
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

    gsr = data.get("RATIOS", {}).get("GSR", "N/A")
    vix = data.get("VIX", {}).get("price", "N/A")

    # Add an explicit canonical values block to prevent fabricated numbers
    canonical_lines = [
        f"* {k}: ${v.get('price', 'N/A')} (change: {v.get('change', 0):+.2f}%)"
        for k, v in data.items()
        if k != "RATIOS" and isinstance(v, dict)
    ]

    canonical_block = "\n".join(canonical_lines)

    safety_instructions = (
        "IMPORTANT: Use ONLY the numeric values explicitly provided below and in 'CURRENT MARKET STATE'. "
        "Do NOT invent, guess, or hallucinate numeric prices. If a value isn't available, write 'N/A'. "
        "If you need to compute levels (support/stop), compute them using the provided prices and show calculations."
    )

    perf_line = f"Performance: {trade_summary['wins']}W / {trade_summary['losses']}L | Win Rate: {trade_summary['win_rate']:.1f}% | Total PnL: ${trade_summary['total_pnl']:.2f}"

    return f"""
You are "Syndicate" - an elite quantitative trading algorithm.
Generate a comprehensive PRE-MARKET PLAN for {week_info['weekday']}, {week_info['formatted']}.

=== CANONICAL VALUES (DO NOT INVENT NUMBERS) ===
{canonical_block}

{safety_instructions}

=== CURRENT MARKET STATE ===
{chr(10).join(data_lines)}

Intermarket:
* Gold/Silver Ratio: {gsr}
* VIX: {vix}
* Current Regime: {regime} (ADX: {gold_adx})

=== ACTIVE POSITIONS ===
{active_trades_text}

{perf_line}

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
| Entry Zone | {support_zone_low:.0f} - {support_zone_high:.0f} | Staggered entry strategy |
| Stop Loss | {suggested_sl:.0f} (2x ATR) | Hard stop, no exceptions |
| Initial Targets | List 2-3 price targets | Partial exit strategy |
| Intraday Notes | Key times/events to watch | Risk reduction before data |

## 5. Key Levels to Watch

* **Immediate Resistance:** $X,XXX
* **Major Resistance:** $X,XXX
* **Immediate Support:** $X,XXX
* **Major Support (Invalidation):** $X,XXX
* **Stop Loss Floor:** {suggested_sl:.0f}

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
*Pre-Market Plan generated by Syndicate*
"""


def generate_premarket(config: Config, logger, model=None, dry_run: bool = False, no_ai: bool = False) -> str:
    """Generate the pre-market plan."""
    logger.info("Generating Pre-Market Plan...")

    # Force AI unless explicitly disabled
    if not no_ai and model is None:
        try:
            model = create_llm_provider(config, logger)
            logger.info("Initialized local LLM provider for Pre-Market generation")
        except Exception as e:
            logger.warning(f"Failed to create LLM provider: {e}")

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
    if "GOLD" in data:
        gold_price = data["GOLD"]["price"]
        triggered = cortex.update_trade_prices({"GOLD": gold_price})
        for trade in triggered:
            cortex.close_trade(trade["id"], gold_price, trade.get("exit_reason", "AUTO"))

    # Build report
    md = []
    filename = f"premarket_{week_info['date']}.md"
    report_path = os.path.join(reports_dir, filename)

    if not no_ai:
        prompt = build_premarket_prompt(config, data, quant.news, cortex, week_info)
        # If async queue enabled, enqueue the task and write a skeleton report immediately
        if os.getenv("LLM_ASYNC_QUEUE", "").lower() in ("1", "true", "yes"):
            logger.info("LLM async queue enabled - enqueuing premarket generation task")
            # write skeleton content placeholder
            skeleton = _generate_skeleton_premarket(data, week_info, cortex)
            md.append(skeleton)
            try:
                from db_manager import get_db

                db = get_db()
                # Use standard provider hint or None to respect global config
                task_id = db.add_llm_task(report_path, prompt, provider_hint=None, task_type="generate")
                logger.info(f"Enqueued LLM task {task_id} for {report_path}")
            except Exception as e:
                logger.warning(f"Failed to enqueue LLM task, falling back to inline generation: {e}")
                # fallback to inline generation
                if model is not None:
                    try:
                        response = model.generate_content(prompt)
                        md[-1] = response.text
                    except Exception as e2:
                        logger.error(f"AI generation failed: {e2}")
                        md[-1] = skeleton
        elif model is not None:
            try:
                # Prefer using the provided model (useful for tests and injected providers)
                try:
                    response = model.generate_content(prompt)
                    generated = getattr(response, "text", None)
                except Exception:
                    generated = None

                # If the provided model did not generate, use global fallback logic
                if not generated:
                    try:
                        provider = create_llm_provider(config, logger)
                        if provider:
                            response = provider.generate_content(prompt)
                            generated = response.text
                    except Exception as ge:
                        logger.error(f"Fallback generation failed for premarket: {ge}")
                        # Fall back to non-AI skeleton to avoid partial/hallucinated content
                        md.append(_generate_skeleton_premarket(data, week_info, cortex))
                        generated = None

                if generated:
                    # Enforce canonical numeric values: replace any incorrect price mentions with canonical data
                    def sanitize_generated(text: str) -> str:
                        import re

                        gold_price = data.get("GOLD", {}).get("price")
                        gold_atr = data.get("GOLD", {}).get("atr") or 0
                        # Support zone calculations used in prompt
                        atr_stop_width = float(gold_atr) * 2 if gold_atr else 0
                        suggested_sl = gold_price - atr_stop_width if gold_price else None
                        support_zone_low = gold_price - (atr_stop_width * 1.5) if gold_price else None
                        support_zone_high = gold_price - atr_stop_width if gold_price else None

                        # Replace explicit 'Current Gold Price' mentions
                        if gold_price is not None:
                            text = re.sub(
                                r"(Current Gold Price:\s*\$)\s*[0-9\.,]+", f"\1{gold_price}", text, flags=re.IGNORECASE
                            )

                            # Replace nearby mentions where gold is referenced with a $<number> if it is off by >5%
                            def fix_match(m):
                                full = m.group(0)
                                num = float(m.group(2).replace(",", "")) if m.group(2) else None
                                if num and abs((num - gold_price) / gold_price) > 0.05:
                                    return m.group(1) + str(gold_price)
                                return full

                            text = re.sub(r"(gold[^\n]{0,40}?\$)([0-9\.,]+)", fix_match, text, flags=re.IGNORECASE)

                        # Replace support/stop placeholders if computed
                        if support_zone_low is not None and support_zone_high is not None and suggested_sl is not None:
                            text = re.sub(r"\$X,XXX|\$X,XXX|\$X,XXX", f"${int(support_zone_low)}", text)

                        # Enforce canonical prices for all known assets to prevent accidental mis-attribution
                        try:

                            def enforce_canonical(text: str) -> str:
                                # For each asset in the data dict, replace nearby $numbers with the canonical price
                                for asset_key, v in data.items():
                                    if not isinstance(v, dict):
                                        continue
                                    asset_price = v.get("price")
                                    if asset_price is None:
                                        continue

                                    # Variants to match in natural language (e.g., 'Yields' -> 'YIELD')
                                    variants = {asset_key, asset_key.lower(), asset_key.title(), asset_key.capitalize()}
                                    if asset_key.upper() == "YIELD":
                                        variants.update({"Yields", "Yield", "YIELD"})

                                    for tok in variants:
                                        # Match constructs like 'DXY ($98.72)' or 'rising Yields ($98.72)'
                                        pattern = re.compile(
                                            rf"({re.escape(tok)}[^\n]{{0,40}}\$)\s*[0-9\.,]+", flags=re.IGNORECASE
                                        )

                                        def _repl(m):
                                            return m.group(1) + f"{asset_price}"

                                        text = pattern.sub(_repl, text)

                                    # As a fallback, also replace explicit 'Asset: $number' patterns where asset key appears
                                    fallback = re.compile(
                                        rf"({re.escape(asset_key)}\s*:\s*\$)\s*[0-9\.,]+", flags=re.IGNORECASE
                                    )

                                    text = fallback.sub(lambda m: m.group(1) + f"{asset_price}", text)

                                return text

                            text = enforce_canonical(text)
                        except Exception:
                            # Non-critical; if enforcement fails, leave text as-is
                            pass

                        return text

                    sanitized = sanitize_generated(generated)
                    md.append(sanitized)
            except Exception as e:
                logger.error(f"AI generation failed: {e}")
                md.append(_generate_skeleton_premarket(data, week_info, cortex))
        else:
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

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Pre-Market Plan written to {report_path}")
    else:
        logger.info(f"[DRY-RUN] Would write to {report_path}")

    return report_path


def _generate_skeleton_premarket(data: Dict[str, Any], week_info: Dict[str, Any], cortex: Cortex) -> str:
    """Generate skeleton pre-market plan without AI."""
    gold_data = data.get("GOLD", {})
    gold_price = gold_data.get("price", "N/A")
    gold_atr = gold_data.get("atr", 0) or 50

    trade_summary = cortex.get_trade_summary()

    # Compute stop loss string safely
    try:
        if gold_price != "N/A":
            stop_loss_val = float(gold_price) - (float(gold_atr) * 2)
            stop_loss_str = f"${stop_loss_val:.0f}"
        else:
            stop_loss_str = "N/A"
    except Exception:
        stop_loss_str = "N/A"

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
| Stop Loss | {stop_loss_str} |

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
    parser.add_argument("--dry-run", action="store_true", help="Do not write files")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI generation")
    parser.add_argument("--gemini-key", default=None, help="Override API key")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    config = Config()
    if args.gemini_key:
        config.GEMINI_API_KEY = args.gemini_key

    logger = setup_logging(config)
    logger.setLevel(getattr(logger, args.log_level.upper(), "INFO"))

    # Configure AI (uses local LLM if available, falls back to Gemini)
    model_obj = None
    if not args.no_ai:
        try:
            model_obj = create_llm_provider(config, logger)
            if model_obj:
                logger.info(f"Using LLM provider: {model_obj.name}")
            else:
                logger.warning("No LLM provider available")
        except Exception as e:
            logger.error(f"Failed to configure LLM: {e}")
            model_obj = None

    generate_premarket(config, logger, model=model_obj, dry_run=args.dry_run, no_ai=args.no_ai)


if __name__ == "__main__":
    main()
