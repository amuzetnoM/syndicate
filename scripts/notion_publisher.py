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
Notion Publisher for Syndicate
Python-based publisher that syncs reports to Notion database.
Includes intelligent deduplication to prevent publishing the same content multiple times.
"""

import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List
import logging
import random

# Add parent to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from notion_client import Client

    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    # Provide a placeholder Client attribute so tests can monkeypatch this module
    Client = None
    print("notion-client not installed. Run: pip install notion-client")

try:
    from syndicate.utils.env_loader import load_env

    load_env(PROJECT_ROOT / ".env")
except Exception:
    # Fallback to python-dotenv if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
# Global env toggle to disable wet Notion publishes for safe testing
_DISABLE_NOTION_PUBLISH = str(os.getenv("DISABLE_NOTION_PUBLISH", "0")).lower() in ("1", "true", "yes")
import hashlib
from filelock import FileLock
import html

# Import database manager for sync tracking
try:
    from db_manager import get_db

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


# Document type mapping - comprehensive coverage
NOTION_TYPES = [
    "journal",
    "research",
    "reports",
    "insights",
    "articles",
    "notes",
    "announcements",
    "charts",
    "economic",
    "institutional",
    "Pre-Market",
    "analysis",
]

# Files and filename substrings to always ignore from Notion sync (case-insensitive)
IGNORE_PATTERNS = [
    "monitor_",
    "data_fetch_",
    "digest_",
    "digests/",
    "_act-",
    "act-",
    "FILE_INDEX",
]

# File pattern to Notion type mapping - ORDER MATTERS (first match wins)
TYPE_PATTERNS = [
    # Journals (daily)
    (r"^Journal_", "journal"),
    (r"^journal_", "journal"),
    (r"^daily_", "journal"),
    # Pre-market plans
    (r"^premarket_", "Pre-Market"),
    (r"^pre_market_", "Pre-Market"),
    (r"^pre-market", "Pre-Market"),
    # Periodic reports
    (r"^weekly_", "reports"),
    (r"^monthly_", "reports"),
    (r"^yearly_", "reports"),
    (r"^1y_", "reports"),
    (r"^3m_", "reports"),
    (r"^rundown_", "reports"),
    (r"_report", "reports"),
    # Analysis
    (r"^analysis_", "analysis"),
    (r"^horizon_", "analysis"),
    (r"^technical_", "analysis"),
    # Catalysts & Research
    (r"^catalyst", "research"),
    (r"^watchlist", "research"),
    (r"^research_", "research"),
    (r"^calc_", "research"),
    (r"^code_", "research"),
    (r"^data_fetch", "research"),
    (r"^monitor_", "research"),
    (r"^news_scan", "research"),
    # Economic calendar
    (r"^economic_", "economic"),
    (r"^calendar_", "economic"),
    (r"^events_", "economic"),
    # Institutional / Insights
    (r"^inst_matrix", "institutional"),
    (r"^institutional", "institutional"),
    (r"^scenario", "institutional"),
    (r"^entity_insights", "insights"),
    (r"^action_insights", "insights"),
    (r"^insights_", "insights"),
    # Notes & Memos
    (r"^notes_", "notes"),
    (r"^memo_", "notes"),
    # Alerts & Announcements
    (r"^announcement", "announcements"),
    (r"^alert_", "announcements"),
    # Charts
    (r"_chart", "charts"),
    (r"^chart_", "charts"),
    (r"\.png$", "charts"),
    (r"\.jpg$", "charts"),
]

# Comprehensive ticker and keyword patterns for tag extraction
TICKER_PATTERNS = [
    # Precious Metals
    r"\b(GOLD|XAUUSD|GC=F|XAU)\b",
    r"\b(SILVER|XAGUSD|SI=F|XAG)\b",
    r"\b(PLATINUM|PL=F|XPT)\b",
    r"\b(PALLADIUM|PA=F|XPD)\b",
    # Indices
    r"\b(SPY|SPX|ES=F|S&P)\b",
    r"\b(QQQ|NDX|NQ=F|NASDAQ)\b",
    r"\b(DIA|DJI|DJIA|DOW)\b",
    r"\b(IWM|RUT|RUSSELL)\b",
    # Volatility
    r"\b(VIX|UVXY|VXX|SVXY)\b",
    # Dollar & Currency
    r"\b(DXY|UUP|USDX|USD)\b",
    r"\b(EUR|EURUSD)\b",
    r"\b(JPY|USDJPY)\b",
    r"\b(GBP|GBPUSD)\b",
    # Bonds & Yields
    r"\b(TLT|TNX|TYX|ZB=F)\b",
    r"\b(10Y|10-Year|2Y|30Y)\b",
    # Mining Stocks
    r"\b(GDX|GDXJ|NEM|GOLD|AEM|KGC)\b",
    r"\b(SLV|PSLV|AG|WPM|HL)\b",
    # Crypto
    r"\b(BTC|ETH|BTCUSD|ETHUSD|Bitcoin|Ethereum)\b",
    # Energy
    r"\b(CL=F|WTI|CRUDE|OIL|USO)\b",
    r"\b(NG=F|NATGAS|UNG)\b",
]

# Economic & Fundamental keywords for tagging
KEYWORD_PATTERNS = [
    # Central Banks & Policy
    r"\b(Fed|FOMC|Federal Reserve)\b",
    r"\b(ECB|BOJ|BOE|PBOC|RBA|SNB)\b",
    r"\b(Powell|Yellen|Lagarde)\b",
    r"\b(hawkish|dovish|pivot)\b",
    r"\b(rate cut|rate hike|QE|QT)\b",
    # Economic Data
    r"\b(CPI|PPI|PCE|NFP|GDP)\b",
    r"\b(inflation|deflation|stagflation)\b",
    r"\b(unemployment|jobless|payrolls)\b",
    r"\b(PMI|ISM|retail sales)\b",
    # Market Sentiment
    r"\b(bullish|bearish|neutral)\b",
    r"\b(risk-on|risk-off|risk on|risk off)\b",
    r"\b(breakout|breakdown|reversal)\b",
    r"\b(support|resistance)\b",
    # Events & Catalysts
    r"\b(OPEC|G7|G20|Jackson Hole|Davos)\b",
    r"\b(earnings|options expiration|OpEx|witching)\b",
    r"\b(geopolitical|sanctions|tariffs)\b",
]


@dataclass
class NotionConfig:
    api_key: str
    database_id: str

    @classmethod
    def from_env(cls) -> "NotionConfig":
        api_key = os.getenv("NOTION_API_KEY", "")
        database_id = os.getenv("NOTION_DATABASE_ID", "")

        if not api_key:
            raise ValueError("NOTION_API_KEY not set in environment")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID not set in environment")

        return cls(api_key=api_key, database_id=database_id)


class NotionPublisher:
    """Publish Syndicate reports to Notion."""

    def __init__(self, config: NotionConfig = None, no_client_ok: bool = False):
        # Allow tests or dry-run to construct without the Notion client.
        if not no_client_ok and not NOTION_AVAILABLE and Client is None:
            raise ImportError("notion-client package not installed")

        self.config = config or NotionConfig.from_env()
        # Initialize the notion client (may be a real client, a monkeypatched fake, or None for dry-run)
        self.client = Client(auth=self.config.api_key) if (Client is not None and not no_client_ok) else None

    def _get_database_properties(self) -> Dict[str, Any]:
        """Return data-source properties if available, otherwise fall back to database properties.

        This method attempts to discover a `data_source_id` for the configured
        database (via the `GET /v1/databases/:database_id` API using
        Notion-Version: 2025-09-03) and then fetches the properties for that
        data source with `GET /v1/data_sources/:data_source_id`.

        If any step fails we fall back to the historic `databases.retrieve`
        behavior to remain compatible with older API versions.
        """
        try:
            # If user pinned a data source via env, respect it
            ds_id = os.getenv("NOTION_DATA_SOURCE_ID") or getattr(self, "_data_source_id", None)

            # Discovery step: fetch data_sources for the database (2025-09-03 behavior)
            if not ds_id:
                try:
                    import requests

                    url = f"https://api.notion.com/v1/databases/{self.config.database_id}"
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Notion-Version": "2025-09-03",
                        "Content-Type": "application/json",
                    }
                    timeout = int(os.getenv("NOTION_API_TIMEOUT", "30"))
                    r = requests.get(url, headers=headers, timeout=timeout)
                    r.raise_for_status()
                    payload = r.json() or {}
                    data_sources = payload.get("data_sources") or []
                    if data_sources:
                        ds_id = data_sources[0].get("id")
                        self._data_source_id = ds_id
                except Exception:
                    # Discovery failed - we will fall back to database properties
                    ds_id = getattr(self, "_data_source_id", None)

            # If we have a data source id, fetch its schema (properties)
            if ds_id:
                try:
                    import requests

                    url = f"https://api.notion.com/v1/data_sources/{ds_id}"
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Notion-Version": "2025-09-03",
                        "Content-Type": "application/json",
                    }
                    timeout = int(os.getenv("NOTION_API_TIMEOUT", "30"))
                    r = requests.get(url, headers=headers, timeout=timeout)
                    r.raise_for_status()
                    payload = r.json() or {}
                    props = payload.get("properties", {}) or {}
                    self._data_source_props = props
                    return props
                except Exception:
                    # If fetching data source failed, fallthrough to DB retrieve
                    pass

            # Fallback: retrieve database properties via the notion client
            try:
                # Respect custom timeout for client-side operations when available
                try:
                    db = self.client.databases.retrieve(self.config.database_id)
                except Exception:
                    # Last resort: try a simple requests call with a larger timeout
                    timeout = int(os.getenv("NOTION_API_TIMEOUT", "30"))
                    import requests as _req

                    url = f"https://api.notion.com/v1/databases/{self.config.database_id}"
                    headers = {
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Notion-Version": "2025-09-03",
                        "Content-Type": "application/json",
                    }
                    r = _req.get(url, headers=headers, timeout=timeout)
                    r.raise_for_status()
                    db = r.json() or {}
                props = db.get("properties", {}) or {}
                return props
            except Exception as e:
                print(f"[NotionPublisher] Could not retrieve database properties: {e}")
                return {}
        except Exception as e:
            print(f"[NotionPublisher] Error while getting database/data-source properties: {e}")
            return {}

    def detect_type(self, filename: str) -> str:
        """Detect document type from filename."""
        name = Path(filename).name

        for pattern, doc_type in TYPE_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return doc_type

        return "notes"

    def extract_tags(self, content: str) -> List[str]:
        """Extract tags from content."""
        tags = set()

        for pattern in TICKER_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                normalized = match.upper()
                # Normalize variations
                if normalized in ("XAUUSD", "GC=F"):
                    normalized = "GOLD"
                elif normalized in ("XAGUSD", "SI=F"):
                    normalized = "SILVER"
                elif normalized in ("SPX", "ES=F"):
                    normalized = "SPY"
                elif normalized in ("BTCUSD",):
                    normalized = "BTC"
                elif normalized in ("ETHUSD",):
                    normalized = "ETH"
                elif normalized in ("Bitcoin",):
                    normalized = "BTC"
                elif normalized in ("Ethereum",):
                    normalized = "ETH"
                tags.add(normalized)

        # Extract keyword tags from KEYWORD_PATTERNS
        for pattern in KEYWORD_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Normalize keywords
                normalized = match.upper() if len(match) <= 4 else match.title()
                # Special cases
                if normalized.lower() in ("bullish", "bearish", "neutral"):
                    normalized = normalized.title()
                elif normalized.lower() in ("fed", "fomc", "ecb", "boj", "boe", "pboc"):
                    normalized = normalized.upper()
                elif "federal reserve" in normalized.lower():
                    normalized = "Fed"
                elif "rate cut" in normalized.lower():
                    normalized = "Rate Cut"
                elif "rate hike" in normalized.lower():
                    normalized = "Rate Hike"
                tags.add(normalized)

        return sorted(list(tags))[:15]  # Allow more tags for comprehensive coverage

    def parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from content."""
        if not content.strip().startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        yaml_str = parts[1].strip()
        body = parts[2].strip()

        # Simple YAML parsing
        meta = {}
        for line in yaml_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Parse arrays [a, b, c]
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
                # Parse booleans
                elif value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                # Strip quotes
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                meta[key] = value

        return meta, body

    def markdown_to_blocks(self, content: str) -> List[Dict]:
        """Convert markdown to Notion blocks with rich formatting."""
        blocks = []
        lines = content.split("\n")
        i = 0

        def parse_rich_text(text: str) -> List[Dict]:
            """Parse inline markdown to rich text annotations."""
            rich_texts = []

            # Simple approach: split by bold/italic markers
            # For now, just detect **bold** and *italic*
            parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text)

            for part in parts:
                if not part:
                    continue

                if part.startswith("**") and part.endswith("**"):
                    rich_texts.append({"type": "text", "text": {"content": part[2:-2]}, "annotations": {"bold": True}})
                elif part.startswith("*") and part.endswith("*") and not part.startswith("**"):
                    rich_texts.append(
                        {"type": "text", "text": {"content": part[1:-1]}, "annotations": {"italic": True}}
                    )
                elif part.startswith("`") and part.endswith("`"):
                    rich_texts.append({"type": "text", "text": {"content": part[1:-1]}, "annotations": {"code": True}})
                else:
                    rich_texts.append({"type": "text", "text": {"content": part}})

            return rich_texts if rich_texts else [{"type": "text", "text": {"content": text}}]

        while i < len(lines):
            line = lines[i]

            # Skip frontmatter (YAML between ---)
            if line.strip() == "---" and i == 0:
                i += 1
                while i < len(lines) and lines[i].strip() != "---":
                    i += 1
                i += 1  # Skip closing ---
                continue

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Headers
            header_match = re.match(r"^(#{1,3})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                block_type = f"heading_{level}"

                blocks.append(
                    {
                        "object": "block",
                        "type": block_type,
                        block_type: {"rich_text": parse_rich_text(text)},
                    }
                )
                i += 1
                continue

            # Tables (convert to code block for better display)
            if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].startswith("|"):
                    # Skip separator rows (|---|---|)
                    if not re.match(r"^\|[-:\s|]+\|$", lines[i]):
                        table_lines.append(lines[i])
                    i += 1

                if table_lines:
                    # Create a simple formatted table
                    blocks.append(
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "rich_text": [{"type": "text", "text": {"content": "\n".join(table_lines)}}],
                                "language": "plain text",
                            },
                        }
                    )
                continue

            # Code blocks
            if line.startswith("```"):
                language = line[3:].strip() or "plain text"
                code_lines = []
                i += 1

                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing ```

                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                            "language": language.lower()
                            if language.lower() in ["python", "javascript", "json", "markdown", "sql", "bash"]
                            else "plain text",
                        },
                    }
                )
                continue

            # Callout (> **text** format often used for metadata)
            if line.startswith("> **"):
                # Collect all blockquote lines
                quote_lines = []
                while i < len(lines) and lines[i].startswith(">"):
                    quote_lines.append(re.sub(r"^>\s*", "", lines[i]))
                    i += 1

                blocks.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": parse_rich_text("\n".join(quote_lines)),
                            "icon": {"emoji": "📊"},
                            "color": "gray_background",
                        },
                    }
                )
                continue

            # Regular blockquote
            if line.startswith(">"):
                text = re.sub(r"^>\s*", "", line)
                blocks.append(
                    {
                        "object": "block",
                        "type": "quote",
                        "quote": {"rich_text": parse_rich_text(text)},
                    }
                )
                i += 1
                continue

            # Bullet list
            if re.match(r"^[-*]\s+", line):
                text = re.sub(r"^[-*]\s+", "", line)
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": parse_rich_text(text)},
                    }
                )
                i += 1
                continue

            # Numbered list
            num_match = re.match(r"^\d+\.\s+(.+)$", line)
            if num_match:
                blocks.append(
                    {
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {"rich_text": parse_rich_text(num_match.group(1))},
                    }
                )
                i += 1
                continue

            # Horizontal rule
            if re.match(r"^---+$", line) or re.match(r"^\*\*\*+$", line):
                blocks.append({"object": "block", "type": "divider", "divider": {}})
                i += 1
                continue

            # Default: paragraph with rich text
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": parse_rich_text(line)},
                }
            )
            i += 1

        return blocks

    def publish(
        self,
        title: str,
        content: str,
        doc_type: str = None,
        tags: List[str] = None,
        doc_date: str = None,
        filename: str = None,
        use_enhanced_formatting: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, str]:
        """Publish a document to Notion."""

        # Parse frontmatter
        meta, body = self.parse_frontmatter(content)

        # Determine type
        if not doc_type:
            doc_type = meta.get("type") or (self.detect_type(filename) if filename else "notes")

        if doc_type not in NOTION_TYPES:
            doc_type = "notes"

        # Determine tags
        if not tags:
            tags = meta.get("tags") if isinstance(meta.get("tags"), list) else self.extract_tags(body)

        # Determine date
        if not doc_date:
            doc_date = meta.get("date") or date.today().isoformat()

        # Get bias from frontmatter
        bias = meta.get("bias")

        # Convert to blocks - use enhanced formatter if available
        if use_enhanced_formatting:
            try:
                from scripts.chart_publisher import ChartPublisher
                from scripts.notion_formatter import format_for_notion

                # Try to get chart URLs for tickers in content
                chart_urls = None
                try:
                    chart_pub = ChartPublisher()
                    chart_urls = chart_pub.get_charts_for_content(body)
                    if chart_urls:
                        print(f"  📊 Adding charts: {', '.join(chart_urls.keys())}")
                except Exception as e:
                    print(f"  ⚠ Chart upload skipped: {e}")

                blocks = format_for_notion(content, doc_type=doc_type, bias=bias, chart_urls=chart_urls)
            except ImportError:
                # Fallback to basic formatting
                blocks = self.markdown_to_blocks(body)
        else:
            blocks = self.markdown_to_blocks(body)

        # Frontmatter validation and tag normalization
        def _validate_frontmatter(meta_obj: Dict) -> List[str]:
            errs = []
            # Validate date if present (simple checks)
            try:
                if meta_obj.get("date"):
                    d = str(meta_obj.get("date"))
                    valid = False
                    # Try ISO-like
                    try:
                        datetime.fromisoformat(d.split("T")[0])
                        valid = True
                    except Exception:
                        pass
                    # Try common formats
                    if not valid:
                        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
                            try:
                                datetime.strptime(d, fmt)
                                valid = True
                                break
                            except Exception:
                                continue
                    if not valid:
                        errs.append(f"Invalid date format: {meta_obj.get('date')}")
            except Exception:
                errs.append("Date validation error")

            # Validate tags
            try:
                t = meta_obj.get("tags")
                if t and not isinstance(t, (list, tuple)):
                    errs.append("'tags' should be a list in frontmatter")
            except Exception:
                errs.append("Tags validation error")

            return errs

        def _normalize_tags(tag_list: List[str]) -> List[str]:
            out = []
            for t in (tag_list or []):
                try:
                    tn = str(t).strip()
                    # Remove stray punctuation
                    tn = re.sub(r"[^A-Za-z0-9\-\._ /]", "", tn)
                    # If looks like a ticker symbol, uppercase
                    if tn.isupper() or (len(tn) <= 5 and tn.replace('.', '').isalpha()):
                        tn = tn.upper()
                    else:
                        tn = tn.title()
                    if tn and tn not in out:
                        out.append(tn)
                except Exception:
                    continue
            return out

        # Run frontmatter validation
        fm_errors = _validate_frontmatter(meta)
        # Normalize tag list for properties
        if tags is None:
            tags = meta.get("tags") if isinstance(meta.get("tags"), list) else tags
        tags = _normalize_tags(tags or [])

        # Build properties - start with required title
        properties = {"title": {"title": [{"text": {"content": title}}]}}

        # Add optional properties - adapt to database schema when possible
        db_props = self._get_database_properties()

        # Type property: prefer select when DB has it
        try:
            if doc_type and "Type" in db_props and db_props["Type"].get("type") == "select":
                properties["Type"] = {"select": {"name": doc_type}}
        except Exception:
            pass

        # Helper: normalize dates and map values to Notion property payloads
        def _normalize_date(val: str) -> str:
            if not val:
                return None
            # Accept ISO-like strings or common formats; prefer YYYY-MM-DD
            try:
                # Fast path: already ISO
                if isinstance(val, str) and re.match(r"^\d{4}-\d{2}-\d{2}", val):
                    return val.split("T")[0]
                # Try fromisoformat
                try:
                    return datetime.fromisoformat(val).date().isoformat()
                except Exception:
                    pass
                # Try known formats
                for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(val, fmt).date().isoformat()
                    except Exception:
                        continue
            except Exception:
                pass
            return None

        def _map_relation(prop_value):
            # Accept list of notion page ids or a single id
            if not prop_value:
                return []
            if isinstance(prop_value, str):
                return [{"id": prop_value}]
            if isinstance(prop_value, list):
                out = []
                for v in prop_value:
                    if isinstance(v, dict) and v.get("id"):
                        out.append({"id": v["id"]})
                    elif isinstance(v, str):
                        out.append({"id": v})
                return out
            return []

        # Date property: normalize and use date if DB has it
        try:
            nd = _normalize_date(doc_date)
            if nd and "Date" in db_props and db_props["Date"].get("type") == "date":
                properties["Date"] = {"date": {"start": nd}}
        except Exception:
            pass

        # Tags property: prefer multi_select when DB has it; ensure unique names
        try:
            if tags and "Tags" in db_props and db_props["Tags"].get("type") == "multi_select":
                uniq = []
                for t in tags:
                    tn = str(t).strip()
                    if tn and tn not in uniq:
                        uniq.append(tn)
                properties["Tags"] = {"multi_select": [{"name": t} for t in uniq]}
        except Exception:
            pass

        # Status property: adapt to either 'status' or 'select' (DB may have either)
        try:
            status = meta.get("status")
            if status and "Status" in db_props:
                prop_type = db_props["Status"].get("type")
                if prop_type == "status":
                    properties["Status"] = {"status": {"name": str(status)}}
                elif prop_type == "select":
                    properties["Status"] = {"select": {"name": str(status)}}
                else:
                    # Unknown, skip setting Status to avoid a 400
                    pass
            elif status:
                # DB property unavailable - try 'status' by default (will be retried on failure)
                properties["Status"] = {"status": {"name": str(status)}}
        except Exception:
            pass

        # Relation properties: support basic relation mapping when frontmatter contains 'relations' or 'related'
        try:
            if "Relations" in db_props:
                rel_meta = meta.get("relations") or meta.get("related") or meta.get("relations_ids")
                if rel_meta:
                    properties["Relations"] = {"relation": _map_relation(rel_meta)}
        except Exception:
            pass

        # Determine parent to use for page creation - prefer a specific data_source_id when available
        parent = {"database_id": self.config.database_id}
        try:
            ds_id = os.getenv("NOTION_DATA_SOURCE_ID") or getattr(self, "_data_source_id", None)
            if not ds_id:
                # Trigger discovery (which will populate _data_source_id if possible)
                _ = self._get_database_properties()
                ds_id = getattr(self, "_data_source_id", None)
            if ds_id:
                parent = {"type": "data_source_id", "data_source_id": ds_id}
        except Exception:
            # Leave parent as database_id on any error to preserve backwards compatibility
            parent = {"database_id": self.config.database_id}

        # Before attempting API calls: if dry_run, validate blocks and properties only
        def _validate_blocks_for_notion(blocks_list: List[Dict]) -> List[str]:
            errs = []
            # Validate table structures: each table_row must match parent table_width
            for b in blocks_list:
                try:
                    if b.get("type") == "table":
                        t = b.get("table", {})
                        width = int(t.get("table_width", 0) or 0)
                        children = t.get("children", [])
                        for idx, r in enumerate(children):
                            cells = r.get("table_row", {}).get("cells", [])
                            if len(cells) != width:
                                errs.append(f"Table row {idx} has {len(cells)} cells but table_width is {width}")
                except Exception:
                    errs.append("Table validation error")
            return errs

        if dry_run:
            # Combine frontmatter and block validations and return a report without calling Notion
            block_errors = _validate_blocks_for_notion(blocks)
            errors = fm_errors + block_errors
            if errors:
                return {"dry_run": True, "valid": False, "errors": errors, "blocks": len(blocks)}
            else:
                return {"dry_run": True, "valid": True, "blocks": len(blocks)}

        # Create page with robust retry logic, exponential backoff, jitter and structured logging
        attempts = int(os.getenv("NOTION_PUBLISH_ATTEMPTS", "7"))
        base_delay = float(os.getenv("NOTION_PUBLISH_BASE_DELAY", "2"))
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                logging.info("Notion publish attempt %d/%d", attempt, attempts)
                # Try to prefer a client-level timeout if available; otherwise rely on retries/backoff
                try:
                    response = self.client.pages.create(parent=parent, properties=properties, children=blocks[:100])
                except TypeError:
                    # Older client may not accept kwargs the same way; fall back to direct call
                    response = self.client.pages.create(parent=parent, properties=properties, children=blocks[:100])
                last_exc = None
                logging.info("Notion publish succeeded on attempt %d", attempt)
                break
            except Exception as e:
                last_exc = e
                logging.exception("Notion publish attempt %d failed", attempt)

                # If it's a property-type error, attempt the Status/Minimal fallbacks before retrying
                try:
                    db_props = db_props if 'db_props' in locals() else self._get_database_properties()
                    # If Status property exists, ensure the chosen option is valid for the DB schema
                    if "Status" in properties and "Status" in db_props:
                        prop_type = db_props["Status"].get("type")
                        desired = None
                        if "status" in properties.get("Status", {}):
                            desired = properties["Status"]["status"].get("name")
                        elif "select" in properties.get("Status", {}):
                            desired = properties["Status"]["select"].get("name")

                        def _normalize_status_name(s: str) -> str:
                            s = str(s or "").strip()
                            s = s.replace("_", " ")
                            s = s.replace("-", " ")
                            if s.lower() == "in progress":
                                return "In Progress"
                            if s.lower() == "inprogress":
                                return "In Progress"
                            if s.lower() == "in_progress":
                                return "In Progress"
                            if s.lower() == "published":
                                return "Published"
                            if s.lower() == "draft":
                                return "Draft"
                            return s.title()

                        if desired:
                            desired_norm = _normalize_status_name(desired)
                        else:
                            desired_norm = None

                        # Inspect allowed options for the property
                        allowed_options = []
                        try:
                            prop_payload = db_props.get("Status", {})
                            ptype = prop_payload.get("type")
                            opts = prop_payload.get(ptype, {}).get("options") if ptype else None
                            if not opts:
                                # Try alternate structures
                                opts = prop_payload.get("status", {}).get("options") or prop_payload.get("select", {}).get("options")
                            if opts:
                                allowed_options = [o.get("name", "").strip() for o in opts]
                        except Exception:
                            allowed_options = []

                        # If desired is present and not allowed, attempt to upsert the option (select/status)
                        if desired_norm and desired_norm not in [a.strip() for a in allowed_options]:
                            try:
                                # For select/status types we can attempt to add the option to the database schema
                                if prop_type in ("select", "status"):
                                    logging.info("Adding missing Status option '%s' to database schema", desired_norm)
                                    # Retrieve existing options payload
                                    options_payload = prop_payload.get(prop_type, {}).get("options", []) if prop_payload.get(prop_type) else []
                                    # Append new option
                                    options_payload.append({"name": desired_norm})
                                    update_payload = {"properties": {"Status": {prop_type: {"options": options_payload}}}}
                                    try:
                                        # Attempt to update the database schema to include the new option
                                        self.client.databases.update(self.config.database_id, **update_payload)
                                        # Refresh db_props
                                        db_props = self._get_database_properties()
                                        logging.info("Status option upserted; retrying publish")
                                        response = self.client.pages.create(parent=parent, properties=properties, children=blocks[:100])
                                        last_exc = None
                                        break
                                    except Exception:
                                        logging.exception("Failed to upsert Status option; will fallback to minimal create")
                            except Exception:
                                logging.exception("Status option upsert attempt failed")
                        # If types mismatch, try alternate representation
                        if prop_type == "status" and "select" in properties["Status"]:
                            properties["Status"] = {"status": {"name": properties["Status"]["select"]["name"]}}
                            logging.info("Retrying with Status as 'status' type")
                            response = self.client.pages.create(parent=parent, properties=properties, children=blocks[:100])
                            last_exc = None
                            break
                        elif prop_type == "select" and "status" in properties["Status"]:
                            properties["Status"] = {"select": {"name": properties["Status"]["status"]["name"]}}
                            logging.info("Retrying with Status as 'select' type")
                            response = self.client.pages.create(parent=parent, properties=properties, children=blocks[:100])
                            last_exc = None
                            break
                except Exception:
                    logging.exception("Status fallback failed")

                # As a last resort, try a minimal create with title only
                try:
                    minimal_props = {"title": properties.get("title")}
                    logging.info("Attempting minimal create (title-only)")
                    response = self.client.pages.create(parent=parent, properties=minimal_props, children=blocks[:100])
                    last_exc = None
                    break
                except Exception:
                    logging.exception("Minimal create failed")

                # Backoff with jitter
                import time

                jitter = random.uniform(0, 0.3 * base_delay)
                sleep_time = base_delay + jitter
                logging.info("Backing off for %.2fs before retrying", sleep_time)
                time.sleep(sleep_time)
                base_delay *= 2

        if last_exc:
            # Raise a combined error with context for debugging and send an alert
            logging.exception("Final Notion publish failure after %d attempts", attempts)
            try:
                from scripts.notifier import send_discord

                send_discord(f"Notion publish failed after {attempts} attempts: {last_exc}")
            except Exception:
                logging.exception("Failed to send failure alert")
            raise Exception(f"Failed to publish to Notion after {attempts} attempts; last error: {last_exc!r}")

        # Track usage
        try:
            from scripts.cleanup_manager import CleanupManager

            CleanupManager().record_notion_page(len(blocks[:100]))
        except Exception:
            pass

        page_id = response["id"]
        url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")

        return {"page_id": page_id, "url": url, "type": doc_type, "tags": tags}

    def sync_file(
        self, filepath: str, doc_type: str = None, tags: List[str] = None, force: bool = False, dry_run: bool = False
    ) -> Dict[str, str]:
        """
        Sync a local file to Notion with deduplication.

        Args:
            filepath: Path to the markdown file
            doc_type: Document type for Notion
            tags: Tags to apply
            force: If True, sync even if file hasn't changed or not published

        Returns:
            Dict with page_id, url, type, tags, and 'skipped' flag
        """
        path = Path(filepath).resolve()  # CRITICAL: Always use absolute resolved path for consistent dedup

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        content = path.read_text(encoding="utf-8")
        filename = path.name

        # Enforce repository-level ignore patterns: never publish these files to Notion
        try:
            fname_lower = filename.lower()
            for pat in IGNORE_PATTERNS:
                if pat.lower() in fname_lower or pat.lower() in str(path).lower():
                    return {
                        "page_id": "",
                        "url": "",
                        "type": doc_type or "notes",
                        "tags": [],
                        "skipped": True,
                        "reason": "excluded_pattern",
                    }
        except Exception:
            pass

        # Normalize path and compute a stronger content fingerprint for DB checks
        normalized_path = str(path)
        file_hash = None
        # Parse frontmatter to include structured metadata in fingerprint
        try:
            meta, body = self.parse_frontmatter(content)
        except Exception:
            meta, body = {}, content

        # Compute a deterministic strong fingerprint (title + frontmatter + normalized body)
        try:
            title_for_hash = None
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title_for_hash = h1_match.group(1).strip() if h1_match else filename.replace(".md", "").replace("_", " ")
            # Unescape and strip tags for fingerprinting
            title_for_hash = html.unescape(title_for_hash)
            title_for_hash = re.sub(r"<[^>]+>", "", title_for_hash)
            body_norm = re.sub(r"\s+", " ", html.unescape(body)).strip()
            meta_str = "" if not meta else ",".join(f"{k}={meta[k]}" for k in sorted(meta.keys()))
            fingerprint_source = "\n".join([title_for_hash, meta_str, body_norm])
            file_hash = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
            # store hash for potential db comparison later
            self._last_checked_hash = file_hash
        except Exception:
            file_hash = None
        if DB_AVAILABLE:
            try:
                db = get_db()
                # Release stale in_progress claims before checking/claiming
                try:
                    ttl = int(os.environ.get("DOCUMENT_CLAIM_TTL", "900"))
                except Exception:
                    ttl = 900
                try:
                    db.release_stale_claims(ttl)
                except Exception:
                    pass
                # Only read stored file hash if we don't have a computed fingerprint
                if not file_hash:
                    file_hash = db.get_file_hash(normalized_path)
                # Check document lifecycle to avoid duplicate publishes
                doc = db.get_document_status(normalized_path)
                if doc:
                    status = doc.get("status")
                    # If already published and hash matches, skip
                    if status == "published" and doc.get("content_hash") == file_hash and not force:
                        return {
                            "page_id": doc.get("notion_page_id", ""),
                            "url": "",
                            "type": doc.get("doc_type", doc_type or "notes"),
                            "tags": [],
                            "skipped": True,
                            "reason": "already_published",
                        }

                    # If another process recently marked it in_progress, skip to avoid racing publishes
                    if status == "in_progress" and not force:
                        try:
                            updated_at = doc.get("updated_at")
                            if updated_at:
                                updated_dt = datetime.fromisoformat(updated_at)
                                if (datetime.now() - updated_dt).total_seconds() < 900:  # 15 minutes
                                    return {
                                        "page_id": "",
                                        "url": "",
                                        "type": doc.get("doc_type", doc_type or "notes"),
                                        "tags": [],
                                        "skipped": True,
                                        "reason": "publish_in_progress",
                                    }
                        except Exception:
                            # If parsing fails, continue to attempt claim
                            pass

                # Attempt to claim the document by registering/upserting as in_progress
                try:
                    # Register the document lifecycle using the computed fingerprint
                    db.register_document(normalized_path, doc_type or "notes", status="in_progress", content_hash=file_hash)
                except Exception:
                    pass
            except Exception:
                # DB checks are best-effort; continue if DB unavailable
                pass

        # Check document lifecycle status - only sync ready documents
        # Ready = published OR (in_progress AND ai_processed)
        if not force:
            try:
                from scripts.frontmatter import get_document_status, is_ai_processed, is_ready_for_sync

                status = get_document_status(content)
                ai_processed = is_ai_processed(content)

                # Allow explicit opt-out for Notion publishing via frontmatter
                meta_publish = meta.get("publish_to_notion") if isinstance(meta, dict) else None
                if meta_publish is False:
                    return {
                        "page_id": "",
                        "url": "",
                        "type": doc_type or "notes",
                        "tags": [],
                        "skipped": True,
                        "reason": "opted_out_publish",
                    }

                # If DB available, consult document lifecycle to prevent publishing drafts
                if DB_AVAILABLE:
                    try:
                        db = get_db()
                        doc_life = db.get_document_status(str(path)) if 'path' in locals() else None
                        if doc_life and doc_life.get('status') == 'draft' and not force:
                            return {
                                "page_id": "",
                                "url": "",
                                "type": doc_type or "notes",
                                "tags": [],
                                "skipped": True,
                                "reason": "lifecycle_draft",
                            }
                        # Prevent publishing if sanitizer corrections exist for associated tasks
                        try:
                            # Find tasks linked to this document path
                            with db._get_connection() as conn:
                                cur = conn.cursor()
                                cur.execute("SELECT id FROM llm_tasks WHERE document_path = ?", (str(path),))
                                task_ids = [r[0] for r in cur.fetchall()]
                                if task_ids:
                                    q = f"SELECT SUM(corrections) as total FROM llm_sanitizer_audit WHERE task_id IN ({','.join(['?']*len(task_ids))})"
                                    cur.execute(q, tuple(task_ids))
                                    row = cur.fetchone()
                                    corrections = int(row[0] or 0) if row else 0
                                    if corrections > 0 and not force:
                                        return {
                                            "page_id": "",
                                            "url": "",
                                            "type": doc_type or "notes",
                                            "tags": [],
                                            "skipped": True,
                                            "reason": "sanitizer_corrections",
                                        }
                        except Exception:
                            pass
                    except Exception:
                        pass

                if not is_ready_for_sync(content):
                    reason = f"Document status is '{status}'"
                    if status == "draft":
                        reason += " (AI processing incomplete or failed)"
                    elif not ai_processed:
                        reason += " (not AI processed)"
                    return {
                        "page_id": "",
                        "url": "",
                        "type": doc_type or "notes",
                        "tags": [],
                        "skipped": True,
                        "reason": reason,
                    }
            except ImportError:
                pass  # Frontmatter module not available, continue with sync

        # Check if file has already been synced (and hasn't changed)
        if DB_AVAILABLE and not force:
            db = get_db()
            try:
                if db.is_file_synced(str(path)):
                    existing = db.get_notion_page_for_file(str(path))
                    return {
                        "page_id": existing.get("notion_page_id", ""),
                        "url": existing.get("notion_url", ""),
                        "type": existing.get("doc_type", "notes"),
                        "tags": [],
                        "skipped": True,
                        "reason": "File unchanged since last sync",
                    }
            except Exception:
                # If DB or notion_sync table is unavailable, proceed to acquire lock and attempt publish
                pass

        # Acquire per-file publish lock to avoid concurrent publishes creating duplicates
        # Ensure locks live under the project cache directory to avoid trying to
        # create a directory with the raw database id as a top-level path.
        lock_dir = Path.home() / ".cache" / "syndicate" / (self.config.database_id or "notion") / "notion_locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_name = hashlib.md5(str(path).encode()).hexdigest() + ".lock"
        lock_path = lock_dir / lock_name

        try:
            lock = FileLock(str(lock_path), timeout=5)
            lock.acquire()
        except Exception:
            # Another process is publishing this file - skip to avoid duplicates
            return {
                "page_id": "",
                "url": "",
                "type": doc_type or "notes",
                "tags": [],
                "skipped": True,
                "reason": "publish_in_progress",
            }

        try:
            # Re-check file unchanged and frontmatter before doing actual publish
            # Extract title from H1 or filename
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else filename.replace(".md", "").replace("_", " ")
            # Sanitize title: strip HTML tags and unescape entities to avoid corrupted Notion titles
            def _sanitize_title(s: str) -> str:
                if not s:
                    return s
                try:
                    # Unescape HTML entities then remove tags
                    t = html.unescape(s)
                    t = re.sub(r"<[^>]+>", "", t)
                    t = re.sub(r"\s+", " ", t).strip()
                    return t
                except Exception:
                    return s

            title = _sanitize_title(title)
            result = self.publish(title=title, content=content, doc_type=doc_type, tags=tags, filename=filename, dry_run=dry_run)

            # Record the sync in the database, using the strong fingerprint when available
            if DB_AVAILABLE:
                db = get_db()
                try:
                    db.record_notion_sync(str(path), result["page_id"], result["url"], result.get("type", "notes"), file_hash=file_hash)
                except TypeError:
                    # Older DB manager without optional param - fall back
                    db.record_notion_sync(str(path), result["page_id"], result["url"], result.get("type", "notes"))
        finally:
            try:
                lock.release()
            except Exception:
                pass

        result["skipped"] = False
        return result

    def list_docs(
        self, doc_type: str = None, start_date: str = None, end_date: str = None, limit: int = 10
    ) -> List[Dict]:
        """List documents from the database."""

        filters = []

        if doc_type:
            filters.append({"property": "Type", "select": {"equals": doc_type}})

        if start_date:
            filters.append({"property": "Date", "date": {"on_or_after": start_date}})

        if end_date:
            filters.append({"property": "Date", "date": {"on_or_before": end_date}})

        # Build query payload
        query_payload = {
            "sorts": [{"property": "Date", "direction": "descending"}],
            "page_size": limit,
        }

        if filters:
            query_payload["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        # Prefer querying data_sources when available (Notion 2025-09-03)
        ds_id = getattr(self, "_data_source_id", None)
        if not ds_id:
            # Attempt discovery (this will populate _data_source_id when possible)
            _ = self._get_database_properties()
            ds_id = getattr(self, "_data_source_id", None)

        results = []
        if ds_id:
            try:
                # Use the data_sources query endpoint; use Notion-Version for compatibility
                resp = self.client.request(
                    "POST",
                    f"/v1/data_sources/{ds_id}/query",
                    json=query_payload,
                    headers={"Notion-Version": "2025-09-03"},
                )
                response = resp
            except Exception:
                logging.exception("Data source query failed; falling back to databases.query")
                response = self.client.databases.query(database_id=self.config.database_id, **query_payload)
        else:
            response = self.client.databases.query(database_id=self.config.database_id, **query_payload)

        for page in response["results"]:
            props = page["properties"]
            results.append(
                {
                    "id": page["id"],
                    "title": props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled"),
                    "type": props.get("Type", {}).get("select", {}).get("name", "notes"),
                    "date": props.get("Date", {}).get("date", {}).get("start", "Unknown"),
                    "tags": [t["name"] for t in props.get("Tags", {}).get("multi_select", [])],
                }
            )

        return results


def sync_all_outputs(output_dir: str = None, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Sync all Syndicate outputs to Notion with intelligent deduplication.

    Args:
        output_dir: Directory containing output files (default: PROJECT_ROOT/output)
        force: If True, sync all files even if unchanged

    Returns:
        Dict with success, skipped, and failed lists
    """
    if output_dir is None:
        output_dir = PROJECT_ROOT / "output"

    output_path = Path(output_dir)
    if not output_path.exists():
        raise FileNotFoundError(f"Output directory not found: {output_dir}")

    # Check schedule before syncing
    if DB_AVAILABLE and not force:
        db = get_db()
        if not db.should_run_task("notion_sync"):
            print("[NOTION] Sync already completed for today, skipping")
            return {"success": [], "skipped": [], "failed": [], "reason": "Already synced today"}

    # If global disable is set, force dry_run mode to avoid any API calls
    if _DISABLE_NOTION_PUBLISH:
        print("[NOTION] Global Notion publish disabled via DISABLE_NOTION_PUBLISH; running in dry-run mode.")
        dry_run = True

    publisher = NotionPublisher(no_client_ok=dry_run)
    results = {"success": [], "skipped": [], "failed": []}

    # Find all markdown files recursively
    md_files = list(output_path.glob("**/*.md"))

    # Filter out index files and archive
    md_files = [f for f in md_files if "FILE_INDEX" not in f.name and "/archive/" not in str(f).replace("\\", "/")]

    # Apply repository-level ignore patterns so certain internal files (digests, executor outputs)
    # never get published even when --force is used.
    def _is_ignored(fpath: Path) -> bool:
        try:
            name = fpath.name.lower()
            s = str(fpath).lower()
            for p in IGNORE_PATTERNS:
                if p.lower() in name or p.lower() in s:
                    return True
        except Exception:
            return False
        return False

    md_files = [f for f in md_files if not _is_ignored(f)]

    for filepath in md_files:
        try:
            result = publisher.sync_file(str(filepath), force=force, dry_run=dry_run)

            # Support future dry-run flows where sync_file returns dry_run results
            if result.get("dry_run"):
                if result.get("valid"):
                    results["success"].append({"file": filepath.name, "dry_run": True, "blocks": result.get("blocks")})
                else:
                    results["failed"].append({"file": filepath.name, "error": result.get("errors")})
                    print(f"✗ {filepath.name} (dry-run): {result.get('errors')}")
                continue

            if result.get("skipped"):
                results["skipped"].append({"file": filepath.name, "reason": result.get("reason", "unchanged")})
                # Don't print for skipped files to reduce noise
            else:
                results["success"].append(
                    {"file": filepath.name, "page_id": result["page_id"], "type": result["type"], "url": result["url"]}
                )
                print(f"✓ {filepath.name} → {result['type']}")
        except Exception as e:
            results["failed"].append({"file": filepath.name, "error": str(e)})
            print(f"✗ {filepath.name}: {e}")

    # Mark task as run (only for real runs)
    if DB_AVAILABLE and not dry_run:
        db = get_db()
        db.mark_task_run("notion_sync")

    # Print summary
    if results["skipped"]:
        print(f"⏭ Skipped {len(results['skipped'])} unchanged files")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Notion Publisher for Syndicate")
    parser.add_argument("--sync-all", action="store_true", help="Sync all outputs to Notion")
    parser.add_argument("--file", type=str, help="Sync a specific file")
    parser.add_argument("--list", action="store_true", help="List recent documents")
    parser.add_argument("--type", type=str, help="Filter by type")
    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--force", action="store_true", help="Force sync even if unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Validate publish without creating pages")
    parser.add_argument("--no-notion", action="store_true", help="Disable wet Notion publishes (safe dry-run)")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    args = parser.parse_args()

    # Allow CLI toggle to override environment
    if getattr(args, 'no_notion', False):
        globals()['_DISABLE_NOTION_PUBLISH'] = True

    try:
        if args.test:
            publisher = NotionPublisher()
            print("✓ Connection successful!")
            print(f"  Database ID: {publisher.config.database_id[:8]}...")

        elif args.status:
            if DB_AVAILABLE:
                db = get_db()
                synced = db.get_all_synced_files()
                print(f"\nSynced files ({len(synced)}):")
                for s in synced[:20]:
                    print(f"  [{s['doc_type']}] {Path(s['file_path']).name} - {s['synced_at'][:10]}")
                if len(synced) > 20:
                    print(f"  ... and {len(synced) - 20} more")
            else:
                print("Database not available")

        elif args.list:
            publisher = NotionPublisher()
            docs = publisher.list_docs(doc_type=args.type, limit=10)
            print(f"\nRecent documents ({len(docs)}):")
            for doc in docs:
                print(f"  [{doc['type']}] {doc['title']} ({doc['date']})")

        elif args.file:
            publisher = NotionPublisher(no_client_ok=args.dry_run)
            result = publisher.sync_file(args.file, force=args.force, dry_run=args.dry_run)
            if result.get("skipped"):
                print(f"⏭ Skipped: {result.get('reason')}")
            else:
                print(f"✓ Published: {result['url']}")

        elif args.sync_all:
            results = sync_all_outputs(force=args.force, dry_run=args.dry_run)
            print(f"\n✓ Success: {len(results['success'])}")
            print(f"⏭ Skipped: {len(results.get('skipped', []))}")
            print(f"✗ Failed: {len(results['failed'])}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
