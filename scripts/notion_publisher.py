#!/usr/bin/env python3
"""
Notion Publisher for Gold Standard
Python-based publisher that syncs reports to Notion database.
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


# Document type mapping
NOTION_TYPES = [
    'journal', 'research', 'reports', 'insights', 
    'articles', 'notes', 'announcements', 'charts'
]

TYPE_PATTERNS = [
    (r'^Journal_', 'journal'),
    (r'journal', 'journal'),
    (r'^(1y|3m|monthly_yearly|weekly_rundown)', 'reports'),
    (r'_report', 'reports'),
    (r'^catalysts_', 'research'),
    (r'^research_', 'research'),
    (r'^inst_matrix', 'insights'),
    (r'^(entity|action)_insights', 'insights'),
    (r'^premarket_', 'articles'),
    (r'^analysis_', 'articles'),
    (r'^economic_calendar', 'articles'),
    (r'^notes_', 'notes'),
    (r'^announcement', 'announcements'),
    (r'^alert_', 'announcements'),
    (r'chart', 'charts'),
]

TICKER_PATTERNS = [
    r'\b(GOLD|XAUUSD|GC=F)\b',
    r'\b(SILVER|XAGUSD|SI=F)\b',
    r'\b(SPY|SPX|ES=F)\b',
    r'\b(VIX|UVXY|VXX)\b',
    r'\b(DXY|UUP)\b',
    r'\b(GDX|GDXJ|NEM)\b',
    r'\b(BTC|ETH)\b',
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
                tags.add(normalized)
        
        # Extract keywords
        keywords = ['Fed', 'FOMC', 'CPI', 'NFP', 'Inflation', 'Bullish', 'Bearish']
        for keyword in keywords:
            if keyword.lower() in content.lower():
                tags.add(keyword)
        
        return sorted(list(tags))[:10]
    
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
        filename: str = None
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
        
        # Convert to blocks
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
        
        page_id = response["id"]
        url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")
        
        return {
            "page_id": page_id,
            "url": url,
            "type": doc_type,
            "tags": tags
        }
    
    def sync_file(self, filepath: str, doc_type: str = None, tags: List[str] = None) -> Dict[str, str]:
        """Sync a local file to Notion."""
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        content = path.read_text(encoding='utf-8')
        filename = path.name
        
        # Extract title from H1 or filename
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else filename.replace('.md', '').replace('_', ' ')
        
        return self.publish(
            title=title,
            content=content,
            doc_type=doc_type,
            tags=tags,
            filename=filename
        )
    
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


def sync_all_outputs(output_dir: str = None) -> Dict[str, Any]:
    """Sync all Gold Standard outputs to Notion."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "output"
    
    output_path = Path(output_dir)
    if not output_path.exists():
        raise FileNotFoundError(f"Output directory not found: {output_dir}")
    
    publisher = NotionPublisher()
    results = {"success": [], "failed": []}
    
    # Find all markdown files recursively
    md_files = list(output_path.glob("**/*.md"))
    
    # Filter out index files
    md_files = [f for f in md_files if 'FILE_INDEX' not in f.name]
    
    for filepath in md_files:
        try:
            result = publisher.sync_file(str(filepath))
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
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Notion Publisher for Gold Standard")
    parser.add_argument('--sync-all', action='store_true', help='Sync all outputs to Notion')
    parser.add_argument('--file', type=str, help='Sync a specific file')
    parser.add_argument('--list', action='store_true', help='List recent documents')
    parser.add_argument('--type', type=str, help='Filter by type')
    parser.add_argument('--test', action='store_true', help='Test connection')
    args = parser.parse_args()
    
    try:
        if args.test:
            publisher = NotionPublisher()
            print("✓ Connection successful!")
            print(f"  Database ID: {publisher.config.database_id[:8]}...")
            
        elif args.list:
            publisher = NotionPublisher()
            docs = publisher.list_docs(doc_type=args.type, limit=10)
            print(f"\nRecent documents ({len(docs)}):")
            for doc in docs:
                print(f"  [{doc['type']}] {doc['title']} ({doc['date']})")
                
        elif args.file:
            publisher = NotionPublisher()
            result = publisher.sync_file(args.file)
            print(f"✓ Published: {result['url']}")
            
        elif args.sync_all:
            results = sync_all_outputs()
            print(f"\n✓ Success: {len(results['success'])}")
            print(f"✗ Failed: {len(results['failed'])}")
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
