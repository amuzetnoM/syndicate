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
Cleanup Manager for Syndicate
Manages storage limits on free-tier services (imgbb, Notion).
Implements smart retention policies and usage tracking.
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

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

# File paths
USAGE_FILE = PROJECT_ROOT / "output" / "usage_stats.json"
CHART_CACHE = PROJECT_ROOT / "output" / "chart_urls.json"

# Limits (free tier)
LIMITS = {
    "imgbb": {"monthly_mb": 32, "description": "32MB/month uploads"},
    "notion": {
        "blocks_per_page": 100,  # API limit per request
        "total_blocks": 1000,  # Rough free tier guidance
        "description": "1000 blocks approx",
    },
}

# Retention defaults (days)
DEFAULT_RETENTION = {
    "charts": 30,  # Keep charts for 30 days
    "notion_pages": 90,  # Keep Notion pages for 90 days
    "local_reports": 180,  # Keep local reports for 180 days
}


@dataclass
class UsageStats:
    """Track usage across services."""

    imgbb_bytes_this_month: int = 0
    imgbb_uploads_this_month: int = 0
    notion_pages_created: int = 0
    notion_blocks_created: int = 0
    last_reset: str = ""
    last_cleanup: str = ""
    charts_deleted: int = 0
    pages_archived: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "UsageStats":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CleanupManager:
    """Manage cleanup and retention for Syndicate services."""

    def __init__(self):
        self.imgbb_key = os.getenv("IMGBB_API_KEY")
        self.notion_key = os.getenv("NOTION_API_KEY")
        self.notion_db = os.getenv("NOTION_DATABASE_ID")
        self.stats = self._load_stats()
        self._check_monthly_reset()

    def _load_stats(self) -> UsageStats:
        """Load usage statistics."""
        if USAGE_FILE.exists():
            try:
                data = json.loads(USAGE_FILE.read_text())
                return UsageStats.from_dict(data)
            except Exception:
                pass
        return UsageStats()

    def _save_stats(self):
        """Save usage statistics."""
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(self.stats.to_dict(), indent=2))

    def _check_monthly_reset(self):
        """Reset monthly counters if new month."""
        now = datetime.now()
        current_month = now.strftime("%Y-%m")

        if self.stats.last_reset != current_month:
            print("📅 New month detected - resetting usage counters")
            self.stats.imgbb_bytes_this_month = 0
            self.stats.imgbb_uploads_this_month = 0
            self.stats.last_reset = current_month
            self._save_stats()

    def record_imgbb_upload(self, file_size_bytes: int):
        """Record an imgbb upload."""
        self.stats.imgbb_bytes_this_month += file_size_bytes
        self.stats.imgbb_uploads_this_month += 1
        self._save_stats()

    def record_notion_page(self, block_count: int):
        """Record a Notion page creation."""
        self.stats.notion_pages_created += 1
        self.stats.notion_blocks_created += block_count
        self._save_stats()

    def get_imgbb_usage(self) -> Tuple[float, float]:
        """Get imgbb usage: (used_mb, limit_mb)."""
        used_mb = self.stats.imgbb_bytes_this_month / (1024 * 1024)
        limit_mb = LIMITS["imgbb"]["monthly_mb"]
        return used_mb, limit_mb

    def get_usage_report(self) -> str:
        """Generate a usage report."""
        used_mb, limit_mb = self.get_imgbb_usage()
        pct = (used_mb / limit_mb * 100) if limit_mb > 0 else 0

        report = [
            "📊 Usage Report",
            "=" * 40,
            "",
            "📸 imgbb (Image Hosting):",
            f"   Used: {used_mb:.2f} MB / {limit_mb} MB ({pct:.1f}%)",
            f"   Uploads this month: {self.stats.imgbb_uploads_this_month}",
            "",
            "📝 Notion:",
            f"   Pages created: {self.stats.notion_pages_created}",
            f"   Blocks created: {self.stats.notion_blocks_created}",
            "",
            "🧹 Cleanup Stats:",
            f"   Charts deleted: {self.stats.charts_deleted}",
            f"   Pages archived: {self.stats.pages_archived}",
            f"   Last cleanup: {self.stats.last_cleanup or 'Never'}",
        ]

        # Warnings
        if pct > 80:
            report.append("")
            report.append(f"⚠️  WARNING: imgbb usage at {pct:.0f}% - consider cleanup!")

        return "\n".join(report)

    def should_upload_chart(self, file_size_bytes: int) -> Tuple[bool, str]:
        """Check if we should upload a chart (within limits)."""
        used_mb, limit_mb = self.get_imgbb_usage()
        new_total = used_mb + (file_size_bytes / (1024 * 1024))

        if new_total > limit_mb * 0.95:  # 95% threshold
            return False, f"Would exceed imgbb limit ({new_total:.1f}/{limit_mb} MB)"

        return True, "OK"

    def cleanup_old_charts(self, days: int = None) -> Dict:
        """Remove charts older than retention period from cache."""
        days = days or DEFAULT_RETENTION["charts"]
        cutoff = datetime.now() - timedelta(days=days)

        if not CHART_CACHE.exists():
            return {"removed": 0, "kept": 0}

        cache = json.loads(CHART_CACHE.read_text())
        charts = cache.get("charts", {})

        to_remove = []
        for filename, data in charts.items():
            uploaded = data.get("uploaded")
            if uploaded:
                try:
                    upload_date = datetime.fromisoformat(uploaded)
                    if upload_date < cutoff:
                        to_remove.append(filename)
                except Exception:
                    pass

        # Remove old entries
        for filename in to_remove:
            del charts[filename]
            self.stats.charts_deleted += 1

        # Save updated cache
        cache["charts"] = charts
        cache["last_cleanup"] = datetime.now().isoformat()
        CHART_CACHE.write_text(json.dumps(cache, indent=2))

        self.stats.last_cleanup = datetime.now().isoformat()
        self._save_stats()

        return {"removed": len(to_remove), "kept": len(charts), "removed_files": to_remove}

    def cleanup_local_reports(self, days: int = None, dry_run: bool = True) -> Dict:
        """Archive old local reports."""
        days = days or DEFAULT_RETENTION["local_reports"]
        cutoff = datetime.now() - timedelta(days=days)

        output_dir = PROJECT_ROOT / "output"
        archive_dir = output_dir / "archive"

        to_archive = []

        # Find old markdown files
        for md_file in output_dir.glob("**/*.md"):
            if "archive" in str(md_file).lower():
                continue
            if "FILE_INDEX" in md_file.name:
                continue

            # Check modification time
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime < cutoff:
                to_archive.append(md_file)

        if dry_run:
            return {
                "would_archive": len(to_archive),
                "files": [str(f.relative_to(output_dir)) for f in to_archive[:10]],
                "dry_run": True,
            }

        # Actually move files
        archived = 0
        for filepath in to_archive:
            try:
                rel_path = filepath.relative_to(output_dir)
                dest = archive_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                filepath.rename(dest)
                archived += 1
            except Exception as e:
                print(f"  ⚠ Failed to archive {filepath.name}: {e}")

        return {"archived": archived, "dry_run": False}

    def archive_notion_pages(self, days: int = None, dry_run: bool = True) -> Dict:
        """Archive old Notion pages (set to archived status)."""
        if not self.notion_key or not self.notion_db:
            return {"error": "Notion not configured"}

        days = days or DEFAULT_RETENTION["notion_pages"]
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        try:
            from notion_client import Client

            client = Client(auth=self.notion_key)

            # Query for old pages
            response = client.databases.query(
                database_id=self.notion_db, filter={"property": "Date", "date": {"before": cutoff}}, page_size=50
            )

            old_pages = response.get("results", [])

            if dry_run:
                return {
                    "would_archive": len(old_pages),
                    "pages": [
                        p.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled")
                        for p in old_pages[:10]
                    ],
                    "dry_run": True,
                }

            # Archive pages
            archived = 0
            for page in old_pages:
                try:
                    client.pages.update(page_id=page["id"], archived=True)
                    archived += 1
                    self.stats.pages_archived += 1
                except Exception as e:
                    print(f"  ⚠ Failed to archive page: {e}")

            self._save_stats()

            return {"archived": archived, "dry_run": False}

        except ImportError:
            return {"error": "notion-client not installed"}
        except Exception as e:
            return {"error": str(e)}

    def run_full_cleanup(self, dry_run: bool = True) -> Dict:
        """Run all cleanup operations."""
        results = {
            "charts": self.cleanup_old_charts(),
            "local_reports": self.cleanup_local_reports(dry_run=dry_run),
            "notion_pages": self.archive_notion_pages(dry_run=dry_run),
            "dry_run": dry_run,
        }

        return results

    def optimize_for_limits(self) -> List[str]:
        """Get recommendations for staying within limits."""
        recommendations = []

        used_mb, limit_mb = self.get_imgbb_usage()
        pct = (used_mb / limit_mb * 100) if limit_mb > 0 else 0

        if pct > 50:
            recommendations.append(f"📸 imgbb at {pct:.0f}% - Run: python scripts/cleanup_manager.py --cleanup-charts")

        if self.stats.notion_pages_created > 50:
            recommendations.append(f"📝 {self.stats.notion_pages_created} Notion pages - Consider archiving old ones")

        # Check chart cache size
        if CHART_CACHE.exists():
            cache = json.loads(CHART_CACHE.read_text())
            chart_count = len(cache.get("charts", {}))
            if chart_count > 30:
                recommendations.append(f"📊 {chart_count} cached charts - Some may be outdated")

        if not recommendations:
            recommendations.append("✅ All good! Usage is within healthy limits.")

        return recommendations


def print_status():
    """Print current status and recommendations."""
    manager = CleanupManager()
    print(manager.get_usage_report())
    print()
    print("💡 Recommendations:")
    for rec in manager.optimize_for_limits():
        print(f"   {rec}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup Manager for Syndicate")
    parser.add_argument("--status", action="store_true", help="Show usage status and recommendations")
    parser.add_argument("--cleanup-charts", action="store_true", help="Remove old chart cache entries")
    parser.add_argument("--cleanup-local", action="store_true", help="Archive old local reports")
    parser.add_argument("--cleanup-notion", action="store_true", help="Archive old Notion pages")
    parser.add_argument("--cleanup-all", action="store_true", help="Run all cleanup operations")
    parser.add_argument("--days", type=int, help="Retention period in days")
    parser.add_argument("--execute", action="store_true", help="Actually execute (not dry run)")
    args = parser.parse_args()

    manager = CleanupManager()

    if args.status or not any([args.cleanup_charts, args.cleanup_local, args.cleanup_notion, args.cleanup_all]):
        print_status()

    elif args.cleanup_charts:
        result = manager.cleanup_old_charts(days=args.days)
        print(f"🧹 Chart cleanup: Removed {result['removed']}, kept {result['kept']}")
        if result.get("removed_files"):
            for f in result["removed_files"][:5]:
                print(f"   - {f}")

    elif args.cleanup_local:
        dry_run = not args.execute
        result = manager.cleanup_local_reports(days=args.days, dry_run=dry_run)
        if dry_run:
            print(f"🔍 Dry run: Would archive {result['would_archive']} files")
            for f in result.get("files", []):
                print(f"   - {f}")
            print("\nRun with --execute to actually archive")
        else:
            print(f"🧹 Archived {result['archived']} files")

    elif args.cleanup_notion:
        dry_run = not args.execute
        result = manager.archive_notion_pages(days=args.days, dry_run=dry_run)
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
        elif dry_run:
            print(f"🔍 Dry run: Would archive {result['would_archive']} Notion pages")
            for p in result.get("pages", []):
                print(f"   - {p}")
            print("\nRun with --execute to actually archive")
        else:
            print(f"🧹 Archived {result['archived']} Notion pages")

    elif args.cleanup_all:
        dry_run = not args.execute
        results = manager.run_full_cleanup(dry_run=dry_run)

        print("🧹 Full Cleanup Results:")
        print(f"   Charts: Removed {results['charts']['removed']}")

        if dry_run:
            print(f"   Local reports: Would archive {results['local_reports'].get('would_archive', 0)}")
            print(f"   Notion pages: Would archive {results['notion_pages'].get('would_archive', 0)}")
            print("\nRun with --execute to actually archive files/pages")
        else:
            print(f"   Local reports: Archived {results['local_reports'].get('archived', 0)}")
            print(f"   Notion pages: Archived {results['notion_pages'].get('archived', 0)}")
