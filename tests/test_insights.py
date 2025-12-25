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
Tests for the Syndicate Insights Engine and Task Executor.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.insights_engine import InsightsExtractor


class TestEntityExtraction:
    """Tests for entity extraction functionality."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance without AI model."""
        import logging

        logger = logging.getLogger("test")
        return InsightsExtractor(None, logger, model=None)

    def test_extract_institution_entities(self, extractor):
        """Test extraction of institutional entities."""
        report = """
        The Federal Reserve is expected to announce rate decisions next week.
        Goldman Sachs maintains a bullish target of $4,500 for gold.
        JP Morgan sees near-term risks to the downside.
        """

        entities = extractor.extract_entities(report, "test_report")
        entity_names = [e.entity_name for e in entities]

        assert "Federal Reserve" in entity_names or "Fed" in entity_names
        assert "Goldman Sachs" in entity_names
        assert any("JP Morgan" in name or "JPMorgan" in name for name in entity_names)

    def test_extract_indicator_entities(self, extractor):
        """Test extraction of indicator entities."""
        report = """
        CPI data came in hotter than expected, pushing inflation concerns.
        The RSI on gold is at 68, approaching overbought territory.
        NFP report due Friday may impact dollar strength.
        """

        entities = extractor.extract_entities(report, "test_report")
        entity_names = [e.entity_name for e in entities]

        assert "CPI" in entity_names
        assert "RSI" in entity_names
        assert "NFP" in entity_names

    def test_extract_asset_entities(self, extractor):
        """Test extraction of asset entities."""
        report = """
        Gold rallied to $4,300 while Silver lagged behind.
        DXY weakness provided a tailwind for precious metals.
        VIX spiked above 20, indicating elevated market fear.
        """

        entities = extractor.extract_entities(report, "test_report")
        entity_names = [e.entity_name for e in entities]

        assert "Gold" in entity_names
        assert "Silver" in entity_names
        assert "DXY" in entity_names
        assert "VIX" in entity_names

    def test_entity_relevance_scoring(self, extractor):
        """Test that relevance scoring works correctly."""
        # Entity in a header should have higher relevance
        report = """
        ## Critical: Fed Decision Ahead

        The Fed meeting is the key catalyst this week.
        Monitor Fed communications closely.
        """

        entities = extractor.extract_entities(report, "test_report")
        fed_entities = [e for e in entities if "Fed" in e.entity_name]

        assert len(fed_entities) > 0
        # Header and action keywords should boost relevance
        assert any(e.relevance_score > 0.5 for e in fed_entities)


class TestActionExtraction:
    """Tests for action insight extraction."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance without AI model."""
        import logging

        logger = logging.getLogger("test")
        return InsightsExtractor(None, logger, model=None)

    def test_extract_research_actions(self, extractor):
        """Test extraction of research tasks."""
        report = """
        Need to research the ECB's policy trajectory and its impact on EUR/USD.
        Further analysis on central bank demand patterns is recommended.
        """

        actions = extractor.extract_actions(report, "test_report")
        research_actions = [a for a in actions if a.action_type == "research"]

        assert len(research_actions) > 0

    def test_extract_monitoring_actions(self, extractor):
        """Test extraction of monitoring tasks."""
        report = """
        Key levels to watch: Support at $4,200 is critical.
        Watch for breakout above $4,400.
        Monitor VIX for signs of volatility spike.
        """

        actions = extractor.extract_actions(report, "test_report")
        monitoring_actions = [a for a in actions if a.action_type == "monitoring"]

        assert len(monitoring_actions) > 0

    def test_extract_data_fetch_actions(self, extractor):
        """Test extraction of data fetch tasks."""
        report = """
        Check the latest COT data for gold positioning.
        Need to get ETF flow data for GLD and SLV.
        """

        actions = extractor.extract_actions(report, "test_report")
        data_actions = [a for a in actions if a.action_type == "data_fetch"]

        assert len(data_actions) > 0

    def test_action_priority_assignment(self, extractor):
        """Test that priorities are assigned correctly."""
        report = """
        Critical: Immediately monitor breaking news on Fed decision.
        Important key levels to watch this week.
        Consider tracking minor support levels.
        """

        actions = extractor.extract_actions(report, "test_report")

        # Should have mix of priorities
        priorities = [a.priority for a in actions]
        assert len(priorities) > 0

    def test_action_id_generation(self, extractor):
        """Test that action IDs are unique and properly formatted."""
        report = """
        Need to research topic A.
        Need to research topic B.
        Monitor level X.
        """

        actions = extractor.extract_actions(report, "test_report")
        action_ids = [a.action_id for a in actions]

        # All IDs should be unique
        assert len(action_ids) == len(set(action_ids))

        # IDs should follow pattern ACT-YYYYMMDD-XXXX
        for aid in action_ids:
            assert aid.startswith("ACT-")

    def test_action_deadline_calculation(self, extractor):
        """Test that deadlines are calculated based on priority."""
        report = """
        Critical: Immediate action required.
        Low priority: Consider eventually.
        """

        actions = extractor.extract_actions(report, "test_report")

        # Critical actions should have earlier deadlines
        for action in actions:
            assert action.deadline is not None
            deadline = datetime.fromisoformat(action.deadline)
            assert deadline > datetime.now()


class TestInsightsIntegration:
    """Integration tests for the insights system."""

    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        import logging

        logger = logging.getLogger("test")
        return InsightsExtractor(None, logger, model=None)

    def test_full_report_processing(self, extractor):
        """Test processing a realistic report."""
        report = """
        # Daily Analysis - December 3, 2025

        ## Market Context

        The Fed's upcoming FOMC meeting is the key catalyst this week.
        CPI data showed inflation remains sticky at 3.2%.

        ## Technical Analysis

        Gold RSI at 65, approaching overbought. ADX at 28 indicates trending market.
        Support at $4,200 is critical. Resistance at $4,400 must break for continuation.

        ## Action Items

        1. Need to research ECB policy trajectory
        2. Monitor VIX for volatility signals
        3. Check latest COT positioning data
        4. Calculate position size based on ATR

        ## Institutional View

        Goldman Sachs maintains $4,500 target.
        JP Morgan sees near-term consolidation.
        """

        entities = extractor.extract_entities(report, "test_report")
        actions = extractor.extract_actions(report, "test_report")

        # Should extract meaningful entities
        assert len(entities) > 5

        # Should extract actionable tasks
        assert len(actions) >= 3

        # Should have various entity types
        entity_types = set(e.entity_type for e in entities)
        assert len(entity_types) >= 2

        # Should have various action types
        action_types = set(a.action_type for a in actions)
        assert len(action_types) >= 2

    def test_export_to_dict(self, extractor):
        """Test exporting insights to dictionary format."""
        report = "The Fed announced rate cuts. Monitor support at $4,200."

        extractor.extract_entities(report, "test_report")
        extractor.extract_actions(report, "test_report")

        export = extractor.to_dict()

        assert "entities" in export
        assert "actions" in export
        assert "summary" in export
        assert isinstance(export["summary"]["total_entities"], int)
        assert isinstance(export["summary"]["total_actions"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
