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
Syndicate Core - Main analysis engine.
"""

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional


class GoldStandard:
    """
    Main Syndicate analysis engine.

    Provides methods for running various analysis modes:
    - Daily journal generation
    - Pre-market plans
    - Weekly/Monthly/Yearly reports
    - Full analysis cycles
    """

    def __init__(self, no_ai: bool = False, project_root: Optional[Path] = None):
        """
        Initialize Syndicate.

        Args:
            no_ai: Disable AI-generated content
            project_root: Override project root directory
        """
        self.no_ai = no_ai
        self.project_root = project_root or self._find_project_root()
        self._setup_paths()
        self._db = None

    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        # Check current directory first
        cwd = Path.cwd()
        if (cwd / "main.py").exists() and (cwd / "run.py").exists():
            return cwd

        # Check if we're in the src package
        package_dir = Path(__file__).parent
        if "site-packages" in str(package_dir):
            # Installed package - use current directory
            return cwd

        # Development mode - go up from src/gost to syndicate
        return package_dir.parent.parent

    def _setup_paths(self):
        """Set up important paths."""
        self.output_dir = self.project_root / "output"
        self.reports_dir = self.output_dir / "reports"
        self.charts_dir = self.output_dir / "charts"
        self.data_dir = self.project_root / "data"
        self.scripts_dir = self.project_root / "scripts"

        # Ensure directories exist
        self.output_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.charts_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

    @property
    def db(self):
        """Lazy-load database manager."""
        if self._db is None:
            # Add project root to path for imports
            sys.path.insert(0, str(self.project_root))
            from db_manager import get_db

            self._db = get_db()
        return self._db

    def _run_script(self, script_path: str, args: list = None) -> bool:
        """Run a Python script with optional arguments."""
        args = args or []
        cmd_parts = [sys.executable, str(self.project_root / script_path)] + args
        if self.no_ai:
            cmd_parts.append("--no-ai")
        return os.system(" ".join(cmd_parts)) == 0

    def run_daily(self) -> bool:
        """Run daily journal analysis."""
        print("\n>> Running Daily Journal Analysis...\n")
        return self._run_script("main.py", ["--once"])

    def run_premarket(self) -> bool:
        """Run pre-market plan generation."""
        print("\n>> Generating Pre-Market Plan...\n")
        return self._run_script("scripts/pre_market.py")

    def run_weekly(self) -> bool:
        """Run weekly report generation."""
        print("\n>> Generating Weekly Report...\n")
        return self._run_script("scripts/split_reports.py", ["--mode", "weekly", "--once"])

    def run_monthly(self) -> bool:
        """Run monthly report generation."""
        print("\n>> Generating Monthly Report...\n")
        return self._run_script("scripts/split_reports.py", ["--mode", "monthly", "--once"])

    def run_yearly(self) -> bool:
        """Run yearly report generation."""
        print("\n>> Generating Yearly Report...\n")
        return self._run_script("scripts/split_reports.py", ["--mode", "yearly", "--once"])

    def run_all(self, force: bool = False) -> Dict[str, bool]:
        """
        Run complete analysis with intelligent redundancy control.

        Args:
            force: Force regenerate reports even if they exist

        Returns:
            Dictionary of task results
        """
        today = date.today()
        iso_cal = today.isocalendar()

        print("\n" + "=" * 60)
        print("              RUNNING FULL ANALYSIS")
        print("=" * 60)

        results = {}

        # 1. Always run daily journal
        print("\n[1/5] DAILY JOURNAL")
        print("-" * 40)
        results["daily"] = self.run_daily()

        # 2. Pre-market plan
        print("\n[2/5] PRE-MARKET PLAN")
        print("-" * 40)
        if not self.db.has_premarket_for_date(today.isoformat()) or force:
            results["premarket"] = self.run_premarket()
        else:
            print("  [SKIP] Pre-market plan already exists for today")
            results["premarket"] = True

        # 3. Weekly report (on weekends or if forced)
        print("\n[3/5] WEEKLY REPORT")
        print("-" * 40)
        is_weekend = iso_cal[2] >= 6
        if not self.db.has_weekly_report(today.year, iso_cal[1]) and (is_weekend or force):
            results["weekly"] = self.run_weekly()
        elif self.db.has_weekly_report(today.year, iso_cal[1]):
            print(f"  [SKIP] Weekly report for Week {iso_cal[1]} already exists")
            results["weekly"] = True
        else:
            print("  [SKIP] Not weekend. Weekly reports generated on Sat/Sun")
            results["weekly"] = True

        # 4. Monthly report
        print("\n[4/5] MONTHLY REPORT")
        print("-" * 40)
        if not self.db.has_monthly_report(today.year, today.month) or force:
            print(f"  Generating report for {today.year}-{today.month:02d}...")
            results["monthly"] = self.run_monthly()
        else:
            print(f"  [SKIP] Monthly report for {today.year}-{today.month:02d} already exists")
            results["monthly"] = True

        # 5. Yearly report
        print("\n[5/5] YEARLY REPORT")
        print("-" * 40)
        if not self.db.has_yearly_report(today.year) or force:
            print(f"  Generating report for {today.year}...")
            results["yearly"] = self.run_yearly()
        else:
            print(f"  [SKIP] Yearly report for {today.year} already exists")
            results["yearly"] = True

        # Summary
        print("\n" + "=" * 60)
        print("                    SUMMARY")
        print("=" * 60)
        for task, success in results.items():
            status = "[OK]" if success else "[FAIL]"
            print(f"  {task.upper():15} {status}")
        print("=" * 60 + "\n")

        return results

    def print_status(self):
        """Print current system status."""
        info = self.db.get_current_period_info()
        missing = self.db.get_missing_reports()
        stats = self.db.get_statistics()

        print("\n" + "=" * 60)
        print("                    SYSTEM STATUS")
        print("=" * 60)
        print(f"  Date: {info['today']}  |  Week {info['week']}  |  {info['month_period']}")
        print("-" * 60)
        print(f"  Total Journals: {stats['total_journals']}")
        print(f"  Weekly Reports: {stats['weekly_reports']}")
        print(f"  Monthly Reports: {stats['monthly_reports']}")
        print(f"  Yearly Reports: {stats['yearly_reports']}")
        print("-" * 60)
        print("  Today's Status:")
        print(f"    Daily Journal:   {'[OK] EXISTS' if not missing['daily_journal'] else '[--] MISSING'}")
        print(f"    Pre-Market Plan: {'[OK] EXISTS' if not missing['premarket_plan'] else '[--] MISSING'}")
        print(f"    Weekly Report:   {'[OK] EXISTS' if not missing['weekly_report'] else '[--] MISSING'}")
        print(f"    Monthly Report:  {'[OK] EXISTS' if not missing['monthly_report'] else '[--] MISSING'}")
        print(f"    Yearly Report:   {'[OK] EXISTS' if not missing['yearly_report'] else '[--] MISSING'}")
        print("=" * 60 + "\n")

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics."""
        return self.db.get_statistics()
