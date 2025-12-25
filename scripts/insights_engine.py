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
Syndicate Insights Engine
Extracts entity insights and action insights from generated reports.
Enables the system to move from "showing" to "doing".

Entity Insights: Named entities of importance (Fed, ECB, CME, central banks, etc.)
Action Insights: Research tasks, data to find, news to investigate, code/math to explore
"""

import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import threading

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================
# DATA CLASSES
# ==========================================


@dataclass
class EntityInsight:
    """Represents an extracted entity from reports."""

    entity_name: str
    entity_type: str  # 'institution', 'indicator', 'asset', 'event', 'person', 'location'
    context: str  # The sentence/context where entity was found
    relevance_score: float  # 0.0 to 1.0
    source_report: str  # Which report it came from
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)


@dataclass
class ActionInsight:
    """Represents an actionable task extracted from reports."""

    action_id: str
    action_type: str  # 'research', 'data_fetch', 'news_scan', 'calculation', 'code_task', 'monitoring'
    title: str
    description: str
    priority: str  # 'critical', 'high', 'medium', 'low'
    status: str = "pending"  # 'pending', 'in_progress', 'completed', 'failed', 'skipped'
    source_report: str = ""
    source_context: str = ""  # The text that triggered this action
    deadline: Optional[str] = None  # ISO timestamp
    scheduled_for: Optional[str] = None  # ISO timestamp - when to execute (None = immediately)
    result: Optional[str] = None  # Output when completed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


# ==========================================
# ENTITY PATTERNS
# ==========================================

# Known entities for pattern matching (expanded list)
KNOWN_ENTITIES = {
    "institutions": [
        "Fed",
        "Federal Reserve",
        "FOMC",
        "ECB",
        "European Central Bank",
        "BOJ",
        "Bank of Japan",
        "BOE",
        "Bank of England",
        "PBOC",
        "People's Bank of China",
        "SNB",
        "Swiss National Bank",
        "RBA",
        "Reserve Bank of Australia",
        "CME",
        "CME Group",
        "COMEX",
        "LBMA",
        "World Gold Council",
        "IMF",
        "BIS",
        "Treasury",
        "US Treasury",
        "Deutsche Bank",
        "Goldman Sachs",
        "JP Morgan",
        "JPMorgan",
        "Bank of America",
        "UBS",
        "Citi",
        "Citigroup",
        "Morgan Stanley",
        "HSBC",
        "Barclays",
        "Credit Suisse",
        "BlackRock",
        "Vanguard",
        "State Street",
        "SPDR",
        "GLD",
        "IAU",
        "SLV",
    ],
    "indicators": [
        "CPI",
        "Consumer Price Index",
        "PPI",
        "Producer Price Index",
        "PCE",
        "Core PCE",
        "NFP",
        "Non-Farm Payrolls",
        "GDP",
        "PMI",
        "ISM",
        "ISM Manufacturing",
        "ISM Services",
        "Unemployment Rate",
        "Jobless Claims",
        "Initial Claims",
        "Retail Sales",
        "Industrial Production",
        "Housing Starts",
        "Consumer Confidence",
        "Michigan Sentiment",
        "JOLTS",
        "ADP",
        "Durable Goods",
        "Trade Balance",
        "Current Account",
        "RSI",
        "ADX",
        "ATR",
        "MACD",
        "Moving Average",
        "SMA",
        "EMA",
        "Bollinger Bands",
        "Fibonacci",
        "Volume",
        "Open Interest",
    ],
    "assets": [
        "Gold",
        "Silver",
        "Platinum",
        "Palladium",
        "Copper",
        "DXY",
        "Dollar Index",
        "USD",
        "EUR",
        "JPY",
        "GBP",
        "CHF",
        "VIX",
        "S&P 500",
        "SPX",
        "SPY",
        "Nasdaq",
        "QQQ",
        "Dow",
        "DJI",
        "Treasury",
        "T-Bill",
        "T-Note",
        "T-Bond",
        "TIPS",
        "10-Year",
        "10Y",
        "2-Year",
        "2Y",
        "30-Year",
        "30Y",
        "Crude Oil",
        "WTI",
        "Brent",
        "Natural Gas",
        "Bitcoin",
        "BTC",
        "Ethereum",
        "ETH",
        "Crypto",
    ],
    "events": [
        "FOMC Meeting",
        "Fed Meeting",
        "Rate Decision",
        "Rate Hike",
        "Rate Cut",
        "Jackson Hole",
        "Davos",
        "G7",
        "G20",
        "ECB Meeting",
        "BOJ Meeting",
        "BOE Meeting",
        "Options Expiration",
        "Quad Witching",
        "Triple Witching",
        "Earnings Season",
        "OpEx",
        "Futures Rollover",
        "Fed Speech",
        "Powell Speech",
        "Lagarde Speech",
        "Testimony",
        "Congressional Testimony",
        "Press Conference",
    ],
    "persons": [
        "Powell",
        "Jerome Powell",
        "Yellen",
        "Janet Yellen",
        "Lagarde",
        "Christine Lagarde",
        "Kuroda",
        "Ueda",
        "Bailey",
        "Waller",
        "Bostic",
        "Daly",
        "Mester",
        "Barkin",
        "Williams",
        "Bowman",
        "Cook",
        "Jefferson",
        "Goolsbee",
    ],
}

# Action trigger patterns
ACTION_PATTERNS = {
    "research": [
        r"(?:need to|should|must|recommend)\s+(?:research|investigate|study|analyze|look into)\s+(.+?)(?:\.|$)",
        r"(?:further|deeper)\s+(?:analysis|research|investigation)\s+(?:on|of|into)\s+(.+?)(?:\.|$)",
        r"(?:monitor|track|watch)\s+(?:closely|carefully)?\s*(.+?)(?:\.|$)",
        r"(?:key|important|critical)\s+(?:to|area)\s+(?:watch|monitor|track)\s*[:\s]+(.+?)(?:\.|$)",
    ],
    "data_fetch": [
        r"(?:check|get|fetch|pull|retrieve)\s+(?:the\s+)?(?:latest|current|recent)?\s*(.+?)\s+(?:data|numbers|figures|stats)",
        r"(?:data|numbers|figures)\s+(?:from|on)\s+(.+?)\s+(?:needed|required|important)",
        r"(?:COT|Commitment of Traders|positioning|flow)\s+data",
        r"(?:ETF|fund)\s+(?:flows?|holdings?)",
    ],
    "news_scan": [
        r"(?:scan|check|monitor)\s+(?:news|headlines?|reports?)\s+(?:on|about|for)\s+(.+?)(?:\.|$)",
        r"(?:breaking|latest|recent)\s+(?:news|developments?|updates?)\s+(?:on|about)\s+(.+?)(?:\.|$)",
        r"(?:geopolitical|political|economic)\s+(?:news|risk|events?)",
    ],
    "calculation": [
        r"(?:calculate|compute|determine|estimate)\s+(.+?)(?:\.|$)",
        r"(?:risk|reward|R:R|risk-reward)\s+(?:ratio|calculation)",
        r"(?:position\s+)?(?:size|sizing)\s+(?:calculation|based on)",
        r"(?:ATR|volatility)-based\s+(?:stops?|targets?|levels?)",
    ],
    "monitoring": [
        r"(?:key|critical|important)\s+levels?\s+(?:to\s+)?(?:watch|monitor)[:\s]+(.+?)(?:\.|$)",
        r"(?:support|resistance)\s+(?:at|around|near)\s+\$?([\d,]+)",
        r"(?:breakout|breakdown)\s+(?:above|below)\s+\$?([\d,]+)",
        r"(?:watch\s+for|look\s+for|alert\s+at)\s+(.+?)(?:\.|$)",
    ],
}


# ==========================================
# INSIGHTS EXTRACTOR
# ==========================================


class InsightsExtractor:
    """
    Extracts entity and action insights from generated reports.
    Powers the transition from passive reporting to active task execution.
    """

    def __init__(self, config, logger: logging.Logger, model=None):
        self.config = config
        self.logger = logger
        self.model = model  # Gemini model for advanced extraction
        self.entity_cache: Dict[str, EntityInsight] = {}
        self.action_queue: List[ActionInsight] = []
        self._action_counter = 0
        self._lock = threading.Lock()

    def _generate_action_id(self) -> str:
        """Generate unique action ID."""
        with self._lock:
            self._action_counter += 1
            return f"ACT-{date.today().strftime('%Y%m%d')}-{self._action_counter:04d}"

    def extract_entities(self, report_content: str, report_name: str) -> List[EntityInsight]:
        """Extract named entities from report content."""
        entities = []

        # Split into sentences for context extraction
        sentences = re.split(r"[.!?]\s+", report_content)

        for entity_type, entity_list in KNOWN_ENTITIES.items():
            for entity in entity_list:
                # Case-insensitive search with word boundaries
                pattern = rf"\b{re.escape(entity)}\b"

                for sentence in sentences:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        # Calculate relevance based on context
                        relevance = self._calculate_entity_relevance(entity, sentence, report_content)

                        # Avoid duplicates
                        entity_key = f"{entity}:{report_name}"
                        if entity_key not in self.entity_cache:
                            insight = EntityInsight(
                                entity_name=entity,
                                entity_type=entity_type.rstrip("s"),  # Remove plural
                                context=sentence.strip()[:500],  # Limit context length
                                relevance_score=relevance,
                                source_report=report_name,
                                metadata={"mentions": 1},
                            )
                            entities.append(insight)
                            self.entity_cache[entity_key] = insight
                        else:
                            # Update mention count
                            self.entity_cache[entity_key].metadata["mentions"] = (
                                self.entity_cache[entity_key].metadata.get("mentions", 1) + 1
                            )

        self.logger.info(f"[INSIGHTS] Extracted {len(entities)} entities from {report_name}")
        return entities

    def _calculate_entity_relevance(self, entity: str, sentence: str, full_content: str) -> float:
        """Calculate relevance score for an entity based on context."""
        score = 0.5  # Base score

        # Boost for entities in headers (##, **bold**)
        if re.search(rf"(?:##.*{re.escape(entity)}|{re.escape(entity)}.*##)", full_content, re.IGNORECASE):
            score += 0.2
        if re.search(rf"\*\*.*{re.escape(entity)}.*\*\*", full_content, re.IGNORECASE):
            score += 0.1

        # Boost for action-related context
        action_keywords = ["watch", "monitor", "key", "critical", "important", "catalyst", "trigger"]
        if any(kw in sentence.lower() for kw in action_keywords):
            score += 0.15

        # Boost for multiple mentions
        mentions = len(re.findall(rf"\b{re.escape(entity)}\b", full_content, re.IGNORECASE))
        score += min(mentions * 0.05, 0.2)  # Cap at 0.2 boost

        return min(score, 1.0)  # Cap at 1.0

    def extract_actions(self, report_content: str, report_name: str) -> List[ActionInsight]:
        """Extract actionable tasks from report content."""
        actions = []

        for action_type, patterns in ACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, report_content, re.IGNORECASE | re.MULTILINE)

                for match in matches:
                    # Get the matched content
                    if match.groups():
                        target = match.group(1).strip() if match.group(1) else match.group(0)
                    else:
                        target = match.group(0)

                    # Clean up the target
                    target = re.sub(r"\s+", " ", target).strip()
                    if len(target) < 5:  # Skip too short matches
                        continue

                    # Find context (surrounding paragraph)
                    context = self._find_context(match.start(), report_content)

                    # Determine priority
                    priority = self._determine_action_priority(target, context)

                    # Extract scheduled date from description/context
                    scheduled_for = self._extract_scheduled_date(target, context)

                    action = ActionInsight(
                        action_id=self._generate_action_id(),
                        action_type=action_type,
                        title=self._generate_action_title(action_type, target),
                        description=f"Auto-extracted from {report_name}: {target}",
                        priority=priority,
                        source_report=report_name,
                        source_context=context[:500],
                        deadline=self._calculate_deadline(priority),
                        scheduled_for=scheduled_for,
                        metadata={"pattern_matched": pattern, "raw_match": match.group(0)[:200]},
                    )
                    actions.append(action)

        # Use AI for advanced extraction if available
        if self.model and len(actions) < 5:
            ai_actions = self._extract_actions_with_ai(report_content, report_name)
            actions.extend(ai_actions)

        # Deduplicate similar actions
        actions = self._deduplicate_actions(actions)

        with self._lock:
            self.action_queue.extend(actions)
        self.logger.info(f"[INSIGHTS] Extracted {len(actions)} actions from {report_name}")
        return actions

    def _find_context(self, position: int, content: str, window: int = 300) -> str:
        """Find surrounding context for a match position."""
        start = max(0, position - window // 2)
        end = min(len(content), position + window // 2)
        return content[start:end].strip()

    def _determine_action_priority(self, target: str, context: str) -> str:
        """Determine priority based on content analysis."""
        combined = f"{target} {context}".lower()

        critical_keywords = ["immediately", "urgent", "critical", "breaking", "flash", "alert"]
        high_keywords = ["important", "key", "significant", "major", "catalyst"]
        medium_keywords = ["monitor", "watch", "track", "consider"]

        if any(kw in combined for kw in critical_keywords):
            return "critical"
        elif any(kw in combined for kw in high_keywords):
            return "high"
        elif any(kw in combined for kw in medium_keywords):
            return "medium"
        return "low"

    def _generate_action_title(self, action_type: str, target: str) -> str:
        """Generate a clean title for the action."""
        # Truncate and clean
        target = target[:100].strip()

        prefixes = {
            "research": "Research:",
            "data_fetch": "Fetch Data:",
            "news_scan": "Scan News:",
            "calculation": "Calculate:",
            "monitoring": "Monitor:",
            "code_task": "Code Task:",
        }

        prefix = prefixes.get(action_type, "Task:")
        return f"{prefix} {target}"

    def _calculate_deadline(self, priority: str) -> str:
        """Calculate deadline based on priority."""
        now = datetime.now()

        if priority == "critical":
            deadline = now + timedelta(minutes=5)
        elif priority == "high":
            deadline = now + timedelta(minutes=30)
        elif priority == "medium":
            deadline = now + timedelta(hours=2)
        else:
            deadline = now + timedelta(hours=4)

        return deadline.isoformat()

    def _extract_scheduled_date(self, description: str, context: str = "") -> Optional[str]:
        """
        Extract a scheduled execution date from task description.

        Looks for patterns like:
        - "Dec 18", "December 18", "Dec 18, 2025"
        - "on December 5-6", "before Dec 18"
        - "January 10", "Jan 29"

        Returns ISO timestamp if a future date is found, None for immediate execution.
        """

        combined = f"{description} {context}"
        now = datetime.now()
        current_year = now.year

        # Month name mappings
        month_names = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }

        # Patterns to match dates
        # "Dec 18", "December 18", "Dec 18, 2025", "December 18th"
        date_patterns = [
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b",
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:,?\s*(\d{4}))?\b",
        ]

        # ISO date pattern: 2025-01-15
        iso_pattern = r"\b(\d{4})-(\d{2})-(\d{2})\b"

        found_dates = []

        # Check ISO dates first
        for match in re.finditer(iso_pattern, combined, re.IGNORECASE):
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    target_date = datetime(year, month, day, 9, 0, 0)
                    if target_date > now:
                        found_dates.append(target_date)
            except (ValueError, IndexError):
                continue

        for pattern in date_patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            for match in matches:
                try:
                    if match[0].isdigit():
                        # Pattern 2: "18 December"
                        day = int(match[0])
                        month = month_names.get(match[1].lower()[:3], 0)
                        year = int(match[2]) if match[2] else current_year
                    else:
                        # Pattern 1: "December 18"
                        month = month_names.get(match[0].lower()[:3], 0)
                        day = int(match[1])
                        year = int(match[2]) if match[2] else current_year

                    if month and 1 <= day <= 31:
                        # Create date, handle year rollover
                        try:
                            target_date = datetime(year, month, day, 9, 0, 0)  # Default to 9 AM

                            # If date is in the past this year, try next year
                            if target_date < now and year == current_year:
                                target_date = datetime(year + 1, month, day, 9, 0, 0)

                            # Only schedule if it's in the future
                            if target_date > now:
                                found_dates.append(target_date)
                        except ValueError:
                            continue  # Invalid date
                except (ValueError, IndexError):
                    continue

        # Return the earliest future date found
        if found_dates:
            earliest = min(found_dates)
            if hasattr(self, "logger") and self.logger:
                self.logger.debug(f"[INSIGHTS] Extracted scheduled date: {earliest.isoformat()}")
            return earliest.isoformat()

        return None  # No date found = execute immediately

    def _deduplicate_actions(self, actions: List[ActionInsight]) -> List[ActionInsight]:
        """Remove duplicate or very similar actions."""
        seen_titles = set()
        unique_actions = []

        for action in actions:
            # Normalize title for comparison
            normalized = action.title.lower().strip()

            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique_actions.append(action)

        return unique_actions

    def _extract_actions_with_ai(self, report_content: str, report_name: str) -> List[ActionInsight]:
        """Use AI to extract additional actionable insights."""
        if not self.model:
            return []

        prompt = f"""Analyze this financial report and extract specific actionable research tasks.
For each task, identify:
1. What needs to be done (research, data gathering, monitoring, calculation)
2. Why it's important
3. Priority (critical/high/medium/low)

Report content:
{report_content[:4000]}

Respond in JSON format:
[
  {{"action_type": "research", "title": "short title", "description": "what to do and why", "priority": "high"}}
]

IMPORTANT: action_type must be exactly ONE of these values (pick the most appropriate):
- "research" - Deep analysis or investigation tasks
- "data_fetch" - Retrieve specific data or prices
- "news_scan" - Monitor news or announcements
- "calculation" - Perform calculations or analysis
- "monitoring" - Set up ongoing monitoring

Extract 3-5 most important actionable tasks. Focus on specific, executable tasks."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON from response
            json_match = re.search(r"\[[\s\S]*\]", response_text)
            if json_match:
                tasks = json.loads(json_match.group())

                # Valid action types
                VALID_ACTION_TYPES = {"research", "data_fetch", "news_scan", "calculation", "monitoring", "code_task"}

                actions = []
                for task in tasks[:5]:  # Limit to 5
                    description = task.get("description", "")
                    title = task.get("title", "AI-extracted task")

                    # Normalize and validate action_type
                    raw_action_type = task.get("action_type", "research")
                    # Handle compound types like "research|monitoring" - take first valid one
                    if "|" in raw_action_type:
                        parts = raw_action_type.split("|")
                        action_type = next((p.strip() for p in parts if p.strip() in VALID_ACTION_TYPES), "research")
                    else:
                        action_type = (
                            raw_action_type.strip() if raw_action_type.strip() in VALID_ACTION_TYPES else "research"
                        )

                    # Extract scheduled date from AI response
                    scheduled_for = self._extract_scheduled_date(description, title)

                    action = ActionInsight(
                        action_id=self._generate_action_id(),
                        action_type=action_type,
                        title=title,
                        description=description,
                        priority=task.get("priority", "medium"),
                        source_report=report_name,
                        source_context="AI-extracted",
                        deadline=self._calculate_deadline(task.get("priority", "medium")),
                        scheduled_for=scheduled_for,
                        metadata={"source": "ai_extraction"},
                    )
                    actions.append(action)

                return actions
        except Exception as e:
            self.logger.warning(f"[INSIGHTS] AI extraction failed: {e}")

        return []

    def process_all_reports(self, reports_dir: Path) -> Tuple[List[EntityInsight], List[ActionInsight]]:
        """Process all reports in a directory."""
        all_entities = []
        all_actions = []

        if not reports_dir.exists():
            self.logger.warning(f"[INSIGHTS] Reports directory not found: {reports_dir}")
            return all_entities, all_actions

        # Process today's reports
        today = date.today().isoformat()

        for report_file in reports_dir.glob(f"*{today}*.md"):
            try:
                content = report_file.read_text(encoding="utf-8")
                report_name = report_file.stem

                entities = self.extract_entities(content, report_name)

                # Optionally enqueue AI-powered insights extraction to the LLM task queue
                if os.getenv("LLM_ASYNC_QUEUE", "").lower() in ("1", "true", "yes"):
                    try:
                        from db_manager import get_db

                        db = get_db()
                        task_id = db.add_llm_task(str(report_file), "", provider_hint=None, task_type="insights")
                        self.logger.info(f"Enqueued insights extraction task {task_id} for {report_file}")
                        actions = []
                    except Exception as e:
                        self.logger.warning(f"Failed to enqueue insights task for {report_file}: {e}")
                        actions = self.extract_actions(content, report_name)
                else:
                    actions = self.extract_actions(content, report_name)

                all_entities.extend(entities)
                all_actions.extend(actions)

            except Exception as e:
                self.logger.error(f"[INSIGHTS] Error processing {report_file}: {e}")

        return all_entities, all_actions

    def get_pending_actions(self, priority_filter: Optional[str] = None) -> List[ActionInsight]:
        """Get pending actions, optionally filtered by priority."""
        pending = [a for a in self.action_queue if a.status == "pending"]

        if priority_filter:
            pending = [a for a in pending if a.priority == priority_filter]

        # Sort by priority (critical first)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        pending.sort(key=lambda a: priority_order.get(a.priority, 4))

        return pending

    def mark_action_complete(self, action_id: str, result: str = None) -> bool:
        """Mark an action as completed."""
        with self._lock:
            for action in self.action_queue:
                if action.action_id == action_id:
                    action.status = "completed"
                    action.completed_at = datetime.now().isoformat()
                    action.result = result
                    self.logger.info(f"[INSIGHTS] Action completed: {action_id}")
                    return True
        return False

    def mark_action_failed(self, action_id: str, reason: str = None) -> bool:
        """Mark an action as failed."""
        with self._lock:
            for action in self.action_queue:
                if action.action_id == action_id:
                    action.status = "failed"
                    action.completed_at = datetime.now().isoformat()
                    action.result = f"FAILED: {reason}" if reason else "FAILED"
                    self.logger.warning(f"[INSIGHTS] Action failed: {action_id} - {reason}")
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Export current state to dictionary."""
        return {
            "entities": [asdict(e) for e in self.entity_cache.values()],
            "actions": [asdict(a) for a in self.action_queue],
            "summary": {
                "total_entities": len(self.entity_cache),
                "total_actions": len(self.action_queue),
                "pending_actions": len([a for a in self.action_queue if a.status == "pending"]),
                "completed_actions": len([a for a in self.action_queue if a.status == "completed"]),
                "extracted_at": datetime.now().isoformat(),
            },
        }


# ==========================================
# STANDALONE TEST
# ==========================================

if __name__ == "__main__":
    # Test with sample report content
    sample_report = """
# Daily Analysis - December 3, 2025

## Market Context

The Fed's upcoming FOMC meeting is critical. Powell's recent comments suggest a hawkish stance.
Monitor the 10Y yield closely - currently at 4.32%.

## Key Levels to Watch

- Support at $4,200 is critical
- Resistance at $4,400 must break for continuation
- Watch for breakout above $4,350

## Action Items

Need to research the ECB's policy trajectory and its impact on EUR/USD.
Check the latest COT data for gold positioning.
Monitor VIX for signs of volatility spike.
Calculate position size based on ATR.

## Institutional View

Goldman Sachs maintains a bullish target of $4,500.
JP Morgan sees risk to the downside near-term.
"""

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("InsightsTest")

    extractor = InsightsExtractor(None, logger)

    entities = extractor.extract_entities(sample_report, "test_report")
    actions = extractor.extract_actions(sample_report, "test_report")

    print("\n=== EXTRACTED ENTITIES ===")
    for e in entities[:10]:
        print(f"  [{e.entity_type}] {e.entity_name} (relevance: {e.relevance_score:.2f})")

    print("\n=== EXTRACTED ACTIONS ===")
    for a in actions:
        print(f"  [{a.priority.upper()}] {a.title}")
        print(f"    Type: {a.action_type}")
        print(f"    Deadline: {a.deadline}")
        print()
