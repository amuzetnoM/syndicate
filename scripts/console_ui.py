"""Console UI helpers: Rich-based logging and progress UI for the executor.

Provides:
- setup_console_logging(logger, log_file=None, verbose=False): attach a Rich-based handler
- get_console(): returns a singleton Rich Console
- progress_context(total, description): a context manager yielding a Rich Progress instance

This module falls back to simple prints if 'rich' is not available.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

try:
    from rich.align import Align
    from rich.columns import Columns
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False


_CONSOLE: Optional["Console"] = None


def get_console() -> "Console":
    global _CONSOLE
    if _CONSOLE is None:
        if RICH_AVAILABLE:
            _CONSOLE = Console()
        else:
            # Minimal stub-like behavior for Console
            class SimpleConsole:
                def print(self, *args, **kwargs):
                    print(*args)

            _CONSOLE = SimpleConsole()
    return _CONSOLE


def render_system_banner(title: str = "Syndicate", subtitle: str = "Precious Metals Intelligence"):
    """Render a consistent system banner for terminal startup using Rich when available."""
    console = get_console()
    if RICH_AVAILABLE:
        from rich.panel import Panel
        from rich.text import Text

        title_text = Text(title, style="bold gold1")
        subtitle_text = Text(subtitle, style="dim")
        # Build a small renderable combining title and subtitle
        header = Text.assemble(title_text, "\n", subtitle_text)
        console.print(Panel(header, style="", expand=True))
    else:
        console.print(f"=== {title} ===\n{subtitle}\n")


MODULE_TAGS = {
    "GoldStandard": ("GS", "yellow"),
    "DatabaseManager": ("DB", "magenta"),
    "executor_daemon": ("EX", "cyan"),
    "genai_compat": ("LLM", "cyan"),
}


def get_compact_message(level: str, module: Optional[str], msg: str) -> str:
    """Return a compact, styled log message for console display.

    Compact format: [level_symbol] [MOD] message
    Module names are mapped to short tokens and colored for quick scanning.
    """
    if RICH_AVAILABLE:
        prefix = {
            "INFO": "[green]✔[/green]",
            "DEBUG": "[cyan]•[/cyan]",
            "WARNING": "[yellow]⚠[/yellow]",
            "ERROR": "[red]✖[/red]",
            "CRITICAL": "[white on red]‼[/white on red]",
        }.get(level, "")

        modpart = ""
        if module:
            tag, color = MODULE_TAGS.get(module, (module.split('.')[-1][:3].upper(), "white"))
            modpart = f" [{tag}]" if tag else ""
            return f"{prefix} [bold {color}]{modpart}[/bold {color}] {msg}"

        return f"{prefix} {msg}"
    else:
        modpart = f" [{module}]" if module else ""
        return f"{level}: {msg}{modpart}"


class RichRightTimestampHandler(logging.Handler):
    """Logging handler that renders messages with a timestamp aligned to the right.

    Uses Rich to color level names and places the timestamp in a right-aligned column.
    Falls back to standard logging if Rich is not available.
    """

    LEVEL_STYLES = {
        "DEBUG": "dim",
        "INFO": "bold green",
        "WARNING": "bold yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
    }

    def __init__(self, verbose: bool = False):
        super().__init__()
        self.console = get_console()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Prefer using the raw record message and the logger name to build a compact line
            msg = record.getMessage()
            ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
            level = record.levelname
            module = record.name
            if RICH_AVAILABLE:
                from rich.text import Text

                style = self.LEVEL_STYLES.get(level, "")
                # Build compact left-hand side with level symbol + short module tag + message
                left = Text()

                # Level symbol
                prefix = {
                    "INFO": "✔",
                    "DEBUG": "•",
                    "WARNING": "⚠",
                    "ERROR": "✖",
                    "CRITICAL": "‼",
                }.get(level, "")
                if prefix:
                    left.append(f"{prefix} ")
                # Module tag (short, colored)
                tag, color = MODULE_TAGS.get(module, (module.split('.')[-1][:3].upper(), "white"))
                left.append(f"[{tag}] ", style=f"bold {color}")

                # Message body
                left.append(msg, style=style)

                right = Align(Text(ts, style="dim"), align="right")
                # Columns with expand=True will attempt to place timestamp at the far right
                self.console.print(Columns([left, right], expand=True))
            else:
                # Fallback: simple print with timestamp on the right separated by '|' for clarity
                print(f"{level}: {msg} | {ts}")
        except Exception:
            self.handleError(record)


def setup_console_logging(logger: logging.Logger, log_file: Optional[str] = None, verbose: bool = False) -> None:
    """Configure the provided logger to use the Rich right-timestamp handler and optional file logging."""
    # Remove existing handlers to avoid duplicate logs
    for h in list(logger.handlers):
        logger.removeHandler(h)

    console_handler = RichRightTimestampHandler(verbose=verbose)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

    # Keep a simple logger name for other modules to reuse
    logger.propagate = False

    # File handler (rotating) keeps a simple format with timestamp at end
    if log_file:
        from logging.handlers import RotatingFileHandler

        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3)
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(levelname)-8s | %(name)s | %(message)s | %(asctime)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fmt)
        logger.addHandler(fh)


def progress_context(total: int, description: str = "Processing"):
    """Return a context manager for a progress bar. Uses Rich Progress when available, otherwise a simple tqdm-like fallback.

    Usage:
        with progress_context(len(tasks), "Tasks") as progress:
            task = progress.add_task(description, total=len(tasks))
            for item in tasks:
                ...
                progress.advance(task)
    """
    if RICH_AVAILABLE:
        progress = Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=True,
        )

        class _Ctx:
            def __enter__(self):
                progress.start()
                return progress

            def __exit__(self, exc_type, exc, tb):
                progress.stop()

        return _Ctx()

    else:
        # Minimal fallback context that yields a dummy object with add_task/advance methods
        class SimpleProgress:
            def add_task(self, desc, total=0):
                print(f"{desc}: 0/{total}")
                return 1

            def advance(self, task_id, step=1):
                pass

        class _Ctx:
            def __enter__(self):
                return SimpleProgress()

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()
