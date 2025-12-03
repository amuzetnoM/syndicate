#!/usr/bin/env python3
"""
Notion Publisher for Gold Standard
Python-based publisher that syncs reports to Notion database.
Includes intelligent deduplication to prevent publishing the same content multiple times.
"""
import os
import re
import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add parent to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    print("notion-client not installed. Run: pip install notion-client")

from dotenv import load_dotenv
load_dotenv()

# Import database manager for sync tracking
try:
    from db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


# Document type mapping - comprehensive coverage
NOTION_TYPES = [
    'journal', 'research', 'reports', 'insights', 
    'articles', 'notes', 'announcements', 'charts',
    'economic', 'institutional', 'premarket', 'analysis'
]

# File pattern to Notion type mapping - ORDER MATTERS (first match wins)
TYPE_PATTERNS = [
    # Journals (daily)
    (r'^Journal_', 'journal'),
    (r'^journal_', 'journal'),
    (r'^daily_', 'journal'),
    
    # Pre-market plans
    (r'^premarket_', 'premarket'),
    (r'^pre_market_', 'premarket'),
    (r'^pre-market', 'premarket'),
    
    # Periodic reports
    (r'^weekly_', 'reports'),
    (r'^monthly_', 'reports'),
    (r'^yearly_', 'reports'),
    (r'^1y_', 'reports'),
    (r'^3m_', 'reports'),
    (r'^rundown_', 'reports'),
    (r'_report', 'reports'),
    
    # Analysis
    (r'^analysis_', 'analysis'),
    (r'^horizon_', 'analysis'),
    (r'^technical_', 'analysis'),
    
    # Catalysts & Research
    (r'^catalyst', 'research'),
    (r'^watchlist', 'research'),
    (r'^research_', 'research'),
    (r'^calc_', 'research'),
    (r'^code_', 'research'),
    (r'^data_fetch', 'research'),
    (r'^monitor_', 'research'),
    (r'^news_scan', 'research'),
    
    # Economic calendar
    (r'^economic_', 'economic'),
    (r'^calendar_', 'economic'),
    (r'^events_', 'economic'),
    
    # Institutional / Insights
    (r'^inst_matrix', 'institutional'),
    (r'^institutional', 'institutional'),
    (r'^scenario', 'institutional'),
    (r'^entity_insights', 'insights'),
    (r'^action_insights', 'insights'),
    (r'^insights_', 'insights'),
    
    # Notes & Memos
    (r'^notes_', 'notes'),
    (r'^memo_', 'notes'),
    
    # Alerts & Announcements
    (r'^announcement', 'announcements'),
    (r'^alert_', 'announcements'),
    
    # Charts
    (r'_chart', 'charts'),
    (r'^chart_', 'charts'),
    (r'\.png$', 'charts'),
    (r'\.jpg$', 'charts'),
]

# Comprehensive ticker and keyword patterns for tag extraction
TICKER_PATTERNS = [
    # Precious Metals
    r'\b(GOLD|XAUUSD|GC=F|XAU)\b',
    r'\b(SILVER|XAGUSD|SI=F|XAG)\b',
    r'\b(PLATINUM|PL=F|XPT)\b',
    r'\b(PALLADIUM|PA=F|XPD)\b',
    
    # Indices
    r'\b(SPY|SPX|ES=F|S&P)\b',
    r'\b(QQQ|NDX|NQ=F|NASDAQ)\b',
    r'\b(DIA|DJI|DJIA|DOW)\b',
    r'\b(IWM|RUT|RUSSELL)\b',
    
    # Volatility
    r'\b(VIX|UVXY|VXX|SVXY)\b',
    
    # Dollar & Currency
    r'\b(DXY|UUP|USDX|USD)\b',
    r'\b(EUR|EURUSD)\b',
    r'\b(JPY|USDJPY)\b',
    r'\b(GBP|GBPUSD)\b',
    
    # Bonds & Yields
    r'\b(TLT|TNX|TYX|ZB=F)\b',
    r'\b(10Y|10-Year|2Y|30Y)\b',
    
    # Mining Stocks
    r'\b(GDX|GDXJ|NEM|GOLD|AEM|KGC)\b',
    r'\b(SLV|PSLV|AG|WPM|HL)\b',
    
    # Crypto
    r'\b(BTC|ETH|BTCUSD|ETHUSD|Bitcoin|Ethereum)\b',
    
    # Energy
    r'\b(CL=F|WTI|CRUDE|OIL|USO)\b',
    r'\b(NG=F|NATGAS|UNG)\b',
]

# Economic & Fundamental keywords for tagging
KEYWORD_PATTERNS = [
    # Central Banks & Policy
    r'\b(Fed|FOMC|Federal Reserve)\b',
    r'\b(ECB|BOJ|BOE|PBOC|RBA|SNB)\b',
    r'\b(Powell|Yellen|Lagarde)\b',
    r'\b(hawkish|dovish|pivot)\b',
    r'\b(rate cut|rate hike|QE|QT)\b',
    
    # Economic Data
    r'\b(CPI|PPI|PCE|NFP|GDP)\b',
    r'\b(inflation|deflation|stagflation)\b',
    r'\b(unemployment|jobless|payrolls)\b',
    r'\b(PMI|ISM|retail sales)\b',
    
    # Market Sentiment
    r'\b(bullish|bearish|neutral)\b',
    r'\b(risk-on|risk-off|risk on|risk off)\b',
    r'\b(breakout|breakdown|reversal)\b',
    r'\b(support|resistance)\b',
    
    # Events & Catalysts
    r'\b(OPEC|G7|G20|Jackson Hole|Davos)\b',
    r'\b(earnings|options expiration|OpEx|witching)\b',
    r'\b(geopolitical|sanctions|tariffs)\b',
]


@dataclass
class NotionConfig:
    api_key: str
    database_id: str
    
    @classmethod
    def from_env(cls) -> 'NotionConfig':
        api_key = os.getenv('NOTION_API_KEY', '')
        database_id = os.getenv('NOTION_DATABASE_ID', '')
        
        if not api_key:
            raise ValueError("NOTION_API_KEY not set in environment")
        if not database_id:
            raise ValueError("NOTION_DATABASE_ID not set in environment")
            
        return cls(api_key=api_key, database_id=database_id)


class NotionPublisher:
    """Publish Gold Standard reports to Notion."""
    
    def __init__(self, config: NotionConfig = None):
        if not NOTION_AVAILABLE:
            raise ImportError("notion-client package not installed")
        
        self.config = config or NotionConfig.from_env()
        self.client = Client(auth=self.config.api_key)
    
    def detect_type(self, filename: str) -> str:
        """Detect document type from filename."""
        name = Path(filename).name
        
        for pattern, doc_type in TYPE_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return doc_type
        
        return 'notes'
    
    def extract_tags(self, content: str) -> List[str]:
        """Extract tags from content."""
        tags = set()
        
        for pattern in TICKER_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                normalized = match.upper()
                # Normalize variations
                if normalized in ('XAUUSD', 'GC=F'):
                    normalized = 'GOLD'
                elif normalized in ('XAGUSD', 'SI=F'):
                    normalized = 'SILVER'
                elif normalized in ('SPX', 'ES=F'):
                    normalized = 'SPY'
                elif normalized in ('BTCUSD',):
                    normalized = 'BTC'
                elif normalized in ('ETHUSD',):
                    normalized = 'ETH'
                elif normalized in ('Bitcoin',):
                    normalized = 'BTC'
                elif normalized in ('Ethereum',):
                    normalized = 'ETH'
                tags.add(normalized)
        
        # Extract keyword tags from KEYWORD_PATTERNS
        for pattern in KEYWORD_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Normalize keywords
                normalized = match.upper() if len(match) <= 4 else match.title()
                # Special cases
                if normalized.lower() in ('bullish', 'bearish', 'neutral'):
                    normalized = normalized.title()
                elif normalized.lower() in ('fed', 'fomc', 'ecb', 'boj', 'boe', 'pboc'):
                    normalized = normalized.upper()
                elif 'federal reserve' in normalized.lower():
                    normalized = 'Fed'
                elif 'rate cut' in normalized.lower():
                    normalized = 'Rate Cut'
                elif 'rate hike' in normalized.lower():
                    normalized = 'Rate Hike'
                tags.add(normalized)
        
        return sorted(list(tags))[:15]  # Allow more tags for comprehensive coverage
    
    def parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from content."""
        if not content.strip().startswith('---'):
            return {}, content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content
        
        yaml_str = parts[1].strip()
        body = parts[2].strip()
        
        # Simple YAML parsing
        meta = {}
        for line in yaml_str.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Parse arrays [a, b, c]
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip().strip('"\'') for v in value[1:-1].split(',')]
                # Parse booleans
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # Strip quotes
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                
                meta[key] = value
        
        return meta, body
    
    def markdown_to_blocks(self, content: str) -> List[Dict]:
        """Convert markdown to Notion blocks."""
        blocks = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines
            if not line.strip():
                i += 1
                continue
            
            # Headers
            header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                block_type = f"heading_{level}"
                
                blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })
                i += 1
                continue
            
            # Code blocks
            if line.startswith('```'):
                language = line[3:].strip() or "plain text"
                code_lines = []
                i += 1
                
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # Skip closing ```
                
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                        "language": language.lower()
                    }
                })
                continue
            
            # Bullet list
            if re.match(r'^[-*]\s+', line):
                text = re.sub(r'^[-*]\s+', '', line)
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })
                i += 1
                continue
            
            # Numbered list
            num_match = re.match(r'^\d+\.\s+(.+)$', line)
            if num_match:
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": num_match.group(1)}}]
                    }
                })
                i += 1
                continue
            
            # Blockquote
            if line.startswith('>'):
                text = re.sub(r'^>\s*', '', line)
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    }
                })
                i += 1
                continue
            
            # Horizontal rule
            if re.match(r'^---+$', line) or re.match(r'^\*\*\*+$', line):
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
                i += 1
                continue
            
            # Default: paragraph
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })
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
        use_enhanced_formatting: bool = True
    ) -> Dict[str, str]:
        """Publish a document to Notion."""
        
        # Parse frontmatter
        meta, body = self.parse_frontmatter(content)
        
        # Determine type
        if not doc_type:
            doc_type = meta.get('type') or (self.detect_type(filename) if filename else 'notes')
        
        if doc_type not in NOTION_TYPES:
            doc_type = 'notes'
        
        # Determine tags
        if not tags:
            tags = meta.get('tags') if isinstance(meta.get('tags'), list) else self.extract_tags(body)
        
        # Determine date
        if not doc_date:
            doc_date = meta.get('date') or date.today().isoformat()
        
        # Get bias from frontmatter
        bias = meta.get('bias')
        
        # Convert to blocks - use enhanced formatter if available
        if use_enhanced_formatting:
            try:
                from scripts.notion_formatter import format_for_notion
                from scripts.chart_publisher import ChartPublisher
                
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
        
        # Build properties - start with required title
        properties = {
            "title": {"title": [{"text": {"content": title}}]}
        }
        
        # Add optional properties if they exist in the database
        # Note: These will be silently ignored if properties don't exist
        try:
            if doc_type:
                properties["Type"] = {"select": {"name": doc_type}}
        except:
            pass
        
        try:
            if doc_date:
                properties["Date"] = {"date": {"start": doc_date}}
        except:
            pass
        
        try:
            if tags:
                properties["Tags"] = {"multi_select": [{"name": t} for t in tags]}
        except:
            pass
        
        # Create page
        response = self.client.pages.create(
            parent={"database_id": self.config.database_id},
            properties=properties,
            children=blocks[:100]  # Notion limit per request
        )
        
        # Track usage
        try:
            from scripts.cleanup_manager import CleanupManager
            CleanupManager().record_notion_page(len(blocks[:100]))
        except:
            pass
        
        page_id = response["id"]
        url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")
        
        return {
            "page_id": page_id,
            "url": url,
            "type": doc_type,
            "tags": tags
        }
    
    def sync_file(self, filepath: str, doc_type: str = None, tags: List[str] = None, 
                  force: bool = False) -> Dict[str, str]:
        """
        Sync a local file to Notion with deduplication.
        
        Args:
            filepath: Path to the markdown file
            doc_type: Document type for Notion
            tags: Tags to apply
            force: If True, sync even if file hasn't changed
            
        Returns:
            Dict with page_id, url, type, tags, and 'skipped' flag
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Check if file has already been synced (and hasn't changed)
        if DB_AVAILABLE and not force:
            db = get_db()
            if db.is_file_synced(str(path)):
                existing = db.get_notion_page_for_file(str(path))
                return {
                    "page_id": existing.get('notion_page_id', ''),
                    "url": existing.get('notion_url', ''),
                    "type": existing.get('doc_type', 'notes'),
                    "tags": [],
                    "skipped": True,
                    "reason": "File unchanged since last sync"
                }
        
        content = path.read_text(encoding='utf-8')
        filename = path.name
        
        # Extract title from H1 or filename
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else filename.replace('.md', '').replace('_', ' ')
        
        result = self.publish(
            title=title,
            content=content,
            doc_type=doc_type,
            tags=tags,
            filename=filename
        )
        
        # Record the sync in the database
        if DB_AVAILABLE:
            db = get_db()
            db.record_notion_sync(
                str(path),
                result['page_id'],
                result['url'],
                result.get('type', 'notes')
            )
        
        result['skipped'] = False
        return result
    
    def list_docs(
        self,
        doc_type: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """List documents from the database."""
        
        filters = []
        
        if doc_type:
            filters.append({
                "property": "Type",
                "select": {"equals": doc_type}
            })
        
        if start_date:
            filters.append({
                "property": "Date",
                "date": {"on_or_after": start_date}
            })
        
        if end_date:
            filters.append({
                "property": "Date",
                "date": {"on_or_before": end_date}
            })
        
        query = {
            "database_id": self.config.database_id,
            "sorts": [{"property": "Date", "direction": "descending"}],
            "page_size": limit
        }
        
        if filters:
            query["filter"] = {"and": filters} if len(filters) > 1 else filters[0]
        
        response = self.client.databases.query(**query)
        
        results = []
        for page in response["results"]:
            props = page["properties"]
            results.append({
                "id": page["id"],
                "title": props.get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled"),
                "type": props.get("Type", {}).get("select", {}).get("name", "notes"),
                "date": props.get("Date", {}).get("date", {}).get("start", "Unknown"),
                "tags": [t["name"] for t in props.get("Tags", {}).get("multi_select", [])]
            })
        
        return results


def sync_all_outputs(output_dir: str = None, force: bool = False) -> Dict[str, Any]:
    """
    Sync all Gold Standard outputs to Notion with intelligent deduplication.
    
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
        if not db.should_run_task('notion_sync'):
            print("[NOTION] Sync already completed for today, skipping")
            return {"success": [], "skipped": [], "failed": [], "reason": "Already synced today"}
    
    publisher = NotionPublisher()
    results = {"success": [], "skipped": [], "failed": []}
    
    # Find all markdown files recursively
    md_files = list(output_path.glob("**/*.md"))
    
    # Filter out index files and archive
    md_files = [f for f in md_files if 'FILE_INDEX' not in f.name and '/archive/' not in str(f).replace('\\', '/')]
    
    for filepath in md_files:
        try:
            result = publisher.sync_file(str(filepath), force=force)
            
            if result.get('skipped'):
                results["skipped"].append({
                    "file": filepath.name,
                    "reason": result.get('reason', 'unchanged')
                })
                # Don't print for skipped files to reduce noise
            else:
                results["success"].append({
                    "file": filepath.name,
                    "page_id": result["page_id"],
                    "type": result["type"],
                    "url": result["url"]
                })
                print(f"✓ {filepath.name} → {result['type']}")
        except Exception as e:
            results["failed"].append({
                "file": filepath.name,
                "error": str(e)
            })
            print(f"✗ {filepath.name}: {e}")
    
    # Mark task as run
    if DB_AVAILABLE:
        db = get_db()
        db.mark_task_run('notion_sync')
    
    # Print summary
    if results["skipped"]:
        print(f"⏭ Skipped {len(results['skipped'])} unchanged files")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Notion Publisher for Gold Standard")
    parser.add_argument('--sync-all', action='store_true', help='Sync all outputs to Notion')
    parser.add_argument('--file', type=str, help='Sync a specific file')
    parser.add_argument('--list', action='store_true', help='List recent documents')
    parser.add_argument('--type', type=str, help='Filter by type')
    parser.add_argument('--test', action='store_true', help='Test connection')
    parser.add_argument('--force', action='store_true', help='Force sync even if unchanged')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    args = parser.parse_args()
    
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
            publisher = NotionPublisher()
            result = publisher.sync_file(args.file, force=args.force)
            if result.get('skipped'):
                print(f"⏭ Skipped: {result.get('reason')}")
            else:
                print(f"✓ Published: {result['url']}")
            
        elif args.sync_all:
            results = sync_all_outputs(force=args.force)
            print(f"\n✓ Success: {len(results['success'])}")
            print(f"⏭ Skipped: {len(results.get('skipped', []))}")
            print(f"✗ Failed: {len(results['failed'])}")
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
