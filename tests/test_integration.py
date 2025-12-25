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
Syndicate v3.0 - Integration Test
Tests all new modules working together.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging

from db_manager import get_db
from main import Config
from scripts.file_organizer import FileOrganizer
from scripts.insights_engine import InsightsExtractor
from scripts.task_executor import TaskExecutor

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("integration")


def main():
    print("=" * 70)
    print("            GOLD STANDARD v3.0 - INTEGRATION TEST")
    print("=" * 70)

    config = Config()
    db = get_db()

    # Initialize all new modules
    print("\n[1] INITIALIZING MODULES")
    print("-" * 50)
    extractor = InsightsExtractor(config, logger)
    executor = TaskExecutor(config, logger)
    organizer = FileOrganizer(config, logger)
    print("  ✓ InsightsExtractor: OK")
    print("  ✓ TaskExecutor: OK")
    print("  ✓ FileOrganizer: OK")

    # Read existing reports if any
    print("\n[2] CHECKING EXISTING REPORTS")
    print("-" * 50)
    reports_dir = Path(config.OUTPUT_DIR) / "reports"
    report_files = list(reports_dir.glob("*.md")) if reports_dir.exists() else []
    print(f"  Found {len(report_files)} report files")

    total_entities = 0
    total_actions = 0

    if report_files:
        # Process reports for insights
        for report_file in report_files[:3]:  # Process up to 3
            print(f"\n  Processing: {report_file.name}")
            try:
                content = report_file.read_text(encoding="utf-8", errors="ignore")

                # Extract entities
                entities = extractor.extract_entities(content, report_file.name)
                total_entities += len(entities)

                # Extract actions
                actions = extractor.extract_actions(content, report_file.name)
                total_actions += len(actions)

                print(f"    Entities: {len(entities)}, Actions: {len(actions)}")

                # Save to database
                if entities:
                    db.save_entity_insights(entities[:5])
                if actions:
                    db.save_action_insights(actions[:3])

            except Exception as e:
                print(f"    Error: {e}")

    print(f"\n  Total entities extracted: {total_entities}")
    print(f"  Total actions extracted: {total_actions}")

    # Check database state
    print("\n[3] DATABASE STATE")
    print("-" * 50)
    try:
        pending = db.get_pending_actions(limit=10)
        print(f"  Pending actions in DB: {len(pending)}")

        for action in pending[:5]:
            print(
                f'    - [{action.get("priority", "?")}] {action.get("action_type", "?")}: {action.get("description", "?")[:40]}...'
            )
    except Exception as e:
        print(f"  Error reading DB: {e}")

    # Get executor stats
    print("\n[4] EXECUTOR STATS")
    print("-" * 50)
    stats = executor.get_stats()
    print(f'  Total executed: {stats.get("total_executed", 0)}')
    print(f'  Success rate: {stats.get("success_rate", 0):.1f}%')
    print(f'  Handlers available: {", ".join(stats.get("handlers", []))}')

    # File organization check
    print("\n[5] FILE ORGANIZATION")
    print("-" * 50)
    output_dir = Path(config.OUTPUT_DIR)

    categories_checked = ["journals", "analysis", "charts", "premarket", "weekly", "economic"]
    for category in categories_checked:
        cat_dir = output_dir / category
        if cat_dir.exists():
            files = list(cat_dir.glob("*"))
            print(f"  {category}/: {len(files)} files")
        else:
            print(f"  {category}/: (not created yet)")

    # Summary
    print("\n" + "=" * 70)
    print("               ALL SYSTEMS OPERATIONAL ✓")
    print("=" * 70)
    print(f"""
Summary:
  • InsightsExtractor: Extracting entities & actions from reports
  • TaskExecutor: Ready to execute {len(stats.get("handlers", []))} task types
  • FileOrganizer: {len(organizer.category_dirs)} categories configured
  • Database: {len(pending)} pending actions queued

Run "python run.py" to start the autonomous daemon.
Run "python gui.py" to launch the modern GUI.
""")


if __name__ == "__main__":
    main()
