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
Chart Publisher for Syndicate
Uploads chart images to image hosting and maintains URL mapping.
Supports: imgbb (free), local file serving, or direct Notion upload.
"""

import base64
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add parent to path
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


# Chart directories
CHART_DIRS = [
    PROJECT_ROOT / "output" / "charts",
    PROJECT_ROOT / "output" / "reports" / "charts",
]

# Cache file for uploaded URLs
CACHE_FILE = PROJECT_ROOT / "output" / "chart_urls.json"

# Ticker patterns to detect in content
TICKER_MAP = {
    "GOLD": ["GOLD", "XAUUSD", "GC=F", "gold", "Gold"],
    "SILVER": ["SILVER", "XAGUSD", "SI=F", "silver", "Silver"],
    "SPX": ["SPX", "SPY", "ES=F", "S&P", "ES", "spx"],
    "VIX": ["VIX", "UVXY", "VXX", "vix", "volatility"],
    "DXY": ["DXY", "UUP", "dollar", "Dollar", "USD"],
    "YIELD": ["YIELD", "TLT", "TNX", "yield", "bonds", "treasury", "10Y"],
}


class ChartPublisher:
    """Upload and manage chart images for Notion integration."""

    def __init__(self, api_key: str = None):
        """Initialize with imgbb API key (free tier: 32MB/month)."""
        self.api_key = api_key or os.getenv("IMGBB_API_KEY")
        self.cache = self._load_cache()
        self.upload_url = "https://api.imgbb.com/1/upload"

    def _load_cache(self) -> Dict:
        """Load cached URLs from file."""
        if CACHE_FILE.exists():
            try:
                return json.loads(CACHE_FILE.read_text())
            except Exception:
                pass
        return {"charts": {}, "last_updated": None}

    def _save_cache(self):
        """Save cache to file."""
        self.cache["last_updated"] = datetime.now().isoformat()
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(self.cache, indent=2))

    def _get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of file for change detection."""
        return hashlib.md5(filepath.read_bytes()).hexdigest()

    def _get_cached_url_for_file(self, filepath: Path) -> Optional[str]:
        """Get cached URL for a file if it exists."""
        cache_key = filepath.name
        if cache_key in self.cache.get("charts", {}):
            return self.cache["charts"][cache_key].get("url")
        return None

    def find_charts(self, tickers: List[str] = None) -> Dict[str, Path]:
        """Find chart files, optionally filtered by tickers."""
        charts = {}

        for chart_dir in CHART_DIRS:
            if not chart_dir.exists():
                continue

            for img_file in chart_dir.glob("*.png"):
                ticker = img_file.stem.split("_")[0].upper()

                if tickers is None or ticker in [t.upper() for t in tickers]:
                    # Prefer non-dated version, but use dated if that's all we have
                    if ticker not in charts or "_" not in img_file.stem:
                        charts[ticker] = img_file

        return charts

    def detect_tickers_in_content(self, content: str) -> List[str]:
        """Detect which tickers are mentioned in content."""
        found = set()

        for ticker, patterns in TICKER_MAP.items():
            for pattern in patterns:
                if pattern in content:
                    found.add(ticker)
                    break

        return sorted(list(found))

    def upload_to_imgbb(self, filepath: Path, name: str = None) -> Optional[str]:
        """Upload image to imgbb and return URL."""
        if not self.api_key:
            print("⚠ No IMGBB_API_KEY set - using local file reference")
            return None

        # Check limits before uploading
        file_size = filepath.stat().st_size
        try:
            from scripts.cleanup_manager import CleanupManager

            cleanup = CleanupManager()
            can_upload, reason = cleanup.should_upload_chart(file_size)
            if not can_upload:
                print(f"⚠ Skipping upload: {reason}")
                return self._get_cached_url_for_file(filepath)
        except ImportError:
            pass  # Cleanup manager not available, proceed anyway

        try:
            # Read and encode image
            with open(filepath, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            # Upload
            response = requests.post(
                self.upload_url,
                data={
                    "key": self.api_key,
                    "image": img_data,
                    "name": name or filepath.stem,
                },
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Record usage
                    try:
                        from scripts.cleanup_manager import CleanupManager

                        CleanupManager().record_imgbb_upload(file_size)
                    except Exception:
                        pass
                    return data["data"]["url"]

            print(f"⚠ Upload failed for {filepath.name}: {response.text[:100]}")
            return None

        except Exception as e:
            print(f"⚠ Upload error for {filepath.name}: {e}")
            return None

    def upload_chart(self, filepath: Path, force: bool = False) -> Optional[str]:
        """Upload a single chart, using cache if unchanged."""
        file_hash = self._get_file_hash(filepath)
        cache_key = filepath.name

        # Check cache
        if not force and cache_key in self.cache["charts"]:
            cached = self.cache["charts"][cache_key]
            if cached.get("hash") == file_hash and cached.get("url"):
                return cached["url"]

        # Upload
        url = self.upload_to_imgbb(filepath)

        if url:
            self.cache["charts"][cache_key] = {
                "url": url,
                "hash": file_hash,
                "uploaded": datetime.now().isoformat(),
                "ticker": filepath.stem.split("_")[0].upper(),
            }
            self._save_cache()

        return url

    def upload_charts_for_tickers(self, tickers: List[str], force: bool = False) -> Dict[str, str]:
        """Upload charts for specific tickers and return URL mapping."""
        charts = self.find_charts(tickers)
        urls = {}

        for ticker, filepath in charts.items():
            url = self.upload_chart(filepath, force=force)
            if url:
                urls[ticker] = url
                print(f"📊 {ticker}: {url[:50]}...")
            else:
                # Fallback: use local file path (won't work in Notion but good for testing)
                urls[ticker] = f"file://{filepath}"

        return urls

    def get_charts_for_content(self, content: str, force_upload: bool = False) -> Dict[str, str]:
        """Detect tickers in content and return chart URLs."""
        tickers = self.detect_tickers_in_content(content)

        if not tickers:
            return {}

        print(f"📈 Detected tickers: {', '.join(tickers)}")
        return self.upload_charts_for_tickers(tickers, force=force_upload)

    def get_cached_url(self, ticker: str) -> Optional[str]:
        """Get cached URL for a ticker without uploading."""
        for cache_key, data in self.cache.get("charts", {}).items():
            if data.get("ticker", "").upper() == ticker.upper():
                return data.get("url")
        return None

    def upload_all_charts(self, force: bool = False) -> Dict[str, str]:
        """Upload all available charts."""
        charts = self.find_charts()
        return self.upload_charts_for_tickers(list(charts.keys()), force=force)

    def list_cached_charts(self) -> List[Dict]:
        """List all cached chart URLs."""
        return [
            {"ticker": data.get("ticker"), "url": data.get("url"), "uploaded": data.get("uploaded"), "file": key}
            for key, data in self.cache.get("charts", {}).items()
        ]


def setup_imgbb_key():
    """Interactive setup for imgbb API key."""
    print("\n📊 Chart Publisher Setup")
    print("=" * 40)
    print("\nTo upload charts to Notion, you need a free imgbb.com API key.")
    print("\n1. Go to https://api.imgbb.com/")
    print("2. Sign up for free")
    print("3. Get your API key")
    print("\nFree tier: 32MB/month (plenty for charts)")

    key = input("\nEnter your imgbb API key (or press Enter to skip): ").strip()

    if key:
        env_file = PROJECT_ROOT / ".env"
        env_content = env_file.read_text() if env_file.exists() else ""

        if "IMGBB_API_KEY" in env_content:
            # Update existing
            import re

            env_content = re.sub(r"IMGBB_API_KEY=.*", f"IMGBB_API_KEY={key}", env_content)
        else:
            # Add new
            env_content += f"\n\n# Image hosting for Notion charts\nIMGBB_API_KEY={key}\n"

        env_file.write_text(env_content)
        print("✓ API key saved to .env")

        # Also update template
        template_file = PROJECT_ROOT / ".env.template"
        if template_file.exists():
            template = template_file.read_text()
            if "IMGBB_API_KEY" not in template:
                template += "\n# Image hosting for Notion charts (free: https://api.imgbb.com/)\nIMGBB_API_KEY=your_imgbb_api_key\n"
                template_file.write_text(template)

        return key

    print("\n⚠ Skipped - charts will not be uploaded to Notion")
    print("  Run this script again to set up later")
    return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chart Publisher for Syndicate")
    parser.add_argument("--setup", action="store_true", help="Set up imgbb API key")
    parser.add_argument("--upload-all", action="store_true", help="Upload all charts")
    parser.add_argument("--upload", type=str, help="Upload specific ticker chart")
    parser.add_argument("--detect", type=str, help="Detect tickers in file")
    parser.add_argument("--list", action="store_true", help="List cached chart URLs")
    parser.add_argument("--force", action="store_true", help="Force re-upload")
    args = parser.parse_args()

    if args.setup:
        setup_imgbb_key()

    elif args.upload_all:
        publisher = ChartPublisher()
        urls = publisher.upload_all_charts(force=args.force)
        print(f"\n✓ Uploaded {len(urls)} charts")

    elif args.upload:
        publisher = ChartPublisher()
        urls = publisher.upload_charts_for_tickers([args.upload], force=args.force)
        if urls:
            print(f"\n✓ {args.upload}: {urls.get(args.upload.upper())}")

    elif args.detect:
        filepath = Path(args.detect)
        if filepath.exists():
            content = filepath.read_text()
            publisher = ChartPublisher()
            tickers = publisher.detect_tickers_in_content(content)
            print(f"Detected tickers: {', '.join(tickers) or 'None'}")
        else:
            print(f"File not found: {args.detect}")

    elif args.list:
        publisher = ChartPublisher()
        charts = publisher.list_cached_charts()
        if charts:
            print(f"\nCached charts ({len(charts)}):")
            for c in charts:
                print(f"  {c['ticker']}: {c['url'][:60]}...")
        else:
            print("No cached charts")

    else:
        parser.print_help()
