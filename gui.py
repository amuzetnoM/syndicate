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
Syndicate GUI v3
═══════════════════════════════════════════════════════════════════════════════
Modern dashboard with dual-pane architecture:
- LEFT: Polished Data View (charts grid, analysis, reports)
- RIGHT: AI Automation Workspace (journals, tasks, execution logs, rationale)

Designed for intuitive navigation and superior user experience.
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Dict, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT SETUP
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"
MEMORY_FILE = PROJECT_ROOT / "cortex_memory.json"
DATA_DIR = PROJECT_ROOT / "data"


def ensure_venv():
    """Ensure we're running inside the virtual environment."""
    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        return

    venv_dirs = ["venv312", "venv", ".venv"]
    venv_python = None

    for venv_name in venv_dirs:
        venv_path = PROJECT_ROOT / venv_name
        if venv_path.is_dir():
            if sys.platform == "win32":
                candidate = venv_path / "Scripts" / "python.exe"
            else:
                candidate = venv_path / "bin" / "python"

            if candidate.is_file():
                venv_python = str(candidate)
                break

    if venv_python:
        print(f"[VENV] Activating: {Path(venv_python).parent.parent.name}")
        os.execv(venv_python, [venv_python] + sys.argv)


ensure_venv()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from db_manager import get_db
except ImportError:
    get_db = None


# ═══════════════════════════════════════════════════════════════════════════════
# THEME CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


class Theme:
    """Premium dark theme with gold accents."""

    # Backgrounds
    BG_MAIN = "#08090A"
    BG_PANEL = "#0F1114"
    BG_CARD = "#161920"
    BG_ELEVATED = "#1C2028"
    BG_HOVER = "#252B35"
    BG_INPUT = "#12151A"

    # Gold accent palette
    GOLD = "#F0B90B"
    GOLD_LIGHT = "#FFD93D"
    GOLD_DIM = "#B8860B"
    GOLD_MUTED = "#806515"

    # Semantic colors
    SUCCESS = "#00D26A"
    ERROR = "#FF4757"
    WARNING = "#FFA502"
    INFO = "#3498DB"
    BULLISH = "#00D26A"
    BEARISH = "#FF4757"

    # Text colors
    TEXT_PRIMARY = "#FAFAFA"
    TEXT_SECONDARY = "#A0A8B8"
    TEXT_MUTED = "#5C6370"
    TEXT_DISABLED = "#3C4048"

    # Borders
    BORDER = "#252B35"
    BORDER_LIGHT = "#303845"
    BORDER_FOCUS = "#F0B90B"

    # Font families
    FONT_MAIN = ("Segoe UI", 10)
    FONT_HEADING = ("Segoe UI", 12, "bold")
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_HERO = ("Segoe UI", 24, "bold")
    FONT_MONO = ("Cascadia Code", 9)
    FONT_SMALL = ("Segoe UI", 9)


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════════════════════════


class GoldButton(tk.Canvas):
    """Custom gold-styled button with hover effects."""

    def __init__(
        self, parent, text: str, command=None, style: str = "primary", width: int = 140, height: int = 36, **kwargs
    ):
        super().__init__(parent, width=width, height=height, bg=Theme.BG_PANEL, highlightthickness=0, **kwargs)

        self.text = text
        self.command = command
        self.style = style
        self.width = width
        self.height = height
        self.is_hovered = False
        self.is_pressed = False

        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _get_colors(self):
        if self.style == "primary":
            if self.is_pressed:
                return Theme.GOLD_DIM, Theme.BG_MAIN
            elif self.is_hovered:
                return Theme.GOLD_LIGHT, Theme.BG_MAIN
            return Theme.GOLD, Theme.BG_MAIN
        else:  # secondary
            if self.is_pressed:
                return Theme.BG_HOVER, Theme.TEXT_PRIMARY
            elif self.is_hovered:
                return Theme.BG_ELEVATED, Theme.GOLD
            return Theme.BG_CARD, Theme.TEXT_SECONDARY

    def _draw(self):
        self.delete("all")
        bg, fg = self._get_colors()

        # Draw rounded rectangle
        r = 4
        self.create_polygon(
            r,
            0,
            self.width - r,
            0,
            self.width,
            r,
            self.width,
            self.height - r,
            self.width - r,
            self.height,
            r,
            self.height,
            0,
            self.height - r,
            0,
            r,
            fill=bg,
            outline="",
        )

        # Draw text
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=fg, font=("Segoe UI", 10, "bold"))

    def _on_enter(self, e):
        self.is_hovered = True
        self._draw()
        self.config(cursor="hand2")

    def _on_leave(self, e):
        self.is_hovered = False
        self.is_pressed = False
        self._draw()

    def _on_press(self, e):
        self.is_pressed = True
        self._draw()

    def _on_release(self, e):
        self.is_pressed = False
        self._draw()
        if self.is_hovered and self.command:
            self.command()


class StatusIndicator(tk.Canvas):
    """Animated status indicator dot."""

    def __init__(self, parent, size: int = 10, **kwargs):
        super().__init__(parent, width=size, height=size, bg=Theme.BG_PANEL, highlightthickness=0, **kwargs)
        self.size = size
        self.status = "idle"
        self._draw()

    def _draw(self):
        self.delete("all")
        colors = {
            "idle": Theme.TEXT_MUTED,
            "ready": Theme.SUCCESS,
            "running": Theme.GOLD,
            "error": Theme.ERROR,
            "success": Theme.SUCCESS,
        }
        color = colors.get(self.status, Theme.TEXT_MUTED)

        padding = 2
        self.create_oval(padding, padding, self.size - padding, self.size - padding, fill=color, outline="")

    def set_status(self, status: str):
        self.status = status
        self._draw()


class ChartCard(tk.Frame):
    """Clickable chart preview card."""

    def __init__(self, parent, title: str, subtitle: str = "", on_click=None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)

        self.on_click = on_click
        self.title = title

        # Border effect
        self.config(highlightthickness=1, highlightbackground=Theme.BORDER)

        # Content area
        content = tk.Frame(self, bg=Theme.BG_CARD)
        content.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Chart placeholder / image area
        self.chart_area = tk.Frame(content, bg=Theme.BG_ELEVATED, height=140)
        self.chart_area.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.chart_area.pack_propagate(False)

        # Placeholder text
        self.placeholder = tk.Label(
            self.chart_area, text="📈", bg=Theme.BG_ELEVATED, fg=Theme.TEXT_MUTED, font=("Segoe UI", 32)
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(content, text=title, bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HEADING).pack(
            anchor=tk.W, padx=10
        )

        # Subtitle
        if subtitle:
            tk.Label(content, text=subtitle, bg=Theme.BG_CARD, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL).pack(
                anchor=tk.W, padx=10, pady=(0, 8)
            )

        # Bindings
        for widget in [self, content, self.chart_area, self.placeholder]:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        self.config(highlightbackground=Theme.GOLD_DIM)
        self.configure(cursor="hand2")

    def _on_leave(self, e):
        self.config(highlightbackground=Theme.BORDER)

    def _on_click(self, e):
        if self.on_click:
            self.on_click(self.title)

    def load_image(self, path: Path):
        """Load chart image from file."""
        try:
            from PIL import Image, ImageTk

            if path.exists():
                img = Image.open(path)
                img = img.resize((200, 130), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                self.placeholder.config(image=self.photo, text="")
        except ImportError:
            pass  # PIL not available, use placeholder


class TaskCard(tk.Frame):
    """Task display card with status and details."""

    def __init__(
        self, parent, task_type: str, description: str, status: str = "pending", priority: str = "medium", **kwargs
    ):
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)

        self.config(highlightthickness=1, highlightbackground=Theme.BORDER)

        # Priority colors
        priority_colors = {
            "critical": Theme.ERROR,
            "high": Theme.WARNING,
            "medium": Theme.INFO,
            "low": Theme.TEXT_MUTED,
        }

        # Status colors
        status_colors = {
            "pending": Theme.TEXT_MUTED,
            "in_progress": Theme.GOLD,
            "completed": Theme.SUCCESS,
            "failed": Theme.ERROR,
        }

        # Header row
        header = tk.Frame(self, bg=Theme.BG_CARD)
        header.pack(fill=tk.X, padx=10, pady=(8, 4))

        # Type badge
        type_frame = tk.Frame(header, bg=Theme.BG_ELEVATED)
        type_frame.pack(side=tk.LEFT)
        tk.Label(
            type_frame,
            text=task_type.upper(),
            bg=Theme.BG_ELEVATED,
            fg=Theme.GOLD,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
        ).pack()

        # Priority indicator
        priority_dot = tk.Canvas(header, width=10, height=10, bg=Theme.BG_CARD, highlightthickness=0)
        priority_dot.pack(side=tk.RIGHT, padx=(4, 0))
        priority_dot.create_oval(2, 2, 8, 8, fill=priority_colors.get(priority, Theme.INFO), outline="")

        # Status
        status_label = tk.Label(
            header,
            text=status.replace("_", " ").title(),
            bg=Theme.BG_CARD,
            fg=status_colors.get(status, Theme.TEXT_MUTED),
            font=Theme.FONT_SMALL,
        )
        status_label.pack(side=tk.RIGHT)

        # Description
        desc_label = tk.Label(
            self,
            text=description,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_SMALL,
            wraplength=280,
            justify=tk.LEFT,
        )
        desc_label.pack(anchor=tk.W, padx=10, pady=(0, 8))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════


class SyndicateGUI:
    """
    Syndicate v3 - Dual-Pane Dashboard

    Architecture:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           HEADER BAR                                    │
    ├────────────────────────────────┬────────────────────────────────────────┤
    │      DATA VIEW (LEFT)          │      AI WORKSPACE (RIGHT)              │
    │  ┌───────────────────────────┐ │  ┌────────────────────────────────────┐│
    │  │     CHARTS GRID           │ │  │     AI JOURNAL & REASONING         ││
    │  │  [GC] [SI] [DX] [VIX]    │ │  │     • Today's analysis              ││
    │  │  [^TNX] [ES]             │ │  │     • Thought process               ││
    │  └───────────────────────────┘ │  │     • Market rationale              ││
    │  ┌───────────────────────────┐ │  └────────────────────────────────────┘│
    │  │     ANALYSIS PANEL        │ │  ┌────────────────────────────────────┐│
    │  │     • Selected chart      │ │  │     TASK QUEUE                     ││
    │  │     • Report content      │ │  │     [■] Research: Fed minutes      ││
    │  │     • Key metrics         │ │  │     [○] Fetch: COT data           ││
    │  └───────────────────────────┘ │  │     [✓] Calculate: Position size   ││
    ├────────────────────────────────┤  └────────────────────────────────────┘│
    │      CONTROL BAR               │  ┌────────────────────────────────────┐│
    │  [▶ RUN] [DAEMON] [SETTINGS]  │  │     EXECUTION LOG                  ││
    │                                │  │     Attempt → Result → Learning    ││
    └────────────────────────────────┴──└────────────────────────────────────┘│
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Syndicate — Precious Metals Intelligence Complex")
        self.root.geometry("1600x950")
        self.root.minsize(1400, 800)
        self.root.configure(bg=Theme.BG_MAIN)

        # State management
        self.is_running = False
        self.daemon_active = False
        self.process: Optional[subprocess.Popen] = None
        self.selected_chart: Optional[str] = None
        self.no_ai = tk.BooleanVar(value=False)

        # Database connection
        self.db = get_db() if get_db else None

        # Build interface
        self._setup_styles()
        self._build_ui()
        self._load_data()

        # Start refresh timer
        self._schedule_refresh()

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook (tabs)
        style.configure("Gold.TNotebook", background=Theme.BG_PANEL)
        style.configure(
            "Gold.TNotebook.Tab",
            background=Theme.BG_CARD,
            foreground=Theme.TEXT_MUTED,
            padding=(16, 8),
            font=Theme.FONT_MAIN,
        )
        style.map(
            "Gold.TNotebook.Tab", background=[("selected", Theme.BG_ELEVATED)], foreground=[("selected", Theme.GOLD)]
        )

        # Scrollbar
        style.configure(
            "Gold.Vertical.TScrollbar",
            background=Theme.BG_CARD,
            troughcolor=Theme.BG_PANEL,
            bordercolor=Theme.BG_PANEL,
            arrowcolor=Theme.TEXT_MUTED,
        )

        # Checkbutton
        style.configure(
            "Gold.TCheckbutton", background=Theme.BG_PANEL, foreground=Theme.TEXT_SECONDARY, font=Theme.FONT_SMALL
        )

    def _build_ui(self):
        """Construct the main UI layout."""
        # Main container
        main = tk.Frame(self.root, bg=Theme.BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        self._build_header(main)

        # Content area - dual pane
        content = tk.Frame(main, bg=Theme.BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        # Left pane - Data View
        self.left_pane = tk.Frame(content, bg=Theme.BG_PANEL)
        self.left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self._build_data_view(self.left_pane)

        # Right pane - AI Workspace
        self.right_pane = tk.Frame(content, bg=Theme.BG_PANEL, width=480)
        self.right_pane.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        self.right_pane.pack_propagate(False)
        self._build_ai_workspace(self.right_pane)

    def _build_header(self, parent):
        """Build the header bar."""
        header = tk.Frame(parent, bg=Theme.BG_PANEL, height=72)
        header.pack(fill=tk.X, padx=16, pady=16)
        header.pack_propagate(False)

        # Left side - Branding
        brand = tk.Frame(header, bg=Theme.BG_PANEL)
        brand.pack(side=tk.LEFT, fill=tk.Y, padx=16)

        title_row = tk.Frame(brand, bg=Theme.BG_PANEL)
        title_row.pack(anchor=tk.W)

        tk.Label(title_row, text="SYNDICATE", bg=Theme.BG_PANEL, fg=Theme.GOLD, font=Theme.FONT_HERO).pack(side=tk.LEFT)
        tk.Label(title_row, text="", bg=Theme.BG_PANEL, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_HERO).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        tk.Label(
            brand,
            text="Precious Metals Intelligence Complex",
            bg=Theme.BG_PANEL,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
        ).pack(anchor=tk.W)

        # Center - Control buttons
        controls = tk.Frame(header, bg=Theme.BG_PANEL)
        controls.pack(side=tk.LEFT, expand=True)

        btn_frame = tk.Frame(controls, bg=Theme.BG_PANEL)
        btn_frame.pack()

        self.run_btn = GoldButton(
            btn_frame, "▶  RUN ANALYSIS", command=self._run_analysis, style="primary", width=160, height=40
        )
        self.run_btn.pack(side=tk.LEFT, padx=4)

        self.daemon_btn = GoldButton(
            btn_frame, "⚡ START DAEMON", command=self._toggle_daemon, style="secondary", width=160, height=40
        )
        self.daemon_btn.pack(side=tk.LEFT, padx=4)

        GoldButton(
            btn_frame, "📊 PRE-MARKET", command=self._run_premarket, style="secondary", width=130, height=40
        ).pack(side=tk.LEFT, padx=4)

        # Right side - Status
        status_frame = tk.Frame(header, bg=Theme.BG_PANEL)
        status_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=16)

        # Date
        tk.Label(
            status_frame,
            text=datetime.now().strftime("%A, %B %d, %Y"),
            bg=Theme.BG_PANEL,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_MAIN,
        ).pack(anchor=tk.E)

        # Status row
        status_row = tk.Frame(status_frame, bg=Theme.BG_PANEL)
        status_row.pack(anchor=tk.E, pady=(4, 0))

        self.status_indicator = StatusIndicator(status_row, size=12)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 6))
        self.status_indicator.set_status("ready")

        self.status_label = tk.Label(
            status_row, text="Ready", bg=Theme.BG_PANEL, fg=Theme.SUCCESS, font=Theme.FONT_MAIN
        )
        self.status_label.pack(side=tk.LEFT)

    def _build_data_view(self, parent):
        """Build the left pane - polished data view."""
        # Charts section header
        header = tk.Frame(parent, bg=Theme.BG_PANEL)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        tk.Label(header, text="MARKET CHARTS", bg=Theme.BG_PANEL, fg=Theme.GOLD, font=Theme.FONT_HEADING).pack(
            side=tk.LEFT
        )

        GoldButton(header, "↻ Refresh", command=self._refresh_charts, style="secondary", width=90, height=28).pack(
            side=tk.RIGHT
        )

        # Charts grid
        charts_frame = tk.Frame(parent, bg=Theme.BG_PANEL)
        charts_frame.pack(fill=tk.X, padx=16, pady=(0, 16))

        self.chart_cards: Dict[str, ChartCard] = {}
        assets = [
            ("GC=F", "Gold Futures", "COMEX"),
            ("SI=F", "Silver Futures", "COMEX"),
            ("DX-Y.NYB", "US Dollar Index", "ICE"),
            ("^VIX", "Volatility Index", "CBOE"),
            ("^TNX", "10Y Treasury Yield", "Index"),
            ("ES=F", "S&P 500 Futures", "CME"),
        ]

        # 3x2 grid
        for i, (symbol, name, exchange) in enumerate(assets):
            row, col = divmod(i, 3)
            card = ChartCard(charts_frame, name, f"{symbol} • {exchange}", on_click=self._on_chart_click)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.chart_cards[symbol] = card

        for i in range(3):
            charts_frame.columnconfigure(i, weight=1)

        # Analysis panel
        analysis_header = tk.Frame(parent, bg=Theme.BG_PANEL)
        analysis_header.pack(fill=tk.X, padx=16, pady=(0, 8))

        tk.Label(analysis_header, text="ANALYSIS", bg=Theme.BG_PANEL, fg=Theme.GOLD, font=Theme.FONT_HEADING).pack(
            side=tk.LEFT
        )

        self.analysis_title = tk.Label(
            analysis_header, text="Select a chart above", bg=Theme.BG_PANEL, fg=Theme.TEXT_MUTED, font=Theme.FONT_SMALL
        )
        self.analysis_title.pack(side=tk.RIGHT)

        # Analysis content with tabs
        analysis_notebook = ttk.Notebook(parent, style="Gold.TNotebook")
        analysis_notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        # Report tab
        report_frame = tk.Frame(analysis_notebook, bg=Theme.BG_CARD)
        analysis_notebook.add(report_frame, text="  📄 Report  ")

        self.report_text = scrolledtext.ScrolledText(
            report_frame,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_MONO,
            relief=tk.FLAT,
            padx=12,
            pady=12,
            wrap=tk.WORD,
            insertbackground=Theme.GOLD,
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Metrics tab
        metrics_frame = tk.Frame(analysis_notebook, bg=Theme.BG_CARD)
        analysis_notebook.add(metrics_frame, text="  📊 Metrics  ")

        self.metrics_text = scrolledtext.ScrolledText(
            metrics_frame,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_MONO,
            relief=tk.FLAT,
            padx=12,
            pady=12,
            wrap=tk.WORD,
        )
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Console tab
        console_frame = tk.Frame(analysis_notebook, bg=Theme.BG_CARD)
        analysis_notebook.add(console_frame, text="  🖥️ Console  ")

        self.console_text = scrolledtext.ScrolledText(
            console_frame,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_MONO,
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.console_text.config(state=tk.DISABLED)

    def _build_ai_workspace(self, parent):
        """Build the right pane - AI automation workspace."""
        # Header
        header = tk.Frame(parent, bg=Theme.BG_PANEL)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        tk.Label(header, text="🤖 AI WORKSPACE", bg=Theme.BG_PANEL, fg=Theme.GOLD, font=Theme.FONT_HEADING).pack(
            side=tk.LEFT
        )

        # AI Journal section
        journal_frame = tk.Frame(parent, bg=Theme.BG_CARD)
        journal_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        journal_header = tk.Frame(journal_frame, bg=Theme.BG_CARD)
        journal_header.pack(fill=tk.X, padx=12, pady=(12, 4))

        tk.Label(
            journal_header, text="TODAY'S JOURNAL", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_MAIN
        ).pack(side=tk.LEFT)

        tk.Label(
            journal_header,
            text=date.today().strftime("%Y-%m-%d"),
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=Theme.FONT_SMALL,
        ).pack(side=tk.RIGHT)

        self.journal_text = scrolledtext.ScrolledText(
            journal_frame,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_MONO,
            relief=tk.FLAT,
            height=8,
            padx=10,
            pady=10,
            wrap=tk.WORD,
        )
        self.journal_text.pack(fill=tk.X, padx=12, pady=(0, 12))

        # AI Rationale section
        rationale_frame = tk.Frame(parent, bg=Theme.BG_CARD)
        rationale_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        tk.Label(
            rationale_frame,
            text="💭 REASONING & RATIONALE",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=Theme.FONT_MAIN,
            padx=12,
            pady=8,
        ).pack(anchor=tk.W)

        self.rationale_text = scrolledtext.ScrolledText(
            rationale_frame,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_SECONDARY,
            font=Theme.FONT_MONO,
            relief=tk.FLAT,
            height=6,
            padx=10,
            pady=10,
            wrap=tk.WORD,
        )
        self.rationale_text.pack(fill=tk.X, padx=12, pady=(0, 12))

        # Task Queue section
        tasks_frame = tk.Frame(parent, bg=Theme.BG_CARD)
        tasks_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        tasks_header = tk.Frame(tasks_frame, bg=Theme.BG_CARD)
        tasks_header.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(
            tasks_header, text="📋 TASK QUEUE", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_MAIN
        ).pack(side=tk.LEFT)

        self.task_count = tk.Label(
            tasks_header, text="0 pending", bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=Theme.FONT_SMALL
        )
        self.task_count.pack(side=tk.RIGHT)

        # Task list container
        self.tasks_container = tk.Frame(tasks_frame, bg=Theme.BG_CARD)
        self.tasks_container.pack(fill=tk.X, padx=12, pady=(0, 12))

        # Execution Log section
        log_frame = tk.Frame(parent, bg=Theme.BG_CARD)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        log_header = tk.Frame(log_frame, bg=Theme.BG_CARD)
        log_header.pack(fill=tk.X, padx=12, pady=(12, 8))

        tk.Label(
            log_header, text="📜 EXECUTION LOG", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY, font=Theme.FONT_MAIN
        ).pack(side=tk.LEFT)

        GoldButton(log_header, "Clear", command=self._clear_execution_log, style="secondary", width=60, height=24).pack(
            side=tk.RIGHT
        )

        self.execution_log = scrolledtext.ScrolledText(
            log_frame, bg=Theme.BG_INPUT, fg=Theme.TEXT_MUTED, font=Theme.FONT_MONO, relief=tk.FLAT, padx=10, pady=10
        )
        self.execution_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.execution_log.config(state=tk.DISABLED)

        # Configure tags for colored output
        self.execution_log.tag_configure("success", foreground=Theme.SUCCESS)
        self.execution_log.tag_configure("error", foreground=Theme.ERROR)
        self.execution_log.tag_configure("warning", foreground=Theme.WARNING)
        self.execution_log.tag_configure("info", foreground=Theme.INFO)
        self.execution_log.tag_configure("timestamp", foreground=Theme.TEXT_MUTED)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_chart_click(self, title: str):
        """Handle chart card click."""
        self.selected_chart = title
        self.analysis_title.config(text=f"Viewing: {title}")
        self._load_chart_analysis(title)

    def _refresh_charts(self):
        """Refresh all chart images."""
        self._log_execution("Refreshing chart data...", "info")

        # Try to load actual chart images
        chart_files = {
            "Gold Futures": "GOLD",
            "Silver Futures": "SILVER",
            "US Dollar Index": "DXY",
            "Volatility Index": "VIX",
            "10Y Treasury Yield": "TNX",
            "S&P 500 Futures": "SPX",
        }

        for title, filename in chart_files.items():
            for card in self.chart_cards.values():
                if card.title == title:
                    chart_path = CHARTS_DIR / f"{filename}.png"
                    if chart_path.exists():
                        card.load_image(chart_path)

        self._log_execution("Charts refreshed", "success")

    def _load_chart_analysis(self, title: str):
        """Load analysis for selected chart."""
        # Map title to report files
        report_map = {
            "Gold Futures": ["Journal", "1y", "3m"],
            "Silver Futures": ["Journal", "1y"],
            "US Dollar Index": ["1y", "3m"],
            "Volatility Index": ["catalysts"],
            "10Y Treasury Yield": ["inst_matrix"],
            "S&P 500 Futures": ["weekly_rundown"],
        }

        today = date.today().isoformat()
        report_types = report_map.get(title, ["Journal"])

        content = f"# {title} Analysis\n\n"

        for report_type in report_types:
            report_file = REPORTS_DIR / f"{report_type}_{today}.md"
            if report_file.exists():
                content += f"\n## {report_type.replace('_', ' ').title()}\n\n"
                content += report_file.read_text()[:2000]  # Limit size
                content += "\n\n---\n"

        if content == f"# {title} Analysis\n\n":
            content += "No analysis available. Run analysis to generate reports."

        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, content)

    def _log_execution(self, message: str, level: str = "info"):
        """Add entry to execution log."""
        self.execution_log.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.execution_log.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.execution_log.insert(tk.END, f"{message}\n", level)

        self.execution_log.see(tk.END)
        self.execution_log.config(state=tk.DISABLED)

    def _log_console(self, message: str):
        """Add entry to console."""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, message)
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)

    def _clear_execution_log(self):
        """Clear the execution log."""
        self.execution_log.config(state=tk.NORMAL)
        self.execution_log.delete(1.0, tk.END)
        self.execution_log.config(state=tk.DISABLED)

    def _set_status(self, text: str, status: str = "ready"):
        """Update status display."""
        colors = {"ready": Theme.SUCCESS, "running": Theme.GOLD, "error": Theme.ERROR, "idle": Theme.TEXT_MUTED}
        self.status_label.config(text=text, fg=colors.get(status, Theme.TEXT_MUTED))
        self.status_indicator.set_status(status)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_analysis(self):
        """Run full analysis."""
        if self.is_running:
            messagebox.showinfo("Info", "Analysis already running")
            return

        self.is_running = True
        self._set_status("Running analysis...", "running")
        self._log_execution("Starting full analysis...", "info")

        def run():
            try:
                cmd = [sys.executable, str(PROJECT_ROOT / "run.py"), "--once"]
                if self.no_ai.get():
                    cmd.append("--no-ai")

                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )

                for line in self.process.stdout:
                    self.root.after(0, self._log_console, line)

                self.process.wait()

                if self.process.returncode == 0:
                    self.root.after(0, self._on_analysis_complete)
                else:
                    self.root.after(0, self._on_analysis_error)

            except Exception as e:
                self.root.after(0, lambda err=e: self._log_execution(f"Error: {err}", "error"))
                self.root.after(0, self._on_analysis_error)
            finally:
                self.is_running = False

        threading.Thread(target=run, daemon=True).start()

    def _on_analysis_complete(self):
        """Handle analysis completion."""
        self._set_status("Analysis complete", "ready")
        self._log_execution("Analysis completed successfully", "success")
        self._load_data()
        self._refresh_charts()

    def _on_analysis_error(self):
        """Handle analysis error."""
        self._set_status("Analysis failed", "error")
        self._log_execution("Analysis failed - check console", "error")

    def _run_premarket(self):
        """Run pre-market analysis."""
        if self.is_running:
            return

        self.is_running = True
        self._set_status("Running pre-market...", "running")
        self._log_execution("Starting pre-market analysis...", "info")

        def run():
            try:
                cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "pre_market.py")]
                process = subprocess.run(cmd, capture_output=True, text=True)

                if process.returncode == 0:
                    self.root.after(0, lambda: self._log_execution("Pre-market complete", "success"))
                    self.root.after(0, lambda: self._set_status("Ready", "ready"))
                else:
                    self.root.after(0, lambda: self._log_execution("Pre-market failed", "error"))
                    self.root.after(0, lambda: self._set_status("Error", "error"))
            except Exception as e:
                self.root.after(0, lambda err=e: self._log_execution(f"Error: {err}", "error"))
            finally:
                self.is_running = False

        threading.Thread(target=run, daemon=True).start()

    def _toggle_daemon(self):
        """Toggle daemon mode."""
        if self.daemon_active:
            self._stop_daemon()
        else:
            self._start_daemon()

    def _start_daemon(self):
        """Start the daemon process."""
        self.daemon_active = True
        self.daemon_btn.text = "⏹ STOP DAEMON"
        self.daemon_btn._draw()
        self._set_status("Daemon active", "running")
        self._log_execution("Daemon started - 1 minute intervals", "info")

        def run():
            try:
                cmd = [sys.executable, str(PROJECT_ROOT / "run.py"), "--interval-min", "1"]
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )

                for line in self.process.stdout:
                    if not self.daemon_active:
                        break
                    self.root.after(0, self._log_console, line)

                    # Parse output for log entries
                    if "[INFO]" in line or "✓" in line:
                        self.root.after(0, lambda line_text=line: self._log_execution(line_text.strip()[:80], "info"))
                    elif "[ERROR]" in line or "✗" in line:
                        self.root.after(0, lambda line_text=line: self._log_execution(line_text.strip()[:80], "error"))

            except Exception as e:
                self.root.after(0, lambda err=e: self._log_execution(f"Daemon error: {err}", "error"))
            finally:
                self.root.after(0, self._on_daemon_stopped)

        threading.Thread(target=run, daemon=True).start()

    def _stop_daemon(self):
        """Stop the daemon process."""
        self.daemon_active = False
        if self.process:
            self.process.terminate()
        self._log_execution("Stopping daemon...", "warning")

    def _on_daemon_stopped(self):
        """Handle daemon stop."""
        self.daemon_active = False
        self.daemon_btn.text = "⚡ START DAEMON"
        self.daemon_btn._draw()
        self._set_status("Ready", "ready")
        self._log_execution("Daemon stopped", "info")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA LOADING
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_data(self):
        """Load all data from database and files."""
        self._load_journal()
        self._load_rationale()
        self._load_tasks()

    def _load_journal(self):
        """Load today's journal."""
        today = date.today().isoformat()
        journal_file = OUTPUT_DIR / f"Journal_{today}.md"

        content = ""
        if journal_file.exists():
            content = journal_file.read_text()
        elif self.db:
            try:
                journal = self.db.get_latest_journal()
                if journal:
                    content = journal.get("content", "")
            except Exception:
                pass

        if not content:
            content = "No journal entry for today.\nRun analysis to generate."

        self.journal_text.delete(1.0, tk.END)
        self.journal_text.insert(tk.END, content[:3000])

    def _load_rationale(self):
        """Load AI rationale from cortex memory."""
        content = ""

        if MEMORY_FILE.exists():
            try:
                memory = json.loads(MEMORY_FILE.read_text())

                # Extract reasoning from memory
                if "reasoning" in memory:
                    content = memory["reasoning"]
                elif "recent_predictions" in memory:
                    content = "Recent Analysis Reasoning:\n\n"
                    for pred in memory["recent_predictions"][-3:]:
                        content += f"• {pred.get('rationale', 'N/A')}\n\n"
            except Exception:
                pass

        if not content:
            content = "No rationale available.\nRun analysis to generate AI reasoning."

        self.rationale_text.delete(1.0, tk.END)
        self.rationale_text.insert(tk.END, content[:2000])

    def _load_tasks(self):
        """Load pending tasks from database."""
        # Clear existing task cards
        for widget in self.tasks_container.winfo_children():
            widget.destroy()

        pending_count = 0

        if self.db:
            try:
                tasks = self.db.get_pending_actions(limit=5)
                pending_count = len(tasks)

                for task in tasks:
                    card = TaskCard(
                        self.tasks_container,
                        task_type=task.get("action_type", "task"),
                        description=task.get("description", "")[:100],
                        status=task.get("status", "pending"),
                        priority=task.get("priority", "medium"),
                    )
                    card.pack(fill=tk.X, pady=2)

            except Exception as e:
                tk.Label(
                    self.tasks_container, text=f"Error: {e}", bg=Theme.BG_CARD, fg=Theme.ERROR, font=Theme.FONT_SMALL
                ).pack(pady=4)

        if pending_count == 0:
            tk.Label(
                self.tasks_container,
                text="No pending tasks",
                bg=Theme.BG_CARD,
                fg=Theme.TEXT_MUTED,
                font=Theme.FONT_SMALL,
            ).pack(pady=8)

        self.task_count.config(text=f"{pending_count} pending")

    def _schedule_refresh(self):
        """Schedule periodic data refresh."""
        self._load_data()
        self.root.after(30000, self._schedule_refresh)  # Every 30 seconds


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Launch the Syndicate GUI."""
    root = tk.Tk()

    # Set icon if available
    try:
        icon_path = PROJECT_ROOT / "data" / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except Exception:
        pass

    app = SyndicateGUI(root)

    # Handle close
    def on_close():
        if app.process:
            app.process.terminate()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
