#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Gold Standard - Task Executor Daemon
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Standalone Task Executor Daemon

A production-hardened task execution service that runs independently of the
main analysis loop. Designed for guaranteed task completion and orphan recovery.

EXECUTION MODES:
    1. Systemd service (recommended for production)
    2. Subprocess spawn from main daemon
    3. Direct CLI execution for debugging

FEATURES:
    - Continuous polling for ready tasks
    - Orphan recovery on startup
    - Graceful shutdown with task completion
    - Signal handling (SIGTERM, SIGINT, SIGHUP)
    - Worker heartbeat tracking
    - Quota-aware retry with exponential backoff
    - Health check endpoint (optional)

USAGE:
    # Run as daemon (continuous)
    python executor_daemon.py --daemon

    # Run once and exit (drain queue)
    python executor_daemon.py --once

    # Recover orphans only
    python executor_daemon.py --recover-orphans

    # Check health
    python executor_daemon.py --health
"""

import argparse
import atexit
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

WORKER_ID = f"executor-{socket.gethostname()}-{os.getpid()}"
POLL_INTERVAL_SECONDS = 30
ORPHAN_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
ORPHAN_TIMEOUT_HOURS = 1
HEARTBEAT_INTERVAL_SECONDS = 60
MAX_CONSECUTIVE_ERRORS = 10
SHUTDOWN_GRACE_PERIOD_SECONDS = 30

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 600

QUOTA_ERROR_PATTERNS = [
    "quota",
    "rate limit",
    "too many requests",
    "429",
    "resource exhausted",
    "capacity",
    "overloaded",
]

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════


def setup_logging(log_file: Optional[Path] = None, verbose: bool = False) -> logging.Logger:
    """Configure logging for the executor daemon."""
    logger = logging.getLogger("executor_daemon")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(console)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTOR DAEMON CLASS
# ══════════════════════════════════════════════════════════════════════════════


class ExecutorDaemon:
    """
    Production-hardened task executor daemon.

    Designed for autonomous operation with:
    - Crash recovery and orphan reclamation
    - Graceful shutdown with task completion
    - Health monitoring and heartbeat
    - Quota-aware execution
    """

    def __init__(
        self,
        logger: logging.Logger,
        poll_interval: int = POLL_INTERVAL_SECONDS,
        worker_id: str = WORKER_ID,
        dry_run: bool = False,
    ):
        self.logger = logger
        self.poll_interval = poll_interval
        self.worker_id = worker_id
        self.dry_run = dry_run

        # State
        self._running = False
        self._shutdown_requested = False
        self._current_task_id: Optional[str] = None
        self._lock = threading.Lock()
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Statistics
        self.stats = {
            "started_at": None,
            "tasks_executed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "orphans_recovered": 0,
            "total_execution_time_ms": 0,
            "last_poll_at": None,
            "last_task_at": None,
            "consecutive_errors": 0,
        }

        # Lazy-loaded components
        self._db = None
        self._config = None
        self._model = None
        self._task_executor = None

        # Register signal handlers
        self._setup_signal_handlers()

        # Register cleanup on exit
        atexit.register(self._cleanup)

    def _setup_signal_handlers(self):
        """Register handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_reload_signal)

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signal - finish current task then exit."""
        sig_name = signal.Signals(signum).name
        self.logger.info(f"Received {sig_name}, initiating graceful shutdown...")
        self._shutdown_requested = True

        if self._current_task_id:
            self.logger.info(f"Waiting for current task to complete: {self._current_task_id}")
        else:
            self.logger.info("No task in progress, shutting down immediately")

    def _handle_reload_signal(self, signum, frame):
        """Handle reload signal - refresh configuration."""
        self.logger.info("Received SIGHUP, reloading configuration...")
        self._reload_config()

    def _reload_config(self):
        """Reload configuration from disk."""
        try:
            from main import Config

            self._config = Config()
            self.logger.info("Configuration reloaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")

    def _cleanup(self):
        """Cleanup on exit - release any claimed tasks."""
        if self._current_task_id:
            self.logger.warning(f"Releasing uncompleted task on exit: {self._current_task_id}")
            try:
                db = self._get_db()
                db.release_action(self._current_task_id, reason="daemon_exit")
            except Exception as e:
                self.logger.error(f"Failed to release task: {e}")

    def _get_db(self):
        """Lazy-load database manager."""
        if self._db is None:
            from db_manager import get_db

            self._db = get_db()
        return self._db

    def _get_config(self):
        """Lazy-load configuration."""
        if self._config is None:
            from main import Config

            self._config = Config()
        return self._config

    def _get_model(self):
        """Lazy-load LLM model."""
        if self._model is None:
            try:
                from main import create_llm_provider
                from main import setup_logging as main_setup_logging

                config = self._get_config()
                main_logger = main_setup_logging(config)
                self._model = create_llm_provider(config, main_logger)
                if self._model:
                    self.logger.info(f"LLM provider initialized: {self._model.name}")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM: {e}")
        return self._model

    def _get_task_executor(self):
        """Lazy-load task executor."""
        if self._task_executor is None:
            try:
                from scripts.insights_engine import InsightsExtractor
                from scripts.task_executor import TaskExecutor

                config = self._get_config()
                model = self._get_model()

                if model:
                    extractor = InsightsExtractor(config, self.logger, model)
                    self._task_executor = TaskExecutor(config, self.logger, model, extractor)
                    self.logger.info("Task executor initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize task executor: {e}")
        return self._task_executor

    # ══════════════════════════════════════════════════════════════════════════
    # ORPHAN RECOVERY
    # ══════════════════════════════════════════════════════════════════════════

    def recover_orphans(self) -> int:
        """
        Recover orphaned tasks (stuck in 'in_progress' state).

        Orphans occur when:
        - Worker crashed during execution
        - Process was killed without graceful shutdown
        - Network partition caused timeout

        Returns:
            Number of orphans recovered
        """
        try:
            db = self._get_db()
            count = db.reset_stuck_actions(max_age_hours=ORPHAN_TIMEOUT_HOURS)
            if count > 0:
                self.logger.info(f"Recovered {count} orphaned tasks")
                self.stats["orphans_recovered"] += count
            return count
        except Exception as e:
            self.logger.error(f"Orphan recovery failed: {e}")
            return 0

    # ══════════════════════════════════════════════════════════════════════════
    # TASK EXECUTION
    # ══════════════════════════════════════════════════════════════════════════

    def _is_quota_error(self, error_msg: str) -> bool:
        """Check if an error is a quota/rate limit error."""
        error_lower = str(error_msg).lower()
        return any(pattern in error_lower for pattern in QUOTA_ERROR_PATTERNS)

    def _wait_for_quota(self, retry_count: int) -> int:
        """Wait for quota reset with exponential backoff."""
        backoff = min(INITIAL_BACKOFF_SECONDS * (2**retry_count), MAX_BACKOFF_SECONDS)
        self.logger.warning(f"Quota limit hit. Waiting {backoff}s before retry {retry_count + 1}/{MAX_RETRIES}...")
        time.sleep(backoff)
        return backoff

    def execute_task(self, action_dict: Dict[str, Any]) -> bool:
        """
        Execute a single task with retry logic.

        Args:
            action_dict: Task data from database

        Returns:
            True if task completed successfully
        """
        action_id = action_dict["action_id"]
        db = self._get_db()

        # Claim the task atomically
        if not db.claim_action(action_id, worker_id=self.worker_id):
            self.logger.debug(f"Task already claimed: {action_id}")
            return False

        with self._lock:
            self._current_task_id = action_id

        try:
            self.logger.info(f"Executing task: {action_dict.get('title', action_id)[:50]}")
            start_time = time.time()

            # DRY RUN MODE - simulate execution without calling LLM
            if self.dry_run:
                self.logger.info(
                    f"[DRY-RUN] Would execute: {action_dict.get('action_type')} - {action_dict.get('title', '')[:80]}"
                )
                time.sleep(0.1)  # Simulate minimal work
                execution_time_ms = (time.time() - start_time) * 1000

                # Release task back to pending (don't mark complete in dry-run)
                db.release_action(action_id, reason="dry_run")

                self.stats["total_execution_time_ms"] += execution_time_ms
                self.stats["tasks_executed"] += 1
                self.stats["tasks_succeeded"] += 1
                self.stats["last_task_at"] = datetime.now().isoformat()

                self.logger.info(f"[DRY-RUN] Task simulated: {action_id}")
                return True

            executor = self._get_task_executor()
            if not executor:
                raise RuntimeError("Task executor not available")

            # Build action insight object
            from scripts.insights_engine import ActionInsight

            action = ActionInsight(
                action_id=action_id,
                action_type=action_dict["action_type"],
                title=action_dict["title"],
                description=action_dict.get("description", ""),
                priority=action_dict.get("priority", "medium"),
                status="in_progress",
                source_report=action_dict.get("source_report", ""),
                source_context=action_dict.get("source_context", ""),
                deadline=action_dict.get("deadline"),
                scheduled_for=action_dict.get("scheduled_for"),
                retry_count=action_dict.get("retry_count", 0),
                last_error=action_dict.get("last_error"),
            )

            # Add to executor's queue
            executor.insights_extractor.action_queue = [action]

            # Execute with retry
            results = executor.execute_all_pending(max_tasks=1)

            execution_time_ms = (time.time() - start_time) * 1000
            self.stats["total_execution_time_ms"] += execution_time_ms
            self.stats["tasks_executed"] += 1
            self.stats["last_task_at"] = datetime.now().isoformat()

            if results and results[0].success:
                db.update_action_status(action_id, "completed", str(results[0].result_data))
                db.log_task_execution(
                    action_id,
                    success=True,
                    result=str(results[0].result_data),
                    execution_time_ms=execution_time_ms,
                    artifacts=str(results[0].artifacts) if results[0].artifacts else None,
                )
                self.stats["tasks_succeeded"] += 1
                self.stats["consecutive_errors"] = 0
                self.logger.info(f"Task completed: {action_id}")
                return True
            else:
                error_msg = results[0].error_message if results else "Unknown error"

                # Check if quota error - schedule retry
                if self._is_quota_error(error_msg):
                    retry_count = db.increment_retry_count(action_id, error_msg)
                    if retry_count < MAX_RETRIES:
                        db.release_action(action_id, reason=f"quota_retry_{retry_count}")
                        self.stats["tasks_retried"] += 1
                        self.logger.warning(f"Task quota-limited, will retry: {action_id}")
                        return False

                # Max retries or non-retriable error
                db.update_action_status(action_id, "failed", error_msg)
                db.log_task_execution(
                    action_id,
                    success=False,
                    error_message=error_msg,
                    execution_time_ms=execution_time_ms,
                )
                self.stats["tasks_failed"] += 1
                self.stats["consecutive_errors"] += 1
                self.logger.error(f"Task failed: {action_id} - {error_msg[:100]}")
                return False

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Task execution error: {error_msg}")

            # Release task for retry if retriable
            if self._is_quota_error(error_msg):
                db.release_action(action_id, reason="exception_quota")
                self.stats["tasks_retried"] += 1
            else:
                retry_count = db.increment_retry_count(action_id, error_msg)
                if retry_count >= MAX_RETRIES:
                    db.update_action_status(action_id, "failed", f"Exception: {error_msg}")
                else:
                    db.release_action(action_id, reason=f"exception_retry_{retry_count}")

            self.stats["consecutive_errors"] += 1
            return False

        finally:
            with self._lock:
                self._current_task_id = None

    def poll_and_execute(self, remaining_limit: int = None) -> int:
        """
        Poll for ready tasks and execute them.

        Args:
            remaining_limit: Max tasks to execute in this poll cycle

        Returns:
            Number of tasks executed
        """
        try:
            db = self._get_db()
            batch_size = min(10, remaining_limit) if remaining_limit else 10
            ready_tasks = db.get_ready_actions(limit=batch_size)

            if not ready_tasks:
                return 0

            self.logger.info(f"Found {len(ready_tasks)} ready tasks")
            executed = 0

            for task in ready_tasks:
                if self._shutdown_requested:
                    self.logger.info("Shutdown requested, stopping execution loop")
                    break

                if remaining_limit and executed >= remaining_limit:
                    break

                if self.execute_task(task):
                    executed += 1

            return executed

        except Exception as e:
            self.logger.error(f"Poll error: {e}")
            self.stats["consecutive_errors"] += 1
            return 0

    # ══════════════════════════════════════════════════════════════════════════
    # HEARTBEAT
    # ══════════════════════════════════════════════════════════════════════════

    def _heartbeat_loop(self):
        """Background thread for heartbeat updates."""
        while self._running and not self._shutdown_requested:
            try:
                db = self._get_db()
                db.set_config(f"executor_heartbeat_{self.worker_id}", datetime.now().isoformat())
                db.set_config(f"executor_stats_{self.worker_id}", json.dumps(self.stats))
            except Exception as e:
                self.logger.debug(f"Heartbeat error: {e}")

            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    def _start_heartbeat(self):
        """Start heartbeat background thread."""
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN LOOPS
    # ══════════════════════════════════════════════════════════════════════════

    def run_once(self, max_tasks: int = None) -> int:
        """
        Run once and exit (drain mode).

        Executes all ready tasks until queue is empty or max_tasks reached.

        Args:
            max_tasks: Optional limit on tasks to execute (None = all)

        Returns:
            Total tasks executed
        """
        mode_str = "dry-run" if self.dry_run else "drain"
        self.logger.info(f"Executor daemon starting ({mode_str} mode) - Worker: {self.worker_id}")
        if max_tasks:
            self.logger.info(f"Task limit: {max_tasks}")
        self.stats["started_at"] = datetime.now().isoformat()

        # Recover any orphans first
        self.recover_orphans()

        total_executed = 0
        while True:
            # Check task limit
            if max_tasks and total_executed >= max_tasks:
                self.logger.info(f"Reached task limit ({max_tasks})")
                break

            remaining = (max_tasks - total_executed) if max_tasks else None
            executed = self.poll_and_execute(remaining_limit=remaining)
            total_executed += executed

            if executed == 0:
                break

            if self._shutdown_requested:
                break

        self.logger.info(f"Drain complete. Executed {total_executed} tasks.")
        self._print_stats()
        return total_executed

    def run_daemon(self):
        """
        Run as continuous daemon.

        Polls for tasks at regular intervals until shutdown.
        """
        self.logger.info(f"Executor daemon starting (continuous) - Worker: {self.worker_id}")
        self.stats["started_at"] = datetime.now().isoformat()
        self._running = True

        # Recover orphans on startup
        self.recover_orphans()

        # Start heartbeat
        self._start_heartbeat()

        last_orphan_check = time.time()

        while not self._shutdown_requested:
            try:
                # Poll and execute
                self.stats["last_poll_at"] = datetime.now().isoformat()
                self.poll_and_execute()

                # Periodic orphan recovery
                if time.time() - last_orphan_check > ORPHAN_CHECK_INTERVAL_SECONDS:
                    self.recover_orphans()
                    last_orphan_check = time.time()

                # Check for too many consecutive errors
                if self.stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
                    self.logger.error(
                        f"Too many consecutive errors ({MAX_CONSECUTIVE_ERRORS}), " "pausing for extended cooldown..."
                    )
                    time.sleep(MAX_BACKOFF_SECONDS)
                    self.stats["consecutive_errors"] = 0

                # Sleep between polls
                time.sleep(self.poll_interval)

            except Exception as e:
                self.logger.error(f"Daemon loop error: {e}")
                time.sleep(self.poll_interval)

        self._running = False
        self.logger.info("Executor daemon stopped")
        self._print_stats()

    def _print_stats(self):
        """Print execution statistics."""
        self.logger.info("=" * 60)
        self.logger.info("EXECUTOR DAEMON STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"  Started:          {self.stats['started_at']}")
        self.logger.info(f"  Tasks Executed:   {self.stats['tasks_executed']}")
        self.logger.info(f"  Succeeded:        {self.stats['tasks_succeeded']}")
        self.logger.info(f"  Failed:           {self.stats['tasks_failed']}")
        self.logger.info(f"  Retried:          {self.stats['tasks_retried']}")
        self.logger.info(f"  Orphans Recovered:{self.stats['orphans_recovered']}")
        if self.stats["tasks_executed"] > 0:
            avg_time = self.stats["total_execution_time_ms"] / self.stats["tasks_executed"]
            self.logger.info(f"  Avg Exec Time:    {avg_time:.2f}ms")
        self.logger.info("=" * 60)

    def health_check(self) -> Dict[str, Any]:
        """
        Get daemon health status.

        Returns:
            Health information dict
        """
        db = self._get_db()

        try:
            health = db.get_system_health()
            task_stats = health.get("tasks", {})
        except Exception:
            task_stats = {}

        return {
            "status": "running" if self._running else "stopped",
            "worker_id": self.worker_id,
            "uptime_seconds": (
                (datetime.now() - datetime.fromisoformat(self.stats["started_at"])).total_seconds()
                if self.stats["started_at"]
                else 0
            ),
            "current_task": self._current_task_id,
            "stats": self.stats,
            "queue": task_stats,
        }


# ══════════════════════════════════════════════════════════════════════════════
# SUBPROCESS SPAWN INTERFACE
# ══════════════════════════════════════════════════════════════════════════════


def spawn_executor_subprocess(detach: bool = True) -> Optional[int]:
    """
    Spawn executor as a detached subprocess.

    Used when systemd is not available or for ad-hoc execution.

    Args:
        detach: If True, subprocess survives parent death

    Returns:
        PID of spawned process, or None on failure
    """
    import subprocess

    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    cmd = [python_exe, str(script_path), "--daemon"]

    try:
        if detach:
            # Detach from parent - survives parent death
            if sys.platform == "win32":
                # Windows: CREATE_NEW_PROCESS_GROUP
                process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # Unix: start_new_session
                process = subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        else:
            process = subprocess.Popen(cmd)

        return process.pid

    except Exception as e:
        print(f"Failed to spawn executor: {e}")
        return None


def is_executor_running() -> bool:
    """Check if an executor daemon is already running."""
    try:
        from db_manager import get_db

        db = get_db()
        heartbeat = db.get_config(f"executor_heartbeat_{WORKER_ID}")

        if heartbeat:
            last_heartbeat = datetime.fromisoformat(heartbeat)
            if datetime.now() - last_heartbeat < timedelta(minutes=2):
                return True
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Gold Standard Task Executor Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --daemon              # Run continuously
  %(prog)s --once                # Drain queue and exit
  %(prog)s --recover-orphans     # Recover stuck tasks only
  %(prog)s --health              # Show health status
  %(prog)s --spawn               # Spawn detached daemon
        """,
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--daemon", "-d", action="store_true", help="Run as continuous daemon")
    mode_group.add_argument("--once", "-1", action="store_true", help="Run once (drain queue) and exit")
    mode_group.add_argument("--recover-orphans", action="store_true", help="Recover orphaned tasks and exit")
    mode_group.add_argument("--health", action="store_true", help="Show health status and exit")
    mode_group.add_argument("--spawn", action="store_true", help="Spawn a detached executor daemon")

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=POLL_INTERVAL_SECONDS,
        help=f"Seconds between polls (default: {POLL_INTERVAL_SECONDS})",
    )
    parser.add_argument("--log-file", type=Path, help="Log file path (default: stdout only)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate execution without actually running tasks (test mode)"
    )
    parser.add_argument(
        "--max-tasks", type=int, default=None, help="Maximum number of tasks to execute (default: unlimited)"
    )

    args = parser.parse_args()

    # Spawn mode - launch detached and exit
    if args.spawn:
        if is_executor_running():
            print("Executor daemon already running")
            sys.exit(0)

        pid = spawn_executor_subprocess(detach=True)
        if pid:
            print(f"Spawned executor daemon with PID: {pid}")
            sys.exit(0)
        else:
            print("Failed to spawn executor daemon")
            sys.exit(1)

    # Setup logging
    log_file = args.log_file or PROJECT_ROOT / "output" / "executor.log"
    logger = setup_logging(log_file, args.verbose)

    # Create daemon
    daemon = ExecutorDaemon(
        logger=logger,
        poll_interval=args.poll_interval,
        dry_run=getattr(args, "dry_run", False),
    )

    # Execute based on mode
    if args.health:
        health = daemon.health_check()
        print(json.dumps(health, indent=2, default=str))

    elif args.recover_orphans:
        count = daemon.recover_orphans()
        print(f"Recovered {count} orphaned tasks")

    elif args.once:
        count = daemon.run_once(max_tasks=args.max_tasks)
        sys.exit(0 if count >= 0 else 1)

    else:  # --daemon or default
        daemon.run_daemon()


if __name__ == "__main__":
    main()
