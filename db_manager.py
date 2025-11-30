#!/usr/bin/env python3
"""
Gold Standard Database Manager
SQLite-based storage for reports, journals, and analysis data.
Provides intelligent redundancy control and date-wise organization.
"""
import os
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import hashlib


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
            
            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_journals_date ON journals(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_type_period ON reports(report_type, period)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_date_asset ON analysis_snapshots(date, asset)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
    
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
