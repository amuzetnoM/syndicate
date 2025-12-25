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
Notion Formatter for Syndicate

Transforms markdown reports into visually rich Notion blocks.
Uses callouts, toggles, colors, columns, and proper formatting
to create professional-looking pages.
"""

import html as _html
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple


class BlockColor(Enum):
    """Notion block colors."""

    DEFAULT = "default"
    GRAY = "gray"
    BROWN = "brown"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    PINK = "pink"
    RED = "red"
    # Background variants
    GRAY_BG = "gray_background"
    BROWN_BG = "brown_background"
    ORANGE_BG = "orange_background"
    YELLOW_BG = "yellow_background"
    GREEN_BG = "green_background"
    BLUE_BG = "blue_background"
    PURPLE_BG = "purple_background"
    PINK_BG = "pink_background"
    RED_BG = "red_background"


# Emoji mappings for different content types
SECTION_EMOJIS = {
    "market": "📊",
    "context": "🌍",
    "analysis": "🔍",
    "technical": "📈",
    "sentiment": "💭",
    "outlook": "🎯",
    "risk": "⚠️",
    "catalyst": "⚡",
    "summary": "📋",
    "key": "🔑",
    "price": "💰",
    "action": "🎬",
    "trade": "💹",
    "position": "📍",
    "support": "🛡️",
    "resistance": "🚧",
    "trend": "📉",
    "momentum": "🚀",
    "economic": "📅",
    "calendar": "📆",
    "institutional": "🏦",
    "research": "🔬",
    "premarket": "🌅",
    "journal": "📓",
    "report": "📑",
    "weekly": "📰",
    "monthly": "📊",
    "yearly": "📈",
    "insight": "💡",
    "data": "📉",
    "fed": "🏛️",
    "fomc": "🏛️",
    "gold": "🥇",
    "silver": "🥈",
    "default": "📌",
}

# Document type emoji mapping
DOC_TYPE_EMOJIS = {
    "journal": "📓",
    "premarket": "🌅",
    "reports": "📑",
    "analysis": "🔍",
    "research": "🔬",
    "economic": "📅",
    "institutional": "🏦",
    "insights": "💡",
    "notes": "📝",
    "announcements": "📢",
    "charts": "📊",
}

# Bias color mapping
BIAS_COLORS = {
    "BULLISH": BlockColor.GREEN,
    "BEARISH": BlockColor.RED,
    "NEUTRAL": BlockColor.YELLOW,
}

BIAS_BG_COLORS = {
    "BULLISH": BlockColor.GREEN_BG,
    "BEARISH": BlockColor.RED_BG,
    "NEUTRAL": BlockColor.YELLOW_BG,
}


def rich_text(
    content: str, bold: bool = False, italic: bool = False, code: bool = False, color: str = "default", link: str = None
) -> Dict:
    """Create a rich text object."""
    text_obj = {
        "type": "text",
        "text": {"content": content, "link": {"url": link} if link else None},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "strikethrough": False,
            "underline": False,
            "code": code,
            "color": color,
        },
    }
    return text_obj


def parse_inline_formatting(text: str, default_color: str = "default") -> List[Dict]:
    """Parse markdown inline formatting to rich text objects."""
    result = []

    # Pattern for **bold**, *italic*, `code`, and combinations
    pattern = r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|([^*`]+))"

    for match in re.finditer(pattern, text):
        if match.group(2):  # ***bold italic***
            result.append(rich_text(match.group(2), bold=True, italic=True, color=default_color))
        elif match.group(3):  # **bold**
            result.append(rich_text(match.group(3), bold=True, color=default_color))
        elif match.group(4):  # *italic*
            result.append(rich_text(match.group(4), italic=True, color=default_color))
        elif match.group(5):  # `code`
            result.append(rich_text(match.group(5), code=True))
        elif match.group(6):  # plain text
            result.append(rich_text(match.group(6), color=default_color))

    if not result:
        result.append(rich_text(text, color=default_color))

    return result


def heading_block(level: int, text: str, color: str = "default", toggleable: bool = False) -> Dict:
    """Create a heading block."""
    block_type = f"heading_{level}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": parse_inline_formatting(text), "color": color, "is_toggleable": toggleable},
    }


def paragraph_block(text: str, color: str = "default") -> Dict:
    """Create a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": parse_inline_formatting(text, color), "color": color},
    }


def callout_block(text: str, emoji: str = "💡", color: str = "default", children: List[Dict] = None) -> Dict:
    """Create a callout block with icon."""
    block = {
        "object": "block",
        "type": "callout",
        "callout": {"rich_text": parse_inline_formatting(text), "icon": {"emoji": emoji}, "color": color},
    }
    if children:
        block["callout"]["children"] = children
    return block


def toggle_block(title: str, children: List[Dict], color: str = "default") -> Dict:
    """Create a toggle block with children."""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {"rich_text": parse_inline_formatting(title), "color": color, "children": children},
    }


def bulleted_list_item(text: str, color: str = "default", children: List[Dict] = None) -> Dict:
    """Create a bulleted list item."""
    block = {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": parse_inline_formatting(text, color), "color": color},
    }
    if children:
        block["bulleted_list_item"]["children"] = children
    return block


def numbered_list_item(text: str, color: str = "default") -> Dict:
    """Create a numbered list item."""
    return {
        "object": "block",
        "type": "numbered_list_item",
        "numbered_list_item": {"rich_text": parse_inline_formatting(text, color), "color": color},
    }


def quote_block(text: str, color: str = "default") -> Dict:
    """Create a quote block."""
    return {"object": "block", "type": "quote", "quote": {"rich_text": parse_inline_formatting(text), "color": color}}


def code_block(code: str, language: str = "plain text") -> Dict:
    """Create a code block."""
    return {"object": "block", "type": "code", "code": {"rich_text": [rich_text(code)], "language": language.lower()}}


def divider_block() -> Dict:
    """Create a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


def table_of_contents_block(color: str = "default") -> Dict:
    """Create a table of contents block."""
    return {"object": "block", "type": "table_of_contents", "table_of_contents": {"color": color}}


def image_block(url: str, caption: str = None) -> Dict:
    """Create an image block from external URL."""
    block = {"object": "block", "type": "image", "image": {"type": "external", "external": {"url": url}}}
    if caption:
        block["image"]["caption"] = [rich_text(caption)]
    return block


def bookmark_block(url: str, caption: str = None) -> Dict:
    """Create a bookmark block for links."""
    block = {"object": "block", "type": "bookmark", "bookmark": {"url": url}}
    if caption:
        block["bookmark"]["caption"] = [rich_text(caption)]
    return block


def table_block(rows: List[List[str]], has_header: bool = True) -> List[Dict]:
    """Create a table with rows."""
    if not rows:
        return []

    # Determine table width as the maximum number of cells in any row
    table_width = max((len(r) for r in rows), default=0)

    table = {
        "object": "block",
        "type": "table",
        "table": {"table_width": table_width, "has_column_header": has_header, "has_row_header": False, "children": []},
    }

    for row in rows:
        # Normalize each row to the table_width by padding empty cells or truncating
        norm = list(row)[:table_width] + [""] * max(0, table_width - len(row))
        cells = []
        for cell in norm:
            cells.append([rich_text(str(cell))])

        table["table"]["children"].append({"object": "block", "type": "table_row", "table_row": {"cells": cells}})

    return [table]


def column_list_block(columns: List[List[Dict]]) -> Dict:
    """Create a column list with multiple columns."""
    if len(columns) < 2:
        # Notion requires at least 2 columns
        return None

    column_blocks = []

    for col_children in columns:
        column_blocks.append({"object": "block", "type": "column", "column": {"children": col_children}})

    return {"object": "block", "type": "column_list", "column_list": {"children": column_blocks}}


def get_section_emoji(header_text: str) -> str:
    """Get appropriate emoji for a section header."""
    text_lower = header_text.lower()

    for keyword, emoji in SECTION_EMOJIS.items():
        if keyword in text_lower:
            return emoji

    return SECTION_EMOJIS["default"]


def detect_bias_in_text(text: str) -> Optional[str]:
    """Detect bias keywords in text."""
    text_upper = text.upper()
    if "BULLISH" in text_upper:
        return "BULLISH"
    elif "BEARISH" in text_upper:
        return "BEARISH"
    elif "NEUTRAL" in text_upper:
        return "NEUTRAL"
    return None


def color_for_bias(bias: str, background: bool = False) -> str:
    """Get color for a bias."""
    if background:
        return BIAS_BG_COLORS.get(bias, BlockColor.DEFAULT).value
    return BIAS_COLORS.get(bias, BlockColor.DEFAULT).value


def parse_markdown_table(lines: List[str], start_idx: int) -> Tuple[List[List[str]], int]:
    """Parse a markdown table starting at the given index."""
    rows = []
    i = start_idx

    while i < len(lines):
        line = lines[i].strip()

        # Check if it's a table row
        if not line.startswith("|"):
            break

        # Skip separator rows (|---|---|)
        if re.match(r"^\|[\s\-:]+\|$", line.replace("|", "|").replace("-", "-")):
            i += 1
            continue

        # Parse cells
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)

        i += 1

    return rows, i


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags and unescape HTML entities."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return _html.unescape(cleaned).strip()


def convert_html_table_to_markdown(table_html: str) -> str:
    """Convert a single HTML table block into a markdown table (code fenced)."""
    # Extract header cells
    headers = re.findall(r"<th[^>]*>(.*?)</th>", table_html, flags=re.S | re.I)

    # Extract all rows
    rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.S | re.I)
    rows = []
    for tr in rows_html:
        # extract both td and th cells
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)
        if cells:
            rows.append([_strip_html_tags(c) for c in cells])

    # Build markdown table
    md_lines = []
    if headers:
        header_texts = [_strip_html_tags(h) for h in headers]
        md_lines.append("| " + " | ".join(header_texts) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(header_texts)) + " |")
        # Append rows, skipping any that are exactly the header
        for r in rows:
            if r == header_texts:
                continue
            # Normalize row length to header length
            row = r + [""] * (len(header_texts) - len(r))
            md_lines.append("| " + " | ".join(row) + " |")
    else:
        # No header: use first row as header if present
        if rows:
            maxcols = max(len(r) for r in rows)
            # Use empty header names
            md_lines.append("| " + " | ".join([""] * maxcols) + " |")
            md_lines.append("| " + " | ".join(["---"] * maxcols) + " |")
            for r in rows:
                r = r + [""] * (maxcols - len(r))
                md_lines.append("| " + " | ".join(r) + " |")
        else:
            return ""

    md = "\n".join(md_lines)
    # Return raw markdown table text so the markdown parser can pick it up as a table
    return "\n" + md + "\n"


def convert_all_html_tables_to_markdown(content: str) -> str:
    """Find all <table>...</table> blocks and replace them with markdown tables."""
    table_pattern = re.compile(r"<table[^>]*>.*?</table>", flags=re.S | re.I)

    def _repl(match):
        table_html = match.group(0)
        try:
            return convert_html_table_to_markdown(table_html)
        except Exception:
            return ""

    return table_pattern.sub(_repl, content)


class NotionFormatter:
    """Transform markdown to enhanced Notion blocks."""

    def __init__(self, bias: str = None):
        self.bias = bias
        self.blocks = []

    def format_document(self, content: str, doc_type: str = "journal") -> List[Dict]:
        """Format a full document into Notion blocks."""
        self.blocks = []

        # Remove frontmatter
        if content.strip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Extract bias from frontmatter if present
                frontmatter = parts[1]
                if "bias:" in frontmatter.lower():
                    match = re.search(r"bias:\s*(\w+)", frontmatter, re.IGNORECASE)
                    if match:
                        self.bias = match.group(1).upper()
                content = parts[2].strip()

        # Convert HTML tables to Markdown to improve Notion conversion
        content = convert_all_html_tables_to_markdown(content)

        # Add header callout based on doc type
        self._add_header_callout(doc_type)

        # Add table of contents for longer documents
        if content.count("\n") > 30:
            self.blocks.append(table_of_contents_block())
            self.blocks.append(divider_block())

        # Process content
        lines = content.split("\n")
        self._process_lines(lines)

        return self.blocks

    def _add_header_callout(self, doc_type: str):
        """Add a styled header callout based on document type."""
        # Comprehensive emoji mapping for all document types
        emoji_map = {
            "journal": "📓",
            "premarket": "🌅",
            "reports": "📑",
            "analysis": "🔍",
            "research": "🔬",
            "economic": "📅",
            "institutional": "🏦",
            "insights": "💡",
            "notes": "📝",
            "announcements": "📢",
            "charts": "📊",
            "catalyst": "⚡",
            "articles": "📰",
            "weekly": "📰",
            "monthly": "📊",
            "yearly": "📈",
        }

        # Comprehensive color mapping for all document types
        color_map = {
            "journal": "yellow_background",
            "premarket": "orange_background",
            "reports": "blue_background",
            "analysis": "purple_background",
            "research": "purple_background",
            "economic": "green_background",
            "institutional": "blue_background",
            "insights": "green_background",
            "notes": "gray_background",
            "announcements": "red_background",
            "charts": "blue_background",
            "catalyst": "red_background",
            "articles": "gray_background",
            "weekly": "blue_background",
            "monthly": "purple_background",
            "yearly": "brown_background",
        }

        emoji = emoji_map.get(doc_type, "📄")
        color = color_map.get(doc_type, "default")

        # Format document type for display
        display_type = doc_type.replace("_", " ").upper()

        # Add bias indicator if present
        if self.bias:
            bias_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(self.bias, "⚪")
            header_text = f"**{display_type}** | Bias: {bias_emoji} {self.bias}"
        else:
            header_text = f"**{display_type}**"

        self.blocks.append(callout_block(header_text, emoji=emoji, color=color))

    def _process_lines(self, lines: List[str]):
        """Process markdown lines into blocks."""
        i = 0
        _current_section = []  # Reserved for future section grouping

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines between sections
            if not stripped:
                i += 1
                continue

            # Headers
            header_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)

                # Style headers based on content
                color = "default"
                bias = detect_bias_in_text(text)
                if bias:
                    color = color_for_bias(bias)

                # Add emoji for H2 sections
                if level == 2:
                    emoji = get_section_emoji(text)
                    text = f"{emoji} {text}"

                self.blocks.append(heading_block(level, text, color=color))
                i += 1
                continue

            # Horizontal rule / divider
            if re.match(r"^---+$", stripped) or re.match(r"^\*\*\*+$", stripped):
                self.blocks.append(divider_block())
                i += 1
                continue

            # Code blocks
            if stripped.startswith("```"):
                language = stripped[3:].strip() or "plain text"
                code_lines = []
                i += 1

                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing ```

                self.blocks.append(code_block("\n".join(code_lines), language))
                continue

            # Tables
            if stripped.startswith("|"):
                rows, i = parse_markdown_table(lines, i)
                if rows:
                    self.blocks.extend(table_block(rows))
                continue

            # Blockquotes - convert to callouts
            if stripped.startswith(">"):
                quote_text = re.sub(r"^>\s*", "", stripped)

                # Detect if it's a special callout
                if any(word in quote_text.lower() for word in ["warning", "caution", "alert"]):
                    self.blocks.append(callout_block(quote_text, emoji="⚠️", color="yellow_background"))
                elif any(word in quote_text.lower() for word in ["note", "info", "tip"]):
                    self.blocks.append(callout_block(quote_text, emoji="💡", color="blue_background"))
                elif any(word in quote_text.lower() for word in ["important", "key"]):
                    self.blocks.append(callout_block(quote_text, emoji="🔑", color="orange_background"))
                else:
                    self.blocks.append(quote_block(quote_text))

                i += 1
                continue

            # Bullet lists with special handling
            bullet_match = re.match(r"^[-*]\s+(.+)$", stripped)
            if bullet_match:
                text = bullet_match.group(1)
                color = "default"

                # Color based on content
                if any(word in text.lower() for word in ["bullish", "positive", "support", "strength"]):
                    color = "green"
                elif any(word in text.lower() for word in ["bearish", "negative", "resistance", "weakness"]):
                    color = "red"
                elif any(word in text.lower() for word in ["neutral", "consolidat"]):
                    color = "yellow"

                self.blocks.append(bulleted_list_item(text, color=color))
                i += 1
                continue

            # Numbered lists
            num_match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if num_match:
                self.blocks.append(numbered_list_item(num_match.group(1)))
                i += 1
                continue

            # Regular paragraphs - detect and color special content
            color = "default"
            bias = detect_bias_in_text(stripped)
            if bias:
                color = color_for_bias(bias)

            # Highlight key metrics
            if re.search(r"\b(RSI|ADX|ATR|SMA|EMA|MACD)\b", stripped):
                color = "blue"
            elif re.search(r"\$[\d,]+", stripped):  # Price mentions
                color = "green"

            self.blocks.append(paragraph_block(stripped, color=color))
            i += 1

    def create_summary_callout(self, summary_text: str) -> Dict:
        """Create a prominent summary callout."""
        color = (
            "green_background"
            if self.bias == "BULLISH"
            else "red_background"
            if self.bias == "BEARISH"
            else "yellow_background"
        )

        return callout_block(f"**Summary:** {summary_text}", emoji="📋", color=color)

    def create_metrics_columns(self, metrics: Dict[str, str]) -> Optional[Dict]:
        """Create a two-column layout for metrics."""
        if len(metrics) < 2:
            return None

        items = list(metrics.items())
        mid = len(items) // 2

        left_col = [callout_block(f"**{k}:** {v}", emoji="📊", color="gray_background") for k, v in items[:mid]]

        right_col = [callout_block(f"**{k}:** {v}", emoji="📊", color="gray_background") for k, v in items[mid:]]

        return column_list_block([left_col, right_col])


def format_for_notion(
    content: str, doc_type: str = "journal", bias: str = None, chart_urls: Dict[str, str] = None
) -> List[Dict]:
    """
    Main entry point: Format markdown content for Notion.

    Args:
        content: Markdown content (may include frontmatter)
        doc_type: Document type (journal, reports, etc.)
        bias: Market bias (BULLISH, BEARISH, NEUTRAL)
        chart_urls: Dict mapping ticker -> image URL for charts

    Returns:
        List of Notion block objects
    """
    formatter = NotionFormatter(bias=bias)
    blocks = formatter.format_document(content, doc_type)

    # Add Related Charts section if chart URLs provided
    if chart_urls:
        blocks.append(divider_block())
        blocks.append(heading_block(2, "📊 Related Charts", color="blue"))

        # Create a callout with chart info
        chart_list = ", ".join(chart_urls.keys())
        blocks.append(
            callout_block(
                f"Charts for tickers mentioned in this report: **{chart_list}**", emoji="📈", color="blue_background"
            )
        )

        # Add each chart as an image
        for ticker, url in chart_urls.items():
            # Add ticker label
            blocks.append(paragraph_block(f"**{ticker}**", color="blue"))
            # Add the chart image
            blocks.append(image_block(url, caption=f"{ticker} Chart"))

    return blocks


if __name__ == "__main__":
    # Test with sample content
    sample = """---
type: journal
bias: BULLISH
---
# Gold Analysis - December 3, 2025

## Market Context

The macro environment is supportive of precious metals. **Key drivers:**

- DXY weakness (below 200 SMA)
- Treasury yields softening
- VIX subdued below 20

> Note: This is a significant shift from last week's neutral stance.

## Technical Analysis

| Indicator | Value | Signal |
|-----------|-------|--------|
| RSI | 72.43 | Overbought |
| ADX | 28 | Trending |
| ATR | 45 | High volatility |

### Price Levels

- **Support:** $2,650
- **Resistance:** $2,720

## Outlook

Bullish bias for the week. Target: $2,700+

---

*Generated by Syndicate*
"""

    blocks = format_for_notion(sample, doc_type="journal", bias="BULLISH")

    import json

    print(json.dumps(blocks[:5], indent=2))
    print(f"\nTotal blocks: {len(blocks)}")
