#!/usr/bin/env python3
"""
Gold Standard GUI v2
Modern dashboard with database integration and date-wise journal browsing.
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from datetime import date, datetime, timedelta
import webbrowser
import json
import calendar

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"
MEMORY_FILE = PROJECT_ROOT / "cortex_memory.json"
DATA_DIR = PROJECT_ROOT / "data"

# Add to path for imports
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from db_manager import get_db, JournalEntry
except ImportError:
    get_db = None


class ModernTheme:
    """Modern dark theme with gold accents."""
    
    # Color palette
    BG_DARK = "#0D1117"       # Main background
    BG_PANEL = "#161B22"      # Panel background
    BG_CARD = "#21262D"       # Card/elevated background
    BG_HOVER = "#30363D"      # Hover state
    
    GOLD = "#F0B90B"          # Primary accent (gold)
    GOLD_DIM = "#B8860B"      # Dimmed gold
    GREEN = "#3FB950"         # Success/bullish
    RED = "#F85149"           # Error/bearish
    BLUE = "#58A6FF"          # Info/links
    
    TEXT = "#E6EDF3"          # Primary text
    TEXT_DIM = "#8B949E"      # Secondary text
    TEXT_MUTED = "#484F58"    # Muted text
    
    BORDER = "#30363D"        # Border color


class GoldStandardGUI:
    """Main GUI application for Gold Standard v2."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gold Standard — Precious Metals Intelligence")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        # Theme
        self.theme = ModernTheme
        self.root.configure(bg=self.theme.BG_DARK)
        
        # State
        self.is_running = False
        self.process = None
        self.no_ai = tk.BooleanVar(value=False)
        self.selected_date = tk.StringVar(value=date.today().isoformat())
        
        # Database
        self.db = get_db() if get_db else None
        
        # Setup
        self._setup_styles()
        self._build_ui()
        self._refresh_all()

    def _setup_styles(self):
        """Configure ttk styles for modern look."""
        style = ttk.Style()
        style.theme_use('clam')
        
        t = self.theme
        
        # Frames
        style.configure('Dark.TFrame', background=t.BG_DARK)
        style.configure('Panel.TFrame', background=t.BG_PANEL)
        style.configure('Card.TFrame', background=t.BG_CARD)
        
        # Labels
        style.configure('Title.TLabel',
                       background=t.BG_DARK,
                       foreground=t.GOLD,
                       font=('Segoe UI', 24, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background=t.BG_DARK,
                       foreground=t.TEXT_DIM,
                       font=('Segoe UI', 11))
        
        style.configure('Header.TLabel',
                       background=t.BG_PANEL,
                       foreground=t.GOLD,
                       font=('Segoe UI', 13, 'bold'))
        
        style.configure('Text.TLabel',
                       background=t.BG_PANEL,
                       foreground=t.TEXT,
                       font=('Segoe UI', 10))
        
        style.configure('Muted.TLabel',
                       background=t.BG_PANEL,
                       foreground=t.TEXT_DIM,
                       font=('Segoe UI', 9))
        
        style.configure('Status.TLabel',
                       background=t.BG_DARK,
                       foreground=t.GREEN,
                       font=('Consolas', 10))
        
        # Buttons
        style.configure('Action.TButton',
                       background=t.GOLD,
                       foreground=t.BG_DARK,
                       font=('Segoe UI', 12, 'bold'),
                       padding=(20, 12))
        style.map('Action.TButton',
                 background=[('active', t.GOLD_DIM), ('pressed', t.GOLD_DIM)])
        
        style.configure('Secondary.TButton',
                       background=t.BG_CARD,
                       foreground=t.TEXT,
                       font=('Segoe UI', 10),
                       padding=(12, 8))
        style.map('Secondary.TButton',
                 background=[('active', t.BG_HOVER)])
        
        style.configure('Small.TButton',
                       background=t.BG_CARD,
                       foreground=t.TEXT_DIM,
                       font=('Segoe UI', 9),
                       padding=(8, 4))
        
        # Checkbutton
        style.configure('Dark.TCheckbutton',
                       background=t.BG_DARK,
                       foreground=t.TEXT,
                       font=('Segoe UI', 10))
        
        # Notebook
        style.configure('Dark.TNotebook', background=t.BG_DARK, borderwidth=0)
        style.configure('Dark.TNotebook.Tab',
                       background=t.BG_PANEL,
                       foreground=t.TEXT_DIM,
                       padding=(16, 8),
                       font=('Segoe UI', 10))
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', t.BG_CARD)],
                 foreground=[('selected', t.GOLD)])
        
        # Treeview
        style.configure('Dark.Treeview',
                       background=t.BG_CARD,
                       foreground=t.TEXT,
                       fieldbackground=t.BG_CARD,
                       font=('Segoe UI', 10),
                       rowheight=28)
        style.configure('Dark.Treeview.Heading',
                       background=t.BG_PANEL,
                       foreground=t.GOLD,
                       font=('Segoe UI', 10, 'bold'))
        style.map('Dark.Treeview',
                 background=[('selected', t.BG_HOVER)])
        
        # Scrollbar
        style.configure('Dark.Vertical.TScrollbar',
                       background=t.BG_PANEL,
                       troughcolor=t.BG_DARK,
                       bordercolor=t.BG_DARK,
                       arrowcolor=t.TEXT_DIM)

    def _build_ui(self):
        """Build the main UI layout."""
        t = self.theme
        
        # Main container
        main = ttk.Frame(self.root, style='Dark.TFrame')
        main.pack(fill=tk.BOTH, expand=True)
        
        # Header bar
        self._build_header(main)
        
        # Content area (sidebar + main content)
        content = ttk.Frame(main, style='Dark.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Left sidebar (controls + status)
        sidebar = ttk.Frame(content, style='Dark.TFrame', width=320)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)
        
        self._build_sidebar(sidebar)
        
        # Right main content
        main_content = ttk.Frame(content, style='Dark.TFrame')
        main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._build_main_content(main_content)

    def _build_header(self, parent):
        """Build the header bar."""
        t = self.theme
        
        header = tk.Frame(parent, bg=t.BG_DARK, height=80)
        header.pack(fill=tk.X, padx=20, pady=(20, 10))
        header.pack_propagate(False)
        
        # Logo/Title
        title_frame = tk.Frame(header, bg=t.BG_DARK)
        title_frame.pack(side=tk.LEFT)
        
        tk.Label(title_frame,
                text="GOLD STANDARD",
                bg=t.BG_DARK,
                fg=t.GOLD,
                font=('Segoe UI', 28, 'bold')).pack(anchor=tk.W)
        
        tk.Label(title_frame,
                text="Precious Metals Intelligence Complex",
                bg=t.BG_DARK,
                fg=t.TEXT_DIM,
                font=('Segoe UI', 12)).pack(anchor=tk.W)
        
        # Status area (right)
        status_frame = tk.Frame(header, bg=t.BG_DARK)
        status_frame.pack(side=tk.RIGHT)
        
        # Date/time
        self.time_label = tk.Label(status_frame,
                                   text=datetime.now().strftime("%B %d, %Y"),
                                   bg=t.BG_DARK,
                                   fg=t.TEXT,
                                   font=('Segoe UI', 12))
        self.time_label.pack(anchor=tk.E)
        
        self.status_label = tk.Label(status_frame,
                                     text="● Ready",
                                     bg=t.BG_DARK,
                                     fg=t.GREEN,
                                     font=('Segoe UI', 11))
        self.status_label.pack(anchor=tk.E)

    def _build_sidebar(self, parent):
        """Build the left sidebar with controls."""
        t = self.theme
        
        # === RUN SECTION ===
        run_panel = tk.Frame(parent, bg=t.BG_PANEL, padx=15, pady=15)
        run_panel.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(run_panel,
                text="RUN ANALYSIS",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Main run button
        self.run_btn = tk.Button(run_panel,
                                text="▶  RUN ALL",
                                bg=t.GOLD,
                                fg=t.BG_DARK,
                                font=('Segoe UI', 14, 'bold'),
                                activebackground=t.GOLD_DIM,
                                activeforeground=t.BG_DARK,
                                bd=0,
                                padx=20,
                                pady=12,
                                cursor='hand2',
                                command=self._run_analysis)
        self.run_btn.pack(fill=tk.X, pady=(0, 10))
        
        # AI toggle
        ai_frame = tk.Frame(run_panel, bg=t.BG_PANEL)
        ai_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(ai_frame,
                       text="Disable AI (No Gemini)",
                       variable=self.no_ai,
                       style='Dark.TCheckbutton').pack(anchor=tk.W)
        
        # Secondary buttons
        btn_frame = tk.Frame(run_panel, bg=t.BG_PANEL)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame,
                 text="Quick Daily",
                 bg=t.BG_CARD,
                 fg=t.TEXT,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=6,
                 cursor='hand2',
                 command=self._run_daily).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(btn_frame,
                 text="Pre-Market",
                 bg=t.BG_CARD,
                 fg=t.TEXT,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=6,
                 cursor='hand2',
                 command=self._run_premarket).pack(side=tk.LEFT)
        
        # === STATUS SECTION ===
        status_panel = tk.Frame(parent, bg=t.BG_PANEL, padx=15, pady=15)
        status_panel.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(status_panel,
                text="SYSTEM STATUS",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.status_text = tk.Text(status_panel,
                                   bg=t.BG_CARD,
                                   fg=t.TEXT,
                                   font=('Consolas', 9),
                                   height=8,
                                   relief=tk.FLAT,
                                   padx=10,
                                   pady=10)
        self.status_text.pack(fill=tk.X)
        
        # === CONSOLE ===
        console_panel = tk.Frame(parent, bg=t.BG_PANEL, padx=15, pady=15)
        console_panel.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(console_panel,
                text="CONSOLE",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(console_panel,
                                                  bg=t.BG_CARD,
                                                  fg=t.TEXT_DIM,
                                                  font=('Consolas', 9),
                                                  relief=tk.FLAT,
                                                  padx=10,
                                                  pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def _build_main_content(self, parent):
        """Build the main content area with tabs."""
        t = self.theme
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(parent, style='Dark.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Journals (with date selector)
        journals_frame = tk.Frame(self.notebook, bg=t.BG_PANEL)
        self.notebook.add(journals_frame, text="  📅 Journals  ")
        self._build_journals_tab(journals_frame)
        
        # Tab 2: Charts
        charts_frame = tk.Frame(self.notebook, bg=t.BG_PANEL)
        self.notebook.add(charts_frame, text="  📊 Charts  ")
        self._build_charts_tab(charts_frame)
        
        # Tab 3: Reports
        reports_frame = tk.Frame(self.notebook, bg=t.BG_PANEL)
        self.notebook.add(reports_frame, text="  📑 Reports  ")
        self._build_reports_tab(reports_frame)
        
        # Tab 4: Trades
        trades_frame = tk.Frame(self.notebook, bg=t.BG_PANEL)
        self.notebook.add(trades_frame, text="  💹 Trades  ")
        self._build_trades_tab(trades_frame)

    def _build_journals_tab(self, parent):
        """Build the journals tab with date-wise browsing."""
        t = self.theme
        
        # Split: left calendar/list, right content
        left = tk.Frame(parent, bg=t.BG_CARD, width=280)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        left.pack_propagate(False)
        
        right = tk.Frame(parent, bg=t.BG_CARD)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        # Left side: Date list
        tk.Label(left,
                text="JOURNAL DATES",
                bg=t.BG_CARD,
                fg=t.GOLD,
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        tk.Label(left,
                text="Starting December 1, 2025",
                bg=t.BG_CARD,
                fg=t.TEXT_DIM,
                font=('Segoe UI', 9)).pack(anchor=tk.W, padx=10, pady=(0, 10))
        
        # Date list
        list_frame = tk.Frame(left, bg=t.BG_CARD)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, style='Dark.Vertical.TScrollbar')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.date_listbox = tk.Listbox(list_frame,
                                       bg=t.BG_PANEL,
                                       fg=t.TEXT,
                                       font=('Consolas', 10),
                                       selectbackground=t.GOLD,
                                       selectforeground=t.BG_DARK,
                                       activestyle='none',
                                       relief=tk.FLAT,
                                       highlightthickness=0,
                                       yscrollcommand=scrollbar.set)
        self.date_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.date_listbox.yview)
        
        self.date_listbox.bind('<<ListboxSelect>>', self._on_date_select)
        
        # Refresh button
        tk.Button(left,
                 text="↻ Refresh Dates",
                 bg=t.BG_PANEL,
                 fg=t.TEXT_DIM,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=6,
                 cursor='hand2',
                 command=self._refresh_date_list).pack(fill=tk.X, padx=10, pady=10)
        
        # Right side: Journal content
        header = tk.Frame(right, bg=t.BG_CARD)
        header.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        self.journal_date_label = tk.Label(header,
                                           text="Select a date",
                                           bg=t.BG_CARD,
                                           fg=t.GOLD,
                                           font=('Segoe UI', 14, 'bold'))
        self.journal_date_label.pack(side=tk.LEFT)
        
        self.journal_bias_label = tk.Label(header,
                                           text="",
                                           bg=t.BG_CARD,
                                           fg=t.TEXT_DIM,
                                           font=('Segoe UI', 11))
        self.journal_bias_label.pack(side=tk.RIGHT)
        
        # Journal content
        self.journal_text = scrolledtext.ScrolledText(right,
                                                      bg=t.BG_PANEL,
                                                      fg=t.TEXT,
                                                      font=('Consolas', 10),
                                                      relief=tk.FLAT,
                                                      padx=15,
                                                      pady=15,
                                                      wrap=tk.WORD)
        self.journal_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.journal_text.config(state=tk.DISABLED)

    def _build_charts_tab(self, parent):
        """Build the charts gallery tab."""
        t = self.theme
        
        # Header
        header = tk.Frame(parent, bg=t.BG_PANEL)
        header.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(header,
                text="CHART GALLERY",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(header,
                 text="↻ Refresh",
                 bg=t.BG_CARD,
                 fg=t.TEXT_DIM,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=4,
                 cursor='hand2',
                 command=self._refresh_charts).pack(side=tk.RIGHT)
        
        tk.Button(header,
                 text="Open Folder",
                 bg=t.BG_CARD,
                 fg=t.TEXT_DIM,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=4,
                 cursor='hand2',
                 command=lambda: self._open_folder(CHARTS_DIR)).pack(side=tk.RIGHT, padx=(0, 5))
        
        # Charts grid
        self.charts_frame = tk.Frame(parent, bg=t.BG_PANEL)
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _build_reports_tab(self, parent):
        """Build the reports list tab."""
        t = self.theme
        
        # Header
        header = tk.Frame(parent, bg=t.BG_PANEL)
        header.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(header,
                text="REPORTS & ANALYSIS",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(header,
                 text="↻ Refresh",
                 bg=t.BG_CARD,
                 fg=t.TEXT_DIM,
                 font=('Segoe UI', 9),
                 bd=0,
                 padx=10,
                 pady=4,
                 cursor='hand2',
                 command=self._refresh_reports).pack(side=tk.RIGHT)
        
        # Reports treeview
        tree_frame = tk.Frame(parent, bg=t.BG_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ('name', 'type', 'date', 'size')
        self.reports_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', 
                                         style='Dark.Treeview', height=15)
        
        self.reports_tree.heading('name', text='Report Name')
        self.reports_tree.heading('type', text='Type')
        self.reports_tree.heading('date', text='Date')
        self.reports_tree.heading('size', text='Size')
        
        self.reports_tree.column('name', width=350)
        self.reports_tree.column('type', width=100)
        self.reports_tree.column('date', width=150)
        self.reports_tree.column('size', width=80)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, 
                                  command=self.reports_tree.yview,
                                  style='Dark.Vertical.TScrollbar')
        self.reports_tree.configure(yscrollcommand=scrollbar.set)
        
        self.reports_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.reports_tree.bind('<Double-1>', self._open_selected_report)

    def _build_trades_tab(self, parent):
        """Build the trades/simulation tab."""
        t = self.theme
        
        # Header
        header = tk.Frame(parent, bg=t.BG_PANEL)
        header.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(header,
                text="TRADE SIMULATION",
                bg=t.BG_PANEL,
                fg=t.GOLD,
                font=('Segoe UI', 13, 'bold')).pack(side=tk.LEFT)
        
        # Stats row
        stats_frame = tk.Frame(parent, bg=t.BG_CARD)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.trade_stats = {}
        for stat in ['Total', 'Wins', 'Losses', 'Win Rate', 'PnL']:
            frame = tk.Frame(stats_frame, bg=t.BG_CARD)
            frame.pack(side=tk.LEFT, padx=20, pady=15)
            
            self.trade_stats[stat] = tk.Label(frame,
                                              text="0",
                                              bg=t.BG_CARD,
                                              fg=t.GOLD,
                                              font=('Segoe UI', 18, 'bold'))
            self.trade_stats[stat].pack()
            
            tk.Label(frame,
                    text=stat,
                    bg=t.BG_CARD,
                    fg=t.TEXT_DIM,
                    font=('Segoe UI', 9)).pack()
        
        # Trade history
        history_frame = tk.Frame(parent, bg=t.BG_CARD)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(history_frame,
                text="Trade History",
                bg=t.BG_CARD,
                fg=t.TEXT,
                font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        self.trades_text = scrolledtext.ScrolledText(history_frame,
                                                     bg=t.BG_PANEL,
                                                     fg=t.TEXT,
                                                     font=('Consolas', 9),
                                                     relief=tk.FLAT,
                                                     padx=15,
                                                     pady=10)
        self.trades_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.trades_text.config(state=tk.DISABLED)

    # ==========================================
    # REFRESH METHODS
    # ==========================================
    
    def _refresh_all(self):
        """Refresh all panels."""
        self._refresh_status()
        self._refresh_date_list()
        self._refresh_charts()
        self._refresh_reports()
        self._refresh_trades()

    def _refresh_status(self):
        """Refresh the status panel."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        
        if self.db:
            try:
                info = self.db.get_current_period_info()
                missing = self.db.get_missing_reports()
                stats = self.db.get_statistics()
                
                lines = [
                    f"Date: {info['today']}",
                    f"Week: {info['week']} | Month: {info['month_period']}",
                    "",
                    f"Journals: {stats['total_journals']}",
                    f"Reports: {stats['weekly_reports']}W / {stats['monthly_reports']}M / {stats['yearly_reports']}Y",
                    "",
                    "Today:",
                    f"  Journal: {'✓' if not missing['daily_journal'] else '○'}",
                    f"  Monthly: {'✓' if not missing['monthly_report'] else '○'}",
                    f"  Yearly:  {'✓' if not missing['yearly_report'] else '○'}",
                ]
                self.status_text.insert(tk.END, "\n".join(lines))
            except Exception as e:
                self.status_text.insert(tk.END, f"Error: {e}")
        else:
            self.status_text.insert(tk.END, "Database not available")
        
        self.status_text.config(state=tk.DISABLED)

    def _refresh_date_list(self):
        """Refresh the journal date list."""
        self.date_listbox.delete(0, tk.END)
        
        # Get dates from database or file system
        dates = []
        
        if self.db:
            dates = self.db.get_journal_dates("2025-12-01")
        
        # Also scan output directory for journal files
        if OUTPUT_DIR.exists():
            for f in OUTPUT_DIR.glob("Journal_*.md"):
                try:
                    date_str = f.stem.replace("Journal_", "")
                    if date_str not in dates:
                        dates.append(date_str)
                except:
                    pass
        
        # Sort descending
        dates = sorted(set(dates), reverse=True)
        
        if not dates:
            # Show placeholder dates from Dec 1
            today = date.today()
            start = date(2025, 12, 1)
            delta = (today - start).days + 1
            dates = [(start + timedelta(days=i)).isoformat() for i in range(delta)]
            dates.reverse()
        
        for d in dates:
            # Check if journal exists
            has_journal = False
            if self.db and self.db.has_journal_for_date(d):
                has_journal = True
            elif (OUTPUT_DIR / f"Journal_{d}.md").exists():
                has_journal = True
            
            marker = "●" if has_journal else "○"
            self.date_listbox.insert(tk.END, f" {marker}  {d}")

    def _on_date_select(self, event):
        """Handle date selection."""
        selection = self.date_listbox.curselection()
        if not selection:
            return
        
        item = self.date_listbox.get(selection[0])
        date_str = item.split()[-1]  # Get the date part
        self._load_journal(date_str)

    def _load_journal(self, date_str: str):
        """Load journal for selected date."""
        t = self.theme
        self.journal_date_label.config(text=date_str)
        
        self.journal_text.config(state=tk.NORMAL)
        self.journal_text.delete(1.0, tk.END)
        
        content = None
        bias = None
        
        # Try database first
        if self.db:
            entry = self.db.get_journal(date_str)
            if entry:
                content = entry.content
                bias = entry.bias
        
        # Fall back to file
        if not content:
            file_path = OUTPUT_DIR / f"Journal_{date_str}.md"
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    pass
        
        if content:
            self.journal_text.insert(tk.END, content)
            if bias:
                self.journal_bias_label.config(text=f"Bias: {bias}")
            else:
                self.journal_bias_label.config(text="")
        else:
            self.journal_text.insert(tk.END, f"No journal entry for {date_str}\n\n")
            self.journal_text.insert(tk.END, "Run analysis to generate this journal.")
            self.journal_bias_label.config(text="")
        
        self.journal_text.config(state=tk.DISABLED)

    def _refresh_charts(self):
        """Refresh the charts gallery."""
        t = self.theme
        
        # Clear existing
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
        
        if not CHARTS_DIR.exists():
            tk.Label(self.charts_frame,
                    text="No charts found. Run analysis to generate.",
                    bg=t.BG_PANEL,
                    fg=t.TEXT_DIM,
                    font=('Segoe UI', 11)).pack(pady=50)
            return
        
        charts = list(CHARTS_DIR.glob("*.png"))
        if not charts:
            tk.Label(self.charts_frame,
                    text="No charts found. Run analysis to generate.",
                    bg=t.BG_PANEL,
                    fg=t.TEXT_DIM,
                    font=('Segoe UI', 11)).pack(pady=50)
            return
        
        # Create grid
        row_frame = None
        for i, chart in enumerate(sorted(charts)):
            if i % 3 == 0:
                row_frame = tk.Frame(self.charts_frame, bg=t.BG_PANEL)
                row_frame.pack(fill=tk.X, pady=5)
            
            card = tk.Frame(row_frame, bg=t.BG_CARD, padx=15, pady=15)
            card.pack(side=tk.LEFT, padx=5)
            
            tk.Label(card,
                    text=chart.stem,
                    bg=t.BG_CARD,
                    fg=t.GOLD,
                    font=('Segoe UI', 11, 'bold')).pack()
            
            try:
                size_kb = chart.stat().st_size / 1024
                tk.Label(card,
                        text=f"{size_kb:.1f} KB",
                        bg=t.BG_CARD,
                        fg=t.TEXT_DIM,
                        font=('Segoe UI', 9)).pack()
            except:
                pass
            
            tk.Button(card,
                     text="Open",
                     bg=t.BG_PANEL,
                     fg=t.TEXT,
                     font=('Segoe UI', 9),
                     bd=0,
                     padx=15,
                     pady=4,
                     cursor='hand2',
                     command=lambda p=chart: self._open_file(p)).pack(pady=(10, 0))

    def _refresh_reports(self):
        """Refresh the reports list."""
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)
        
        # Gather all reports
        reports = []
        
        for report_dir in [OUTPUT_DIR, REPORTS_DIR]:
            if not report_dir.exists():
                continue
            
            for f in report_dir.glob("*.md"):
                try:
                    stat = f.stat()
                    size_kb = stat.st_size / 1024
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    
                    # Determine type
                    name = f.stem
                    if 'Journal' in name:
                        rtype = 'Daily'
                    elif 'Weekly' in name or 'weekly' in name:
                        rtype = 'Weekly'
                    elif 'Monthly' in name or 'monthly' in name:
                        rtype = 'Monthly'
                    elif 'Yearly' in name or 'yearly' in name:
                        rtype = 'Yearly'
                    elif 'premarket' in name.lower():
                        rtype = 'Pre-Market'
                    else:
                        rtype = 'Other'
                    
                    reports.append({
                        'name': f.name,
                        'type': rtype,
                        'date': mtime,
                        'size': f"{size_kb:.1f} KB",
                        'path': str(f)
                    })
                except:
                    pass
        
        # Sort by date descending
        reports.sort(key=lambda x: x['date'], reverse=True)
        
        for r in reports:
            self.reports_tree.insert('', tk.END, values=(
                r['name'], r['type'], r['date'], r['size']
            ), tags=(r['path'],))

    def _refresh_trades(self):
        """Refresh the trades tab."""
        t = self.theme
        
        # Load from cortex memory
        try:
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
            else:
                memory = {}
        except:
            memory = {}
        
        # Update stats
        total_wins = memory.get('total_wins', 0)
        total_losses = memory.get('total_losses', 0)
        total = total_wins + total_losses
        win_rate = (total_wins / total * 100) if total > 0 else 0
        total_pnl = memory.get('total_pnl', 0)
        
        self.trade_stats['Total'].config(text=str(total))
        self.trade_stats['Wins'].config(text=str(total_wins), fg=t.GREEN)
        self.trade_stats['Losses'].config(text=str(total_losses), fg=t.RED)
        self.trade_stats['Win Rate'].config(text=f"{win_rate:.0f}%")
        self.trade_stats['PnL'].config(
            text=f"${total_pnl:+.2f}",
            fg=t.GREEN if total_pnl >= 0 else t.RED
        )
        
        # Update history
        self.trades_text.config(state=tk.NORMAL)
        self.trades_text.delete(1.0, tk.END)
        
        closed = memory.get('closed_trades', [])
        if not closed:
            self.trades_text.insert(tk.END, "No trade history yet.\n\n")
            self.trades_text.insert(tk.END, "Trades will appear here as they are simulated.")
        else:
            for trade in reversed(closed[-20:]):
                result = trade.get('result', '?')
                marker = "[WIN]" if result == 'WIN' else "[LOSS]" if result == 'LOSS' else "[BE]"
                pnl = trade.get('realized_pnl', 0)
                
                self.trades_text.insert(tk.END, f"{marker} Trade #{trade.get('id', '?')}\n")
                self.trades_text.insert(tk.END, f"  {trade.get('direction', '?')} @ ${trade.get('entry_price', 0):.2f}")
                self.trades_text.insert(tk.END, f" → ${trade.get('exit_price', 0):.2f}\n")
                self.trades_text.insert(tk.END, f"  PnL: ${pnl:+.2f}\n")
                self.trades_text.insert(tk.END, "-" * 40 + "\n")
        
        self.trades_text.config(state=tk.DISABLED)

    # ==========================================
    # ACTION METHODS
    # ==========================================
    
    def _run_analysis(self):
        """Run full analysis."""
        if self.is_running:
            messagebox.showwarning("Running", "Analysis is already in progress.")
            return
        
        self._log("Starting full analysis...")
        self._set_status("Running...", self.theme.GOLD)
        self.run_btn.config(state=tk.DISABLED, bg=self.theme.GOLD_DIM)
        self.is_running = True
        
        thread = threading.Thread(target=self._run_subprocess, args=("--run",))
        thread.daemon = True
        thread.start()

    def _run_daily(self):
        """Quick daily run."""
        if self.is_running:
            return
        
        self._log("Running quick daily...")
        self._set_status("Running...", self.theme.GOLD)
        self.is_running = True
        
        thread = threading.Thread(target=self._run_subprocess, args=("--daily",))
        thread.daemon = True
        thread.start()

    def _run_premarket(self):
        """Run pre-market plan."""
        if self.is_running:
            return
        
        self._log("Generating pre-market plan...")
        self._set_status("Running...", self.theme.GOLD)
        self.is_running = True
        
        thread = threading.Thread(target=self._run_subprocess, args=("--premarket",))
        thread.daemon = True
        thread.start()

    def _run_subprocess(self, mode: str):
        """Run the analysis subprocess."""
        try:
            cmd = [sys.executable, str(PROJECT_ROOT / "run.py"), mode]
            if self.no_ai.get():
                cmd.append("--no-ai")
            
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(PROJECT_ROOT),
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.root.after(0, self._log, line.rstrip())
            
            self.process.wait()
            self.root.after(0, self._analysis_complete, self.process.returncode)
            
        except Exception as e:
            self.root.after(0, self._log, f"Error: {e}")
            self.root.after(0, self._analysis_complete, -1)

    def _analysis_complete(self, return_code: int):
        """Handle analysis completion."""
        self.is_running = False
        self.run_btn.config(state=tk.NORMAL, bg=self.theme.GOLD)
        
        if return_code == 0:
            self._log("✓ Analysis completed successfully")
            self._set_status("● Complete", self.theme.GREEN)
        else:
            self._log(f"✗ Analysis finished with code {return_code}")
            self._set_status("● Error", self.theme.RED)
        
        self._refresh_all()

    def _log(self, message: str):
        """Add message to console."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_status(self, text: str, color: str):
        """Update status label."""
        self.status_label.config(text=text, fg=color)

    def _open_file(self, path: Path):
        """Open file with default app."""
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def _open_folder(self, path: Path):
        """Open folder in explorer."""
        path.mkdir(parents=True, exist_ok=True)
        self._open_file(path)

    def _open_selected_report(self, event):
        """Open selected report from treeview."""
        selection = self.reports_tree.selection()
        if not selection:
            return
        
        item = self.reports_tree.item(selection[0])
        tags = item.get('tags', [])
        if tags:
            path = Path(tags[0])
            self._open_file(path)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = GoldStandardGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
