#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Intelligent File Gate
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Intelligent file gate for input validation.

Features:
- Multi-source document retrieval (files + database)
- Fuzzy filename matching with date extraction
- Configurable retry logic with exponential backoff
- Staleness detection and validation
- Smart file discovery across multiple directories
"""

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import Config, get_config

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """
    Represents a retrieved document.

    Attributes:
        content: Document text content
        source: Source type ('file' or 'database')
        path: File path (if from file)
        date: Document date
        doc_type: Document type (journal, premarket, weekly)
        metadata: Additional metadata
    """

    content: str
    source: str  # 'file' or 'database'
    path: Optional[Path] = None
    date: Optional[date] = None
    doc_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if document has valid content."""
        return bool(self.content and len(self.content.strip()) > 50)

    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.content.split())

    def __repr__(self) -> str:
        return (
            f"Document(type={self.doc_type!r}, date={self.date}, " f"source={self.source!r}, words={self.word_count})"
        )


@dataclass
class GateStatus:
    """
    Status of all input gates.

    Tracks which inputs are ready and provides
    detailed status for logging.
    """

    journal_ready: bool = False
    journal_doc: Optional[Document] = None

    premarket_ready: bool = False
    premarket_doc: Optional[Document] = None

    weekly_ready: bool = False
    weekly_doc: Optional[Document] = None

    digest_exists: bool = False
    digest_path: Optional[Path] = None

    @property
    def all_inputs_ready(self) -> bool:
        """Check if all required inputs are available."""
        return self.journal_ready and self.premarket_ready and self.weekly_ready

    @property
    def should_skip(self) -> bool:
        """Check if digest already exists (idempotent)."""
        return self.digest_exists

    def summary(self) -> str:
        """Generate human-readable status summary."""

        def status_icon(ready: bool) -> str:
            return "✓" if ready else "✗"

        lines = [
            f"  Journal:   {status_icon(self.journal_ready)} {'Ready' if self.journal_ready else 'Missing'}",
            f"  Pre-market:{status_icon(self.premarket_ready)} {'Ready' if self.premarket_ready else 'Missing'}",
            f"  Weekly:    {status_icon(self.weekly_ready)} {'Ready' if self.weekly_ready else 'Missing'}",
        ]

        if self.digest_exists:
            lines.append(f"  Digest:    ⚠ Already exists at {self.digest_path}")

        return "\n".join(lines)


class FileGate:
    """
    Intelligent file gate for document retrieval.

    Searches for documents across multiple sources:
    1. Primary directory (configured path)
    2. Alternative directories (reports root, archive)
    3. Database fallback (if enabled)

    Features fuzzy matching for flexible filename patterns
    and configurable staleness validation.
    """

    # Filename patterns for document types
    PATTERNS = {
        "journal": [
            r"Journal_(\d{4}-\d{2}-\d{2})\.md",
            r"daily_journal_(\d{4}-\d{2}-\d{2})\.md",
            r"journal_(\d{4}-\d{2}-\d{2})\.md",
            r"(\d{4}-\d{2}-\d{2})_daily_journal\.md",
        ],
        "premarket": [
            r"premarket_(\d{4}-\d{2}-\d{2})\.md",
            r"pre_market_(\d{4}-\d{2}-\d{2})\.md",
            r"PreMarket_(\d{4}-\d{2}-\d{2})\.md",
            r"(\d{4}-\d{2}-\d{2})_premarket\.md",
            r"(\d{4}-\d{2}-\d{2})_pre_market\.md",
        ],
        "weekly": [
            r"weekly_rundown_(\d{4}-\d{2}-\d{2})\.md",
            r"Weekly_(\d{4}-W\d{2})\.md",
            r"weekly_(\d{4}-\d{2}-\d{2})\.md",
            r"(\d{4}-W\d{2})_weekly\.md",
        ],
    }

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize file gate.

        Args:
            config: Configuration object (uses global if None)
        """
        self.config = config or get_config()
        self._db_conn: Optional[sqlite3.Connection] = None

    @property
    def today(self) -> date:
        """Get current date."""
        return date.today()

    @property
    def today_str(self) -> str:
        """Get today's date as YYYY-MM-DD string."""
        return self.today.isoformat()

    def _connect_db(self) -> Optional[sqlite3.Connection]:
        """Get database connection if available."""
        if not self.config.gate.use_database_fallback:
            return None

        if self._db_conn is None:
            db_path = self.config.paths.database_path
            if db_path.exists():
                try:
                    self._db_conn = sqlite3.connect(str(db_path))
                    self._db_conn.row_factory = sqlite3.Row
                    logger.debug(f"Connected to database: {db_path}")
                except Exception as e:
                    logger.warning(f"Database connection failed: {e}")
                    return None

        return self._db_conn

    def _close_db(self) -> None:
        """Close database connection."""
        if self._db_conn is not None:
            self._db_conn.close()
            self._db_conn = None

    def _extract_date_from_filename(self, filename: str, doc_type: str) -> Optional[date]:
        """
        Extract date from filename using type-specific patterns.

        Args:
            filename: Filename to parse
            doc_type: Document type (journal, premarket, weekly)

        Returns:
            Extracted date or None
        """
        patterns = self.PATTERNS.get(doc_type, [])

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Handle YYYY-MM-DD format
                    if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                        return datetime.strptime(date_str, "%Y-%m-%d").date()
                    # Handle YYYY-Www format
                    elif re.match(r"\d{4}-W\d{2}", date_str):
                        return datetime.strptime(date_str + "-1", "%Y-W%W-%w").date()
                except ValueError:
                    continue

        return None

    def _scan_directory(
        self,
        directory: Path,
        doc_type: str,
        target_date: Optional[date] = None,
        max_staleness_days: Optional[int] = None,
    ) -> List[Tuple[Path, date]]:
        """
        Scan directory for matching documents.

        Args:
            directory: Directory to scan
            doc_type: Document type to find
            target_date: Specific date to match (None = any)
            max_staleness_days: Maximum age of documents

        Returns:
            List of (path, date) tuples, sorted by date descending
        """
        if not directory.exists():
            return []

        matches = []

        for file_path in directory.glob("*.md"):
            # Try to extract date from filename
            file_date = self._extract_date_from_filename(file_path.name, doc_type)

            if file_date is None:
                continue

            # Check target date match
            if target_date and file_date != target_date:
                continue

            # Check staleness
            if max_staleness_days is not None:
                age = (self.today - file_date).days
                if age > max_staleness_days:
                    continue

            # Validate file size
            if file_path.stat().st_size < self.config.gate.min_file_size:
                logger.debug(f"Skipping empty file: {file_path}")
                continue

            matches.append((file_path, file_date))

        # Sort by date descending (newest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _search_all_directories(
        self,
        doc_type: str,
        target_date: Optional[date] = None,
        max_staleness_days: Optional[int] = None,
    ) -> List[Tuple[Path, date]]:
        """
        Search all possible directories for a document type.

        Args:
            doc_type: Document type
            target_date: Target date
            max_staleness_days: Max age

        Returns:
            Combined results from all directories
        """
        all_matches = []

        # Define search directories based on type
        search_dirs = []

        if doc_type == "journal":
            search_dirs = [
                self.config.paths.journals_dir,
                self.config.paths.reports_dir / "journals",
                self.config.paths.reports_dir,
                self.config.paths.output_dir / "journals",
            ]
        elif doc_type == "premarket":
            search_dirs = [
                self.config.paths.premarket_dir,
                self.config.paths.reports_dir / "premarket",
                self.config.paths.reports_dir,
                self.config.paths.output_dir / "premarket",
            ]
        elif doc_type == "weekly":
            search_dirs = [
                self.config.paths.weekly_dir,
                self.config.paths.reports_dir / "weekly",
                self.config.paths.reports_dir,
                self.config.paths.output_dir / "weekly",
            ]

        # Remove duplicates while preserving order
        seen = set()
        unique_dirs = []
        for d in search_dirs:
            d_resolved = d.resolve()
            if d_resolved not in seen:
                seen.add(d_resolved)
                unique_dirs.append(d)

        # Scan each directory
        for directory in unique_dirs:
            matches = self._scan_directory(directory, doc_type, target_date, max_staleness_days)
            all_matches.extend(matches)

        # Remove duplicates (same file from different paths)
        seen_files = set()
        unique_matches = []
        for path, file_date in all_matches:
            resolved = path.resolve()
            if resolved not in seen_files:
                seen_files.add(resolved)
                unique_matches.append((path, file_date))

        # Sort by date descending
        unique_matches.sort(key=lambda x: x[1], reverse=True)
        return unique_matches

    def _read_file(self, path: Path) -> Optional[str]:
        """
        Read file content with error handling.

        Args:
            path: File path

        Returns:
            File content or None on error
        """
        try:
            content = path.read_text(encoding="utf-8")
            return content if content.strip() else None
        except Exception as e:
            logger.warning(f"Failed to read file {path}: {e}")
            return None

    def _extract_frontmatter_date(self, content: str) -> Optional[date]:
        """Extract an ISO date from YAML frontmatter if present."""
        if not content.startswith("---"):
            return None

        # Look for a `date: YYYY-MM-DD` line in the first frontmatter block
        lines = content.splitlines()
        for line in lines[1:15]:  # inspect only the frontmatter window
            if line.strip() == "---":
                break
            if line.lower().startswith("date:"):
                _, _, value = line.partition(":")
                value = value.strip().strip("\"'")
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    return None
        return None

    def _validate_document_date(
        self,
        *,
        file_date: date,
        target_date: date,
        doc_type: str,
        content: Optional[str],
        path: Path,
    ) -> bool:
        """Ensure the document strictly matches the target date."""
        if file_date != target_date:
            self._log_skipped_candidate(
                path=path,
                doc_type=doc_type,
                reason=f"filename date {file_date} != target {target_date}",
                file_date=file_date,
            )
            return False

        if content:
            fm_date = self._extract_frontmatter_date(content)
            if fm_date and fm_date != target_date:
                self._log_skipped_candidate(
                    path=path,
                    doc_type=doc_type,
                    reason=f"frontmatter date {fm_date} != target {target_date}",
                    file_date=file_date,
                )
                return False

        return True

    def _log_skipped_candidate(
        self, *, path: Path, doc_type: str, reason: str, file_date: Optional[date] = None
    ) -> None:
        """Surface skipped candidates to logs for ops visibility."""
        logger.info(
            "Skipping %s candidate at %s (%s%s)",
            doc_type,
            path,
            reason,
            f"; file_date={file_date}" if file_date else "",
        )

    def _fetch_from_database(
        self,
        doc_type: str,
        target_date: date,
    ) -> Optional[Document]:
        """
        Fetch document from database.

        Args:
            doc_type: Document type
            target_date: Target date

        Returns:
            Document or None
        """
        conn = self._connect_db()
        if conn is None:
            return None

        try:
            cursor = conn.cursor()
            date_str = target_date.isoformat()

            if doc_type == "journal":
                cursor.execute(
                    "SELECT content, bias, gold_price, created_at FROM journals WHERE date = ?",
                    (date_str,),
                )
            elif doc_type == "premarket":
                cursor.execute(
                    "SELECT content, bias, catalysts, created_at FROM premarket_plans WHERE date = ?",
                    (date_str,),
                )
            else:
                return None

            row = cursor.fetchone()
            if row and row["content"]:
                row_map = {key: row[key] for key in row.keys()}
                return Document(
                    content=row["content"],
                    source="database",
                    date=target_date,
                    doc_type=doc_type,
                    metadata={
                        "bias": row_map.get("bias"),
                        "created_at": row_map.get("created_at"),
                    },
                )
        except Exception as e:
            logger.warning(f"Database fetch failed for {doc_type}: {e}")

        return None

    def find_journal(self, target_date: Optional[date] = None) -> Optional[Document]:
        """
        Find today's journal document.

        Args:
            target_date: Date to find (defaults to today)

        Returns:
            Document or None
        """
        target = target_date or self.today

        # Search files first
        matches = self._search_all_directories(
            "journal",
            target_date=target,
            max_staleness_days=self.config.gate.max_staleness_days,
        )

        for path, file_date in matches:
            content = self._read_file(path)
            if not content:
                continue

            if not self._validate_document_date(
                file_date=file_date,
                target_date=target,
                doc_type="journal",
                content=content,
                path=path,
            ):
                continue

            logger.info(f"Found journal file: {path}")
            return Document(
                content=content,
                source="file",
                path=path,
                date=file_date,
                doc_type="journal",
            )

        # Database fallback
        if self.config.gate.use_database_fallback:
            doc = self._fetch_from_database("journal", target)
            if doc:
                logger.info(f"Found journal in database for {target}")
                return doc

        logger.debug(f"No journal found for {target}")
        return None

    def find_premarket(self, target_date: Optional[date] = None) -> Optional[Document]:
        """
        Find today's pre-market document.

        Args:
            target_date: Date to find (defaults to today)

        Returns:
            Document or None
        """
        target = target_date or self.today

        # Search files
        matches = self._search_all_directories(
            "premarket",
            target_date=target,
            max_staleness_days=self.config.gate.max_staleness_days,
        )

        for path, file_date in matches:
            content = self._read_file(path)
            if not content:
                continue

            if not self._validate_document_date(
                file_date=file_date,
                target_date=target,
                doc_type="premarket",
                content=content,
                path=path,
            ):
                continue

            logger.info(f"Found premarket file: {path}")
            return Document(
                content=content,
                source="file",
                path=path,
                date=file_date,
                doc_type="premarket",
            )

        # Database fallback
        if self.config.gate.use_database_fallback:
            doc = self._fetch_from_database("premarket", target)
            if doc:
                logger.info(f"Found premarket in database for {target}")
                return doc

        logger.debug(f"No premarket found for {target}")
        return None

    def find_weekly(self) -> Optional[Document]:
        """
        Find the most recent weekly report.

        Uses configured lookback window to find latest weekly report.

        Returns:
            Document or None
        """
        # Search with extended lookback
        matches = self._search_all_directories(
            "weekly",
            target_date=None,  # Any date
            max_staleness_days=self.config.gate.weekly_lookback_days,
        )

        if matches:
            path, file_date = matches[0]
            content = self._read_file(path)
            if content:
                logger.info(f"Found weekly report: {path} (dated {file_date})")
                return Document(
                    content=content,
                    source="file",
                    path=path,
                    date=file_date,
                    doc_type="weekly",
                )

        logger.debug("No weekly report found")
        return None

    def get_digest_path(self, target_date: Optional[date] = None) -> Path:
        """
        Get the path for today's digest file.

        Args:
            target_date: Date for digest (defaults to today)

        Returns:
            Path for digest file
        """
        target = target_date or self.today
        filename = f"{target.isoformat()}_digest.md"
        return self.config.paths.digest_output_dir / filename

    def digest_exists(self, target_date: Optional[date] = None) -> bool:
        """
        Check if digest already exists for date.

        Args:
            target_date: Date to check (defaults to today)

        Returns:
            True if digest exists
        """
        path = self.get_digest_path(target_date)
        return path.exists() and path.stat().st_size >= self.config.gate.min_file_size

    def check_all_gates(self, target_date: Optional[date] = None) -> GateStatus:
        """
        Check status of all input gates.

        Args:
            target_date: Date to check (defaults to today)

        Returns:
            GateStatus with results
        """
        target = target_date or self.today
        status = GateStatus()

        # Check journal
        journal = self.find_journal(target)
        if journal and journal.is_valid:
            status.journal_ready = True
            status.journal_doc = journal

        # Check premarket
        premarket = self.find_premarket(target)
        if premarket and premarket.is_valid:
            status.premarket_ready = True
            status.premarket_doc = premarket

        # Check weekly (any recent)
        weekly = self.find_weekly()
        if weekly and weekly.is_valid:
            status.weekly_ready = True
            status.weekly_doc = weekly

        # Check if digest already exists
        digest_path = self.get_digest_path(target)
        if self.digest_exists(target):
            status.digest_exists = True
            status.digest_path = digest_path

        return status

    def wait_for_inputs(
        self,
        target_date: Optional[date] = None,
        max_retries: Optional[int] = None,
        retry_interval: Optional[int] = None,
        callback=None,
    ) -> GateStatus:
        """
        Wait for all inputs to be ready with retry logic.

        Args:
            target_date: Date to wait for
            max_retries: Override max retries
            retry_interval: Override retry interval (seconds)
            callback: Optional callback(attempt, status) for progress

        Returns:
            Final GateStatus
        """
        import time

        max_attempts = max_retries or self.config.gate.max_retries
        interval = retry_interval or self.config.gate.retry_interval_sec

        for attempt in range(max_attempts + 1):
            status = self.check_all_gates(target_date)

            # Already done - digest exists
            if status.should_skip:
                logger.info("Digest already exists, skipping")
                return status

            # All inputs ready
            if status.all_inputs_ready:
                logger.info("All inputs ready")
                return status

            # Progress callback
            if callback:
                callback(attempt, status)

            # Don't sleep on last attempt
            if attempt < max_attempts:
                logger.info(f"Waiting for inputs (attempt {attempt + 1}/{max_attempts + 1})\n" f"{status.summary()}")
                time.sleep(interval)

        # Max retries reached
        logger.warning(f"Max retries ({max_attempts}) reached, inputs not ready")
        return status

    def close(self) -> None:
        """Clean up resources."""
        self._close_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
