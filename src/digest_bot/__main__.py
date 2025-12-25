#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - CLI Entry Point
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Command-line interface for the Digest Bot.

Features:
- Rich console output with progress
- Structured logging (console + rotating file)
- Dry-run mode for testing
- One-shot and daemon modes
"""

import logging
import sys
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import click

from .config import Config, get_config
from .file_gate import FileGate
from .summarizer import Summarizer
from .writer import DigestWriter

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════


def setup_logging(
    verbose: bool = False,
    log_file: Optional[Path] = None,
    quiet: bool = False,
) -> None:
    """
    Configure logging for the application.

    Args:
        verbose: Enable DEBUG level
        log_file: Path to log file
        quiet: Suppress console output
    """
    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Clear existing handlers
    root.handlers.clear()

    # Format
    fmt = "%(asctime)s [%(levelname)-.1s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # Console handler
    if not quiet:
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(logging.DEBUG if verbose else logging.INFO)
        console.setFormatter(formatter)
        root.addHandler(console)

    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)

        file_fmt = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
        file_handler.setFormatter(logging.Formatter(file_fmt))
        root.addHandler(file_handler)


# ══════════════════════════════════════════════════════════════════════════════
# CONSOLE OUTPUT HELPERS
# ══════════════════════════════════════════════════════════════════════════════


class Console:
    """Simple console output with status indicators."""

    # ANSI colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    @classmethod
    def supports_color(cls) -> bool:
        """Check if terminal supports color."""
        if not sys.stderr.isatty():
            return False
        # Windows terminal support
        if sys.platform == "win32":
            try:
                import os

                os.system("")  # Enable ANSI on Windows
                return True
            except Exception:
                return False
        return True

    @classmethod
    def _color(cls, text: str, color: str) -> str:
        if not cls.supports_color():
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def _safe_print(cls, text: str) -> None:
        """Print text with fallback for encoding issues."""
        try:
            print(text)
        except UnicodeEncodeError:
            # Fall back to ASCII-safe version
            safe_text = text.encode("ascii", errors="replace").decode("ascii")
            print(safe_text)

    @classmethod
    def header(cls, text: str) -> None:
        """Print header."""
        line = "=" * 60  # Use ASCII = instead of Unicode ═
        cls._safe_print(cls._color(line, cls.CYAN))
        cls._safe_print(cls._color(f"  {text}", cls.BOLD + cls.CYAN))
        cls._safe_print(cls._color(line, cls.CYAN))

    @classmethod
    def step(cls, text: str) -> None:
        """Print step indicator."""
        cls._safe_print(f"  {cls._color('->', cls.BLUE)} {text}")  # Use -> instead of →

    @classmethod
    def success(cls, text: str) -> None:
        """Print success message."""
        cls._safe_print(f"  {cls._color('[OK]', cls.GREEN)} {text}")

    @classmethod
    def warning(cls, text: str) -> None:
        """Print warning message."""
        cls._safe_print(f"  {cls._color('[!]', cls.YELLOW)} {text}")

    @classmethod
    def error(cls, text: str) -> None:
        """Print error message."""
        cls._safe_print(f"  {cls._color('[X]', cls.RED)} {text}")

    @classmethod
    def info(cls, text: str) -> None:
        """Print info message."""
        cls._safe_print(f"  {cls._color('*', cls.DIM)} {text}")

    @classmethod
    def divider(cls) -> None:
        """Print divider line."""
        cls._safe_print(cls._color("  " + "-" * 56, cls.DIM))


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════════════


def run_digest_pipeline(
    config: Config,
    target_date: Optional[date] = None,
    dry_run: bool = False,
    wait: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> int:
    """
    Execute the digest generation pipeline.

    Args:
        config: Configuration object
        target_date: Target date for digest
        dry_run: Don't write output
        wait: Wait for inputs
        overwrite: Overwrite existing digest
        verbose: Verbose output

    Returns:
        Exit code (0=success, 1=error)
    """
    target = target_date or date.today()

    Console.header(f"Daily Digest - {target.isoformat()}")
    print()

    # Initialize components
    Console.step("Initializing components...")

    gate = FileGate(config)
    writer = DigestWriter(config)

    # Check if digest exists
    if writer.exists(target) and not overwrite and not dry_run:
        Console.warning(f"Digest already exists for {target}")
        Console.info("Use --overwrite to regenerate")
        return 0

    # Check input readiness
    Console.step("Checking input documents...")

    if wait:
        Console.info("Waiting for all inputs (Ctrl+C to cancel)...")
        status = gate.wait_for_inputs(target)
    else:
        status = gate.check_all_gates(target)

    # Report status
    Console.divider()

    if status.journal_ready:
        Console.success(f"Journal: {status.journal_doc.source} ({len(status.journal_doc.content)} chars)")
    else:
        Console.error("Journal: NOT FOUND")

    if status.premarket_ready:
        Console.success(f"Pre-market: {status.premarket_doc.source} ({len(status.premarket_doc.content)} chars)")
    else:
        Console.error("Pre-market: NOT FOUND")

    if status.weekly_ready:
        Console.success(f"Weekly: {status.weekly_doc.source} ({len(status.weekly_doc.content)} chars)")
    else:
        Console.warning("Weekly: NOT FOUND (will use fallback)")

    Console.divider()

    # Check if we can proceed
    if not status.all_inputs_ready:
        Console.error("Cannot generate digest: missing required inputs")

        if not wait:
            Console.info("Use --wait to wait for inputs")

        return 1

    # Generate digest
    Console.step("Generating digest with LLM...")

    with Summarizer(config) as summarizer:
        result = summarizer.generate(status, target)

        if not result.success:
            Console.error(f"Generation failed: {result.error}")

            # Try fallback
            Console.step("Attempting fallback generation...")
            result = summarizer.generate_fallback(status, target)

            if not result.success:
                Console.error(f"Fallback also failed: {result.error}")
                return 1

            Console.warning("Used fallback prompt")

    # Report generation stats
    if result.metadata:
        meta = result.metadata
        Console.success(f"Generated: {meta.get('tokens_used', '?')} tokens in {meta.get('generation_time', 0):.2f}s")
        Console.info(f"Provider: {meta.get('provider', '?')} / {meta.get('model', '?')}")

    Console.divider()

    # Write output
    if dry_run:
        Console.warning("DRY RUN — Output not saved")
        print()
        print("=" * 60)
        print(writer.write_dry_run(result, target))
        print("=" * 60)
        return 0

    Console.step("Writing digest file...")

    write_result = writer.write(
        result,
        target,
        overwrite=overwrite,
        backup=True,
    )

    if not write_result.success:
        Console.error(f"Write failed: {write_result.error}")
        return 1

    Console.success(f"Saved: {write_result.path}")

    if write_result.backup_path:
        Console.info(f"Backup: {write_result.backup_path}")

    print()
    Console.success("Digest generation complete!")

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# CLI COMMANDS
# ══════════════════════════════════════════════════════════════════════════════


@click.group(invoke_without_command=True)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose (debug) output",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress console output",
)
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    help="Path to log file",
)
@click.pass_context
def main(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    log_file: Optional[Path],
) -> None:
    """
    Syndicate Digest Bot

    Generates daily market intelligence digests by synthesizing
    pre-market plans, daily journals, and weekly reports using
    local LLM inference.
    """
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Default log file if not specified
    if log_file is None:
        config = get_config()
        log_file = config.paths.log_file

    setup_logging(verbose, log_file, quiet)

    # If no subcommand, run default
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@main.command()
@click.option(
    "--date",
    "-d",
    "target_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Target date for digest (default: today)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Don't write output, just print",
)
@click.option(
    "--wait",
    "-w",
    is_flag=True,
    help="Wait for all inputs to be ready",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing digest",
)
@click.pass_context
def run(
    ctx: click.Context,
    target_date: Optional[datetime],
    dry_run: bool,
    wait: bool,
    overwrite: bool,
) -> None:
    """
    Generate daily digest (default command).

    Examples:

        digest-bot run

        digest-bot run --date 2025-01-15

        digest-bot run --dry-run

        digest-bot run --wait
    """
    config = get_config()

    target = target_date.date() if target_date else date.today()

    exit_code = run_digest_pipeline(
        config=config,
        target_date=target,
        dry_run=dry_run,
        wait=wait,
        overwrite=overwrite,
        verbose=ctx.obj.get("verbose", False),
    )

    sys.exit(exit_code)


@main.command()
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["llamacpp", "ollama"]),
    help="Check specific provider",
)
@click.pass_context
def check(
    ctx: click.Context,
    provider: Optional[str],
) -> None:
    """
    Check configuration and environment.

    Validates:
    - Configuration file
    - LLM provider availability
    - Input/output directories
    """
    config = get_config()

    Console.header("Configuration Check")
    print()

    # Paths
    Console.step("Checking paths...")

    if config.paths.output_dir.exists():
        Console.success(f"Output dir: {config.paths.output_dir}")
    else:
        Console.warning(f"Output dir missing: {config.paths.output_dir}")

    if config.paths.database_path.exists():
        Console.success(f"Database: {config.paths.database_path}")
    else:
        Console.warning(f"Database missing: {config.paths.database_path}")

    Console.divider()

    # LLM
    Console.step(f"Checking LLM provider: {config.llm.provider}")

    if config.llm.provider == "local":
        model_path = Path(config.llm.local_model_path)
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            Console.success(f"Model: {model_path.name} ({size_mb:.0f} MB)")
        else:
            Console.error(f"Model not found: {model_path}")

    elif config.llm.provider == "ollama":
        Console.info(f"Ollama host: {config.llm.ollama_host}")
        Console.info(f"Model: {config.llm.ollama_model}")

        # Check Ollama server health and models
        try:
            from .llm.ollama import OllamaProvider

            oll = OllamaProvider(host=config.llm.ollama_host, model=config.llm.ollama_model)
            if oll.health_check():
                Console.success("Ollama server: reachable")
                models = oll.list_models()
                if models:
                    Console.info(f"Available models: {', '.join(models[:5])}")
                else:
                    Console.info("No models reported by Ollama (server may be starting or no models pulled)")
            else:
                Console.warning("Ollama server: unreachable or not responding")
        except Exception as e:
            Console.error(f"Ollama check failed: {e}")

    Console.divider()

    # Gate check
    Console.step("Checking today's inputs...")

    gate = FileGate(config)
    status = gate.check_all_gates()

    if status.journal_ready:
        Console.success("Journal: available")
    else:
        Console.warning("Journal: not found")

    if status.premarket_ready:
        Console.success("Pre-market: available")
    else:
        Console.warning("Pre-market: not found")

    if status.weekly_ready:
        Console.success("Weekly: available")
    else:
        Console.warning("Weekly: not found")

    print()
    Console.success("Configuration check complete")


@main.command()
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Number of digests to list",
)
def history(limit: int) -> None:
    """
    List recent digests.
    """
    config = get_config()
    writer = DigestWriter(config)

    Console.header("Recent Digests")
    print()

    digests = writer.list_digests(limit)

    if not digests:
        Console.info("No digests found")
        return

    for path in digests:
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        size_kb = stat.st_size / 1024

        Console.info(f"{path.stem}  {mtime.strftime('%Y-%m-%d %H:%M')}  {size_kb:.1f} KB")

    print()
    Console.info(f"Showing {len(digests)} of {limit} max")


@main.command()
@click.option(
    "--keep",
    "-k",
    type=int,
    default=30,
    help="Number of recent digests to keep",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Don't delete, just show what would be removed",
)
@click.confirmation_option(
    prompt="Are you sure you want to cleanup old digests?",
)
def cleanup(keep: int, dry_run: bool) -> None:
    """
    Remove old digest files.
    """
    config = get_config()
    writer = DigestWriter(config)

    Console.header("Cleanup Old Digests")
    print()

    deleted = writer.cleanup_old_digests(keep, dry_run)

    if not deleted:
        Console.success("No digests to clean up")
    elif dry_run:
        Console.warning(f"Would delete {len(deleted)} digests")
    else:
        Console.success(f"Deleted {len(deleted)} old digests")


@main.command()
@click.pass_context
def discord(ctx: click.Context) -> None:
    """
    Run the Discord bot with self-healing capabilities.

    The bot will:
    - Auto-connect and reconnect on failures
    - Auto-create channels/roles if missing
    - Post daily digests automatically
    - Respond to slash commands

    Required: Set DISCORD_BOT_TOKEN environment variable.
    """
    Console.header("Discord Bot")
    print()

    try:
        from .discord import DigestDiscordBot
    except ImportError:
        Console.error("discord.py is not installed")
        Console.info("Install with: pip install discord.py")
        sys.exit(1)

    config = get_config()

    if not config.discord.bot_token:
        Console.error("DISCORD_BOT_TOKEN environment variable not set")
        Console.info("Set your bot token in .env or environment")
        sys.exit(1)

    Console.success("Configuration loaded")
    Console.info(f"Guild ID: {config.discord.guild_id or 'Auto-detect'}")

    print()
    Console.step("Starting Discord bot with self-healing...")
    Console.info("Press Ctrl+C to stop")
    print()

    bot = DigestDiscordBot(config)

    try:
        bot.run_forever()
    except KeyboardInterrupt:
        Console.warning("Shutdown requested")
    except Exception as e:
        Console.error(f"Bot crashed: {e}")
        sys.exit(1)

    Console.success("Bot stopped gracefully")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
