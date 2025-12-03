#!/usr/bin/env python3
"""
Frontmatter Utilities for Gold Standard Reports

Adds YAML frontmatter headers to markdown files for MCP publishing.
Supports automatic type detection and tag extraction.
"""
import os
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pathlib import Path


# Mapping of file patterns to Notion types
FILE_TYPE_PATTERNS = {
    'journal': [
        r'^Journal_\d{4}-\d{2}-\d{2}\.md$',
        r'journal.*\.md$',
    ],
    'reports': [
        r'^(?:1y|3m|monthly_yearly).*\.md$',
        r'^weekly_rundown.*\.md$',
        r'_report.*\.md$',
    ],
    'research': [
        r'^research_.*\.md$',
        r'^catalysts_.*\.md$',
    ],
    'insights': [
        r'^inst_matrix.*\.md$',
        r'^insights_.*\.md$',
        r'^entity_insights.*\.md$',
        r'^action_insights.*\.md$',
    ],
    'articles': [
        r'^premarket_.*\.md$',
        r'^analysis_.*\.md$',
    ],
    'notes': [
        r'^notes_.*\.md$',
        r'^memo_.*\.md$',
    ],
    'announcements': [
        r'^announcement.*\.md$',
        r'^alert_.*\.md$',
    ],
    'charts': [
        r'.*_chart.*\.md$',
        r'^chart_.*\.md$',
    ],
}

# Common ticker patterns to extract as tags
TICKER_PATTERNS = [
    r'\b(GOLD|XAUUSD|GC=F)\b',
    r'\b(SILVER|XAGUSD|SI=F)\b',
    r'\b(SPY|SPX|ES=F)\b',
    r'\b(VIX|UVXY|VXX)\b',
    r'\b(DXY|UUP|USDX)\b',
    r'\b(TLT|TNX|ZB=F)\b',
    r'\b(GDX|GDXJ|NEM|GOLD)\b',
    r'\b(BTC|ETH|BTCUSD|ETHUSD)\b',
]


def detect_type(filename: str) -> str:
    """Detect Notion type from filename pattern."""
    name = os.path.basename(filename)
    
    for doc_type, patterns in FILE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return doc_type
    
    return 'notes'  # Default fallback


def extract_tags_from_content(content: str) -> List[str]:
    """Extract relevant tags from markdown content."""
    tags = set()
    
    # Extract tickers
    for pattern in TICKER_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        tags.update(match.upper() for match in matches)
    
    # Normalize common variations
    tag_map = {
        'XAUUSD': 'GOLD',
        'GC=F': 'GOLD',
        'XAGUSD': 'SILVER',
        'SI=F': 'SILVER',
        'SPX': 'SPY',
        'ES=F': 'SPY',
    }
    
    normalized = set()
    for tag in tags:
        normalized.add(tag_map.get(tag, tag))
    
    # Extract keywords from headers
    header_pattern = r'^#{1,3}\s+(.+)$'
    headers = re.findall(header_pattern, content, re.MULTILINE)
    
    keywords = ['Fed', 'FOMC', 'CPI', 'NFP', 'GDP', 'Inflation', 'Recession',
                'Bullish', 'Bearish', 'Technical', 'Fundamental', 'Risk']
    
    for header in headers:
        for keyword in keywords:
            if keyword.lower() in header.lower():
                normalized.add(keyword)
    
    return sorted(list(normalized))[:10]  # Limit to 10 tags


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract date from filename if present."""
    name = os.path.basename(filename)
    
    # Pattern: _YYYY-MM-DD or _YYYY_MM_DD
    date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', name)
    if date_match:
        return date_match.group(1).replace('_', '-')
    
    return None


def generate_frontmatter(
    filename: str,
    content: str,
    doc_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate YAML frontmatter for a markdown file.
    
    Args:
        filename: Name of the file
        content: Markdown content
        doc_type: Override auto-detected type
        tags: Override auto-extracted tags
        title: Override title extraction
        custom_fields: Additional frontmatter fields
    
    Returns:
        YAML frontmatter string (including --- delimiters)
    """
    # Auto-detect type if not provided
    if doc_type is None:
        doc_type = detect_type(filename)
    
    # Auto-extract tags if not provided
    if tags is None:
        tags = extract_tags_from_content(content)
    
    # Extract title from first H1 if not provided
    if title is None:
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
        else:
            # Use filename as title
            name = os.path.basename(filename)
            title = os.path.splitext(name)[0].replace('_', ' ').replace('-', ' ')
    
    # Extract date
    doc_date = extract_date_from_filename(filename) or str(date.today())
    
    # Build frontmatter
    lines = ['---']
    lines.append(f'type: {doc_type}')
    lines.append(f'title: "{title}"')
    lines.append(f'date: {doc_date}')
    lines.append(f'generated: {datetime.now().isoformat()}')
    
    if tags:
        tags_str = ', '.join(tags)
        lines.append(f'tags: [{tags_str}]')
    
    # Add custom fields
    if custom_fields:
        for key, value in custom_fields.items():
            if isinstance(value, list):
                value_str = ', '.join(str(v) for v in value)
                lines.append(f'{key}: [{value_str}]')
            elif isinstance(value, bool):
                lines.append(f'{key}: {str(value).lower()}')
            else:
                lines.append(f'{key}: {value}')
    
    lines.append('---')
    lines.append('')  # Empty line after frontmatter
    
    return '\n'.join(lines)


def add_frontmatter(
    content: str,
    filename: str,
    doc_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> str:
    """
    Add frontmatter to markdown content.
    
    If content already has frontmatter, it will be replaced.
    """
    # Check if content already has frontmatter
    if content.strip().startswith('---'):
        # Remove existing frontmatter
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    
    frontmatter = generate_frontmatter(filename, content, doc_type, tags, **kwargs)
    return frontmatter + content


def has_frontmatter(content: str) -> bool:
    """Check if content already has YAML frontmatter."""
    return content.strip().startswith('---')


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse frontmatter from markdown content.
    
    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    if not has_frontmatter(content):
        return {}, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    frontmatter_str = parts[1].strip()
    remaining = parts[2].strip()
    
    # Simple YAML parsing (for basic key: value pairs)
    frontmatter = {}
    for line in frontmatter_str.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Parse arrays [a, b, c]
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].split(',')
                value = [item.strip().strip('"\'') for item in items]
            # Parse booleans
            elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            # Parse numbers
            elif value.replace('.', '').replace('-', '').isdigit():
                value = float(value) if '.' in value else int(value)
            # Strip quotes from strings
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            frontmatter[key] = value
    
    return frontmatter, remaining


# Convenience functions for specific report types
def journal_frontmatter(content: str, filename: str, bias: str = 'NEUTRAL', 
                        gold_price: float = 0, **kwargs) -> str:
    """Generate frontmatter for journal entries."""
    return add_frontmatter(
        content, filename,
        doc_type='journal',
        custom_fields={
            'bias': bias,
            'gold_price': gold_price,
            **kwargs
        }
    )


def report_frontmatter(content: str, filename: str, report_type: str = 'weekly', **kwargs) -> str:
    """Generate frontmatter for reports."""
    return add_frontmatter(
        content, filename,
        doc_type='reports',
        custom_fields={
            'report_type': report_type,
            **kwargs
        }
    )


def research_frontmatter(content: str, filename: str, **kwargs) -> str:
    """Generate frontmatter for research documents."""
    return add_frontmatter(content, filename, doc_type='research', **kwargs)


def insights_frontmatter(content: str, filename: str, **kwargs) -> str:
    """Generate frontmatter for insights."""
    return add_frontmatter(content, filename, doc_type='insights', **kwargs)


def chart_frontmatter(content: str, filename: str, ticker: str = '', **kwargs) -> str:
    """Generate frontmatter for chart documents."""
    tags = [ticker.upper()] if ticker else None
    return add_frontmatter(
        content, filename,
        doc_type='charts',
        tags=tags,
        custom_fields={'ticker': ticker.upper(), **kwargs}
    )


if __name__ == '__main__':
    # Test the module
    sample_content = """# Gold Analysis - Weekly Report

## Market Overview

Gold (XAUUSD) is showing bullish momentum as the Fed signals rate cuts.
Silver follows with strong relative strength.

## Technical Analysis

- RSI: 65 (neutral-bullish)
- ADX: 28 (trending)
- Support: $2,650
- Resistance: $2,720

## Outlook

Bullish bias for the week ahead.
"""
    
    result = add_frontmatter(sample_content, "weekly_rundown_2025-12-03.md")
    print(result)
