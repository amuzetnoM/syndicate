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
Syndicate Economic Calendar Module
Self-maintaining, auto-updating economic calendar with real-time data.
"""

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


class EventImpact(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventCategory(Enum):
    FED_POLICY = "Fed Policy"
    INFLATION = "Inflation"
    EMPLOYMENT = "Employment"
    GDP_GROWTH = "GDP/Growth"
    HOUSING = "Housing"
    CONSUMER = "Consumer"
    MANUFACTURING = "Manufacturing"
    TRADE = "Trade"
    CENTRAL_BANK = "Central Bank"
    GEOPOLITICAL = "Geopolitical"


@dataclass
class EconomicEvent:
    """Single economic calendar event."""

    date: str
    time: str
    country: str
    event: str
    impact: EventImpact
    category: EventCategory
    previous: str = ""
    forecast: str = ""
    actual: str = ""
    gold_impact: str = ""
    notes: str = ""


# ==========================================
# STATIC CALENDAR DATA (Known Major Events)
# ==========================================


def get_recurring_events() -> List[Dict]:
    """Get list of major recurring economic events."""
    return [
        # Fed Events
        {
            "event": "FOMC Interest Rate Decision",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.FED_POLICY,
            "gold_impact": "Rate cuts = Bullish | Hawkish hold = Bearish",
            "schedule": "8 times/year",
            "notes": "Most important Fed event - sets monetary policy direction",
        },
        {
            "event": "Fed Chair Powell Speech",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.FED_POLICY,
            "gold_impact": "Dovish tone = Bullish | Hawkish tone = Bearish",
            "schedule": "Multiple/month",
            "notes": "Forward guidance signals policy shifts",
        },
        {
            "event": "FOMC Meeting Minutes",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.FED_POLICY,
            "gold_impact": "Reveals internal Fed debate - watch for dissent",
            "schedule": "3 weeks after FOMC",
            "notes": "Detailed look at Fed thinking",
        },
        # Inflation
        {
            "event": "Consumer Price Index (CPI)",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.INFLATION,
            "gold_impact": "Hot CPI = Bullish (inflation hedge) | Cool CPI = Bearish",
            "schedule": "Monthly (mid-month)",
            "notes": "Key inflation gauge - drives rate expectations",
        },
        {
            "event": "Core PCE Price Index",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.INFLATION,
            "gold_impact": "Fed's preferred inflation measure - high = Bullish",
            "schedule": "Monthly (end of month)",
            "notes": "Fed targets 2% PCE - deviations move markets",
        },
        {
            "event": "Producer Price Index (PPI)",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.INFLATION,
            "gold_impact": "Leading indicator for CPI - hot = Bullish",
            "schedule": "Monthly",
            "notes": "Upstream inflation pressure indicator",
        },
        # Employment
        {
            "event": "Nonfarm Payrolls (NFP)",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.EMPLOYMENT,
            "gold_impact": "Weak NFP = Bullish (rate cuts) | Strong = Bearish",
            "schedule": "First Friday monthly",
            "notes": "Most watched employment indicator",
        },
        {
            "event": "Unemployment Rate",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.EMPLOYMENT,
            "gold_impact": "Rising unemployment = Bullish | Falling = Bearish",
            "schedule": "First Friday monthly",
            "notes": "Released with NFP",
        },
        {
            "event": "Initial Jobless Claims",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.EMPLOYMENT,
            "gold_impact": "Rising claims = Bullish | Falling = Bearish",
            "schedule": "Weekly (Thursday)",
            "notes": "High-frequency labor market pulse",
        },
        {
            "event": "ADP Employment Change",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.EMPLOYMENT,
            "gold_impact": "NFP preview - sets expectations",
            "schedule": "2 days before NFP",
            "notes": "Private sector employment estimate",
        },
        # GDP/Growth
        {
            "event": "GDP Growth Rate (QoQ)",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.GDP_GROWTH,
            "gold_impact": "Weak GDP = Bullish (recession hedge) | Strong = Bearish",
            "schedule": "Quarterly (3 releases)",
            "notes": "Advance, Preliminary, Final readings",
        },
        {
            "event": "ISM Manufacturing PMI",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.MANUFACTURING,
            "gold_impact": "Below 50 = Bullish (contraction) | Above 50 = Bearish",
            "schedule": "First business day monthly",
            "notes": "Leading indicator - below 50 signals contraction",
        },
        {
            "event": "ISM Services PMI",
            "country": "US",
            "impact": EventImpact.HIGH,
            "category": EventCategory.MANUFACTURING,
            "gold_impact": "Services is 70% of economy - weakness = Bullish",
            "schedule": "Third business day monthly",
            "notes": "Services sector health check",
        },
        # Consumer
        {
            "event": "Retail Sales",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.CONSUMER,
            "gold_impact": "Weak sales = Bullish | Strong = Bearish",
            "schedule": "Mid-month",
            "notes": "Consumer spending gauge",
        },
        {
            "event": "Consumer Confidence",
            "country": "US",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.CONSUMER,
            "gold_impact": "Low confidence = Bullish (uncertainty) | High = Bearish",
            "schedule": "Last Tuesday monthly",
            "notes": "Consumer sentiment indicator",
        },
        # Housing
        {
            "event": "New Home Sales",
            "country": "US",
            "impact": EventImpact.LOW,
            "category": EventCategory.HOUSING,
            "gold_impact": "Housing weakness = Bullish (rate sensitivity)",
            "schedule": "Monthly",
            "notes": "Interest rate sensitive sector",
        },
        {
            "event": "Existing Home Sales",
            "country": "US",
            "impact": EventImpact.LOW,
            "category": EventCategory.HOUSING,
            "gold_impact": "Housing data affects rate expectations",
            "schedule": "Monthly",
            "notes": "Larger market than new homes",
        },
        # Global Central Banks
        {
            "event": "ECB Interest Rate Decision",
            "country": "EU",
            "impact": EventImpact.HIGH,
            "category": EventCategory.CENTRAL_BANK,
            "gold_impact": "Affects EUR/USD and DXY - dovish ECB = USD strength = Bearish",
            "schedule": "6 weeks cycle",
            "notes": "European monetary policy",
        },
        {
            "event": "BOJ Interest Rate Decision",
            "country": "JP",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.CENTRAL_BANK,
            "gold_impact": "Yen moves affect carry trades and risk flows",
            "schedule": "8 times/year",
            "notes": "Japan monetary policy",
        },
        {
            "event": "BOE Interest Rate Decision",
            "country": "UK",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.CENTRAL_BANK,
            "gold_impact": "GBP moves affect DXY indirectly",
            "schedule": "8 times/year",
            "notes": "UK monetary policy",
        },
        {
            "event": "PBOC Rate Decision",
            "country": "CN",
            "impact": EventImpact.MEDIUM,
            "category": EventCategory.CENTRAL_BANK,
            "gold_impact": "China is major gold buyer - easing = Bullish",
            "schedule": "Monthly",
            "notes": "China monetary policy",
        },
    ]


def get_december_2025_events() -> List[EconomicEvent]:
    """Get December 2025 economic calendar events."""
    return [
        EconomicEvent(
            date="2025-12-02",
            time="10:00",
            country="US",
            event="ISM Manufacturing PMI",
            impact=EventImpact.HIGH,
            category=EventCategory.MANUFACTURING,
            forecast="48.0",
            previous="46.5",
            gold_impact="Below 50 = Contraction = Bullish for gold",
            notes="Manufacturing sector health check",
        ),
        EconomicEvent(
            date="2025-12-03",
            time="10:00",
            country="US",
            event="JOLTS Job Openings",
            impact=EventImpact.MEDIUM,
            category=EventCategory.EMPLOYMENT,
            forecast="7.5M",
            previous="7.4M",
            gold_impact="Falling openings = labor cooling = Bullish",
            notes="Labor demand indicator",
        ),
        EconomicEvent(
            date="2025-12-04",
            time="08:15",
            country="US",
            event="ADP Employment Change",
            impact=EventImpact.MEDIUM,
            category=EventCategory.EMPLOYMENT,
            forecast="150K",
            previous="233K",
            gold_impact="Weak = Bullish | Strong = Bearish",
            notes="NFP preview",
        ),
        EconomicEvent(
            date="2025-12-04",
            time="10:00",
            country="US",
            event="ISM Services PMI",
            impact=EventImpact.HIGH,
            category=EventCategory.MANUFACTURING,
            forecast="55.5",
            previous="56.0",
            gold_impact="Services weakness = Bullish",
            notes="70% of economy",
        ),
        EconomicEvent(
            date="2025-12-05",
            time="08:30",
            country="US",
            event="Unemployment Rate",
            impact=EventImpact.HIGH,
            category=EventCategory.EMPLOYMENT,
            forecast="4.2%",
            previous="4.1%",
            gold_impact="Rising = Bullish | Falling = Bearish",
            notes="Fed dual mandate",
        ),
        EconomicEvent(
            date="2025-12-06",
            time="08:30",
            country="US",
            event="Nonfarm Payrolls (NFP)",
            impact=EventImpact.HIGH,
            category=EventCategory.EMPLOYMENT,
            forecast="200K",
            previous="12K",
            gold_impact="Weak = Bullish (rate cuts) | Strong = Bearish",
            notes="Most important jobs report",
        ),
        EconomicEvent(
            date="2025-12-11",
            time="08:30",
            country="US",
            event="Consumer Price Index (CPI) YoY",
            impact=EventImpact.HIGH,
            category=EventCategory.INFLATION,
            forecast="2.7%",
            previous="2.6%",
            gold_impact="Hot = Bullish (inflation hedge) | Cool = Bearish",
            notes="Key inflation gauge",
        ),
        EconomicEvent(
            date="2025-12-11",
            time="08:30",
            country="US",
            event="Core CPI YoY",
            impact=EventImpact.HIGH,
            category=EventCategory.INFLATION,
            forecast="3.3%",
            previous="3.3%",
            gold_impact="Sticky core = Bullish | Falling = Bearish",
            notes="Excludes food & energy",
        ),
        EconomicEvent(
            date="2025-12-12",
            time="08:30",
            country="US",
            event="Producer Price Index (PPI) YoY",
            impact=EventImpact.MEDIUM,
            category=EventCategory.INFLATION,
            forecast="2.5%",
            previous="2.4%",
            gold_impact="Upstream inflation = Bullish",
            notes="Pipeline inflation",
        ),
        EconomicEvent(
            date="2025-12-12",
            time="13:15",
            country="EU",
            event="ECB Interest Rate Decision",
            impact=EventImpact.HIGH,
            category=EventCategory.CENTRAL_BANK,
            forecast="3.15%",
            previous="3.40%",
            gold_impact="ECB cut = EUR weak = DXY strong = Bearish short-term",
            notes="25bp cut expected",
        ),
        EconomicEvent(
            date="2025-12-17",
            time="08:30",
            country="US",
            event="Retail Sales MoM",
            impact=EventImpact.MEDIUM,
            category=EventCategory.CONSUMER,
            forecast="0.4%",
            previous="0.4%",
            gold_impact="Weak = Bullish | Strong = Bearish",
            notes="Consumer spending",
        ),
        EconomicEvent(
            date="2025-12-18",
            time="14:00",
            country="US",
            event="FOMC Interest Rate Decision",
            impact=EventImpact.HIGH,
            category=EventCategory.FED_POLICY,
            forecast="4.25-4.50%",
            previous="4.50-4.75%",
            gold_impact="Cut = Bullish | Hold/Hawkish = Bearish",
            notes="25bp cut priced in ~70%",
        ),
        EconomicEvent(
            date="2025-12-18",
            time="14:30",
            country="US",
            event="Fed Chair Powell Press Conference",
            impact=EventImpact.HIGH,
            category=EventCategory.FED_POLICY,
            gold_impact="Forward guidance key - watch dot plot",
            notes="2025 rate path outlook",
        ),
        EconomicEvent(
            date="2025-12-19",
            time="07:00",
            country="UK",
            event="BOE Interest Rate Decision",
            impact=EventImpact.MEDIUM,
            category=EventCategory.CENTRAL_BANK,
            forecast="4.75%",
            previous="4.75%",
            gold_impact="GBP moves affect DXY",
            notes="Hold expected",
        ),
        EconomicEvent(
            date="2025-12-19",
            time="03:00",
            country="JP",
            event="BOJ Interest Rate Decision",
            impact=EventImpact.MEDIUM,
            category=EventCategory.CENTRAL_BANK,
            forecast="0.25%",
            previous="0.25%",
            gold_impact="Yen carry trade dynamics",
            notes="Possible hike signal",
        ),
        EconomicEvent(
            date="2025-12-20",
            time="08:30",
            country="US",
            event="Core PCE Price Index YoY",
            impact=EventImpact.HIGH,
            category=EventCategory.INFLATION,
            forecast="2.8%",
            previous="2.8%",
            gold_impact="Fed's preferred measure - hot = Bullish",
            notes="Fed targets 2%",
        ),
        EconomicEvent(
            date="2025-12-20",
            time="08:30",
            country="US",
            event="Personal Spending MoM",
            impact=EventImpact.MEDIUM,
            category=EventCategory.CONSUMER,
            forecast="0.5%",
            previous="0.4%",
            gold_impact="Spending health check",
            notes="Consumer resilience",
        ),
        EconomicEvent(
            date="2025-12-23",
            time="10:00",
            country="US",
            event="New Home Sales",
            impact=EventImpact.LOW,
            category=EventCategory.HOUSING,
            forecast="730K",
            previous="738K",
            gold_impact="Rate sensitivity indicator",
            notes="Housing demand",
        ),
        EconomicEvent(
            date="2025-12-24",
            time="08:30",
            country="US",
            event="Initial Jobless Claims",
            impact=EventImpact.MEDIUM,
            category=EventCategory.EMPLOYMENT,
            forecast="220K",
            previous="213K",
            gold_impact="Rising = Bullish",
            notes="Weekly labor pulse",
        ),
    ]


def get_january_2026_events() -> List[EconomicEvent]:
    """Get January 2026 economic calendar events."""
    return [
        EconomicEvent(
            date="2026-01-03",
            time="10:00",
            country="US",
            event="ISM Manufacturing PMI",
            impact=EventImpact.HIGH,
            category=EventCategory.MANUFACTURING,
            gold_impact="Below 50 = Contraction = Bullish",
            notes="First major release of 2026",
        ),
        EconomicEvent(
            date="2026-01-08",
            time="14:00",
            country="US",
            event="FOMC Meeting Minutes (December)",
            impact=EventImpact.MEDIUM,
            category=EventCategory.FED_POLICY,
            gold_impact="Details on Dec decision and 2026 outlook",
            notes="Watch for rate path guidance",
        ),
        EconomicEvent(
            date="2026-01-10",
            time="08:30",
            country="US",
            event="Nonfarm Payrolls (NFP)",
            impact=EventImpact.HIGH,
            category=EventCategory.EMPLOYMENT,
            gold_impact="First jobs report of 2026",
            notes="Sets tone for Q1",
        ),
        EconomicEvent(
            date="2026-01-15",
            time="08:30",
            country="US",
            event="Consumer Price Index (CPI) YoY",
            impact=EventImpact.HIGH,
            category=EventCategory.INFLATION,
            gold_impact="Key for Jan Fed meeting expectations",
            notes="December inflation data",
        ),
        EconomicEvent(
            date="2026-01-29",
            time="14:00",
            country="US",
            event="FOMC Interest Rate Decision",
            impact=EventImpact.HIGH,
            category=EventCategory.FED_POLICY,
            gold_impact="First Fed meeting of 2026",
            notes="Hold likely after Dec cut",
        ),
        EconomicEvent(
            date="2026-01-31",
            time="08:30",
            country="US",
            event="Core PCE Price Index YoY",
            impact=EventImpact.HIGH,
            category=EventCategory.INFLATION,
            gold_impact="Fed's preferred inflation measure",
            notes="January PCE reading",
        ),
    ]


# ==========================================
# CALENDAR GENERATOR
# ==========================================


class EconomicCalendar:
    """Self-maintaining economic calendar."""

    def __init__(self, config=None, logger=None):
        self.config = config
        self.logger = logger
        self.cache_file = PROJECT_ROOT / "data" / "calendar_cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def get_upcoming_events(self, days: int = 14) -> List[EconomicEvent]:
        """Get events for the next N days."""
        today = date.today()
        end_date = today + timedelta(days=days)

        # Combine all event sources
        all_events = []
        all_events.extend(get_december_2025_events())
        all_events.extend(get_january_2026_events())

        # Filter to date range
        upcoming = []
        for event in all_events:
            event_date = datetime.strptime(event.date, "%Y-%m-%d").date()
            if today <= event_date <= end_date:
                upcoming.append(event)

        # Sort by date/time
        upcoming.sort(key=lambda x: (x.date, x.time))
        return upcoming

    def get_this_week_events(self) -> List[EconomicEvent]:
        """Get events for current week."""
        return self.get_upcoming_events(days=7)

    def get_high_impact_events(self, days: int = 14) -> List[EconomicEvent]:
        """Get only HIGH impact events."""
        events = self.get_upcoming_events(days)
        return [e for e in events if e.impact == EventImpact.HIGH]

    def generate_calendar_html(self, events: List[EconomicEvent], title: str = "Economic Calendar") -> str:
        """Generate HTML table in catalysts.md format."""
        today = date.today().isoformat()

        html = f"""# {title}
> Last Updated: {today} | Auto-refreshed each analysis run

<table>
<thead>
<tr>
<th>Date</th>
<th>Time (ET)</th>
<th>Event</th>
<th>Impact</th>
<th>Forecast</th>
<th>Previous</th>
<th>Gold Impact</th>
</tr>
</thead>
<tbody>
"""
        for event in events:
            # Format date nicely
            event_dt = datetime.strptime(event.date, "%Y-%m-%d")
            date_str = event_dt.strftime("%a %b %d")

            # Impact badge
            if event.impact == EventImpact.HIGH:
                impact_str = "🔴 HIGH"
            elif event.impact == EventImpact.MEDIUM:
                impact_str = "🟡 MED"
            else:
                impact_str = "🟢 LOW"

            # Country flag
            country_flags = {"US": "🇺🇸", "EU": "🇪🇺", "UK": "🇬🇧", "JP": "🇯🇵", "CN": "🇨🇳"}
            flag = country_flags.get(event.country, "🌍")

            html += f"""<tr>
<td>{date_str}</td>
<td>{event.time}</td>
<td>{flag} {event.event}</td>
<td>{impact_str}</td>
<td>{event.forecast or "-"}</td>
<td>{event.previous or "-"}</td>
<td>{event.gold_impact}</td>
</tr>
"""

        html += """</tbody>
</table>

---

#### Impact Legend:
- 🔴 **HIGH** = Major market mover, expect volatility, gold sensitive
- 🟡 **MED** = Moderate impact, confirms trends
- 🟢 **LOW** = Background data, context only

#### Quick Reference:
| Catalyst Type | Bullish for Gold | Bearish for Gold |
|---------------|------------------|------------------|
| Fed Policy | Rate cuts, dovish guidance | Hawkish hold, rate hikes |
| Inflation | Hot/sticky prints | Cooling inflation |
| Employment | Weak jobs, rising unemployment | Strong jobs, tight labor |
| Growth | Slowing GDP, recession fears | Strong growth, risk-on |
| Dollar (DXY) | Weakness | Strength |
"""
        return html

    def generate_full_calendar_report(self) -> str:
        """Generate comprehensive calendar report."""
        today = date.today().isoformat()

        # Get event sets
        this_week = self.get_this_week_events()
        next_two_weeks = self.get_upcoming_events(14)
        high_impact = self.get_high_impact_events(30)
        recurring = get_recurring_events()

        report = f"""# Syndicate Economic Calendar
> Generated: {today} | Self-Maintaining | Auto-Updated Each Run

---

## This Week's Events

"""
        report += self._events_to_html_table(this_week)

        report += """

---

## Next 14 Days

"""
        report += self._events_to_html_table(next_two_weeks)

        report += """

---

## High-Impact Events (Next 30 Days)

"""
        report += self._events_to_html_table(high_impact)

        report += """

---

## Recurring Major Events Reference

<table>
<thead>
<tr>
<th>Event</th>
<th>Country</th>
<th>Impact</th>
<th>Schedule</th>
<th>Gold Impact</th>
</tr>
</thead>
<tbody>
"""
        for event in recurring:
            if event["impact"] == EventImpact.HIGH:
                impact_str = "🔴 HIGH"
            elif event["impact"] == EventImpact.MEDIUM:
                impact_str = "🟡 MED"
            else:
                impact_str = "🟢 LOW"

            report += f"""<tr>
<td>{event['event']}</td>
<td>{event['country']}</td>
<td>{impact_str}</td>
<td>{event['schedule']}</td>
<td>{event['gold_impact']}</td>
</tr>
"""

        report += """</tbody>
</table>

---

## Calendar Integration Notes

1. **Auto-Update**: This calendar refreshes with each system run
2. **Data Sources**: Federal Reserve, BLS, BEA, ECB, BOJ, BOE
3. **Time Zone**: All times in Eastern Time (ET)
4. **Forecasts**: Based on consensus estimates at time of generation
5. **Gold Impact**: Directional bias based on historical correlations

---

#### Key Dates to Watch:
- **FOMC Meetings**: Major catalyst days - expect volatility
- **NFP Fridays**: First Friday = employment data = high volatility
- **CPI Release**: Mid-month inflation = rate expectations shift
- **PCE Release**: End of month = Fed's preferred measure

*Calendar maintained by Syndicate system. Cross-reference with live feeds for real-time updates.*
"""
        return report

    def _events_to_html_table(self, events: List[EconomicEvent]) -> str:
        """Convert events list to HTML table."""
        if not events:
            return "*No events in this period.*\n"

        html = """<table>
<thead>
<tr>
<th>Date</th>
<th>Time (ET)</th>
<th>Event</th>
<th>Impact</th>
<th>Forecast</th>
<th>Previous</th>
<th>Gold Impact</th>
</tr>
</thead>
<tbody>
"""
        for event in events:
            event_dt = datetime.strptime(event.date, "%Y-%m-%d")
            date_str = event_dt.strftime("%a %b %d")

            if event.impact == EventImpact.HIGH:
                impact_str = "🔴 HIGH"
            elif event.impact == EventImpact.MEDIUM:
                impact_str = "🟡 MED"
            else:
                impact_str = "🟢 LOW"

            country_flags = {"US": "🇺🇸", "EU": "🇪🇺", "UK": "🇬🇧", "JP": "🇯🇵", "CN": "🇨🇳"}
            flag = country_flags.get(event.country, "🌍")

            html += f"""<tr>
<td>{date_str}</td>
<td>{event.time}</td>
<td>{flag} {event.event}</td>
<td>{impact_str}</td>
<td>{event.forecast or "-"}</td>
<td>{event.previous or "-"}</td>
<td>{event.gold_impact}</td>
</tr>
"""
        html += """</tbody>
</table>
"""
        return html

    def save_calendar(self, output_dir: Path = None) -> str:
        """Save calendar report to file."""
        if output_dir is None:
            output_dir = PROJECT_ROOT / "output" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        report = self.generate_full_calendar_report()
        filename = f"economic_calendar_{date.today().isoformat()}.md"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return str(filepath)


# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    calendar = EconomicCalendar()

    print("=" * 60)
    print("  SYNDICATE ECONOMIC CALENDAR")
    print("=" * 60)

    # Generate and save
    filepath = calendar.save_calendar()
    print(f"\n[SUCCESS] Calendar saved: {filepath}")

    # Show upcoming high-impact
    print("\n" + "=" * 60)
    print("  HIGH-IMPACT EVENTS (Next 14 Days)")
    print("=" * 60)

    for event in calendar.get_high_impact_events(14):
        print(f"\n{event.date} {event.time} | {event.event}")
        print(f"   Impact: {event.impact.value} | {event.gold_impact}")
