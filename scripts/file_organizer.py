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
Syndicate File Organizer
Intelligently organizes, titles, dates, and archives reports and charts.
Maintains a clean, accessible output structure.
"""

import json
import logging
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================
# FILE ORGANIZER
# ==========================================


class FileOrganizer:
    """
    Manages intelligent organization of reports and charts.
    - Auto-titles with proper naming conventions
    - Dates and timestamps all files
    - Categorizes into appropriate folders
    - Archives files older than threshold
    - Maintains index/catalog of all outputs
    """

    # File type categories
    CATEGORIES = {
        "journals": ["Journal_", "journal_", "daily_"],
        "premarket": ["premarket_", "pre_market_", "pre-market"],
        "weekly": ["weekly_", "week_", "rundown_"],
        "monthly": ["monthly_", "month_"],
        "yearly": ["yearly_", "year_", "annual_"],
        "catalysts": ["catalyst", "watchlist"],
        "institutional": ["inst_matrix", "institutional", "scenario"],
        "analysis": ["1y_", "3m_", "analysis_", "horizon_"],
        "economic": ["economic_", "calendar_", "events_"],
        "research": ["research_", "calc_", "code_", "data_fetch", "monitor_", "news_scan"],
        "charts": [".png", ".jpg", ".svg", ".gif"],
    }

    # Archive threshold in days
    DEFAULT_ARCHIVE_DAYS = 7

    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger

        # Set up directory structure
        self.base_dir = Path(config.OUTPUT_DIR) if config else PROJECT_ROOT / "output"
        self.reports_dir = self.base_dir / "reports"
        self.charts_dir = self.base_dir / "charts"
        self.archive_dir = self.base_dir / "archive"
        self.research_dir = self.base_dir / "research"
        self.index_file = self.base_dir / "file_index.json"

        # Category subdirectories
        self.category_dirs = {
            "journals": self.reports_dir / "journals",
            "premarket": self.reports_dir / "premarket",
            "weekly": self.reports_dir / "weekly",
            "monthly": self.reports_dir / "monthly",
            "yearly": self.reports_dir / "yearly",
            "catalysts": self.reports_dir / "catalysts",
            "institutional": self.reports_dir / "institutional",
            "analysis": self.reports_dir / "analysis",
            "economic": self.reports_dir / "economic",
            "research": self.research_dir,
            "charts": self.charts_dir,
        }

        # Initialize directory structure
        self._ensure_directories()

        # Load or create index
        self.file_index = self._load_index()

    def _ensure_directories(self):
        """Create all necessary directories."""
        dirs_to_create = [
            self.base_dir,
            self.reports_dir,
            self.charts_dir,
            self.archive_dir,
            self.research_dir,
            self.archive_dir / "reports",
            self.archive_dir / "charts",
        ]

        # Add category subdirectories
        dirs_to_create.extend(self.category_dirs.values())

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> Dict:
        """Load file index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"[ORGANIZER] Could not load index: {e}")

        return {
            "files": {},
            "categories": {cat: [] for cat in self.CATEGORIES.keys()},
            "last_updated": None,
            "statistics": {"total_files": 0, "total_archived": 0, "by_category": {}},
        }

    def _save_index(self):
        """Save file index to disk."""
        self.file_index["last_updated"] = datetime.now().isoformat()

        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.file_index, f, indent=2)
        except Exception as e:
            self.logger.error(f"[ORGANIZER] Could not save index: {e}")

    def categorize_file(self, filename: str) -> str:
        """Determine the category for a file based on its name."""
        filename_lower = filename.lower()

        for category, patterns in self.CATEGORIES.items():
            for pattern in patterns:
                if pattern.lower() in filename_lower:
                    return category

        return "other"

    def generate_standardized_name(self, original_name: str, category: str, file_date: Optional[date] = None) -> str:
        """Generate a standardized filename."""
        if file_date is None:
            file_date = date.today()

        # Extract extension
        ext = Path(original_name).suffix or ".md"

        # Clean the original name for key content
        name_clean = re.sub(r"[\d]{4}-[\d]{2}-[\d]{2}", "", original_name)  # Remove existing dates
        name_clean = re.sub(r"[_\-]+", "_", name_clean)  # Normalize separators
        name_clean = name_clean.strip("_")

        # Build standardized name
        date_str = file_date.strftime("%Y-%m-%d")

        # Category-specific naming
        if category == "journals":
            return f"Journal_{date_str}{ext}"
        elif category == "premarket":
            return f"PreMarket_{date_str}{ext}"
        elif category == "weekly":
            week_num = file_date.isocalendar()[1]
            return f"Weekly_W{week_num:02d}_{date_str}{ext}"
        elif category == "monthly":
            return f"Monthly_{file_date.strftime('%Y-%m')}{ext}"
        elif category == "yearly":
            return f"Yearly_{file_date.year}{ext}"
        elif category == "catalysts":
            return f"Catalysts_{date_str}{ext}"
        elif category == "institutional":
            return f"InstMatrix_{date_str}{ext}"
        elif category == "analysis":
            # Preserve horizon indicator (1y, 3m)
            horizon_match = re.search(r"(1y|3m|6m|12m)", original_name, re.IGNORECASE)
            horizon = horizon_match.group(1).upper() if horizon_match else "Analysis"
            return f"{horizon}_{date_str}{ext}"
        elif category == "economic":
            return f"EconCalendar_{date_str}{ext}"
        elif category == "charts":
            # Keep chart names but add date
            base_name = Path(original_name).stem
            base_name = re.sub(r"_[\d]{4}-[\d]{2}-[\d]{2}", "", base_name)
            return f"{base_name}_{date_str}{ext}"
        else:
            return f"{Path(original_name).stem}_{date_str}{ext}"

    def organize_file(self, source_path: Path, move: bool = True) -> Optional[Path]:
        """
        Organize a single file into the appropriate category folder.
        Returns the new path, or None if failed.
        """
        if not source_path.exists():
            self.logger.warning(f"[ORGANIZER] Source file not found: {source_path}")
            return None

        # (Incoming change removed; skip logic handled below to cover casing)
        filename = source_path.name

        # Skip FILE_INDEX files to prevent recursive renaming (filename explosion bug)
        if filename.startswith("FILE_INDEX") or filename.lower().startswith("file_index"):
            self.logger.debug(f"[ORGANIZER] Skipping index file: {filename}")
            return None

        category = self.categorize_file(filename)

        # Determine file date from name or modification time
        date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
        if date_match:
            file_date = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
        else:
            file_date = date.fromtimestamp(source_path.stat().st_mtime)

        # Get destination directory
        dest_dir = self.category_dirs.get(category, self.reports_dir)

        # Generate standardized name
        new_name = self.generate_standardized_name(filename, category, file_date)
        dest_path = dest_dir / new_name

        try:
            if move:
                shutil.move(str(source_path), str(dest_path))
            else:
                shutil.copy2(str(source_path), str(dest_path))

            # Update index
            self.file_index["files"][str(dest_path)] = {
                "original_name": filename,
                "category": category,
                "date": file_date.isoformat(),
                "organized_at": datetime.now().isoformat(),
                "size_bytes": dest_path.stat().st_size,
            }

            if category not in self.file_index["categories"]:
                self.file_index["categories"][category] = []
            self.file_index["categories"][category].append(str(dest_path))

            self.logger.info(f"[ORGANIZER] Organized: {filename} -> {category}/{new_name}")
            return dest_path

        except Exception as e:
            self.logger.error(f"[ORGANIZER] Failed to organize {filename}: {e}")
            return None

    def organize_all(self, source_dirs: Optional[List[Path]] = None) -> Dict[str, int]:
        """
        Organize all files in source directories.
        Returns counts by category.
        """
        if source_dirs is None:
            source_dirs = [
                self.base_dir,
                self.reports_dir,
            ]

        counts = {cat: 0 for cat in self.CATEGORIES.keys()}
        counts["other"] = 0

        for source_dir in source_dirs:
            if not source_dir.exists():
                continue

            # Process markdown files
            for md_file in source_dir.glob("*.md"):
                # Skip if already in a category subdirectory
                if md_file.parent != source_dir and md_file.parent != self.reports_dir:
                    continue

                result = self.organize_file(md_file)
                if result:
                    category = self.categorize_file(md_file.name)
                    counts[category] = counts.get(category, 0) + 1

            # Process chart files
            for chart_file in source_dir.glob("*.png"):
                if chart_file.parent == self.charts_dir:
                    continue  # Already in charts

                result = self.organize_file(chart_file)
                if result:
                    counts["charts"] = counts.get("charts", 0) + 1

        self._save_index()
        self._update_statistics()

        self.logger.info(f"[ORGANIZER] Organized {sum(counts.values())} files")
        return counts

    def archive_old_files(self, days_threshold: int = None) -> int:
        """
        Archive files older than threshold.
        Returns count of archived files.
        """
        if days_threshold is None:
            days_threshold = self.DEFAULT_ARCHIVE_DAYS

        cutoff_date = date.today() - timedelta(days=days_threshold)
        archived_count = 0

        # Archive from each category directory
        for category, cat_dir in self.category_dirs.items():
            if category == "charts":
                archive_subdir = self.archive_dir / "charts"
            else:
                archive_subdir = self.archive_dir / "reports" / category
            archive_subdir.mkdir(parents=True, exist_ok=True)

            for file_path in cat_dir.glob("*"):
                if file_path.is_dir():
                    continue

                # Determine file date
                date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", file_path.name)
                if date_match:
                    file_date = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
                else:
                    file_date = date.fromtimestamp(file_path.stat().st_mtime)

                if file_date < cutoff_date:
                    # Archive the file
                    archive_path = archive_subdir / file_path.name

                    # Add year/month subdirectory for better organization
                    year_month_dir = archive_subdir / f"{file_date.year}" / f"{file_date.month:02d}"
                    year_month_dir.mkdir(parents=True, exist_ok=True)
                    archive_path = year_month_dir / file_path.name

                    try:
                        shutil.move(str(file_path), str(archive_path))
                        archived_count += 1

                        # Update index
                        if str(file_path) in self.file_index["files"]:
                            self.file_index["files"][str(file_path)]["archived"] = True
                            self.file_index["files"][str(file_path)]["archive_path"] = str(archive_path)

                        self.logger.debug(f"[ORGANIZER] Archived: {file_path.name}")

                    except Exception as e:
                        self.logger.error(f"[ORGANIZER] Failed to archive {file_path}: {e}")

        self.file_index["statistics"]["total_archived"] += archived_count
        self._save_index()

        self.logger.info(f"[ORGANIZER] Archived {archived_count} files older than {days_threshold} days")
        return archived_count

    def _update_statistics(self):
        """Update statistics in the index."""
        stats = self.file_index["statistics"]
        stats["total_files"] = len(self.file_index["files"])
        stats["by_category"] = {}

        for category, files in self.file_index["categories"].items():
            stats["by_category"][category] = len(files)

    def get_recent_files(self, category: Optional[str] = None, days: int = 7) -> List[Dict]:
        """Get files from the last N days."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        recent = []

        for file_path, info in self.file_index["files"].items():
            if info.get("archived"):
                continue
            if category and info.get("category") != category:
                continue
            if info.get("date", "") >= cutoff:
                recent.append({"path": file_path, **info})

        # Sort by date descending
        recent.sort(key=lambda x: x.get("date", ""), reverse=True)
        return recent

    def generate_index_report(self) -> str:
        """Generate a markdown index of all organized files."""
        report = f"""# Syndicate File Index
> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Statistics

| Metric | Value |
|--------|-------|
| Total Files | {self.file_index['statistics'].get('total_files', 0)} |
| Total Archived | {self.file_index['statistics'].get('total_archived', 0)} |

## Files by Category

"""

        for category, count in self.file_index["statistics"].get("by_category", {}).items():
            report += f"- **{category.title()}**: {count} files\n"

        report += "\n## Recent Files (Last 7 Days)\n\n"

        recent = self.get_recent_files(days=7)
        for file_info in recent[:20]:
            report += f"- [{Path(file_info['path']).name}]({file_info['path']}) - {file_info['category']} ({file_info['date']})\n"

        report += "\n---\n*File index auto-generated by Syndicate File Organizer*\n"

        return report

    def cleanup_empty_directories(self):
        """Remove empty directories."""
        for dir_path in self.category_dirs.values():
            if dir_path.exists():
                for subdir in dir_path.iterdir():
                    if subdir.is_dir() and not any(subdir.iterdir()):
                        subdir.rmdir()
                        self.logger.debug(f"[ORGANIZER] Removed empty directory: {subdir}")

    def run_maintenance(self, archive_days: int = None) -> Dict:
        """
        Run full maintenance cycle:
        1. Organize new files
        2. Archive old files
        3. Clean up empty directories
        4. Update statistics
        """
        results = {"organized": 0, "archived": 0, "timestamp": datetime.now().isoformat()}

        # Organize new files
        organize_counts = self.organize_all()
        results["organized"] = sum(organize_counts.values())
        results["by_category"] = organize_counts

        # Archive old files
        results["archived"] = self.archive_old_files(archive_days)

        # Cleanup
        self.cleanup_empty_directories()

        # Save index report
        index_report = self.generate_index_report()
        index_path = self.base_dir / "FILE_INDEX.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_report)

        self.logger.info(
            f"[ORGANIZER] Maintenance complete: {results['organized']} organized, {results['archived']} archived"
        )

        return results


# ==========================================
# STANDALONE EXECUTION
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("OrganizerTest")

    # Create mock config
    class MockConfig:
        OUTPUT_DIR = str(PROJECT_ROOT / "output")

    organizer = FileOrganizer(MockConfig(), logger)

    print("\n=== File Organizer Test ===")
    print(f"Base directory: {organizer.base_dir}")
    print(f"Categories: {list(organizer.category_dirs.keys())}")

    # Run maintenance
    results = organizer.run_maintenance(archive_days=7)

    print("\nMaintenance Results:")
    print(f"  Organized: {results['organized']}")
    print(f"  Archived: {results['archived']}")

    # Show recent files
    recent = organizer.get_recent_files(days=3)
    print(f"\nRecent files ({len(recent)}):")
    for f in recent[:5]:
        print(f"  - {Path(f['path']).name} ({f['category']})")
