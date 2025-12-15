#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Test Suite
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Comprehensive test suite for the Digest Bot.
"""

import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from typing import Generator

import pytest

# Import modules under test
from src.digest_bot.config import Config, GateConfig, LLMConfig, PathConfig
from src.digest_bot.file_gate import Document, FileGate, GateStatus
from src.digest_bot.summarizer import DigestResult, Summarizer, clean_content, extract_frontmatter, truncate_content
from src.digest_bot.writer import DigestWriter

# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_config(temp_dir: Path) -> Config:
    """Create test configuration."""
    output_dir = temp_dir / "output"
    output_dir.mkdir(parents=True)

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True)

    log_dir = temp_dir / "logs"
    log_dir.mkdir(parents=True)

    return Config(
        llm=LLMConfig(
            provider="local",
            local_model_path=temp_dir / "model.gguf",
            temperature=0.3,
            max_tokens=500,
        ),
        paths=PathConfig(
            output_dir=output_dir,
            reports_dir=reports_dir,
            journals_dir=reports_dir / "journals",
            premarket_dir=reports_dir / "premarket",
            weekly_dir=reports_dir / "weekly",
            digest_output_dir=output_dir / "digests",
            database_path=temp_dir / "test.db",
            log_file=log_dir / "digest_bot.log",
        ),
        gate=GateConfig(
            retry_interval_sec=1,
            max_retries=2,
            max_staleness_days=400,
            weekly_lookback_days=400,
            min_file_size=50,
            use_database_fallback=True,
        ),
    )


@pytest.fixture
def sample_journal_content() -> str:
    """Sample journal markdown."""
    return """---
title: "Daily Journal"
date: 2025-01-15
---

# Daily Trading Journal

## Market Summary
Gold opened at $2,680 and tested resistance at $2,700.

## Key Observations
- Strong buying pressure in Asian session
- Dollar weakness supporting metals
- Technical breakout above 50 DMA

## Trades
1. Long XAU/USD at $2,685
2. Target: $2,720
3. Stop: $2,670

## Lessons Learned
Patience paid off waiting for the retest.
"""


@pytest.fixture
def sample_premarket_content() -> str:
    """Sample pre-market plan."""
    return """---
title: "Pre-Market Plan"
date: 2025-01-15
---

# Pre-Market Analysis

## Overnight Developments
- Gold futures up 0.5% in Asian trading
- Fed minutes released, dovish tone

## Key Levels
- Resistance: $2,700, $2,720
- Support: $2,660, $2,640

## Trading Plan
Look for long entries on pullback to $2,680 support.
Risk: 0.5% of account per trade.
"""


@pytest.fixture
def sample_weekly_content() -> str:
    """Sample weekly report."""
    return """# Weekly Market Report

## Week Summary
Gold gained 2.3% this week on dollar weakness.

## Key Events
- Fed rate decision
- NFP data
- Treasury auctions

## Outlook
Bullish bias continues into next week.
"""


@pytest.fixture
def test_db(temp_dir: Path) -> Path:
    """Create test database with sample data."""
    db_path = temp_dir / "test.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE journals (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            bias TEXT,
            gold_price REAL,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE premarket_plans (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            bias TEXT,
            catalysts TEXT,
            created_at TEXT
        )
    """)

    # Insert test data
    cursor.execute(
        "INSERT INTO journals (date, content) VALUES (?, ?)", ("2025-01-15", "Database journal content for 2025-01-15")
    )

    cursor.execute(
        "INSERT INTO premarket_plans (date, content) VALUES (?, ?)",
        ("2025-01-15", "Database premarket content for 2025-01-15"),
    )

    conn.commit()
    conn.close()

    return db_path


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestConfig:
    """Tests for configuration module."""

    def test_llm_config_defaults(self):
        """Test LLM config default values."""
        config = LLMConfig()

        assert config.provider == "local"
        assert config.temperature == 0.3
        assert config.max_tokens == 768

    def test_path_config_creates_paths(self, temp_dir: Path):
        """Test path config creates Path objects."""
        config = PathConfig(
            output_dir=temp_dir / "output",
            database_path=temp_dir / "db.sqlite",
        )

        assert isinstance(config.output_dir, Path)
        assert isinstance(config.database_path, Path)

    def test_gate_config_defaults(self):
        """Test gate config defaults."""
        config = GateConfig()

        assert config.retry_interval_sec == 300
        assert config.max_retries == 48
        assert config.max_staleness_days == 1
        assert config.use_database_fallback is True

    def test_config_validate_paths(self, mock_config: Config):
        """Test config validation creates directories."""
        # Ensure database path exists to avoid validation warning for tests
        mock_config.paths.database_path.touch()
        mock_config.validate()

        assert mock_config.paths.output_dir.exists()
        assert mock_config.paths.digest_output_dir.exists()
        assert mock_config.paths.log_file.parent.exists()


# ══════════════════════════════════════════════════════════════════════════════
# FILE GATE TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestFileGate:
    """Tests for file gate module."""

    def test_document_creation(self):
        """Test Document dataclass."""
        doc = Document(
            content="Test content",
            source="file",
            path=Path("/test/path.md"),
        )

        assert doc.content == "Test content"
        assert doc.source == "file"
        assert doc.path == Path("/test/path.md")

    def test_document_from_database(self):
        """Test creating document from database."""
        doc = Document(
            content="DB content",
            source="database",
            path=None,
        )

        assert doc.source == "database"
        assert doc.path is None

    def test_gate_status_all_ready(
        self,
        sample_journal_content: str,
        sample_premarket_content: str,
        sample_weekly_content: str,
    ):
        """Test gate status when all inputs ready."""
        status = GateStatus(
            journal_doc=Document(sample_journal_content, "file"),
            premarket_doc=Document(sample_premarket_content, "file"),
            weekly_doc=Document(sample_weekly_content, "file"),
            journal_ready=True,
            premarket_ready=True,
            weekly_ready=True,
        )

        assert status.journal_ready is True
        assert status.premarket_ready is True
        assert status.weekly_ready is True
        assert status.all_inputs_ready is True

    def test_gate_status_missing_journal(
        self,
        sample_premarket_content: str,
    ):
        """Test gate status with missing journal."""
        status = GateStatus(
            journal_doc=None,
            premarket_doc=Document(sample_premarket_content, "file"),
            weekly_doc=None,
            premarket_ready=True,
        )

        assert status.journal_ready is False
        assert status.premarket_ready is True
        assert status.all_inputs_ready is False

    def test_file_gate_find_journal_from_file(
        self,
        mock_config: Config,
        sample_journal_content: str,
    ):
        """Test finding journal from file."""
        # Create test file
        reports_dir = mock_config.paths.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        journal_file = reports_dir / "Journal_2025-01-15.md"
        journal_file.write_text(sample_journal_content, encoding="utf-8")

        gate = FileGate(mock_config)
        doc = gate.find_journal(date(2025, 1, 15))

        assert doc is not None
        assert "Daily Trading Journal" in doc.content
        assert doc.source == "file"

    def test_file_gate_find_journal_from_db(
        self,
        mock_config: Config,
        test_db: Path,
    ):
        """Test finding journal from database fallback."""
        mock_config.paths.database_path = test_db

        gate = FileGate(mock_config)
        doc = gate.find_journal(date(2025, 1, 15))

        assert doc is not None
        assert "Database journal content" in doc.content
        assert doc.source == "database"

    def test_file_gate_rejects_wrong_date_file(self, mock_config: Config, sample_journal_content: str):
        """Ensure older journal files are not selected for today's run."""
        mock_config.gate.use_database_fallback = False

        # Create only an older journal file
        journal_dir = mock_config.paths.journals_dir
        journal_dir.mkdir(parents=True, exist_ok=True)

        older = journal_dir / "Journal_2025-01-14.md"
        older.write_text(sample_journal_content, encoding="utf-8")

        gate = FileGate(mock_config)
        doc = gate.find_journal(date(2025, 1, 15))

        assert doc is None

    def test_file_gate_rejects_frontmatter_mismatch(self, mock_config: Config, sample_journal_content: str):
        """Reject files whose frontmatter date disagrees with filename/target."""
        mock_config.gate.use_database_fallback = False

        journal_dir = mock_config.paths.journals_dir
        journal_dir.mkdir(parents=True, exist_ok=True)

        bad_content = sample_journal_content.replace("2025-01-15", "2025-01-14")
        target_file = journal_dir / "Journal_2025-01-15.md"
        target_file.write_text(bad_content, encoding="utf-8")

        gate = FileGate(mock_config)
        doc = gate.find_journal(date(2025, 1, 15))

        assert doc is None

    def test_file_gate_premarket_date_strict(self, mock_config: Config, sample_premarket_content: str):
        """Only pick premarket matching the target date."""
        mock_config.gate.use_database_fallback = False

        pre_dir = mock_config.paths.premarket_dir
        pre_dir.mkdir(parents=True, exist_ok=True)

        # Older file
        (pre_dir / "premarket_2025-01-14.md").write_text(sample_premarket_content, encoding="utf-8")

        gate = FileGate(mock_config)
        doc = gate.find_premarket(date(2025, 1, 15))

        assert doc is None

    def test_file_gate_check_all(
        self,
        mock_config: Config,
        sample_journal_content: str,
        sample_premarket_content: str,
        sample_weekly_content: str,
    ):
        """Test checking all gates."""
        # Create test files
        reports_dir = mock_config.paths.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        (reports_dir / "Journal_2025-01-15.md").write_text(sample_journal_content, encoding="utf-8")
        (reports_dir / "premarket_2025-01-15.md").write_text(sample_premarket_content, encoding="utf-8")
        (reports_dir / "weekly_rundown_2025-01-12.md").write_text(sample_weekly_content, encoding="utf-8")

        gate = FileGate(mock_config)
        status = gate.check_all_gates(date(2025, 1, 15))

        assert status.journal_ready is True
        assert status.premarket_ready is True


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARIZER TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSummarizerHelpers:
    """Tests for summarizer helper functions."""

    def test_extract_frontmatter_valid(self):
        """Test extracting valid YAML frontmatter."""
        content = """---
title: "Test"
date: 2025-01-15
---

# Content
Some text here.
"""
        fm, body = extract_frontmatter(content)

        assert fm["title"] == "Test"
        assert fm["date"] == "2025-01-15"
        assert "# Content" in body

    def test_extract_frontmatter_none(self):
        """Test content without frontmatter."""
        content = "# Just Content\nNo frontmatter here."

        fm, body = extract_frontmatter(content)

        assert fm == {}
        assert body == content

    def test_truncate_content_short(self):
        """Test truncation of short content."""
        content = "Short content that fits."

        result = truncate_content(content, max_tokens=100)

        assert result == content
        assert "[truncated]" not in result

    def test_truncate_content_long(self):
        """Test truncation of long content."""
        content = "A" * 10000

        result = truncate_content(content, max_tokens=100)

        assert len(result) < len(content)
        assert "[... content truncated for length ...]" in result

    def test_clean_content(self, sample_journal_content: str):
        """Test content cleaning."""
        cleaned = clean_content(sample_journal_content)

        assert "---" not in cleaned.split("\n")[0]  # No frontmatter start
        assert "title:" not in cleaned
        assert "Daily Trading Journal" in cleaned


class TestSummarizer:
    """Tests for Summarizer class."""

    def test_summarizer_init(self, mock_config: Config):
        """Test summarizer initialization."""
        summarizer = Summarizer(mock_config)

        assert summarizer.config == mock_config
        assert summarizer._provider is None

    def test_summarizer_prepare_document(
        self,
        mock_config: Config,
        sample_journal_content: str,
    ):
        """Test document preparation."""
        summarizer = Summarizer(mock_config)

        doc = Document(sample_journal_content, "file")
        prepared = summarizer._prepare_document(doc)

        assert "Daily Trading Journal" in prepared
        assert len(prepared) > 0

    def test_summarizer_prepare_none_document(self, mock_config: Config):
        """Test preparation of None document."""
        summarizer = Summarizer(mock_config)

        prepared = summarizer._prepare_document(None)

        assert "[Document not available]" in prepared

    def test_summarizer_build_prompt(
        self,
        mock_config: Config,
        sample_journal_content: str,
        sample_premarket_content: str,
        sample_weekly_content: str,
    ):
        """Test prompt building."""
        summarizer = Summarizer(mock_config)

        status = GateStatus(
            journal_doc=Document(sample_journal_content, "file"),
            premarket_doc=Document(sample_premarket_content, "file"),
            weekly_doc=Document(sample_weekly_content, "file"),
        )

        prompt = summarizer.build_prompt(status, date(2025, 1, 15))

        assert "2025-01-15" in prompt
        assert "Daily Trading Journal" in prompt
        assert "Pre-Market" in prompt
        assert "Key Takeaways" in prompt

    def test_summarizer_generate_missing_inputs(self, mock_config: Config):
        """Test generation with missing inputs."""
        summarizer = Summarizer(mock_config)

        status = GateStatus(
            journal_doc=None,
            premarket_doc=None,
            weekly_doc=None,
        )

        result = summarizer.generate(status)

        assert result.success is False
        assert "Missing required inputs" in result.error


# ══════════════════════════════════════════════════════════════════════════════
# WRITER TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDigestWriter:
    """Tests for DigestWriter class."""

    def test_writer_init(self, mock_config: Config):
        """Test writer initialization."""
        writer = DigestWriter(mock_config)

        assert writer.config == mock_config

    def test_writer_output_dir_creation(self, mock_config: Config):
        """Test automatic output directory creation."""
        writer = DigestWriter(mock_config)

        output_dir = writer.output_dir

        assert output_dir.exists()
        assert "digests" in str(output_dir)

    def test_writer_get_digest_path(self, mock_config: Config):
        """Test getting digest path."""
        writer = DigestWriter(mock_config)

        path = writer.get_digest_path(date(2025, 1, 15))

        assert "digest_2025-01-15.md" in str(path)

    def test_writer_exists_false(self, mock_config: Config):
        """Test exists check for missing digest."""
        writer = DigestWriter(mock_config)

        assert writer.exists(date(2025, 1, 15)) is False

    def test_writer_exists_true(self, mock_config: Config):
        """Test exists check for existing digest."""
        writer = DigestWriter(mock_config)

        # Create a digest file
        path = writer.get_digest_path(date(2025, 1, 15))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Test digest")

        assert writer.exists(date(2025, 1, 15)) is True

    def test_writer_format_digest(self, mock_config: Config):
        """Test digest formatting."""
        writer = DigestWriter(mock_config)

        result = DigestResult(
            content="# Key Takeaways\n- Point 1\n- Point 2",
            success=True,
            metadata={
                "provider": "llamacpp",
                "model": "test-model",
                "tokens_used": 150,
                "generation_time": 2.5,
            },
        )

        formatted = writer.format_digest(result, date(2025, 1, 15))

        assert "Daily Digest — 2025-01-15" in formatted
        assert "Key Takeaways" in formatted
        assert "llamacpp" in formatted

    def test_writer_write_success(self, mock_config: Config):
        """Test successful write."""
        writer = DigestWriter(mock_config)

        result = DigestResult(
            content="# Key Takeaways\n- Point 1\n- Point 2\n\n## Actionable Steps\n- Step 1",
            success=True,
            metadata={
                "provider": "llamacpp",
                "model": "test-model",
                "tokens_used": 150,
                "generation_time": 2.5,
            },
        )

        write_result = writer.write(result, date(2025, 1, 15))

        assert write_result.success is True
        assert write_result.path.exists()

        content = write_result.path.read_text()
        assert "Key Takeaways" in content

    def test_writer_write_no_overwrite(self, mock_config: Config):
        """Test write fails without overwrite flag."""
        writer = DigestWriter(mock_config)

        result = DigestResult(
            content="# Test content here with enough length to pass validation checks",
            success=True,
            metadata={},
        )

        # First write
        writer.write(result, date(2025, 1, 15))

        # Second write without overwrite
        write_result = writer.write(result, date(2025, 1, 15), overwrite=False)

        assert write_result.success is False
        assert "already exists" in write_result.error

    def test_writer_write_with_backup(self, mock_config: Config):
        """Test write creates backup."""
        writer = DigestWriter(mock_config)

        result = DigestResult(
            content="# Original content that is long enough to pass validation",
            success=True,
            metadata={},
        )

        # First write
        writer.write(result, date(2025, 1, 15))

        # Overwrite with backup
        result2 = DigestResult(
            content="# Updated content that is also long enough for validation",
            success=True,
            metadata={},
        )

        write_result = writer.write(result2, date(2025, 1, 15), overwrite=True, backup=True)

        assert write_result.success is True
        assert write_result.backup_path is not None
        assert write_result.backup_path.exists()

    def test_writer_dry_run(self, mock_config: Config):
        """Test dry run returns content without writing."""
        writer = DigestWriter(mock_config)

        result = DigestResult(
            content="# Dry run content",
            success=True,
            metadata={},
        )

        formatted = writer.write_dry_run(result, date(2025, 1, 15))

        assert "Dry run content" in formatted
        assert not writer.exists(date(2025, 1, 15))

    def test_writer_list_digests(self, mock_config: Config):
        """Test listing digests."""
        writer = DigestWriter(mock_config)

        # Create some digests
        for day in range(1, 6):
            result = DigestResult(
                content=(f"# Digest {day}\n" + "Line of detail " * 10),
                success=True,
                metadata={},
            )
            write_result = writer.write(result, date(2025, 1, day))
            assert write_result.success is True

        digests = writer.list_digests(limit=3)

        assert len(digests) == 3

    def test_writer_cleanup(self, mock_config: Config):
        """Test digest cleanup."""
        writer = DigestWriter(mock_config)

        # Create some digests
        for day in range(1, 11):
            result = DigestResult(
                content=(f"# Digest {day}\n" + "Detail " * 20),
                success=True,
                metadata={},
            )
            write_result = writer.write(result, date(2025, 1, day))
            assert write_result.success is True

        # Cleanup keeping only 5
        deleted = writer.cleanup_old_digests(keep_count=5, dry_run=True)

        assert len(deleted) == 5


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Integration tests for the digest pipeline."""

    def test_full_pipeline_mock_llm(
        self,
        mock_config: Config,
        sample_journal_content: str,
        sample_premarket_content: str,
        sample_weekly_content: str,
    ):
        """Test full pipeline with mocked LLM."""
        # Setup files
        reports_dir = mock_config.paths.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        (reports_dir / "Journal_2025-01-15.md").write_text(sample_journal_content, encoding="utf-8")
        (reports_dir / "premarket_2025-01-15.md").write_text(sample_premarket_content, encoding="utf-8")
        (reports_dir / "weekly_rundown_2025-01-12.md").write_text(sample_weekly_content, encoding="utf-8")

        # Check gate
        gate = FileGate(mock_config)
        status = gate.check_all_gates(date(2025, 1, 15))

        assert status.all_inputs_ready is True

        # Build prompt (without running LLM)
        summarizer = Summarizer(mock_config)
        prompt = summarizer.build_prompt(status, date(2025, 1, 15))

        assert len(prompt) > 500
        assert "Key Takeaways" in prompt

        # Simulate LLM response
        mock_result = DigestResult(
            content="""## Key Takeaways
- Gold tested $2,700 resistance as expected
- Dollar weakness continues to support metals
- Technical breakout above 50 DMA confirmed

## Actionable Next Steps
- Watch for pullback to $2,680 support for long entry
- Set alerts at $2,700 and $2,720 resistance levels

## Rationale
Pre-market analysis correctly identified key levels and the journal
confirms the technical breakout. Maintain bullish bias.""",
            success=True,
            metadata={
                "provider": "llamacpp",
                "model": "test",
                "tokens_used": 100,
                "generation_time": 1.0,
            },
        )

        # Write digest
        writer = DigestWriter(mock_config)
        write_result = writer.write(mock_result, date(2025, 1, 15))

        assert write_result.success is True
        assert write_result.path.exists()

        content = write_result.path.read_text()
        assert "Key Takeaways" in content
        assert "Gold tested $2,700" in content


# ══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
