#!/usr/bin/env python3
"""
Gold Standard Database Manager
SQLite-based storage for reports, journals, analysis data, and insights.
Provides intelligent redundancy control, date-wise organization, and task management.
"""
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict


# Database path
DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "gold_standard.db"


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
    Manages SQLite database for Gold Standard system.
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
                    result TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
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
            
            # Initialize default schedules if not present
            self._init_default_schedules(cursor)
    
    def _init_default_schedules(self, cursor):
        """Initialize default task schedules."""
        default_schedules = [
            # Daily tasks
            ('journal_publish', 'daily', 'Publish daily journal to Notion'),
            ('notion_sync', 'daily', 'Sync all outputs to Notion (skips unchanged files)'),
            ('insights_extraction', 'daily', 'Extract insights from reports'),
            
            # Weekly tasks
            ('economic_calendar', 'weekly', 'Generate economic calendar'),
            ('institution_watchlist', 'weekly', 'Update institution watchlist'),
            ('task_execution', 'weekly', 'Execute pending research/data tasks'),
            ('weekly_report_publish', 'weekly', 'Publish weekly report to Notion'),
            
            # Monthly tasks
            ('monthly_report_publish', 'monthly', 'Publish monthly report to Notion'),
            
            # Yearly tasks
            ('yearly_report_publish', 'yearly', 'Publish yearly report to Notion'),
        ]
        
        for task_name, frequency, description in default_schedules:
            cursor.execute("""
                INSERT OR IGNORE INTO schedule_tracker (task_name, frequency, metadata)
                VALUES (?, ?, ?)
            """, (task_name, frequency, description))
    
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
            cursor.execute("""
                SELECT last_run, frequency, enabled 
                FROM schedule_tracker 
                WHERE task_name = ?
            """, (task_name,))
            row = cursor.fetchone()
            
            if not row:
                return True  # Unknown task, allow it
            
            if not row['enabled']:
                return False
            
            if not row['last_run']:
                return True  # Never run before
            
            last_run = datetime.fromisoformat(row['last_run'])
            now = datetime.now()
            frequency = row['frequency']
            
            if frequency == 'daily':
                return last_run.date() < now.date()
            elif frequency == 'weekly':
                days_since = (now - last_run).days
                return days_since >= 7
            elif frequency == 'monthly':
                return (last_run.year, last_run.month) < (now.year, now.month)
            elif frequency == 'yearly':
                return last_run.year < now.year
            elif frequency == 'hourly':
                return (now - last_run).total_seconds() >= 3600
            else:
                return True  # Unknown frequency, allow
    
    def mark_task_run(self, task_name: str) -> bool:
        """Mark a scheduled task as having just run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE schedule_tracker 
                SET last_run = ?
                WHERE task_name = ?
            """, (now, task_name))
            
            if cursor.rowcount == 0:
                # Task doesn't exist, create it
                cursor.execute("""
                    INSERT INTO schedule_tracker (task_name, last_run, frequency)
                    VALUES (?, ?, 'daily')
                """, (task_name, now))
            
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
                task['should_run'] = self.should_run_task(row['task_name'])
                if row['last_run']:
                    last = datetime.fromisoformat(row['last_run'])
                    task['time_since_last'] = str(now - last)
                else:
                    task['time_since_last'] = 'Never'
                results.append(task)
            
            return results
    
    # ==========================================
    # NOTION SYNC TRACKING METHODS
    # ==========================================
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate a simple hash of file contents for change detection."""
        import hashlib
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ''
    
    def is_file_synced(self, file_path: str) -> bool:
        """Check if a file has been synced to Notion and hasn't changed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_hash FROM notion_sync WHERE file_path = ?
            """, (file_path,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            # Check if file has changed
            current_hash = self.get_file_hash(file_path)
            return row['file_hash'] == current_hash
    
    def record_notion_sync(self, file_path: str, page_id: str, 
                          url: str, doc_type: str = None) -> bool:
        """Record that a file has been synced to Notion."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            file_hash = self.get_file_hash(file_path)
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO notion_sync (file_path, file_hash, notion_page_id, notion_url, doc_type, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    notion_page_id = excluded.notion_page_id,
                    notion_url = excluded.notion_url,
                    doc_type = excluded.doc_type,
                    synced_at = excluded.synced_at
            """, (file_path, file_hash, page_id, url, doc_type, now))
            
            return True
    
    def get_notion_page_for_file(self, file_path: str) -> Optional[Dict]:
        """Get Notion page info for a synced file."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notion_sync WHERE file_path = ?
            """, (file_path,))
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notion_sync WHERE file_path = ?", (file_path,))
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
            
            cursor.execute("""
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
            """, (entry.date, entry.content, entry.bias, entry.gold_price, 
                  entry.silver_price, entry.gsr, entry.ai_enabled, now, now, now))
            
            return True
    
    def get_journal(self, date_str: str) -> Optional[JournalEntry]:
        """Get journal for specific date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM journals WHERE date = ?", (date_str,))
            row = cursor.fetchone()
            if row:
                return JournalEntry(
                    date=row['date'],
                    content=row['content'],
                    bias=row['bias'],
                    gold_price=row['gold_price'],
                    silver_price=row['silver_price'],
                    gsr=row['gsr'],
                    ai_enabled=bool(row['ai_enabled']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None
    
    def get_all_journals(self, limit: int = 100, offset: int = 0) -> List[JournalEntry]:
        """Get all journals ordered by date descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM journals 
                ORDER BY date DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [
                JournalEntry(
                    date=row['date'],
                    content=row['content'],
                    bias=row['bias'],
                    gold_price=row['gold_price'],
                    silver_price=row['silver_price'],
                    gsr=row['gsr'],
                    ai_enabled=bool(row['ai_enabled']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                for row in cursor.fetchall()
            ]
    
    def get_journals_for_month(self, year: int, month: int) -> List[JournalEntry]:
        """Get all journals for a specific month."""
        month_prefix = f"{year:04d}-{month:02d}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM journals 
                WHERE date LIKE ?
                ORDER BY date ASC
            """, (f"{month_prefix}%",))
            
            return [
                JournalEntry(
                    date=row['date'],
                    content=row['content'],
                    bias=row['bias'],
                    gold_price=row['gold_price'],
                    silver_price=row['silver_price'],
                    gsr=row['gsr'],
                    ai_enabled=bool(row['ai_enabled']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
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
            cursor.execute(
                "SELECT 1 FROM reports WHERE report_type = ? AND period = ?",
                (report_type, period)
            )
            return cursor.fetchone() is not None
    
    def has_monthly_report(self, year: int, month: int) -> bool:
        """Check if monthly report exists for given month."""
        period = f"{year:04d}-{month:02d}"
        return self.has_report('monthly', period)
    
    def has_yearly_report(self, year: int) -> bool:
        """Check if yearly report exists for given year."""
        period = f"{year:04d}"
        return self.has_report('yearly', period)
    
    def has_weekly_report(self, year: int, week: int) -> bool:
        """Check if weekly report exists for given week."""
        period = f"{year:04d}-W{week:02d}"
        return self.has_report('weekly', period)
    
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
            
            cursor.execute("""
                INSERT INTO reports (report_type, period, content, summary, ai_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_type, period) DO UPDATE SET
                    content = excluded.content,
                    summary = excluded.summary,
                    ai_enabled = excluded.ai_enabled
            """, (report.report_type, report.period, report.content, 
                  report.summary, report.ai_enabled, now))
            
            return True
    
    def get_report(self, report_type: str, period: str) -> Optional[Report]:
        """Get a specific report."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM reports WHERE report_type = ? AND period = ?",
                (report_type, period)
            )
            row = cursor.fetchone()
            if row:
                return Report(
                    report_type=row['report_type'],
                    period=row['period'],
                    content=row['content'],
                    summary=row['summary'],
                    ai_enabled=bool(row['ai_enabled']),
                    created_at=row['created_at']
                )
            return None
    
    def get_reports_by_type(self, report_type: str, limit: int = 50) -> List[Report]:
        """Get all reports of a specific type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reports 
                WHERE report_type = ?
                ORDER BY period DESC
                LIMIT ?
            """, (report_type, limit))
            
            return [
                Report(
                    report_type=row['report_type'],
                    period=row['period'],
                    content=row['content'],
                    summary=row['summary'],
                    ai_enabled=bool(row['ai_enabled']),
                    created_at=row['created_at']
                )
                for row in cursor.fetchall()
            ]
    
    # ==========================================
    # ANALYSIS SNAPSHOT METHODS
    # ==========================================
    
    def save_analysis_snapshot(self, snapshot: AnalysisSnapshot) -> bool:
        """Save an analysis snapshot for an asset."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
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
            """, (snapshot.date, snapshot.asset, snapshot.price, snapshot.rsi,
                  snapshot.sma_50, snapshot.sma_200, snapshot.atr, snapshot.adx,
                  snapshot.trend, snapshot.raw_data))
            
            return True
    
    def get_analysis_history(self, asset: str, days: int = 30) -> List[AnalysisSnapshot]:
        """Get analysis history for an asset over last N days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_snapshots 
                WHERE asset = ?
                ORDER BY date DESC
                LIMIT ?
            """, (asset, days))
            
            return [
                AnalysisSnapshot(
                    date=row['date'],
                    asset=row['asset'],
                    price=row['price'],
                    rsi=row['rsi'],
                    sma_50=row['sma_50'],
                    sma_200=row['sma_200'],
                    atr=row['atr'],
                    adx=row['adx'],
                    trend=row['trend'],
                    raw_data=row['raw_data']
                )
                for row in cursor.fetchall()
            ]
    
    # ==========================================
    # PRE-MARKET PLANS
    # ==========================================
    
    def has_premarket_for_date(self, date_str: str) -> bool:
        """Check if pre-market plan exists for date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM premarket_plans WHERE date = ?", (date_str,))
            return cursor.fetchone() is not None
    
    def save_premarket_plan(self, date_str: str, content: str, 
                           bias: str = None, catalysts: str = None,
                           ai_enabled: bool = True) -> bool:
        """Save a pre-market plan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO premarket_plans (date, content, bias, catalysts, ai_enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    bias = excluded.bias,
                    catalysts = excluded.catalysts,
                    ai_enabled = excluded.ai_enabled
            """, (date_str, content, bias, catalysts, ai_enabled, now))
            
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
            'today': today.isoformat(),
            'year': today.year,
            'month': today.month,
            'week': iso_cal[1],
            'day_of_week': iso_cal[2],
            'month_period': f"{today.year:04d}-{today.month:02d}",
            'year_period': f"{today.year:04d}",
            'week_period': f"{today.year:04d}-W{iso_cal[1]:02d}",
            'has_today_journal': self.has_journal_for_date(today.isoformat()),
            'has_monthly_report': self.has_monthly_report(today.year, today.month),
            'has_yearly_report': self.has_yearly_report(today.year),
            'has_weekly_report': self.has_weekly_report(today.year, iso_cal[1]),
            'has_premarket_today': self.has_premarket_for_date(today.isoformat()),
        }
    
    def get_missing_reports(self) -> Dict[str, bool]:
        """
        Check which reports are missing for current period.
        Returns dict with report types and whether they're missing.
        """
        info = self.get_current_period_info()
        return {
            'daily_journal': not info['has_today_journal'],
            'weekly_report': not info['has_weekly_report'],
            'monthly_report': not info['has_monthly_report'],
            'yearly_report': not info['has_yearly_report'],
            'premarket_plan': not info['has_premarket_today'],
        }
    
    def get_journal_dates(self, start_date: str = "2025-12-01") -> List[str]:
        """Get all dates that have journal entries, starting from a date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date FROM journals 
                WHERE date >= ?
                ORDER BY date DESC
            """, (start_date,))
            return [row['date'] for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM journals")
            journal_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'weekly'")
            weekly_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'monthly'")
            monthly_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM reports WHERE report_type = 'yearly'")
            yearly_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT MIN(date) as first, MAX(date) as last FROM journals")
            date_range = cursor.fetchone()
            
            return {
                'total_journals': journal_count,
                'weekly_reports': weekly_count,
                'monthly_reports': monthly_count,
                'yearly_reports': yearly_count,
                'first_journal': date_range['first'],
                'last_journal': date_range['last'],
            }
    
    # ==========================================
    # ENTITY INSIGHTS METHODS
    # ==========================================
    
    def save_entity_insight(self, entity_name: str, entity_type: str,
                           context: str, relevance_score: float,
                           source_report: str, metadata: str = None) -> bool:
        """Save an entity insight."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO entity_insights 
                (entity_name, entity_type, context, relevance_score, source_report, extracted_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_name, source_report) DO UPDATE SET
                    context = excluded.context,
                    relevance_score = excluded.relevance_score,
                    metadata = excluded.metadata
            """, (entity_name, entity_type, context, relevance_score, source_report, now, metadata))
            
            return True
    
    def get_entity_insights(self, entity_type: str = None, 
                           min_relevance: float = 0.0,
                           limit: int = 100) -> List[Dict]:
        """Get entity insights with optional filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if entity_type:
                cursor.execute("""
                    SELECT * FROM entity_insights 
                    WHERE entity_type = ? AND relevance_score >= ?
                    ORDER BY relevance_score DESC, extracted_at DESC
                    LIMIT ?
                """, (entity_type, min_relevance, limit))
            else:
                cursor.execute("""
                    SELECT * FROM entity_insights 
                    WHERE relevance_score >= ?
                    ORDER BY relevance_score DESC, extracted_at DESC
                    LIMIT ?
                """, (min_relevance, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_top_entities(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get most frequently mentioned entities in recent period."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT entity_name, entity_type, 
                       COUNT(*) as mention_count,
                       AVG(relevance_score) as avg_relevance
                FROM entity_insights 
                WHERE extracted_at >= ?
                GROUP BY entity_name, entity_type
                ORDER BY mention_count DESC, avg_relevance DESC
                LIMIT ?
            """, (cutoff, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_entity_insights(self, entities: list) -> int:
        """Save multiple entity insights (batch operation)."""
        saved = 0
        for entity in entities:
            try:
                # Support both dataclass and dict
                if hasattr(entity, 'entity_name'):
                    self.save_entity_insight(
                        entity_name=entity.entity_name,
                        entity_type=entity.entity_type,
                        context=entity.context,
                        relevance_score=entity.relevance_score,
                        source_report=entity.source_report,
                        metadata=str(entity.metadata) if entity.metadata else None
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
        for action in actions:
            try:
                # Support both dataclass and dict
                if hasattr(action, 'action_id'):
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
                        metadata=str(action.metadata) if action.metadata else None
                    )
                else:
                    self.save_action_insight(**action)
                saved += 1
            except Exception:
                continue
        return saved
    
    def save_action_insight(self, action_id: str, action_type: str,
                           title: str, description: str = None,
                           priority: str = 'medium', status: str = 'pending',
                           source_report: str = None, source_context: str = None,
                           deadline: str = None, metadata: str = None) -> bool:
        """Save an action insight."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO action_insights 
                (action_id, action_type, title, description, priority, status,
                 source_report, source_context, deadline, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    status = excluded.status,
                    description = excluded.description
            """, (action_id, action_type, title, description, priority, status,
                  source_report, source_context, deadline, now, metadata))
            
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
    
    def update_action_status(self, action_id: str, status: str, 
                            result: str = None) -> bool:
        """Update action insight status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE action_insights 
                SET status = ?, result = ?, completed_at = ?
                WHERE action_id = ?
            """, (status, result, now if status in ('completed', 'failed') else None, action_id))
            
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
            
            stats = {'pending': 0, 'in_progress': 0, 'completed': 0, 'failed': 0, 'skipped': 0}
            for row in cursor.fetchall():
                stats[row['status']] = row['count']
            
            stats['total'] = sum(stats.values())
            stats['completion_rate'] = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            return stats
    
    # ==========================================
    # TASK EXECUTION LOG METHODS
    # ==========================================
    
    def log_task_execution(self, action_id: str, success: bool,
                          result_data: str = None, execution_time_ms: float = 0,
                          error_message: str = None, artifacts: str = None) -> bool:
        """Log task execution result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO task_execution_log 
                (action_id, success, result_data, execution_time_ms, error_message, artifacts)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (action_id, 1 if success else 0, result_data, execution_time_ms, error_message, artifacts))
            
            return True
    
    def get_execution_history(self, action_id: str = None, 
                             days: int = 7) -> List[Dict]:
        """Get task execution history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            if action_id:
                cursor.execute("""
                    SELECT * FROM task_execution_log 
                    WHERE action_id = ? AND executed_at >= ?
                    ORDER BY executed_at DESC
                """, (action_id, cutoff))
            else:
                cursor.execute("""
                    SELECT * FROM task_execution_log 
                    WHERE executed_at >= ?
                    ORDER BY executed_at DESC
                    LIMIT 100
                """, (cutoff,))
            
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
            return row['value'] if row else default
    
    def set_config(self, key: str, value: str, description: str = None) -> bool:
        """Set a system configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    description = COALESCE(excluded.description, system_config.description),
                    updated_at = excluded.updated_at
            """, (key, value, description, now))
            
            return True
    
    def get_all_config(self) -> Dict[str, str]:
        """Get all system configuration values."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM system_config")
            return {row['key']: row['value'] for row in cursor.fetchall()}


# Singleton instance
_db_manager: Optional[DatabaseManager] = None

def get_db() -> DatabaseManager:
    """Get the singleton database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


if __name__ == '__main__':
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
