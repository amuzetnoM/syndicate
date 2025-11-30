#!/usr/bin/env python3
"""
Gold Standard GUI
Dashboard and wizard for running reports and viewing results.
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from datetime import date, datetime
import webbrowser
import json

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"
MEMORY_FILE = PROJECT_ROOT / "cortex_memory.json"


class GoldStandardGUI:
    """Main GUI application for Gold Standard."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gold Standard — Precious Metals Intelligence")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # Configure dark theme colors
        self.colors = {
            'bg': '#1a1a2e',
            'bg_light': '#16213e',
            'accent': '#e94560',
            'gold': '#ffd700',
            'text': '#eaeaea',
            'text_dim': '#a0a0a0',
            'success': '#4ecca3',
            'warning': '#ff9f1c',
            'panel': '#0f3460'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # State
        self.selected_mode = tk.StringVar(value="daily")
        self.no_ai = tk.BooleanVar(value=False)
        self.is_running = False
        self.process = None
        
        # Configure styles
        self._configure_styles()
        
        # Build UI
        self._build_ui()
        
        # Refresh results on start
        self._refresh_results()

    def _configure_styles(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure('Dark.TFrame', background=self.colors['bg'])
        style.configure('Panel.TFrame', background=self.colors['panel'])
        style.configure('Light.TFrame', background=self.colors['bg_light'])
        
        # Label styles
        style.configure('Title.TLabel', 
                       background=self.colors['bg'],
                       foreground=self.colors['gold'],
                       font=('Consolas', 24, 'bold'))
        style.configure('Subtitle.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text_dim'],
                       font=('Segoe UI', 10))
        style.configure('Dark.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        style.configure('Panel.TLabel',
                       background=self.colors['panel'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        style.configure('Gold.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['gold'],
                       font=('Segoe UI', 11, 'bold'))
        
        # Button styles
        style.configure('Action.TButton',
                       background=self.colors['accent'],
                       foreground='white',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 10))
        style.map('Action.TButton',
                 background=[('active', '#ff6b6b'), ('disabled', '#555')])
        
        style.configure('Secondary.TButton',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 9),
                       padding=(10, 5))
        
        # Radiobutton styles
        style.configure('Mode.TRadiobutton',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 11),
                       padding=10)
        style.map('Mode.TRadiobutton',
                 background=[('selected', self.colors['bg_light'])])
        
        # Checkbutton styles
        style.configure('Dark.TCheckbutton',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        
        # Notebook styles
        style.configure('Dark.TNotebook',
                       background=self.colors['bg'],
                       borderwidth=0)
        style.configure('Dark.TNotebook.Tab',
                       background=self.colors['bg_light'],
                       foreground=self.colors['text'],
                       padding=(15, 8),
                       font=('Segoe UI', 10))
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', self.colors['panel'])],
                 foreground=[('selected', self.colors['gold'])])

    def _build_ui(self):
        """Build the main UI layout."""
        # Main container
        main = ttk.Frame(self.root, style='Dark.TFrame')
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._build_header(main)
        
        # Content area with two columns
        content = ttk.Frame(main, style='Dark.TFrame')
        content.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Left panel - Mode selection and controls
        left_panel = ttk.Frame(content, style='Dark.TFrame', width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_panel.pack_propagate(False)
        
        self._build_mode_selector(left_panel)
        self._build_controls(left_panel)
        self._build_progress_panel(left_panel)
        
        # Right panel - Results dashboard
        right_panel = ttk.Frame(content, style='Dark.TFrame')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._build_results_dashboard(right_panel)

    def _build_header(self, parent):
        """Build the header section."""
        header = ttk.Frame(parent, style='Dark.TFrame')
        header.pack(fill=tk.X)
        
        # ASCII art title (simplified for GUI)
        title_frame = ttk.Frame(header, style='Dark.TFrame')
        title_frame.pack(side=tk.LEFT)
        
        title = ttk.Label(title_frame, text="[ GOLD STANDARD ]", style='Title.TLabel')
        title.pack(anchor=tk.W)
        
        subtitle = ttk.Label(title_frame, 
                            text="Precious Metals Intelligence Dashboard",
                            style='Subtitle.TLabel')
        subtitle.pack(anchor=tk.W)
        
        # Status indicator
        self.status_frame = ttk.Frame(header, style='Dark.TFrame')
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_label = ttk.Label(self.status_frame, 
                                      text="[*] Ready",
                                      style='Dark.TLabel')
        self.status_label.pack()

    def _build_mode_selector(self, parent):
        """Build the mode selection panel."""
        # Section title
        section = ttk.Frame(parent, style='Dark.TFrame')
        section.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(section, text="SELECT MODE", style='Gold.TLabel').pack(anchor=tk.W)
        
        # Mode options
        modes = [
            ("daily", "Daily Journal", "Full daily analysis with AI-generated thesis"),
            ("weekly", "Weekly Rundown", "Short-horizon tactical weekend overview"),
            ("monthly", "Monthly Report", "Monthly performance tables + AI outlook"),
            ("yearly", "Yearly Report", "Year-over-year analysis + AI forecast"),
        ]
        
        for mode_id, mode_name, mode_desc in modes:
            frame = ttk.Frame(parent, style='Dark.TFrame')
            frame.pack(fill=tk.X, pady=2)
            
            rb = ttk.Radiobutton(
                frame,
                text=mode_name,
                value=mode_id,
                variable=self.selected_mode,
                style='Mode.TRadiobutton'
            )
            rb.pack(anchor=tk.W)
            
            desc = ttk.Label(frame, text=f"  {mode_desc}", style='Subtitle.TLabel')
            desc.pack(anchor=tk.W, padx=(25, 0))

    def _build_controls(self, parent):
        """Build the control buttons panel."""
        controls = ttk.Frame(parent, style='Dark.TFrame')
        controls.pack(fill=tk.X, pady=20)
        
        # Options
        options_frame = ttk.Frame(controls, style='Dark.TFrame')
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Checkbutton(
            options_frame,
            text="No AI Mode (skip Gemini)",
            variable=self.no_ai,
            style='Dark.TCheckbutton'
        ).pack(anchor=tk.W)
        
        # Run button
        self.run_btn = ttk.Button(
            controls,
            text=">>  RUN ANALYSIS",
            style='Action.TButton',
            command=self._run_analysis
        )
        self.run_btn.pack(fill=tk.X)
        
        # Secondary buttons
        btn_frame = ttk.Frame(controls, style='Dark.TFrame')
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            btn_frame,
            text="Open Output Folder",
            style='Secondary.TButton',
            command=self._open_output_folder
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="Refresh Results",
            style='Secondary.TButton',
            command=self._refresh_results
        ).pack(side=tk.LEFT)

    def _build_progress_panel(self, parent):
        """Build the progress/log panel."""
        progress_frame = ttk.Frame(parent, style='Dark.TFrame')
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        ttk.Label(progress_frame, text="CONSOLE OUTPUT", style='Gold.TLabel').pack(anchor=tk.W)
        
        # Scrolled text for logs
        self.log_text = scrolledtext.ScrolledText(
            progress_frame,
            height=12,
            bg=self.colors['bg_light'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.log_text.insert(tk.END, "Ready to run analysis...\n")
        self.log_text.config(state=tk.DISABLED)

    def _build_results_dashboard(self, parent):
        """Build the results dashboard with tabs."""
        # Section title
        header = ttk.Frame(parent, style='Dark.TFrame')
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="RESULTS DASHBOARD", style='Gold.TLabel').pack(side=tk.LEFT)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(parent, style='Dark.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Charts tab (first)
        charts_frame = ttk.Frame(self.notebook, style='Panel.TFrame')
        self.notebook.add(charts_frame, text="  Charts  ")
        self._build_charts_tab(charts_frame)
        
        # Reports tab
        reports_frame = ttk.Frame(self.notebook, style='Panel.TFrame')
        self.notebook.add(reports_frame, text="  Reports  ")
        self._build_reports_tab(reports_frame)
        
        # Preview tab
        preview_frame = ttk.Frame(self.notebook, style='Panel.TFrame')
        self.notebook.add(preview_frame, text="  Preview  ")
        self._build_preview_tab(preview_frame)
        
        # Journal tab (persistent Cortex memory)
        journal_frame = ttk.Frame(self.notebook, style='Panel.TFrame')
        self.notebook.add(journal_frame, text="  Journal  ")
        self._build_journal_tab(journal_frame)

    def _build_reports_tab(self, parent):
        """Build the reports list tab."""
        # Treeview for reports
        columns = ('name', 'date', 'size', 'path')
        self.reports_tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        self.reports_tree.heading('name', text='Report Name')
        self.reports_tree.heading('date', text='Generated')
        self.reports_tree.heading('size', text='Size')
        self.reports_tree.heading('path', text='Path')
        
        self.reports_tree.column('name', width=250)
        self.reports_tree.column('date', width=150)
        self.reports_tree.column('size', width=80)
        self.reports_tree.column('path', width=300)
        
        self.reports_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Double-click to open
        self.reports_tree.bind('<Double-1>', self._open_selected_report)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=scrollbar.set)

    def _build_charts_tab(self, parent):
        """Build the charts gallery tab."""
        # Canvas with scrollbar for chart thumbnails
        canvas_frame = ttk.Frame(parent, style='Panel.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.charts_canvas = tk.Canvas(canvas_frame, bg=self.colors['panel'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.charts_canvas.yview)
        
        self.charts_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.charts_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Inner frame for charts
        self.charts_inner = ttk.Frame(self.charts_canvas, style='Panel.TFrame')
        self.charts_canvas.create_window((0, 0), window=self.charts_inner, anchor=tk.NW)
        
        self.charts_inner.bind('<Configure>', 
                               lambda e: self.charts_canvas.configure(scrollregion=self.charts_canvas.bbox("all")))

    def _build_preview_tab(self, parent):
        """Build the report preview tab."""
        # Report content viewer
        self.preview_text = scrolledtext.ScrolledText(
            parent,
            bg=self.colors['bg_light'],
            fg=self.colors['text'],
            font=('Consolas', 10),
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.preview_text.insert(tk.END, "Select a report from the Reports tab to preview its contents.")

    def _build_journal_tab(self, parent):
        """Build the Journal tab with persistent Cortex memory display."""
        # Header with refresh button
        header = ttk.Frame(parent, style='Panel.TFrame')
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(header, text="CORTEX MEMORY", style='Gold.TLabel').pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Refresh",
            style='Secondary.TButton',
            command=self._refresh_journal
        ).pack(side=tk.RIGHT)
        
        # Main journal content area - two panels
        content = ttk.Frame(parent, style='Panel.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side: Stats panel (narrower)
        stats_frame = ttk.Frame(content, style='Light.TFrame', width=250)
        stats_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        stats_frame.pack_propagate(False)
        
        # Stats header
        ttk.Label(stats_frame, text="Performance Stats", 
                 font=('Segoe UI', 11, 'bold'),
                 background=self.colors['bg_light'],
                 foreground=self.colors['gold']).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Stats content
        self.stats_text = tk.Text(
            stats_frame,
            bg=self.colors['bg_light'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            relief=tk.FLAT,
            padx=10,
            pady=10,
            wrap=tk.WORD
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right side: Latest Journal Report
        journal_frame = ttk.Frame(content, style='Light.TFrame')
        journal_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Journal header
        ttk.Label(journal_frame, text="Latest Daily Journal", 
                 font=('Segoe UI', 11, 'bold'),
                 background=self.colors['bg_light'],
                 foreground=self.colors['gold']).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Journal content (the actual report)
        self.journal_text = scrolledtext.ScrolledText(
            journal_frame,
            bg=self.colors['bg_light'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            relief=tk.FLAT,
            padx=10,
            pady=10,
            wrap=tk.WORD
        )
        self.journal_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Load initial journal data
        self._refresh_journal()

    def _get_latest_journal_file(self):
        """Find the most recent Journal markdown file."""
        journal_files = list(OUTPUT_DIR.glob("Journal_*.md"))
        if not journal_files:
            return None
        # Sort by modification time, most recent first
        journal_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return journal_files[0]

    def _refresh_journal(self):
        """Refresh the journal tab with current Cortex memory and latest journal."""
        # Load Cortex memory for stats
        try:
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
            else:
                memory = {}
        except Exception as e:
            memory = {'error': str(e)}
        
        # Update stats panel
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        
        stats_lines = []
        stats_lines.append("CORTEX MEMORY STATS")
        stats_lines.append("=" * 24)
        stats_lines.append("")
        
        # Current bias
        last_bias = memory.get('last_bias', 'N/A')
        stats_lines.append(f"Current Bias: {last_bias}")
        stats_lines.append("")
        
        # Last price
        last_price = memory.get('last_price', 'N/A')
        if last_price != 'N/A':
            stats_lines.append(f"Last Price: ${last_price:.2f}")
        else:
            stats_lines.append(f"Last Price: {last_price}")
        stats_lines.append("")
        
        # Win/Loss record
        wins = memory.get('wins', 0)
        losses = memory.get('losses', 0)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        stats_lines.append(f"W/L: {wins}W / {losses}L")
        stats_lines.append(f"Win Rate: {win_rate:.1f}%")
        stats_lines.append("")
        
        # Streaks
        current_streak = memory.get('current_streak', 0)
        streak_type = memory.get('streak_type', 'none')
        stats_lines.append(f"Streak: {abs(current_streak)} ({streak_type})")
        stats_lines.append("")
        
        # Last updated
        last_run = memory.get('last_run', 'Never')
        stats_lines.append(f"Last Run: {last_run}")
        stats_lines.append("")
        stats_lines.append("=" * 24)
        
        # Add prediction history summary
        history = memory.get('history', [])
        if history:
            stats_lines.append("")
            stats_lines.append("RECENT PREDICTIONS")
            stats_lines.append("-" * 24)
            for entry in reversed(history[-5:]):
                entry_date = entry.get('date', '?')
                entry_bias = entry.get('bias', '?')
                entry_result = entry.get('result', 'pending')
                result_mark = "[OK]" if entry_result == 'correct' else "[X]" if entry_result == 'incorrect' else "[?]"
                stats_lines.append(f"{entry_date}: {entry_bias} {result_mark}")
        
        self.stats_text.insert(tk.END, "\n".join(stats_lines))
        self.stats_text.config(state=tk.DISABLED)
        
        # Update journal content panel with actual journal file
        self.journal_text.config(state=tk.NORMAL)
        self.journal_text.delete(1.0, tk.END)
        
        journal_file = self._get_latest_journal_file()
        if journal_file:
            try:
                with open(journal_file, 'r', encoding='utf-8') as f:
                    journal_content = f.read()
                self.journal_text.insert(tk.END, f"File: {journal_file.name}\n")
                self.journal_text.insert(tk.END, "=" * 50 + "\n\n")
                self.journal_text.insert(tk.END, journal_content)
            except Exception as e:
                self.journal_text.insert(tk.END, f"Error reading journal: {e}")
        else:
            self.journal_text.insert(tk.END, "No journal files found.\n\n")
            self.journal_text.insert(tk.END, "Run a 'Daily' analysis to generate your first journal report.")
        
        self.journal_text.config(state=tk.DISABLED)

    def _log(self, message: str):
        """Add a message to the log panel."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_status(self, text: str, color: str = None):
        """Update the status indicator."""
        self.status_label.config(text=text)
        if color:
            # Update style dynamically
            pass

    def _run_analysis(self):
        """Run the selected analysis mode."""
        if self.is_running:
            messagebox.showwarning("Already Running", "An analysis is already in progress.")
            return
        
        mode = self.selected_mode.get()
        no_ai = self.no_ai.get()
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self._log(f"Starting {mode.upper()} analysis...")
        if no_ai:
            self._log("(No AI mode - Gemini will be skipped)")
        self._log("-" * 40)
        
        self._set_status("[~] Running...", self.colors['warning'])
        self.run_btn.config(state=tk.DISABLED)
        self.is_running = True
        
        # Run in background thread
        thread = threading.Thread(target=self._run_subprocess, args=(mode, no_ai))
        thread.daemon = True
        thread.start()

    def _run_subprocess(self, mode: str, no_ai: bool):
        """Run the analysis subprocess."""
        try:
            cmd = [sys.executable, str(PROJECT_ROOT / "run.py"), "--mode", mode]
            if no_ai:
                cmd.append("--no-ai")
            
            # Use UTF-8 encoding and handle errors gracefully
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
            
            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    # Schedule UI update on main thread
                    self.root.after(0, self._log, line.rstrip())
            
            self.process.wait()
            
            # Done
            self.root.after(0, self._analysis_complete, self.process.returncode)
            
        except Exception as e:
            self.root.after(0, self._log, f"Error: {e}")
            self.root.after(0, self._analysis_complete, -1)

    def _analysis_complete(self, return_code: int):
        """Handle analysis completion."""
        self.is_running = False
        self.run_btn.config(state=tk.NORMAL)
        
        if return_code == 0:
            self._log("-" * 40)
            self._log("[OK] Analysis completed successfully!")
            self._set_status("[+] Complete", self.colors['success'])
        else:
            self._log("-" * 40)
            self._log(f"[X] Analysis finished with code {return_code}")
            self._set_status("[!] Error", self.colors['accent'])
        
        # Refresh results
        self._refresh_results()

    def _refresh_results(self):
        """Refresh the results dashboard."""
        self._refresh_reports()
        self._refresh_charts()
        self._refresh_journal()

    def _refresh_reports(self):
        """Refresh the reports list."""
        # Clear existing
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)
        
        # Find all reports
        report_dirs = [OUTPUT_DIR, REPORTS_DIR]
        
        for report_dir in report_dirs:
            if not report_dir.exists():
                continue
            
            for file in report_dir.glob("*.md"):
                try:
                    stat = file.stat()
                    size_kb = stat.st_size / 1024
                    mtime = date.fromtimestamp(stat.st_mtime).isoformat()
                    
                    self.reports_tree.insert('', tk.END, values=(
                        file.name,
                        mtime,
                        f"{size_kb:.1f} KB",
                        str(file)
                    ))
                except Exception:
                    pass

    def _refresh_charts(self):
        """Refresh the charts gallery."""
        # Clear existing
        for widget in self.charts_inner.winfo_children():
            widget.destroy()
        
        if not CHARTS_DIR.exists():
            ttk.Label(self.charts_inner, text="No charts found", style='Panel.TLabel').pack(pady=20)
            return
        
        # Find chart files
        chart_files = list(CHARTS_DIR.glob("*.png"))
        
        if not chart_files:
            ttk.Label(self.charts_inner, text="No charts found", style='Panel.TLabel').pack(pady=20)
            return
        
        # Create grid of chart cards
        row_frame = None
        for i, chart_file in enumerate(chart_files):
            if i % 3 == 0:
                row_frame = ttk.Frame(self.charts_inner, style='Panel.TFrame')
                row_frame.pack(fill=tk.X, pady=5)
            
            card = ttk.Frame(row_frame, style='Light.TFrame')
            card.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Chart name
            name_label = ttk.Label(card, text=chart_file.stem, style='Dark.TLabel')
            name_label.pack(pady=(5, 2))
            
            # Size info
            try:
                size_kb = chart_file.stat().st_size / 1024
                size_label = ttk.Label(card, text=f"{size_kb:.1f} KB", style='Subtitle.TLabel')
                size_label.pack()
            except:
                pass
            
            # Open button
            btn = ttk.Button(
                card,
                text="View",
                style='Secondary.TButton',
                command=lambda f=chart_file: self._open_file(f)
            )
            btn.pack(pady=5)

    def _open_selected_report(self, event):
        """Open the selected report from treeview."""
        selection = self.reports_tree.selection()
        if not selection:
            return
        
        item = self.reports_tree.item(selection[0])
        path = item['values'][3]
        
        # Show preview
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, content)
            self.preview_text.config(state=tk.DISABLED)
            
            # Switch to preview tab
            self.notebook.select(2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")

    def _open_file(self, path: Path):
        """Open a file with the default application."""
        try:
            if sys.platform == 'win32':
                os.startfile(str(path))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        try:
            if sys.platform == 'win32':
                os.startfile(str(OUTPUT_DIR))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(OUTPUT_DIR)])
            else:
                subprocess.run(['xdg-open', str(OUTPUT_DIR)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")


def main():
    """Main entry point for GUI."""
    root = tk.Tk()
    
    # Set icon if available
    try:
        # Could add an icon file later
        pass
    except:
        pass
    
    app = GoldStandardGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
