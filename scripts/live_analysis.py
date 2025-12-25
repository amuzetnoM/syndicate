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
Syndicate Live Analysis Module
Generates catalyst watchlist, institutional matrix, and time-horizon reports.
"""

import sys
from datetime import date
from pathlib import Path
from typing import Dict

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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

# Lazy GenAI loader: do not import heavy Google GenAI packages at module import time.
genai = None


def get_genai():
    """Lazily import a GenAI client (legacy `google.generativeai` or compat shim).

    Returns the imported module or None if not available.
    """
    global genai
    if genai is not None:
        return genai
    try:
        import google.generativeai as genai_mod  # type: ignore

        genai = genai_mod
        return genai
    except Exception:
        try:
            from scripts import genai_compat as genai_compat  # type: ignore

            genai = genai_compat
            return genai
        except Exception:
            genai = None
            return None


# ==========================================
# CATALYST WATCHLIST GENERATOR
# ==========================================

CATALYST_CATEGORIES = [
    {
        "id": 1,
        "name": "Fed Policy & Interest Rates",
        "description": "FOMC decisions, rate guidance, Fed speeches",
        "impact": "Direct impact on real yields and USD",
        "bullish_trigger": "Rate cuts, dovish guidance",
        "bearish_trigger": "Hawkish surprise, rate hike signals",
    },
    {
        "id": 2,
        "name": "U.S. Inflation Data",
        "description": "CPI, PPI, PCE, inflation expectations",
        "impact": "Inflation hedge demand for gold",
        "bullish_trigger": "High/sticky inflation prints",
        "bearish_trigger": "Disinflation, cooling prices",
    },
    {
        "id": 3,
        "name": "Employment & Labor Market",
        "description": "NFP, unemployment, wages, claims",
        "impact": "Rate expectations and risk sentiment",
        "bullish_trigger": "Weak jobs, rising unemployment",
        "bearish_trigger": "Strong employment, wage growth",
    },
    {
        "id": 4,
        "name": "GDP & Economic Activity",
        "description": "GDP prints, ISM/PMI, retail sales",
        "impact": "Growth outlook affects risk appetite",
        "bullish_trigger": "Slowing growth, recession fears",
        "bearish_trigger": "Strong growth, risk-on sentiment",
    },
    {
        "id": 5,
        "name": "U.S. Dollar (DXY)",
        "description": "Dollar index, major FX pairs",
        "impact": "Gold priced in USD - inverse correlation",
        "bullish_trigger": "Dollar weakness, depreciation",
        "bearish_trigger": "Dollar strength, safe-haven USD flows",
    },
    {
        "id": 6,
        "name": "Geopolitical Risk Events",
        "description": "Conflicts, crises, political instability",
        "impact": "Safe-haven demand spikes",
        "bullish_trigger": "Escalation, uncertainty spikes",
        "bearish_trigger": "De-escalation, stability returns",
    },
    {
        "id": 7,
        "name": "Central Bank Demand",
        "description": "Reserve purchases, ETF flows, institutional buying",
        "impact": "Structural supply/demand balance",
        "bullish_trigger": "Accelerated CB buying, ETF inflows",
        "bearish_trigger": "Demand slowdown, outflows",
    },
    {
        "id": 8,
        "name": "Global Currency Risks",
        "description": "EM currency stress, fiat debasement",
        "impact": "Global flight to gold",
        "bullish_trigger": "Currency crises, devaluation",
        "bearish_trigger": "Currency stabilization",
    },
    {
        "id": 9,
        "name": "Real Yields & Bond Markets",
        "description": "TIPS yields, treasury rates, credit spreads",
        "impact": "Opportunity cost of holding gold",
        "bullish_trigger": "Low/negative real yields",
        "bearish_trigger": "Rising real yields, bond strength",
    },
    {
        "id": 10,
        "name": "Technical Structure",
        "description": "Support/resistance, breakouts, patterns",
        "impact": "Entry/exit triggers, momentum",
        "bullish_trigger": "Breakout above resistance",
        "bearish_trigger": "Breakdown below support",
    },
    {
        "id": 11,
        "name": "Sentiment & Positioning",
        "description": "COT data, ETF flows, retail/institutional positioning",
        "impact": "Crowd psychology, flow reversals",
        "bullish_trigger": "Bullish sentiment, strong inflows",
        "bearish_trigger": "Complacency, outflows",
    },
]


def generate_catalyst_watchlist(market_data: Dict, ai_analysis: str = "") -> str:
    """Generate a live catalyst watchlist based on current market conditions."""
    today = date.today().isoformat()

    # Build dynamic status based on market data
    gold_price = market_data.get("GOLD", {}).get("price", 0)
    dxy_price = market_data.get("DXY", {}).get("price", 0)
    vix_price = market_data.get("VIX", {}).get("price", 0)
    yield_10y = market_data.get("YIELD", {}).get("price", 0)

    # Determine market conditions
    vix_status = "ELEVATED" if vix_price > 20 else "NORMAL" if vix_price > 15 else "LOW"
    yield_status = "HIGH" if yield_10y > 4.5 else "MODERATE" if yield_10y > 3.5 else "LOW"

    report = f"""# Live Catalyst Watchlist
> Generated: {today} | Gold: ${gold_price:,.2f} | DXY: {dxy_price:.2f} | VIX: {vix_price:.2f} | 10Y: {yield_10y:.2f}%

---

## Market Condition Summary

<table>
<thead>
<tr>
<th>Indicator</th>
<th>Current</th>
<th>Status</th>
<th>Gold Impact</th>
</tr>
</thead>
<tbody>
<tr>
<td>VIX (Volatility)</td>
<td>{vix_price:.2f}</td>
<td>{vix_status}</td>
<td>{"Supportive" if vix_price > 18 else "Neutral"}</td>
</tr>
<tr>
<td>10Y Yield</td>
<td>{yield_10y:.2f}%</td>
<td>{yield_status}</td>
<td>{"Headwind" if yield_10y > 4.5 else "Neutral" if yield_10y > 3.5 else "Tailwind"}</td>
</tr>
<tr>
<td>DXY (Dollar)</td>
<td>{dxy_price:.2f}</td>
<td>{"Strong" if dxy_price > 105 else "Moderate" if dxy_price > 100 else "Weak"}</td>
<td>{"Headwind" if dxy_price > 105 else "Neutral" if dxy_price > 100 else "Tailwind"}</td>
</tr>
</tbody>
</table>

---

## Active Catalyst Matrix

<table>
<thead>
<tr>
<th>#</th>
<th>Event / Data / Catalyst</th>
<th>What to Monitor / Why It Matters for Gold</th>
<th>What Its Impact Could Be (if triggered)</th>
</tr>
</thead>
<tbody>
"""

    for cat in CATALYST_CATEGORIES:
        # Dynamic status based on category
        if cat["id"] == 5:  # DXY
            status = "Dollar Weak" if dxy_price < 102 else "Dollar Strong" if dxy_price > 105 else "Range-Bound"
        elif cat["id"] == 9:  # Yields
            status = f"10Y at {yield_10y:.2f}%"
        elif cat["id"] == 6:  # Geopolitical
            status = "Elevated Uncertainty" if vix_price > 20 else "Moderate" if vix_price > 15 else "Low Risk"
        else:
            status = "Monitoring"

        report += f"""<tr>
<td>{cat['id']}</td>
<td><strong>{cat['name']}</strong><br/><em>{status}</em></td>
<td>{cat['description']}<br/>Bullish: {cat['bullish_trigger']}</td>
<td>Bullish: Price rally, breakout potential<br/>Bearish: {cat['bearish_trigger']} → Pullback risk</td>
</tr>
"""

    report += """</tbody>
</table>

---

## Actionable Notes

<table>
<thead>
<tr>
<th>#</th>
<th>Action Item</th>
<th>Why It Matters</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>Keep economic calendar open</td>
<td>Monitor Fed, CPI, NFP releases in real-time</td>
</tr>
<tr>
<td>2</td>
<td>Watch DXY and real yields</td>
<td>Primary short-term drivers for gold</td>
</tr>
<tr>
<td>3</td>
<td>Track ETF flows</td>
<td>GLD, IAU for institutional sentiment</td>
</tr>
<tr>
<td>4</td>
<td>Geopolitical radar</td>
<td>Any escalation = potential spike trigger</td>
</tr>
<tr>
<td>5</td>
<td>Combine catalysts</td>
<td>Multiple bullish triggers = high-conviction setup</td>
</tr>
</tbody>
</table>

---
*This watchlist updates with each system run. Use alongside technical analysis.*
"""

    return report


# ==========================================
# INSTITUTIONAL MATRIX GENERATOR
# ==========================================

INSTITUTIONAL_FORECASTS = {
    "Deutsche Bank": {"2026_target": 4450, "range_low": 3950, "range_high": 4950, "stance": "Bullish"},
    "Bank of America": {"2026_target": 4800, "range_low": 4200, "range_high": 5000, "stance": "Bullish"},
    "Goldman Sachs": {"2026_target": 4500, "range_low": 4000, "range_high": 4800, "stance": "Neutral-Bullish"},
    "UBS": {"2026_target": 4300, "range_low": 3800, "range_high": 4600, "stance": "Neutral"},
    "JP Morgan": {"2026_target": 4400, "range_low": 3900, "range_high": 4700, "stance": "Neutral-Bullish"},
}


def generate_institutional_matrix(market_data: Dict, current_bias: str = "NEUTRAL") -> str:
    """Generate institutional scenario matrix with current market positioning."""
    today = date.today().isoformat()
    gold_price = market_data.get("GOLD", {}).get("price", 0)

    # Calculate scenario probabilities based on market conditions
    vix = market_data.get("VIX", {}).get("price", 15)
    dxy = market_data.get("DXY", {}).get("price", 103)

    # Adjust probabilities dynamically
    if vix > 25 or dxy < 100:
        bull_prob, base_prob, bear_prob = 35, 45, 20
    elif vix < 15 and dxy > 105:
        bull_prob, base_prob, bear_prob = 20, 45, 35
    else:
        bull_prob, base_prob, bear_prob = 30, 50, 20

    # Calculate consensus
    avg_target = sum(f["2026_target"] for f in INSTITUTIONAL_FORECASTS.values()) / len(INSTITUTIONAL_FORECASTS)

    report = f"""# Institutional Scenario Matrix
> Generated: {today} | Current Gold: ${gold_price:,.2f} | System Bias: {current_bias}

---

## Scenario Probability Framework

<table>
<thead>
<tr>
<th>Scenario</th>
<th>12-Month Target</th>
<th>2026-2027 Range</th>
<th>Probability</th>
<th>Current Alignment</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>🟢 Bull / Extended Run</strong></td>
<td>$4,600 - $5,200</td>
<td>$5,000 - $5,500</td>
<td>~{bull_prob}%</td>
<td>{"✓ ALIGNED" if current_bias == "BULLISH" else "○ Watching"}</td>
</tr>
<tr>
<td><strong>⚪ Base / Structural Bull</strong></td>
<td>$4,200 - $4,600</td>
<td>$4,600 - $4,900</td>
<td>~{base_prob}%</td>
<td>{"✓ ALIGNED" if current_bias == "NEUTRAL" else "○ Watching"}</td>
</tr>
<tr>
<td><strong>🔴 Bear / Correction</strong></td>
<td>$3,800 - $4,100</td>
<td>$3,700 - $4,200</td>
<td>~{bear_prob}%</td>
<td>{"✓ ALIGNED" if current_bias == "BEARISH" else "○ Watching"}</td>
</tr>
</tbody>
</table>

---

## Institutional Forecast Anchors

<table>
<thead>
<tr>
<th>Institution</th>
<th>2026 Target</th>
<th>Trading Range</th>
<th>Stance</th>
<th>vs Current</th>
</tr>
</thead>
<tbody>
"""

    for inst, forecast in INSTITUTIONAL_FORECASTS.items():
        vs_current = ((forecast["2026_target"] - gold_price) / gold_price) * 100
        report += f"""<tr>
<td>{inst}</td>
<td>${forecast['2026_target']:,}</td>
<td>${forecast['range_low']:,} - ${forecast['range_high']:,}</td>
<td>{forecast['stance']}</td>
<td>{vs_current:+.1f}%</td>
</tr>
"""

    report += f"""</tbody>
</table>

**Consensus 2026 Target:** ${avg_target:,.0f}/oz ({((avg_target - gold_price) / gold_price) * 100:+.1f}% from current)

---

## Scenario Detail Matrix

<table>
<thead>
<tr>
<th>Scenario</th>
<th>Price Target</th>
<th>Probability</th>
<th>Key Drivers</th>
<th>Invalidation Triggers</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>🟢 Bull Scenario</strong><br/>(Extended Bullish Run)</td>
<td>$4,600 - $5,200<br/>(spikes to $5,400+)</td>
<td>~{bull_prob}%</td>
<td>Accelerated CB buying, macro stress, flight-to-safety, technical breakout</td>
<td>Yield resurgence, global de-risking, demand saturation, hawkish Fed</td>
</tr>
<tr>
<td><strong>⚪ Base Scenario</strong><br/>(Structural Bull)</td>
<td>$4,200 - $4,600</td>
<td>~{base_prob}%</td>
<td>Persistent CB demand, low real yields, macro hedging, steady accumulation</td>
<td>Hawkish surprise, yield/dollar reversal, risk-on cycle</td>
</tr>
<tr>
<td><strong>🔴 Bear Scenario</strong><br/>(Correction)</td>
<td>$3,800 - $4,100<br/>(dips to $3,600)</td>
<td>~{bear_prob}%</td>
<td>Policy headwinds, risk-on rally, supply/demand shift, technical breakdown</td>
<td>Renewed macro shock, supply disruptions, demand reversal</td>
</tr>
</tbody>
</table>

---

## Strategic Implications

<table>
<thead>
<tr>
<th>#</th>
<th>Implication</th>
<th>Action</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>Gold structurally re-rated higher</td>
<td>Base allocation makes sense as hedge/insurance</td>
</tr>
<tr>
<td>2</td>
<td>Entry discipline essential</td>
<td>Accumulate on dips/consolidation phases</td>
</tr>
<tr>
<td>3</td>
<td>Diversify metals basket</td>
<td>Consider silver, platinum for spread</td>
</tr>
<tr>
<td>4</td>
<td>Monitor macro closely</td>
<td>Maintain dynamic allocation, don't assume linear rally</td>
</tr>
<tr>
<td>5</td>
<td>Risk controls mandatory</td>
<td>Use stops, position sizing, scenario planning</td>
</tr>
</tbody>
</table>

---
*Matrix updated each analysis run. Probabilities are scenario weights, not certainties.*
"""

    return report


# ==========================================
# TIME-HORIZON ANALYSIS (1Y & 3M)
# ==========================================


def generate_1y_analysis(market_data: Dict, ai_analysis: str = "", no_ai: bool = False) -> str:
    """Generate 12-24 month projection report."""
    today = date.today().isoformat()
    gold_price = market_data.get("GOLD", {}).get("price", 0)
    silver_price = market_data.get("SILVER", {}).get("price", 0)
    gsr = gold_price / silver_price if silver_price > 0 else 0

    report = f"""# 1-Year Projection Report
> Generated: {today} | Gold: ${gold_price:,.2f} | Silver: ${silver_price:,.2f} | GSR: {gsr:.2f}

---

## Executive Overview
The 12-24 month outlook for gold is anchored by a **structurally bullish thesis**. Current price of ${gold_price:,.2f}/oz
positions gold {"above" if gold_price > 4000 else "near"} key institutional target ranges.

---

## Scenario Matrix: 12-24 Month Outlook

<table>
<thead>
<tr>
<th>Scenario</th>
<th>12-Month Range</th>
<th>Through 2027</th>
<th>Likelihood</th>
<th>Key Drivers</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Base / Structural Bull</strong></td>
<td>$4,200 - $4,600</td>
<td>$4,600 - $4,900</td>
<td>~50%</td>
<td>CB demand, low real yields, macro hedging</td>
</tr>
<tr>
<td><strong>Bull / Extended Run</strong></td>
<td>$4,600 - $5,200</td>
<td>$5,000 - $5,500</td>
<td>~30%</td>
<td>Macro stress, flight-to-safety, demand surge</td>
</tr>
<tr>
<td><strong>Bear / Correction</strong></td>
<td>$3,800 - $4,100</td>
<td>$3,700 - $4,200</td>
<td>~20%</td>
<td>Hawkish Fed, risk-on rally, demand slowdown</td>
</tr>
</tbody>
</table>

---

## Core Structural Drivers

<table>
<thead>
<tr>
<th>Driver</th>
<th>Description</th>
<th>Gold Impact</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Inelastic Supply vs Rising Demand</strong></td>
<td>Central bank reserve purchases and ETF accumulation absorbing significant annual supply</td>
<td>Creates structural "demand overhang" supporting higher long-term price floor</td>
</tr>
<tr>
<td><strong>Supportive Macro Environment</strong></td>
<td>Low-to-negative real yields, persistent inflation concerns, currency debasement risk, sovereign debt fears</td>
<td>Multiple tailwinds reinforcing gold's appeal as hedge</td>
</tr>
<tr>
<td><strong>Institutional Re-rating</strong></td>
<td>Pension funds and sovereign wealth funds re-evaluating gold as necessary "insurance asset"</td>
<td>Durable inflows from long-term allocators</td>
</tr>
<tr>
<td><strong>Volatility as Upside Catalyst</strong></td>
<td>Tight supply-demand balance means any macro shock triggers outsized price response</td>
<td>Asymmetric upside on crisis events</td>
</tr>
</tbody>
</table>

---

## Key Risks to Monitor

<table>
<thead>
<tr>
<th>#</th>
<th>Risk Factor</th>
<th>Impact on Gold</th>
<th>Probability</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>Hawkish Policy Surprise</td>
<td>Fed remains aggressive longer than expected - bearish</td>
<td>Medium</td>
</tr>
<tr>
<td>2</td>
<td>Dollar/Yield Surge</td>
<td>Significant rise in real yields reduces gold appeal - bearish</td>
<td>Low-Medium</td>
</tr>
<tr>
<td>3</td>
<td>Risk-On Rotation</td>
<td>Strong equity rally diminishes safe-haven demand - bearish</td>
<td>Medium</td>
</tr>
<tr>
<td>4</td>
<td>Demand Saturation</td>
<td>CB buying pauses, ETF flows reverse - bearish</td>
<td>Low</td>
</tr>
</tbody>
</table>

---

## Current Price vs Scenarios

<table>
<thead>
<tr>
<th>Scenario</th>
<th>Target Midpoint</th>
<th>vs Current</th>
<th>Assessment</th>
</tr>
</thead>
<tbody>
<tr>
<td>Base Case</td>
<td>$4,400</td>
<td>{((4400 - gold_price) / gold_price) * 100:+.1f}%</td>
<td>{"On Track" if gold_price > 4000 else "Room to Run"}</td>
</tr>
<tr>
<td>Bull Case</td>
<td>$4,900</td>
<td>{((4900 - gold_price) / gold_price) * 100:+.1f}%</td>
<td>Requires catalysts</td>
</tr>
<tr>
<td>Bear Case</td>
<td>$3,950</td>
<td>{((3950 - gold_price) / gold_price) * 100:+.1f}%</td>
<td>Risk scenario</td>
</tr>
</tbody>
</table>

---
*Report generated by Syndicate system. Review with current market conditions.*
"""

    return report


def generate_3m_analysis(market_data: Dict, ai_analysis: str = "", no_ai: bool = False) -> str:
    """Generate 1-3 month tactical analysis."""
    today = date.today().isoformat()
    gold_price = market_data.get("GOLD", {}).get("price", 0)
    dxy = market_data.get("DXY", {}).get("price", 103)
    vix = market_data.get("VIX", {}).get("price", 15)
    yield_10y = market_data.get("YIELD", {}).get("price", 4.0)

    # Determine tactical bias
    bullish_factors = 0
    if dxy < 103:
        bullish_factors += 1
    if vix > 18:
        bullish_factors += 1
    if yield_10y < 4.0:
        bullish_factors += 1

    tactical_bias = "BULLISH" if bullish_factors >= 2 else "BEARISH" if bullish_factors == 0 else "NEUTRAL"

    report = f"""# 3-Month Tactical Analysis
> Generated: {today} | Gold: ${gold_price:,.2f} | DXY: {dxy:.2f} | VIX: {vix:.2f} | 10Y: {yield_10y:.2f}%

---

## Executive Summary
The near-term outlook (1-3 months) is **{tactical_bias}**. Current conditions suggest:
- Dollar: {"Supportive" if dxy < 103 else "Headwind" if dxy > 105 else "Neutral"}
- Volatility: {"Elevated (Supportive)" if vix > 20 else "Normal" if vix > 15 else "Low (Risk-On)"}
- Yields: {"Tailwind" if yield_10y < 3.5 else "Headwind" if yield_10y > 4.5 else "Neutral"}

---

## Scenario Matrix: 1-3 Month Outlook

<table>
<thead>
<tr>
<th>Scenario</th>
<th>Price Band</th>
<th>Probability</th>
<th>Key Assumptions</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Bull / Breakout</strong></td>
<td>$4,400 - $4,650</td>
<td>~30%</td>
<td>Dovish Fed, weak dollar, macro stress</td>
</tr>
<tr>
<td><strong>Base / Consolidation</strong></td>
<td>$4,250 - $4,400</td>
<td>~50%</td>
<td>Neutral Fed, range-bound dollar</td>
</tr>
<tr>
<td><strong>Bear / Pullback</strong></td>
<td>$4,000 - $4,150</td>
<td>~20%</td>
<td>Hawkish surprise, dollar strength</td>
</tr>
</tbody>
</table>

---

## Current Condition Assessment

<table>
<thead>
<tr>
<th>Factor</th>
<th>Reading</th>
<th>Impact</th>
<th>Score</th>
</tr>
</thead>
<tbody>
<tr>
<td>DXY (Dollar)</td>
<td>{dxy:.2f}</td>
<td>{"Bullish" if dxy < 103 else "Bearish" if dxy > 105 else "Neutral"}</td>
<td>{"🟢" if dxy < 103 else "🔴" if dxy > 105 else "⚪"}</td>
</tr>
<tr>
<td>VIX (Volatility)</td>
<td>{vix:.2f}</td>
<td>{"Bullish" if vix > 18 else "Bearish" if vix < 12 else "Neutral"}</td>
<td>{"🟢" if vix > 18 else "🔴" if vix < 12 else "⚪"}</td>
</tr>
<tr>
<td>10Y Yield</td>
<td>{yield_10y:.2f}%</td>
<td>{"Bullish" if yield_10y < 3.5 else "Bearish" if yield_10y > 4.5 else "Neutral"}</td>
<td>{"🟢" if yield_10y < 3.5 else "🔴" if yield_10y > 4.5 else "⚪"}</td>
</tr>
</tbody>
</table>

**Aggregate Score:** {bullish_factors}/3 Bullish Factors → **{tactical_bias}**

---

## Key Catalysts Next 4-12 Weeks

<table>
<thead>
<tr>
<th>#</th>
<th>Catalyst</th>
<th>Why It Matters</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>Fed Communications</td>
<td>FOMC minutes, speeches, rate decisions shape expectations</td>
</tr>
<tr>
<td>2</td>
<td>Inflation Data</td>
<td>CPI, PCE prints critical for rate expectations</td>
</tr>
<tr>
<td>3</td>
<td>Employment Reports</td>
<td>NFP, unemployment influencing Fed path</td>
</tr>
<tr>
<td>4</td>
<td>Dollar Direction</td>
<td>DXY trend confirmation or reversal</td>
</tr>
<tr>
<td>5</td>
<td>Geopolitical Events</td>
<td>Any escalation = spike potential</td>
</tr>
</tbody>
</table>

---

## Tactical Positioning

<table>
<thead>
<tr>
<th>Condition</th>
<th>Strategy</th>
<th>Risk Level</th>
</tr>
</thead>
<tbody>
<tr>
<td>Breakout above $4,400</td>
<td>Add on confirmation</td>
<td>Medium</td>
</tr>
<tr>
<td>Consolidation $4,250-$4,400</td>
<td>Range trade, accumulate dips</td>
<td>Low</td>
</tr>
<tr>
<td>Breakdown below $4,200</td>
<td>Reduce, wait for support</td>
<td>High</td>
</tr>
</tbody>
</table>

---

## Support & Resistance Levels

<table>
<thead>
<tr>
<th>Level</th>
<th>Price</th>
<th>Significance</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>R3</strong></td>
<td>$4,600</td>
<td>Major psychological</td>
</tr>
<tr>
<td><strong>R2</strong></td>
<td>$4,450</td>
<td>Institutional target</td>
</tr>
<tr>
<td><strong>R1</strong></td>
<td>$4,350</td>
<td>Near-term resistance</td>
</tr>
<tr>
<td><strong>Current</strong></td>
<td>${gold_price:,.2f}</td>
<td>—</td>
</tr>
<tr>
<td><strong>S1</strong></td>
<td>$4,200</td>
<td>Near-term support</td>
</tr>
<tr>
<td><strong>S2</strong></td>
<td>$4,100</td>
<td>Key support zone</td>
</tr>
<tr>
<td><strong>S3</strong></td>
<td>$4,000</td>
<td>Major psychological</td>
</tr>
</tbody>
</table>

---
*Tactical analysis for short-term positioning. Combine with longer-term thesis.*
"""

    return report


def generate_all_reports(market_data: Dict, current_bias: str = "NEUTRAL", no_ai: bool = False) -> Dict[str, str]:
    """Generate all analysis reports."""
    return {
        "catalyst_watchlist": generate_catalyst_watchlist(market_data),
        "institutional_matrix": generate_institutional_matrix(market_data, current_bias),
        "1y_analysis": generate_1y_analysis(market_data, no_ai=no_ai),
        "3m_analysis": generate_3m_analysis(market_data, no_ai=no_ai),
    }


# ==========================================
# LIVE ANALYZER CLASS (for main.py integration)
# ==========================================


class LiveAnalyzer:
    """Wrapper class for live analysis integration with main system."""

    def __init__(self, config, logger, model=None):
        self.config = config
        self.logger = logger
        self.model = model
        self.output_dir = Path(config.OUTPUT_DIR) / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_full_analysis(
        self, gold_price: float = 0, silver_price: float = 0, current_bias: str = "NEUTRAL"
    ) -> Dict[str, str]:
        """Run all analysis and save to files. Returns dict of report name -> file path."""
        # Build market data dict
        market_data = {
            "GOLD": {"price": gold_price},
            "SILVER": {"price": silver_price},
            "DXY": {"price": 103.0},  # Will be enhanced with real data
            "VIX": {"price": 17.0},
            "YIELD": {"price": 4.3},
        }

        # Generate all reports
        reports = generate_all_reports(market_data, current_bias)

        # Generate economic calendar
        try:
            from scripts.economic_calendar import EconomicCalendar

            calendar = EconomicCalendar(self.config, self.logger)
            reports["economic_calendar"] = calendar.generate_full_calendar_report()
        except ImportError:
            try:
                from economic_calendar import EconomicCalendar

                calendar = EconomicCalendar(self.config, self.logger)
                reports["economic_calendar"] = calendar.generate_full_calendar_report()
            except ImportError:
                self.logger.debug("Economic calendar module not available")

        # Save to files
        saved_reports = {}
        today = date.today().isoformat()

        file_mapping = {
            "catalyst_watchlist": f"catalysts_{today}.md",
            "institutional_matrix": f"inst_matrix_{today}.md",
            "1y_analysis": f"1y_{today}.md",
            "3m_analysis": f"3m_{today}.md",
            "economic_calendar": f"economic_calendar_{today}.md",
        }

        # Type mapping for frontmatter (reserved for future use)
        _type_mapping = {
            "catalyst_watchlist": "research",
            "institutional_matrix": "insights",
            "1y_analysis": "reports",
            "3m_analysis": "reports",
            "economic_calendar": "articles",
        }

        for report_name, content in reports.items():
            filename = file_mapping.get(report_name, f"{report_name}_{today}.md")
            filepath = self.output_dir / filename

            try:
                # Note: Frontmatter is applied as FINAL step in run.py
                # after all file organization is complete

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_reports[report_name] = str(filepath)
                self.logger.info(f"[LIVE] Saved {report_name}: {filepath}")
            except Exception as e:
                self.logger.error(f"[LIVE] Failed to save {report_name}: {e}")

        return saved_reports


if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        "GOLD": {"price": 4218.30},
        "SILVER": {"price": 56.43},
        "DXY": {"price": 103.25},
        "VIX": {"price": 17.5},
        "YIELD": {"price": 4.32},
    }

    reports = generate_all_reports(sample_data, "NEUTRAL")

    print("Generated Reports:")
    for name, content in reports.items():
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        print(content[:500] + "...")
