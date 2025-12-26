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
Syndicate Database Manager
SQLite-based storage for reports, journals, analysis data, and insights.
Provides intelligent redundancy control, date-wise organization, and task management.
"""

import os
import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database path
DB_DIR = Path(__file__).resolve().parent / "data"
# Allow overriding DB path via environment (useful for tests and alternate deployments)
_env_db = os.getenv("GOLD_STANDARD_TEST_DB") or os.getenv("GOLD_STANDARD_DB")
if _env_db:
    DB_PATH = Path(_env_db)
else:
    DB_PATH = DB_DIR / "syndicate.db"


@dataclass
class JournalEntry:
    """Represents a daily journal entry."""

    date: str  # YYYY-MM-DD
    content: str
    bias: Optional[str] = None
    gold_price: Optional[float] = None
    silver_price: Optional[float] = None
    gsr: Optional[float] = None  # Gold/Silver ratio
    ai_enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Report:
    """Represents a periodic report (weekly, monthly, yearly)."""

    report_type: str  # 'weekly', 'monthly', 'yearly'
    period: str  # 'YYYY-WW', 'YYYY-MM', 'YYYY'
    content: str
    summary: Optional[str] = None
    ai_enabled: bool = True
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AnalysisSnapshot:
    """Stores technical analysis data for historical tracking."""

    date: str
    asset: str
    price: float
    rsi: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    trend: Optional[str] = None
    raw_data: Optional[str] = None  # JSON blob for full data


class DatabaseManager:
    """
    Manages SQLite database for Syndicate system.
    Handles journals, reports, and analysis data with intelligent redundancy control.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Performance and concurrency tuning for SQLite
            try:
                cursor.execute("PRAGMA journal_mode = WAL;")
            except Exception:
                pass
            try:
                cursor.execute("PRAGMA synchronous = NORMAL;")
            except Exception:
                pass
            try:
                cursor.execute("PRAGMA temp_store = MEMORY;")
            except Exception:
                pass
            try:
                # Larger cache (negative value -> KB * -1 pages depending on SQLite build)
                cursor.execute("PRAGMA cache_size = -20000;")
            except Exception:
                pass
            try:
                cursor.execute("PRAGMA busy_timeout = 5000;")
            except Exception:
                pass

            # Journals table - one per day
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS journals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    bias TEXT,
                    gold_price REAL,
                    silver_price REAL,
                    gsr REAL,
                    ai_enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # LLM sanitizer audit table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_sanitizer_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    corrections INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Bot audit table - records operator and bot actions (approve, flag, rerun, moderation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Discord message history for dedupe/rate-limit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discord_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT,
                    fingerprint TEXT,
                    payload_hash TEXT,
                    sent_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # social posts table for external platforms (audit and dedupe)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT,
                    fingerprint TEXT,
                    payload_hash TEXT,
                    external_id TEXT,
                    status TEXT DEFAULT 'sent',
                    sent_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # Subscriptions table - user subscriptions to topics for alerts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_id, topic)
                )
            """)
            # Persistent LLM tasks queue (ensure created early so tests and scripts can rely on it)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_path TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    provider_hint TEXT,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    response TEXT,
                    error TEXT,
                    priority TEXT DEFAULT 'normal',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    started_at TEXT,
                    last_attempt_at TEXT,
                    completed_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_tasks_status_created ON llm_tasks(status, created_at)")
            # Migration: add 'task_type' column to distinguish generation vs post-processing tasks
            try:
                cursor.execute("ALTER TABLE llm_tasks ADD COLUMN task_type TEXT DEFAULT 'generate'")
            except sqlite3.OperationalError:
                pass  # Column likely already exists

            # Ensure model_usage table exists for pruning/metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_path TEXT UNIQUE NOT NULL,
                    name TEXT,
                    size_gb REAL,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Reports table - weekly, monthly, yearly
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    period TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    ai_enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(report_type, period)
                )
            """)

            # Analysis snapshots - historical technical data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    price REAL NOT NULL,
                    rsi REAL,
                    sma_50 REAL,
                    sma_200 REAL,
                    atr REAL,
                    adx REAL,
                    trend TEXT,
                    raw_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, asset)
                )
            """)

            # Pre-market plans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premarket_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    bias TEXT,
                    catalysts TEXT,
                    ai_enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Trade simulations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    direction TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT DEFAULT 'OPEN',
                    result TEXT,
                    pnl REAL,
                    pnl_pct REAL,
                    entry_date TEXT NOT NULL,
                    exit_date TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Entity insights table - extracted entities from reports
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    context TEXT,
                    relevance_score REAL DEFAULT 0.5,
                    source_report TEXT,
                    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    UNIQUE(entity_name, source_report)
                )
            """)

            # Action insights table - actionable tasks extracted from reports
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE NOT NULL,
                    action_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    source_report TEXT,
                    source_context TEXT,
                    deadline TEXT,
                    scheduled_for TEXT,
                    result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    metadata TEXT
                )
            """)

            # System configuration table - stores runtime settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Cortex memory table - dedicated storage for persistent memory (JSON)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cortex_memory (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    memory_json TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Task execution log - tracks task executor results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_execution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT NOT NULL,
                    success INTEGER DEFAULT 0,
                    result_data TEXT,
                    execution_time_ms REAL,
                    error_message TEXT,
                    artifacts TEXT,
                    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Notion sync tracking - prevents duplicate publishing
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notion_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    notion_page_id TEXT,
                    notion_url TEXT,
                    doc_type TEXT,
                    synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_path)
                )
            """)

            # Schedule tracking - controls frequency of different operations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT UNIQUE NOT NULL,
                    last_run TEXT,
                    next_run TEXT,
                    frequency TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)

            # Document lifecycle - tracks draft/in_progress/published status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_lifecycle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    doc_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    published_at TEXT,
                    notion_page_id TEXT,
                    content_hash TEXT,
                    version INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)

            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_journals_date ON journals(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_type_period ON reports(report_type, period)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_date_asset ON analysis_snapshots(date, asset)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_insights_name ON entity_insights(entity_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_insights_status ON action_insights(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_action_insights_priority ON action_insights(priority)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_log_action ON task_execution_log(action_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notion_sync_path ON notion_sync(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_task ON schedule_tracker(task_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_lifecycle_path ON document_lifecycle(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_lifecycle_status ON document_lifecycle(status)")

            # LLM caching and usage tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    prompt TEXT,
                    response TEXT,
                    usage_count INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    tokens_used INTEGER,
                    cost REAL,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Initialize default schedules if not present
            self._init_default_schedules(cursor)

    def save_llm_sanitizer_audit(self, task_id: int, corrections: int, notes: str = None) -> int:
        """Save a sanitizer audit record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO llm_sanitizer_audit (task_id, corrections, notes) VALUES (?, ?, ?)",
                (task_id, corrections, notes),
            )
            return cursor.lastrowid

    def save_bot_audit(self, user: str, action: str, details: str = None) -> int:
        """Save an operator or bot action to the bot_audit table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO bot_audit (user, action, details) VALUES (?, ?, ?)",
                (user, action, details),
            )
            return cursor.lastrowid

    # ------------------------------------------------------------------
    # Discord message dedupe helpers
    # ------------------------------------------------------------------
    def record_discord_send(self, channel: str, fingerprint: str, payload_hash: str) -> int:
        """Record a discord message send for dedupe and auditing."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO discord_messages (channel, fingerprint, payload_hash, sent_at) VALUES (?, ?, ?, datetime('now'))",
                (channel, fingerprint, payload_hash),
            )
            return cur.lastrowid

    def was_discord_recent(self, channel: str, fingerprint: str, minutes: int = 30) -> bool:
        """Return True if same fingerprint was sent to `channel` within `minutes` minutes."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(1) as cnt FROM discord_messages WHERE channel = ? AND fingerprint = ? AND sent_at >= datetime('now', ?)",
                (channel, fingerprint, f"-{minutes} minutes"),
            )
            row = cur.fetchone()
            return int(row["cnt"] or 0) > 0

    # ------------------------------------------------------------------
    # Subscription helpers
    # ------------------------------------------------------------------
    def add_subscription(self, user_id: str, topic: str) -> int:
        """Subscribe a user to a topic. Returns the subscription id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO subscriptions (user_id, topic) VALUES (?, ?)",
                    (user_id, topic),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Already subscribed
                cursor.execute(
                    "SELECT id FROM subscriptions WHERE user_id = ? AND topic = ?", (user_id, topic)
                )
                row = cursor.fetchone()
                return row["id"] if row else 0

    def remove_subscription(self, user_id: str, topic: str) -> bool:
        """Remove a subscription for a user and topic."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ? AND topic = ?", (user_id, topic))
            return cursor.rowcount > 0

    def list_subscriptions(self, topic: str = None) -> list:
        """List subscriptions optionally filtered by topic."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if topic:
                cursor.execute("SELECT user_id, topic, created_at FROM subscriptions WHERE topic = ? ORDER BY created_at DESC", (topic,))
            else:
                cursor.execute("SELECT user_id, topic, created_at FROM subscriptions ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def get_user_subscriptions(self, user_id: str) -> list:
        """Return list of topics a user is subscribed to."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM subscriptions WHERE user_id = ?", (user_id,))
            return [r["topic"] for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Model usage helpers
    # ------------------------------------------------------------------
    def record_model_usage(self, model_path: str, name: str | None = None, size_gb: float | None = None) -> None:
        """Insert or update model usage metadata and set last_used timestamp."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO model_usage (model_path, name, size_gb, last_used, usage_count) VALUES (?, ?, ?, datetime('now'), 1) "
                "ON CONFLICT(model_path) DO UPDATE SET last_used = datetime('now'), usage_count = usage_count + 1, name = COALESCE(?, name), size_gb = COALESCE(?, size_gb)",
                (model_path, name, size_gb, name, size_gb),
            )

    def get_unused_models(self, days_threshold: int = 30, keep_list: list[str] | None = None, min_keep: int = 1) -> list:
        """Return list of model rows eligible for pruning.

        - days_threshold: models not used in the last N days are eligible
        - keep_list: names/paths to exclude from deletion
        - min_keep: keep at least this many models even if older than threshold
        """
        keep_list = keep_list or []
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT model_path, name, size_gb, last_used, usage_count FROM model_usage ORDER BY last_used DESC"
            )
            rows = [dict(r) for r in cur.fetchall()]

        # filter by keep_list
        filtered = []
        for r in rows:
            name = (r.get("name") or Path(r.get("model_path")).stem).lower()
            path = str(r.get("model_path") or "")
            if any(k.lower() in name or k.lower() in path for k in keep_list):
                continue
            filtered.append(r)

        # eligible where last_used is NULL or older than threshold
        from datetime import datetime, timezone

        cutoff = (datetime.now(timezone.utc) - datetime.timedelta(days=days_threshold)).isoformat()
        eligible = [r for r in reversed(filtered) if (r.get("last_used") is None or str(r.get("last_used")) < cutoff)]

        # Keep at least min_keep models (the most recently used ones) - remove from eligible if needed
        total_models = len(filtered)
        to_remove = eligible
        to_remove = to_remove[: max(0, total_models - min_keep)] if total_models > min_keep else []
        return to_remove
    def get_recent_sanitizer_total(self, hours: int = 1) -> int:
        """Return sum of sanitizer corrections in the last <hours> hours."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(corrections) as total FROM llm_sanitizer_audit WHERE created_at >= datetime('now', ?)", (f"-{hours} hours",))
            row = cursor.fetchone()
            return int(row["total"] or 0)

    def _init_default_schedules(self, cursor):
        """Initialize default task schedules."""
        default_schedules = [
            # Daily tasks
            ("journal_publish", "daily", "Publish daily journal to Notion"),
            ("notion_sync", "daily", "Sync all outputs to Notion (skips unchanged files)"),
            ("insights_extraction", "daily", "Extract insights from reports"),
            # Weekly tasks
            ("economic_calendar", "weekly", "Generate economic calendar"),
            ("institution_watchlist", "weekly", "Update institution watchlist"),
            ("task_execution", "weekly", "Execute pending research/data tasks"),
            ("weekly_report_publish", "weekly", "Publish weekly report to Notion"),
            # Monthly tasks
            ("monthly_report_publish", "monthly", "Publish monthly report to Notion"),
            # Yearly tasks
            ("yearly_report_publish", "yearly", "Publish yearly report to Notion"),
        ]

        for task_name, frequency, description in default_schedules:
            cursor.execute(
                """
                INSERT OR IGNORE INTO schedule_tracker (task_name, frequency, metadata)
                VALUES (?, ?, ?)
            """,
                (task_name, frequency, description),
            )

    # ==========================================
    # SCHEDULE TRACKING METHODS
    # ==========================================

    def should_run_task(self, task_name: str) -> bool:
        """
        Check if a scheduled task should run based on its frequency.
        Returns True if the task should run now.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT last_run, frequency, enabled
                FROM schedule_tracker
                WHERE task_name = ?
            """,
                (task_name,),
            )
            row = cursor.fetchone()

            if not row:
                return True  # Unknown task, allow it

            if not row["enabled"]:
                return False

            if not row["last_run"]:
                return True  # Never run before

            last_run = datetime.fromisoformat(row["last_run"])
            now = datetime.now()
            frequency = row["frequency"]

            if frequency == "daily":
                return last_run.date() < now.date()
            elif frequency == "weekly":
                days_since = (now - last_run).days
                return days_since >= 7
            elif frequency == "monthly":
                return (last_run.year, last_run.month) < (now.year, now.month)
            elif frequency == "yearly":
                return last_run.year < now.year
            elif frequency == "hourly":
                return (now - last_run).total_seconds() >= 3600
            else:
                return True  # Unknown frequency, allow

    def mark_task_run(self, task_name: str) -> bool:
        """Mark a scheduled task as having just run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE schedule_tracker
                SET last_run = ?
                WHERE task_name = ?
            """,
                (now, task_name),
            )

            if cursor.rowcount == 0:
                # Task doesn't exist, create it
                cursor.execute(
                    """
                    INSERT INTO schedule_tracker (task_name, last_run, frequency)
                    VALUES (?, ?, 'daily')
                """,
                    (task_name, now),
                )

            return True

    def get_schedule_status(self) -> List[Dict]:
        """Get status of all scheduled tasks."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_name, last_run, frequency, enabled, metadata
                FROM schedule_tracker
                ORDER BY task_name
            """)

            results = []
            now = datetime.now()
            for row in cursor.fetchall():
                task = dict(row)
                task["should_run"] = self.should_run_task(row["task_name"])
                if row["last_run"]:
                    last = datetime.fromisoformat(row["last_run"])
                    task["time_since_last"] = str(now - last)
                else:
                    task["time_since_last"] = "Never"
                results.append(task)

            return results

    # ==========================================
    # DOCUMENT LIFECYCLE METHODS
    # ==========================================

    def get_document_status(self, file_path: str) -> Optional[Dict]:
        """Get the lifecycle status of a document."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_path, doc_type, status, created_at, updated_at,
                       published_at, notion_page_id, content_hash, version
                FROM document_lifecycle
                WHERE file_path = ?
            """,
                (file_path,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def register_document(self, file_path: str, doc_type: str, status: str = "draft", content_hash: str = None) -> bool:
        """
        Register a new document in the lifecycle system.

        Uses UPSERT to prevent duplicate drafts - if document already exists,
        updates the content_hash and updated_at but preserves the original status
        (unless explicitly upgrading from draft to a higher status).
        """
        # Normalize path to prevent duplicates from relative vs absolute paths
        from pathlib import Path

        file_path = str(Path(file_path).resolve())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Check if document already exists
            cursor.execute("SELECT status, content_hash FROM document_lifecycle WHERE file_path = ?", (file_path,))
            existing = cursor.fetchone()

            if existing:
                existing_status = existing[0]
                existing_hash = existing[1]

                # Don't downgrade status (published -> draft)
                status_order = {"draft": 0, "in_progress": 1, "review": 2, "published": 3, "archived": 4}
                if status_order.get(status, 0) <= status_order.get(existing_status, 0):
                    status = existing_status  # Keep higher status

                # Only update if content changed or status upgraded
                if content_hash != existing_hash or status != existing_status:
                    cursor.execute(
                        """
                        UPDATE document_lifecycle
                        SET doc_type = ?, status = ?, content_hash = ?, updated_at = ?, version = version + 1
                        WHERE file_path = ?
                        """,
                        (doc_type, status, content_hash, now, file_path),
                    )
                return True
            else:
                # New document
                cursor.execute(
                    """
                    INSERT INTO document_lifecycle
                    (file_path, doc_type, status, content_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (file_path, doc_type, status, content_hash, now, now),
                )
                return True

    def update_document_status(self, file_path: str, status: str, notion_page_id: str = None) -> bool:
        """
        Update document lifecycle status.
        Status: 'draft' -> 'in_progress' -> 'published'
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # If transitioning to published, set published_at
            published_at = now if status == "published" else None

            cursor.execute(
                """
                UPDATE document_lifecycle
                SET status = ?,
                    updated_at = ?,
                    published_at = COALESCE(?, published_at),
                    notion_page_id = COALESCE(?, notion_page_id),
                    version = version + 1
                WHERE file_path = ?
            """,
                (status, now, published_at, notion_page_id, file_path),
            )
            return cursor.rowcount > 0

    def get_documents_by_status(self, status: str) -> List[Dict]:
        """Get all documents with a specific status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_path, doc_type, status, created_at, updated_at,
                       published_at, notion_page_id, version
                FROM document_lifecycle
                WHERE status = ?
                ORDER BY updated_at DESC
            """,
                (status,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_unpublished_documents(self) -> List[Dict]:
        """Get all documents that haven't been published to Notion."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, doc_type, status, created_at, updated_at, version
                FROM document_lifecycle
                WHERE status != 'published' OR notion_page_id IS NULL
                ORDER BY
                    CASE status
                        WHEN 'in_progress' THEN 1
                        WHEN 'draft' THEN 2
                        ELSE 3
                    END,
                    updated_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def is_document_safe_to_overwrite(self, file_path: str) -> bool:
        """
        Check if a document is safe to overwrite.
        Safe to overwrite if:
        - Not registered (new file)
        - Status is 'draft'
        - Never been published
        """
        doc = self.get_document_status(file_path)
        if doc is None:
            return True  # New file, safe to create
        if doc["status"] == "draft" and doc["published_at"] is None:
            return True  # Draft that was never published
        return False  # In progress or published, not safe

    def mark_document_for_update(self, file_path: str) -> bool:
        """Mark a published document as needing an update (creates new version)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE document_lifecycle
                SET status = 'in_progress',
                    updated_at = ?,
                    version = version + 1
                WHERE file_path = ?
            """,
                (now, file_path),
            )
            return cursor.rowcount > 0

    # ==========================================
    # NOTION SYNC TRACKING METHODS
    # ==========================================

    def get_file_hash(self, file_path: str) -> str:
        """Calculate a simple hash of file contents for change detection."""
        import hashlib

        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def is_file_synced(self, file_path: str) -> bool:
        """Check if a file has been synced to Notion and hasn't changed.

        If `file_hash` is provided, compare against the stored sync fingerprint
        (useful when publishing uses a computed strong fingerprint instead of raw
        file bytes). If not provided, fall back to the existing MD5-of-file check.
        """
        # Normalize path to absolute resolved form for consistent dedupe
        from pathlib import Path

        normalized_path = str(Path(file_path).resolve())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_hash FROM notion_sync WHERE file_path = ?
            """,
                (normalized_path,),
            )
            row = cursor.fetchone()

            if not row:
                return False

            stored_hash = row["file_hash"]

            # If caller provided an explicit fingerprint, compare that
            if hasattr(self, '_last_checked_hash') and self._last_checked_hash:
                return stored_hash == self._last_checked_hash

            # Otherwise fall back to file MD5
            current_hash = self.get_file_hash(normalized_path)
            return stored_hash == current_hash

    def record_notion_sync(self, file_path: str, page_id: str, url: str, doc_type: str = None, file_hash: str | None = None) -> bool:
        """Record that a file has been synced to Notion.

        If `file_hash` is provided it will be stored as the canonical fingerprint
        for deduplication. This allows the publisher to write a computed strong
        fingerprint (title + body + frontmatter) rather than a raw MD5 of the
        file bytes when content normalization is used.
        """
        # Normalize path to absolute resolved form for consistent dedupe
        from pathlib import Path

        normalized_path = str(Path(file_path).resolve())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if not file_hash:
                file_hash = self.get_file_hash(normalized_path)

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO notion_sync (file_path, file_hash, notion_page_id, notion_url, doc_type, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    notion_page_id = excluded.notion_page_id,
                    notion_url = excluded.notion_url,
                    doc_type = excluded.doc_type,
                    synced_at = excluded.synced_at
            """,
                (normalized_path, file_hash, page_id, url, doc_type, now),
            )

            # Also update document lifecycle table to mark this file as published
            try:
                cursor.execute(
                    """
                    UPDATE document_lifecycle
                    SET status = 'published',
                        notion_page_id = ?,
                        published_at = COALESCE(?, published_at),
                        updated_at = ?,
                        content_hash = COALESCE(?, content_hash)
                    WHERE file_path = ?
                """,
                    (page_id, now, now, file_hash, normalized_path),
                )
            except Exception:
                # If document_lifecycle isn't present or update fails, ignore silently
                pass

            return True

    def get_notion_page_for_file(self, file_path: str) -> Optional[Dict]:
        """Get Notion page info for a synced file."""
        # Normalize path to absolute resolved form for consistent lookup
        from pathlib import Path

        normalized_path = str(Path(file_path).resolve())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM notion_sync WHERE file_path = ?
            """,
                (normalized_path,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_synced_files(self) -> List[Dict]:
        """Get all files that have been synced to Notion."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notion_sync
                ORDER BY synced_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def clear_sync_for_file(self, file_path: str) -> bool:
        """Clear sync record for a file (forces re-sync)."""
        # Normalize path to absolute resolved form for consistent lookup
        from pathlib import Path

        normalized_path = str(Path(file_path).resolve())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notion_sync WHERE file_path = ?", (normalized_path,))
            return cursor.rowcount > 0

    def clear_all_sync_records(self) -> int:
        """Clear all sync records (forces full re-sync)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notion_sync")
            return cursor.rowcount

    # ==========================================
    # JOURNAL METHODS
    # ==========================================

    def has_journal_for_date(self, date_str: str) -> bool:
        """Check if a journal exists for given date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM journals WHERE date = ?", (date_str,))
            return cursor.fetchone() is not None

    def get_journal_last_update(self, date_str: str) -> Optional[str]:
        """Get the last update timestamp for a journal entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT updated_at FROM journals WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            return row["updated_at"] if row else None

    def save_journal(self, entry: JournalEntry, overwrite: bool = True) -> bool:
        """
        Save a journal entry. If overwrite=True, updates existing entry.
        Returns True if saved/updated, False if skipped.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if self.has_journal_for_date(entry.date) and not overwrite:
                return False

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO journals (date, content, bias, gold_price, silver_price, gsr, ai_enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    bias = excluded.bias,
                    gold_price = excluded.gold_price,
                    silver_price = excluded.silver_price,
                    gsr = excluded.gsr,
                    ai_enabled = excluded.ai_enabled,
                    updated_at = ?
            """,
                (
                    entry.date,
                    entry.content,
                    entry.bias,
                    entry.gold_price,
                    entry.silver_price,
                    entry.gsr,
                    entry.ai_enabled,
                    now,
                    now,
                    now,
                ),
            )

            return True

    def get_journal(self, date_str: str) -> Optional[JournalEntry]:
        """Get journal for specific date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM journals WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if row:
                return JournalEntry(
                    date=row["date"],
                    content=row["content"],
                    bias=row["bias"],
                    gold_price=row["gold_price"],
                    silver_price=row["silver_price"],
                    gsr=row["gsr"],
                    ai_enabled=bool(row["ai_enabled"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    def get_all_journals(self, limit: int = 100, offset: int = 0) -> List[JournalEntry]:
        """Get all journals ordered by date descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM journals
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            return [
                JournalEntry(
                    date=row["date"],
                    content=row["content"],
                    bias=row["bias"],
                    gold_price=row["gold_price"],
                    silver_price=row["silver_price"],
                    gsr=row["gsr"],
                    ai_enabled=bool(row["ai_enabled"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

    def get_latest_journal(self) -> Optional[Dict[str, Any]]:
        """Return the most recent journal as a dict for backward compatibility with the web UI.

        Returns a dict with keys: date, content, bias, gold_price, silver_price, gsr
        or None if no journal exists.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM journals ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    "date": row["date"],
                    "content": row["content"],
                    "bias": row["bias"],
                    "gold_price": row["gold_price"],
                    "silver_price": row["silver_price"],
                    "gsr": row.get("gsr") if isinstance(row, dict) else row["gsr"],
                }
            return None

    def get_journals_for_month(self, year: int, month: int) -> List[JournalEntry]:
        """Get all journals for a specific month."""
        month_prefix = f"{year:04d}-{month:02d}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM journals
                WHERE date LIKE ?
                ORDER BY date ASC
            """,
                (f"{month_prefix}%",),
            )

            return [
                JournalEntry(
                    date=row["date"],
                    content=row["content"],
                    bias=row["bias"],
                    gold_price=row["gold_price"],
                    silver_price=row["silver_price"],
                    gsr=row["gsr"],
                    ai_enabled=bool(row["ai_enabled"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

    def delete_journal(self, date_str: str) -> bool:
        """Delete a journal entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM journals WHERE date = ?", (date_str,))
            return cursor.rowcount > 0

    # ==========================================
    # REPORT METHODS (with redundancy control)
    # ==========================================

    def has_report(self, report_type: str, period: str) -> bool:
        """
        Check if a report exists for given type and period.

        Args:
            report_type: 'weekly', 'monthly', 'yearly'
            period: 'YYYY-WW' for weekly, 'YYYY-MM' for monthly, 'YYYY' for yearly
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM reports WHERE report_type = ? AND period = ?", (report_type, period))
            return cursor.fetchone() is not None

    def has_monthly_report(self, year: int, month: int) -> bool:
        """Check if monthly report exists for given month."""
        period = f"{year:04d}-{month:02d}"
        return self.has_report("monthly", period)

    def has_yearly_report(self, year: int) -> bool:
        """Check if yearly report exists for given year."""
        period = f"{year:04d}"
        return self.has_report("yearly", period)

    def has_weekly_report(self, year: int, week: int) -> bool:
        """Check if weekly report exists for given week."""
        period = f"{year:04d}-W{week:02d}"
        return self.has_report("weekly", period)

    def save_report(self, report: Report, overwrite: bool = False) -> bool:
        """
        Save a report. By default, won't overwrite existing reports.
        Returns True if saved, False if skipped (already exists).
        """
        if self.has_report(report.report_type, report.period) and not overwrite:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO reports (report_type, period, content, summary, ai_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_type, period) DO UPDATE SET
                    content = excluded.content,
                    summary = excluded.summary,
                    ai_enabled = excluded.ai_enabled
            """,
                (report.report_type, report.period, report.content, report.summary, report.ai_enabled, now),
            )

            return True

    def get_report(self, report_type: str, period: str) -> Optional[Report]:
        """Get a specific report."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE report_type = ? AND period = ?", (report_type, period))
            row = cursor.fetchone()
            if row:
                return Report(
                    report_type=row["report_type"],
                    period=row["period"],
                    content=row["content"],
                    summary=row["summary"],
                    ai_enabled=bool(row["ai_enabled"]),
                    created_at=row["created_at"],
                )
            return None

    def get_reports_by_type(self, report_type: str, limit: int = 50) -> List[Report]:
        """Get all reports of a specific type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM reports
                WHERE report_type = ?
                ORDER BY period DESC
                LIMIT ?
            """,
                (report_type, limit),
            )

            return [
                Report(
                    report_type=row["report_type"],
                    period=row["period"],
                    content=row["content"],
                    summary=row["summary"],
                    ai_enabled=bool(row["ai_enabled"]),
                    created_at=row["created_at"],
                )
                for row in cursor.fetchall()
            ]

    # ==========================================
    # LLM TASK QUEUE METHODS
    # ==========================================

    def add_llm_task(self, document_path: str, prompt: str, provider_hint: Optional[str] = None, priority: str = "normal", task_type: str = "generate") -> int:
        """Enqueue a new LLM task and return the new task id.

        task_type: 'generate'|'insights' etc - worker will decide behavior based on this.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO llm_tasks (document_path, prompt, provider_hint, priority, task_type)
                VALUES (?, ?, ?, ?, ?)
            """,
                (document_path, prompt, provider_hint, priority, task_type),
            )
            return cursor.lastrowid

    def claim_llm_tasks(self, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Atomically claim up to `limit` pending tasks and mark them as in_progress.
        Returns list of task rows as dicts.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM llm_tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
                (limit,),
            )
            ids = [row["id"] for row in cursor.fetchall()]
            if not ids:
                return []
            q = ",".join("?" for _ in ids)
            cursor.execute(
                f"UPDATE llm_tasks SET status = 'in_progress', started_at = CURRENT_TIMESTAMP WHERE id IN ({q})",
                ids,
            )
            cursor.execute(f"SELECT * FROM llm_tasks WHERE id IN ({q})", ids)
            rows = [dict(r) for r in cursor.fetchall()]
            return rows

    def update_llm_task_result(self, task_id: int, status: str, response: Optional[str] = None, error: Optional[str] = None, attempts: Optional[int] = None):
        """Update task status, response, error and attempts count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            params: List[Any] = []
            if response is not None:
                fields.append("response = ?")
                params.append(response)
            if error is not None:
                fields.append("error = ?")
                params.append(error)
            if attempts is not None:
                fields.append("attempts = ?")
                params.append(attempts)
            if status == "completed":
                fields.append("completed_at = CURRENT_TIMESTAMP")
            fields.append("status = ?")
            params.append(status)
            params.append(task_id)
            cursor.execute(f"UPDATE llm_tasks SET {', '.join(fields)} WHERE id = ?", params)

    def get_llm_queue_length(self) -> int:
        """Return number of tasks pending or in progress."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(1) as cnt FROM llm_tasks WHERE status IN ('pending','in_progress')")
            return cursor.fetchone()["cnt"]

    def get_llm_task(self, task_id: int) -> Optional[dict]:
        """Fetch a single llm task by id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM llm_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def approve_llm_task(self, task_id: int, approver: str) -> bool:
        """Mark a task as approved/published (requires sanitizer checks upstream)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE llm_tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
            cursor.execute("INSERT INTO bot_audit (user, action, details) VALUES (?, 'approve', ?)", (approver, f"task={task_id}"))
            return cursor.rowcount > 0

    # ==========================================
    # ANALYSIS SNAPSHOT METHODS
    # ==========================================

    def save_analysis_snapshot(self, snapshot: AnalysisSnapshot) -> bool:
        """Save an analysis snapshot for an asset."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO analysis_snapshots
                    (date, asset, price, rsi, sma_50, sma_200, atr, adx, trend, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date, asset) DO UPDATE SET
                        price = excluded.price,
                        rsi = excluded.rsi,
                        sma_50 = excluded.sma_50,
                        sma_200 = excluded.sma_200,
                        atr = excluded.atr,
                        adx = excluded.adx,
                        trend = excluded.trend,
                        raw_data = excluded.raw_data
                """,
                    (
                        snapshot.date,
                        snapshot.asset,
                        snapshot.price,
                        snapshot.rsi,
                        snapshot.sma_50,
                        snapshot.sma_200,
                        snapshot.atr,
                        snapshot.adx,
                        snapshot.trend,
                        snapshot.raw_data,
                    ),
                )
            except sqlite3.OperationalError as oe:
                if 'no such table' in str(oe).lower():
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS analysis_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT NOT NULL,
                            asset TEXT NOT NULL,
                            price REAL,
                            rsi REAL,
                            sma_50 REAL,
                            sma_200 REAL,
                            atr REAL,
                            adx REAL,
                            trend TEXT,
                            raw_data TEXT,
                            UNIQUE(date, asset)
                        )
                        """
                    )
                    cursor.execute(
                        """
                        INSERT INTO analysis_snapshots
                        (date, asset, price, rsi, sma_50, sma_200, atr, adx, trend, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date, asset) DO UPDATE SET
                            price = excluded.price,
                            rsi = excluded.rsi,
                            sma_50 = excluded.sma_50,
                            sma_200 = excluded.sma_200,
                            atr = excluded.atr,
                            adx = excluded.adx,
                            trend = excluded.trend,
                            raw_data = excluded.raw_data
                    """,
                        (
                            snapshot.date,
                            snapshot.asset,
                            snapshot.price,
                            snapshot.rsi,
                            snapshot.sma_50,
                            snapshot.sma_200,
                            snapshot.atr,
                            snapshot.adx,
                            snapshot.trend,
                            snapshot.raw_data,
                        ),
                    )
                else:
                    raise

            return True

    def get_analysis_history(self, asset: str, days: int = 30) -> List[AnalysisSnapshot]:
        """Get analysis history for an asset over last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM analysis_snapshots
                WHERE asset = ?
                ORDER BY date DESC
                LIMIT ?
            """,
                (asset, days),
            )

            return [
                AnalysisSnapshot(
                    date=row["date"],
                    asset=row["asset"],
                    price=row["price"],
                    rsi=row["rsi"],
                    sma_50=row["sma_50"],
                    sma_200=row["sma_200"],
                    atr=row["atr"],
                    adx=row["adx"],
                    trend=row["trend"],
                    raw_data=row["raw_data"],
                )
                for row in cursor.fetchall()
            ]

    def get_latest_price(self, asset: str) -> Optional[float]:
        """Return the latest recorded price for the given asset from analysis_snapshots.

        Returns None if no historic price is available.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT price FROM analysis_snapshots
                WHERE asset = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (asset,),
            )
            row = cursor.fetchone()
            if row:
                return row["price"]
            return None

    # ==========================================
    # PRE-MARKET PLANS
    # ==========================================

    def has_premarket_for_date(self, date_str: str) -> bool:
        """Check if pre-market plan exists for date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM premarket_plans WHERE date = ?", (date_str,))
            return cursor.fetchone() is not None

    def save_premarket_plan(
        self, date_str: str, content: str, bias: str = None, catalysts: str = None, ai_enabled: bool = True
    ) -> bool:
        """Save a pre-market plan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO premarket_plans (date, content, bias, catalysts, ai_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    bias = excluded.bias,
                    catalysts = excluded.catalysts,
                    ai_enabled = excluded.ai_enabled
            """,
                (date_str, content, bias, catalysts, ai_enabled, now),
            )

            return True

    def get_premarket_plan(self, date_str: str) -> Optional[Dict]:
        """Get pre-market plan for date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM premarket_plans WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_current_period_info(self) -> Dict[str, Any]:
        """
        Get info about current period and what reports exist.
        Useful for determining what needs to be generated.
        """
        today = date.today()
        iso_cal = today.isocalendar()

        return {
            "today": today.isoformat(),
            "year": today.year,
            "month": today.month,
            "week": iso_cal[1],
            "day_of_week": iso_cal[2],
            "month_period": f"{today.year:04d}-{today.month:02d}",
            "year_period": f"{today.year:04d}",
            "week_period": f"{today.year:04d}-W{iso_cal[1]:02d}",
            "has_today_journal": self.has_journal_for_date(today.isoformat()),
            "has_monthly_report": self.has_monthly_report(today.year, today.month),
            "has_yearly_report": self.has_yearly_report(today.year),
            "has_weekly_report": self.has_weekly_report(today.year, iso_cal[1]),
            "has_premarket_today": self.has_premarket_for_date(today.isoformat()),
        }

    def get_missing_reports(self) -> Dict[str, bool]:
        """
        Check which reports are missing for current period.
        Returns dict with report types and whether they're missing.
        """
        info = self.get_current_period_info()
        return {
            "daily_journal": not info["has_today_journal"],
            "weekly_report": not info["has_weekly_report"],
            "monthly_report": not info["has_monthly_report"],
            "yearly_report": not info["has_yearly_report"],
            "premarket_plan": not info["has_premarket_today"],
        }

    def get_journal_dates(self, start_date: str = "2025-12-01") -> List[str]:
        """Get all dates that have journal entries, starting from a date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT date FROM journals
                WHERE date >= ?
                ORDER BY date DESC
            """,
                (start_date,),
            )
            return [row["date"] for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM journals")
            journal_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'weekly'")
            weekly_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'monthly'")
            monthly_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'yearly'")
            yearly_count = cursor.fetchone()["count"]

            cursor.execute("SELECT MIN(date) as first, MAX(date) as last FROM journals")
            date_range = cursor.fetchone()

            return {
                "total_journals": journal_count,
                "weekly_reports": weekly_count,
                "monthly_reports": monthly_count,
                "yearly_reports": yearly_count,
                "first_journal": date_range["first"],
                "last_journal": date_range["last"],
            }

        def release_stale_claims(self, ttl_seconds: int = 900) -> int:
            """
            Release stale 'in_progress' document claims older than `ttl_seconds`.

            Returns the number of rows updated.
            """
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Compute threshold in UNIX epoch seconds
                try:
                    cursor.execute(
                        """
                        UPDATE document_lifecycle
                        SET status = 'draft',
                            updated_at = CURRENT_TIMESTAMP,
                            version = version + 1
                        WHERE status = 'in_progress'
                          AND (strftime('%s', 'now') - strftime('%s', updated_at)) > ?
                    """,
                        (ttl_seconds,),
                    )
                    return cursor.rowcount
                except Exception:
                    return 0

    # ==========================================
    # ENTITY INSIGHTS METHODS
    # ==========================================

    def save_entity_insight(
        self,
        entity_name: str,
        entity_type: str,
        context: str,
        relevance_score: float,
        source_report: str,
        metadata: str = None,
    ) -> bool:
        """Save an entity insight."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO entity_insights
                (entity_name, entity_type, context, relevance_score, source_report, extracted_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_name, source_report) DO UPDATE SET
                    context = excluded.context,
                    relevance_score = excluded.relevance_score,
                    metadata = excluded.metadata
            """,
                (entity_name, entity_type, context, relevance_score, source_report, now, metadata),
            )

            return True

    def get_entity_insights(self, entity_type: str = None, min_relevance: float = 0.0, limit: int = 100) -> List[Dict]:
        """Get entity insights with optional filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if entity_type:
                cursor.execute(
                    """
                    SELECT * FROM entity_insights
                    WHERE entity_type = ? AND relevance_score >= ?
                    ORDER BY relevance_score DESC, extracted_at DESC
                    LIMIT ?
                """,
                    (entity_type, min_relevance, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM entity_insights
                    WHERE relevance_score >= ?
                    ORDER BY relevance_score DESC, extracted_at DESC
                    LIMIT ?
                """,
                    (min_relevance, limit),
                )

            return [dict(row) for row in cursor.fetchall()]

    def get_top_entities(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get most frequently mentioned entities in recent period."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (date.today() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT entity_name, entity_type,
                       COUNT(*) as mention_count,
                       AVG(relevance_score) as avg_relevance
                FROM entity_insights
                WHERE extracted_at >= ?
                GROUP BY entity_name, entity_type
                ORDER BY mention_count DESC, avg_relevance DESC
                LIMIT ?
            """,
                (cutoff, limit),
            )

            return [dict(row) for row in cursor.fetchall()]

    def save_entity_insights(self, entities: list) -> int:
        """Save multiple entity insights (batch operation)."""
        saved = 0
        for entity in entities:
            try:
                # Support both dataclass and dict
                if hasattr(entity, "entity_name"):
                    self.save_entity_insight(
                        entity_name=entity.entity_name,
                        entity_type=entity.entity_type,
                        context=entity.context,
                        relevance_score=entity.relevance_score,
                        source_report=entity.source_report,
                        metadata=str(entity.metadata) if entity.metadata else None,
                    )
                else:
                    self.save_entity_insight(**entity)
                saved += 1
            except Exception:
                continue
        return saved

    # ==========================================
    # ACTION INSIGHTS METHODS
    # ==========================================

    def save_action_insights(self, actions: list) -> int:
        """Save multiple action insights (batch operation)."""
        saved = 0
        logger = logging.getLogger("DatabaseManager")
        for action in actions:
            try:
                # Support both dataclass and dict
                if hasattr(action, "action_id"):
                    self.save_action_insight(
                        action_id=action.action_id,
                        action_type=action.action_type,
                        title=action.title,
                        description=action.description,
                        priority=action.priority,
                        status=action.status,
                        source_report=action.source_report,
                        source_context=action.source_context,
                        deadline=action.deadline,
                        scheduled_for=getattr(action, "scheduled_for", None),
                        metadata=str(action.metadata) if action.metadata else None,
                    )
                else:
                    # Filter dict keys to only those accepted by save_action_insight to avoid
                    # TypeError when external dicts include extra fields.
                    allowed = {
                        "action_id",
                        "action_type",
                        "title",
                        "description",
                        "priority",
                        "status",
                        "source_report",
                        "source_context",
                        "deadline",
                        "scheduled_for",
                        "result",
                        "created_at",
                        "completed_at",
                        "retry_count",
                        "last_error",
                        "metadata",
                    }
                    filtered = {k: v for k, v in action.items() if k in allowed}
                    # Normalize metadata to string for DB binding
                    if filtered.get("metadata") is not None and not isinstance(filtered.get("metadata"), str):
                        filtered["metadata"] = str(filtered["metadata"])
                    self.save_action_insight(**filtered)
                saved += 1
            except Exception:  # pragma: no cover - defensive logging
                # Log the exception so callers can diagnose failures
                logger.exception("Failed to save action insight: %s", getattr(action, "action_id", action))
                continue

        return saved

    def save_action_insight(
        self,
        action_id: str,
        action_type: str,
        title: str,
        description: str = None,
        priority: str = "medium",
        status: str = "pending",
        result: str = None,
        created_at: str = None,
        completed_at: str = None,
        retry_count: int = 0,
        last_error: str = None,
        source_report: str = None,
        source_context: str = None,
        deadline: str = None,
        scheduled_for: str = None,
        metadata: str = None,
    ) -> bool:
        """
        Save an action insight.

        Args:
            scheduled_for: ISO timestamp when task should execute.
                          If None, task executes immediately.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            # Use provided created_at if present, otherwise use now
            created = created_at or now

            try:
                cursor.execute(
                    """
                    INSERT INTO action_insights
                    (action_id, action_type, title, description, priority, status,
                     source_report, source_context, deadline, scheduled_for, result, created_at, completed_at, retry_count, last_error, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(action_id) DO UPDATE SET
                        status = excluded.status,
                        description = excluded.description,
                        scheduled_for = excluded.scheduled_for,
                        result = excluded.result,
                        retry_count = excluded.retry_count,
                        last_error = excluded.last_error,
                        metadata = COALESCE(excluded.metadata, action_insights.metadata)
                """,
                    (
                        action_id,
                        action_type,
                        title,
                        description,
                        priority,
                        status,
                        source_report,
                        source_context,
                        deadline,
                        scheduled_for,
                        result,
                        created,
                        completed_at,
                        retry_count,
                        last_error,
                        metadata,
                    ),
                )
            except sqlite3.OperationalError as oe:
                # Defensive: ensure table exists in case initialization failed unexpectedly
                if 'no such table' in str(oe).lower():
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS action_insights (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            action_id TEXT UNIQUE NOT NULL,
                            action_type TEXT NOT NULL,
                            title TEXT NOT NULL,
                            description TEXT,
                            priority TEXT DEFAULT 'medium',
                            status TEXT DEFAULT 'pending',
                            source_report TEXT,
                            source_context TEXT,
                            deadline TEXT,
                            scheduled_for TEXT,
                            result TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            completed_at TEXT,
                            retry_count INTEGER DEFAULT 0,
                            last_error TEXT,
                            metadata TEXT
                        )
                        """
                    )
                    # Retry the insert
                    cursor.execute(
                        """
                        INSERT INTO action_insights
                        (action_id, action_type, title, description, priority, status,
                         source_report, source_context, deadline, scheduled_for, result, created_at, completed_at, retry_count, last_error, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(action_id) DO UPDATE SET
                            status = excluded.status,
                            description = excluded.description,
                            scheduled_for = excluded.scheduled_for,
                            result = excluded.result,
                            retry_count = excluded.retry_count,
                            last_error = excluded.last_error,
                            metadata = COALESCE(excluded.metadata, action_insights.metadata)
                    """,
                        (
                            action_id,
                            action_type,
                            title,
                            description,
                            priority,
                            status,
                            source_report,
                            source_context,
                            deadline,
                            scheduled_for,
                            result,
                            created,
                            completed_at,
                            retry_count,
                            last_error,
                            metadata,
                        ),
                    )
                else:
                    raise

            return True

    def get_pending_actions(self, priority: str = None, limit: int = None) -> List[Dict]:
        """
        Get pending action insights.

        Args:
            priority: Filter by priority level
            limit: Max number of actions to return (None = ALL pending actions)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            base_query = """
                SELECT * FROM action_insights
                WHERE status = 'pending'
            """
            order_by = """
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    created_at ASC
            """

            if priority and limit:
                cursor.execute(f"{base_query} AND priority = ? {order_by} LIMIT ?", (priority, limit))
            elif priority:
                cursor.execute(f"{base_query} AND priority = ? {order_by}", (priority,))
            elif limit:
                cursor.execute(f"{base_query} {order_by} LIMIT ?", (limit,))
            else:
                cursor.execute(f"{base_query} {order_by}")

            return [dict(row) for row in cursor.fetchall()]

    def get_ready_actions(self, limit: int = None) -> List[Dict]:
        """
        Get actions that are ready to execute NOW.

        Returns actions where:
        - status = 'pending' AND
        - (scheduled_for IS NULL OR scheduled_for <= now)

        Tasks without scheduled_for execute immediately.
        Tasks with scheduled_for execute when that time arrives.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            query = """
                SELECT * FROM action_insights
                WHERE status = 'pending'
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    scheduled_for ASC NULLS FIRST,
                    created_at ASC
            """

            if limit:
                cursor.execute(query + " LIMIT ?", (now, limit))
            else:
                cursor.execute(query, (now,))

            return [dict(row) for row in cursor.fetchall()]

    def get_scheduled_actions(self) -> List[Dict]:
        """
        Get actions that are scheduled for the future.
        Useful for displaying upcoming tasks.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                SELECT * FROM action_insights
                WHERE status = 'pending'
                  AND scheduled_for IS NOT NULL
                  AND scheduled_for > ?
                ORDER BY scheduled_for ASC
            """,
                (now,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def increment_retry_count(self, action_id: str, error_message: str = None) -> int:
        """
        Increment retry count for a failed action and record the error.
        Returns the new retry count.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE action_insights
                SET retry_count = COALESCE(retry_count, 0) + 1,
                    last_error = ?
                WHERE action_id = ?
            """,
                (error_message, action_id),
            )

            cursor.execute("SELECT retry_count FROM action_insights WHERE action_id = ?", (action_id,))
            row = cursor.fetchone()
            return row["retry_count"] if row else 0

    def reset_stuck_actions(self, max_age_hours: int = 24) -> int:
        """
        Reset actions that got stuck in 'in_progress' status.
        Called on daemon startup to recover from crashes.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()

            cursor.execute(
                """
                UPDATE action_insights
                SET status = 'pending'
                WHERE status = 'in_progress'
                  AND created_at < ?
            """,
                (cutoff,),
            )

            return cursor.rowcount

    def update_action_status(self, action_id: str, status: str, result: str = None) -> bool:
        """Update action insight status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                UPDATE action_insights
                SET status = ?, result = ?, completed_at = ?
                WHERE action_id = ?
            """,
                (status, result, now if status in ("completed", "failed") else None, action_id),
            )

            return cursor.rowcount > 0

    def get_action_stats(self) -> Dict[str, Any]:
        """Get action insights statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM action_insights
                GROUP BY status
            """)

            stats = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0, "skipped": 0}
            for row in cursor.fetchall():
                stats[row["status"]] = row["count"]

            stats["total"] = sum(stats.values())
            stats["completion_rate"] = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0

            return stats

    # ==========================================
    # TASK EXECUTION LOG METHODS
    # ==========================================

    def log_task_execution(
        self,
        action_id: str,
        success: bool,
        result_data: str = None,
        # Backwards-compat alias for older callers that used 'result' keyword
        result: str = None,
        execution_time_ms: float = 0,
        error_message: str = None,
        artifacts: str = None,
    ) -> bool:
        """Log task execution result."""
        # Support legacy callers that pass `result` kwarg
        final_result = result_data if result_data is not None else result

        # Retry transient I/O/DB errors (Errno 5 / sqlite3 OperationalError)
        import sqlite3
        import time

        retries = 0
        max_retries = 5
        backoff = 0.5

        while True:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO task_execution_log
                        (action_id, success, result_data, execution_time_ms, error_message, artifacts)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (action_id, 1 if success else 0, final_result, execution_time_ms, error_message, artifacts),
                    )
                return True
            except (OSError, IOError, sqlite3.OperationalError) as e:
                retries += 1
                # Increment prometheus retry counter if available
                try:
                    from syndicate.metrics import METRICS

                    METRICS["db_log_retries_total"].inc()
                except Exception:
                    pass
                if retries > max_retries:
                    # Final failure - increment error counter if present
                    try:
                        from syndicate.metrics import METRICS

                        METRICS["db_log_errors_total"].inc()
                    except Exception:
                        pass
                    logging.getLogger(__name__).error(f"Failed to log task execution after {max_retries} retries: {e}")
                    raise
                logging.getLogger(__name__).warning(
                    f"Transient DB error logging task (attempt {retries}/{max_retries}): {e}; retrying in {backoff}s"
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 5.0)

    def get_execution_history(self, action_id: str = None, days: int = 7) -> List[Dict]:
        """Get task execution history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            if action_id:
                cursor.execute(
                    """
                    SELECT * FROM task_execution_log
                    WHERE action_id = ? AND executed_at >= ?
                    ORDER BY executed_at DESC
                """,
                    (action_id, cutoff),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM task_execution_log
                    WHERE executed_at >= ?
                    ORDER BY executed_at DESC
                    LIMIT 100
                """,
                    (cutoff,),
                )

            return [dict(row) for row in cursor.fetchall()]

    # ==========================================
    # SYSTEM CONFIG METHODS
    # ==========================================

    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """Get a system configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    # ==========================================
    # CORTEX MEMORY METHODS
    # ==========================================

    def get_cortex_memory(self) -> Optional[Dict[str, Any]]:
        """Return the cortex memory as a Python dict if present, else None."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT memory_json FROM cortex_memory WHERE id = 1")
            row = cursor.fetchone()
            if not row or not row["memory_json"]:
                return None
            try:
                return json.loads(row["memory_json"])
            except Exception:
                return None

    def set_cortex_memory(self, memory: Dict[str, Any]) -> bool:
        """Persist cortex memory dict into the cortex_memory table (atomic)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            mem_json = json.dumps(memory)
            # Upsert into single-row table
            cursor.execute(
                "INSERT INTO cortex_memory (id, memory_json, updated_at) VALUES (1, ?, CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET memory_json = excluded.memory_json, updated_at = excluded.updated_at",
                (mem_json,),
            )
            return True

    # ==========================================
    # LLM CACHE & USAGE
    # ==========================================

    def get_llm_cache(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Return cached LLM response by prompt_hash if present."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT prompt, response, usage_count, last_used FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "prompt": row["prompt"],
                "response": row["response"],
                "usage_count": row["usage_count"],
                "last_used": row["last_used"],
            }

    def set_llm_cache(self, prompt_hash: str, prompt: str, response: str) -> bool:
        """Insert or update LLM cache entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO llm_cache (prompt_hash, prompt, response, usage_count, created_at, last_used)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(prompt_hash) DO UPDATE SET
                    response = excluded.response,
                    usage_count = llm_cache.usage_count + 1,
                    last_used = excluded.last_used
                """,
                (prompt_hash, prompt, response, now, now),
            )
            return True

    def log_llm_usage(self, provider: str, tokens_used: int, cost: float = 0.0) -> bool:
        """Record LLM usage metrics for billing and rate tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO llm_usage (provider, tokens_used, cost, recorded_at) VALUES (?, ?, ?, ?)",
                (provider, tokens_used, cost, datetime.now().isoformat()),
            )
            return True

    def set_config(self, key: str, value: str, description: str = None) -> bool:
        """Set a system configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    description = COALESCE(excluded.description, system_config.description),
                    updated_at = excluded.updated_at
            """,
                (key, value, description, now),
            )

            return True

    def get_all_config(self) -> Dict[str, str]:
        """Get all system configuration values."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_config")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    # ==========================================
    # FEATURE TOGGLES
    # ==========================================

    def is_notion_publishing_enabled(self) -> bool:
        """Check if Notion publishing is enabled (default: True)."""
        value = self.get_config("notion_publishing_enabled", "true")
        return value.lower() in ("true", "1", "yes", "on")

    def set_notion_publishing_enabled(self, enabled: bool) -> bool:
        """Enable or disable Notion publishing without changing other config."""
        return self.set_config(
            "notion_publishing_enabled",
            "true" if enabled else "false",
            "Toggle to temporarily disable Notion publishing",
        )

    def is_task_execution_enabled(self) -> bool:
        """Check if task execution is enabled (default: True)."""
        value = self.get_config("task_execution_enabled", "true")
        return value.lower() in ("true", "1", "yes", "on")

    def set_task_execution_enabled(self, enabled: bool) -> bool:
        """Enable or disable task execution without changing other config."""
        return self.set_config(
            "task_execution_enabled",
            "true" if enabled else "false",
            "Toggle to temporarily disable task execution",
        )

    def is_insights_extraction_enabled(self) -> bool:
        """Check if insights extraction is enabled (default: True)."""
        value = self.get_config("insights_extraction_enabled", "true")
        return value.lower() in ("true", "1", "yes", "on")

    def set_insights_extraction_enabled(self, enabled: bool) -> bool:
        """Enable or disable insights extraction without changing other config."""
        return self.set_config(
            "insights_extraction_enabled",
            "true" if enabled else "false",
            "Toggle to temporarily disable insights extraction",
        )

    # ==========================================
    # EXECUTION STATE MACHINE
    # ==========================================
    #
    # Task State Transitions:
    #   pending -> in_progress (claim_action)
    #   in_progress -> completed (mark_complete)
    #   in_progress -> pending (release_action, retry)
    #   in_progress -> failed (max retries exceeded)
    #
    # Scheduling States:
    #   scheduled_for IS NULL -> execute immediately
    #   scheduled_for <= NOW -> execute immediately
    #   scheduled_for > NOW -> wait until scheduled time
    #
    # ==========================================

    def claim_action(self, action_id: str, worker_id: str = None) -> bool:
        """
        Atomically claim an action for execution.

        Uses optimistic locking pattern:
        - Only claims if action is still 'pending'
        - Records claim timestamp and worker ID
        - Prevents duplicate execution across processes

        Args:
            action_id: The action to claim
            worker_id: Optional worker identifier for debugging

        Returns:
            True if claim succeeded, False if action was already claimed
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            worker = worker_id or f"worker_{now}"

            # Atomic claim: only succeeds if status is still 'pending'
            cursor.execute(
                """
                UPDATE action_insights
                SET status = 'in_progress',
                    metadata = json_set(
                        COALESCE(metadata, '{}'),
                        '$.claimed_at', ?,
                        '$.claimed_by', ?
                    )
                WHERE action_id = ?
                  AND status = 'pending'
            """,
                (now, worker, action_id),
            )

            return cursor.rowcount > 0

    def release_action(self, action_id: str, reason: str = "released", delay_seconds: int = 0) -> bool:
        """
        Release a claimed action back to pending state.

        Used when:
        - Worker crashes and needs to release claims
        - Task needs to be rescheduled for later
        - Voluntary release before completion

        Args:
            action_id: The action to release
            reason: Why the action was released

        Returns:
            True if release succeeded
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            if delay_seconds and isinstance(delay_seconds, int) and delay_seconds > 0:
                scheduled_for = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()
                cursor.execute(
                    """
                    UPDATE action_insights
                    SET status = 'pending',
                        scheduled_for = ?,
                        metadata = json_set(
                            COALESCE(metadata, '{}'),
                            '$.released_at', ?,
                            '$.release_reason', ?
                        )
                    WHERE action_id = ?
                      AND status = 'in_progress'
                """,
                    (scheduled_for, now, reason, action_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE action_insights
                    SET status = 'pending',
                        metadata = json_set(
                            COALESCE(metadata, '{}'),
                            '$.released_at', ?,
                            '$.release_reason', ?
                        )
                    WHERE action_id = ?
                      AND status = 'in_progress'
                """,
                    (now, reason, action_id),
                )

            return cursor.rowcount > 0

    def get_execution_context(self, action_id: str) -> Optional[Dict]:
        """
        Get full execution context for an action.

        Returns comprehensive state info for debugging and monitoring:
        - Current status and timestamps
        - Retry history
        - Scheduling information
        - Execution metadata
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now()

            cursor.execute(
                """
                SELECT
                    a.*,
                    (SELECT COUNT(*) FROM task_execution_log WHERE action_id = a.action_id) as execution_attempts,
                    (SELECT MAX(executed_at) FROM task_execution_log WHERE action_id = a.action_id) as last_execution
                FROM action_insights a
                WHERE a.action_id = ?
            """,
                (action_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            context = dict(row)

            # Add computed fields
            scheduled_for = context.get("scheduled_for")
            if scheduled_for:
                scheduled_dt = datetime.fromisoformat(scheduled_for)
                context["is_ready"] = scheduled_dt <= now
                context["time_until_ready"] = max(0, (scheduled_dt - now).total_seconds())
            else:
                context["is_ready"] = True
                context["time_until_ready"] = 0

            context["can_retry"] = (context.get("retry_count", 0) or 0) < 10

            return context

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health metrics.

        Returns real-time statistics for monitoring:
        - Task queue depth and distribution
        - Execution rates and failures
        - Scheduling status
        - Resource utilization indicators
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            health = {
                "timestamp": now,
                "tasks": {},
                "schedules": {},
                "execution": {},
            }

            # Task queue metrics
            cursor.execute(
                """
                SELECT
                    status,
                    priority,
                    COUNT(*) as count,
                    SUM(CASE WHEN scheduled_for IS NULL OR scheduled_for <= ? THEN 1 ELSE 0 END) as ready_count
                FROM action_insights
                GROUP BY status, priority
            """,
                (now,),
            )

            task_stats = {}
            for row in cursor.fetchall():
                key = f"{row['status']}_{row['priority']}"
                task_stats[key] = {"count": row["count"], "ready": row["ready_count"]}
            health["tasks"] = task_stats

            # Ready to execute
            cursor.execute(
                """
                SELECT COUNT(*) as ready_now
                FROM action_insights
                WHERE status = 'pending'
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
            """,
                (now,),
            )
            health["tasks"]["ready_now"] = cursor.fetchone()["ready_now"]

            # Scheduled for future
            cursor.execute(
                """
                SELECT COUNT(*) as scheduled_future
                FROM action_insights
                WHERE status = 'pending'
                  AND scheduled_for > ?
            """,
                (now,),
            )
            health["tasks"]["scheduled_future"] = cursor.fetchone()["scheduled_future"]

            # Stuck in progress (> 1 hour)
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) as stuck
                FROM action_insights
                WHERE status = 'in_progress'
                  AND created_at < ?
            """,
                (one_hour_ago,),
            )
            health["tasks"]["stuck_in_progress"] = cursor.fetchone()["stuck"]

            # Recent execution stats (last 24h)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successful,
                    AVG(execution_time_ms) as avg_time_ms
                FROM task_execution_log
                WHERE executed_at >= ?
            """,
                (yesterday,),
            )
            row = cursor.fetchone()
            health["execution"] = {
                "last_24h_total": row["total"] or 0,
                "last_24h_success": row["successful"] or 0,
                "last_24h_avg_time_ms": round(row["avg_time_ms"] or 0, 2),
            }

            # Schedule status
            cursor.execute("""
                SELECT task_name, last_run, frequency, enabled
                FROM schedule_tracker
                ORDER BY task_name
            """)
            health["schedules"] = [dict(row) for row in cursor.fetchall()]

            return health


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get the singleton database manager instance.

    If the environment variable `GOLD_STANDARD_TEST_DB` (or `GOLD_STANDARD_DB`) is set and
    differs from the currently-opened DB, a new DatabaseManager instance will be created.
    This allows per-test DB isolation without rebooting the process.
    """
    global _db_manager

    env_db = os.getenv("GOLD_STANDARD_TEST_DB") or os.getenv("GOLD_STANDARD_DB")
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path=Path(env_db) if env_db else None)
        return _db_manager

    # If env override present and different from current, recreate the manager
    if env_db and str(_db_manager.db_path) != str(Path(env_db)):
        _db_manager = DatabaseManager(db_path=Path(env_db))
    return _db_manager


if __name__ == "__main__":
    # Test the database manager
    db = get_db()
    print("Database initialized at:", db.db_path)
    print("\nCurrent period info:")
    info = db.get_current_period_info()
    for k, v in info.items():
        print(f"  {k}: {v}")
    print("\nMissing reports:")
    missing = db.get_missing_reports()
    for k, v in missing.items():
        print(f"  {k}: {'MISSING' if v else 'EXISTS'}")
