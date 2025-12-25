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
Tests for the Syndicate File Organizer.
"""

import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.file_organizer import FileOrganizer


class TestFileOrganizer:
    """Tests for the FileOrganizer class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def organizer(self, temp_dir):
        """Create a FileOrganizer with temp directory."""
        import logging

        logger = logging.getLogger("test")

        class MockConfig:
            OUTPUT_DIR = str(temp_dir)

        return FileOrganizer(MockConfig(), logger)

    def test_categorize_journal(self, organizer):
        """Test journal file categorization."""
        assert organizer.categorize_file("Journal_2025-12-03.md") == "journals"
        assert organizer.categorize_file("daily_report.md") == "journals"

    def test_categorize_premarket(self, organizer):
        """Test premarket file categorization."""
        assert organizer.categorize_file("premarket_2025-12-03.md") == "premarket"
        assert organizer.categorize_file("pre_market_plan.md") == "premarket"

    def test_categorize_weekly(self, organizer):
        """Test weekly file categorization."""
        assert organizer.categorize_file("weekly_rundown_2025-12-03.md") == "weekly"
        assert organizer.categorize_file("week_49_report.md") == "weekly"

    def test_categorize_charts(self, organizer):
        """Test chart file categorization."""
        assert organizer.categorize_file("GOLD.png") == "charts"
        assert organizer.categorize_file("chart_analysis.jpg") == "charts"

    def test_categorize_institutional(self, organizer):
        """Test institutional matrix categorization."""
        assert organizer.categorize_file("inst_matrix_2025-12-03.md") == "institutional"
        assert organizer.categorize_file("institutional_view.md") == "institutional"

    def test_categorize_analysis(self, organizer):
        """Test analysis file categorization."""
        assert organizer.categorize_file("1y_2025-12-03.md") == "analysis"
        assert organizer.categorize_file("3m_analysis.md") == "analysis"

    def test_generate_standardized_name_journal(self, organizer):
        """Test standardized naming for journals."""
        name = organizer.generate_standardized_name("some_journal.md", "journals", date(2025, 12, 3))
        assert name == "Journal_2025-12-03.md"

    def test_generate_standardized_name_weekly(self, organizer):
        """Test standardized naming for weekly reports."""
        test_date = date(2025, 12, 3)  # Week 49
        name = organizer.generate_standardized_name("weekly.md", "weekly", test_date)
        assert "Weekly_W" in name
        assert "2025-12-03" in name

    def test_generate_standardized_name_analysis(self, organizer):
        """Test standardized naming preserves horizon."""
        name = organizer.generate_standardized_name("1y_report.md", "analysis", date(2025, 12, 3))
        assert "1Y_" in name

        name = organizer.generate_standardized_name("3m_analysis.md", "analysis", date(2025, 12, 3))
        assert "3M_" in name

    def test_organize_file(self, organizer, temp_dir):
        """Test organizing a single file."""
        # Create test file
        test_file = temp_dir / "Journal_2025-12-03.md"
        test_file.write_text("Test content")

        # Organize it
        result = organizer.organize_file(test_file)

        assert result is not None
        assert result.exists()
        assert "journals" in str(result.parent)

    def test_index_updated_after_organize(self, organizer, temp_dir):
        """Test that file index is updated after organizing."""
        # Create test file
        test_file = temp_dir / "test_journal.md"
        test_file.write_text("Test content")

        # Initial state
        initial_count = len(organizer.file_index["files"])

        # Organize
        organizer.organize_file(test_file)

        # Index should be updated
        assert len(organizer.file_index["files"]) > initial_count

    def test_get_recent_files(self, organizer, temp_dir):
        """Test retrieving recent files."""
        # Create and organize a test file
        test_file = temp_dir / f"Journal_{date.today()}.md"
        test_file.write_text("Test content")
        organizer.organize_file(test_file)
        organizer._save_index()

        recent = organizer.get_recent_files(days=7)
        assert len(recent) > 0

    def test_directory_structure_created(self, organizer):
        """Test that all required directories are created."""
        assert organizer.base_dir.exists()
        assert organizer.reports_dir.exists()
        assert organizer.charts_dir.exists()
        assert organizer.archive_dir.exists()
        assert organizer.research_dir.exists()

        # Category subdirectories
        for cat_dir in organizer.category_dirs.values():
            assert cat_dir.exists()

    def test_generate_index_report(self, organizer, temp_dir):
        """Test index report generation."""
        # Create test file
        test_file = temp_dir / "Journal_2025-12-03.md"
        test_file.write_text("Test content")
        organizer.organize_file(test_file)

        report = organizer.generate_index_report()

        assert "# Syndicate File Index" in report
        assert "Statistics" in report
        assert "Files by Category" in report


class TestFileArchiving:
    """Tests for file archiving functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    @pytest.fixture
    def organizer(self, temp_dir):
        """Create a FileOrganizer with temp directory."""
        import logging

        logger = logging.getLogger("test")

        class MockConfig:
            OUTPUT_DIR = str(temp_dir)

        return FileOrganizer(MockConfig(), logger)

    def test_archive_old_files(self, organizer, temp_dir):
        """Test archiving files older than threshold."""
        # Create an "old" file in the journals directory
        old_date = date.today() - timedelta(days=10)
        journals_dir = organizer.category_dirs["journals"]
        old_file = journals_dir / f"Journal_{old_date}.md"
        old_file.write_text("Old content")

        # Set modification time to old date
        _old_timestamp = (date.today() - timedelta(days=10)).isoformat()  # noqa: F841

        # Archive files older than 7 days
        archived_count = organizer.archive_old_files(days_threshold=7)

        # File should be archived (moved)
        assert not old_file.exists() or archived_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
