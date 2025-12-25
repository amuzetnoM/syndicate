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
# ══════════════════════════════════════════════════════════════════════════════
"""
Prometheus Metrics Endpoint for Syndicate

Exposes system health metrics via HTTP for Prometheus scraping.
Run alongside the daemon with: python scripts/metrics_server.py
"""

import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    # Prefer the centralized Prometheus instrumentation if available
    from scripts.metrics import expose_metrics
except Exception:
    expose_metrics = None

# Metrics configuration
METRICS_PORT = int(os.environ.get("METRICS_PORT", 8080))
METRICS_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")

# Metric counters (in-memory, reset on restart)
task_completions = 0
task_failures = 0
last_execution_time = 0


def get_metrics():
    """Return Prometheus output. Use centralized `scripts.metrics` when possible.

    This function intentionally falls back to a minimal, safe output
    if the project's `scripts.metrics` is unavailable to avoid crashes
    when metrics server is started independently.
    """
    # If the consolidated metrics module is available, use it (bytes)
    if expose_metrics:
        try:
            output = expose_metrics()
            # ensure bytes -> str
            if isinstance(output, bytes):
                return output.decode("utf-8")
            return str(output)
        except Exception:
            # Fall through to minimal fallback below
            pass

    # Minimal safe fallback metrics (no DB calls, always safe)
    metrics = []
    metrics.append("# HELP syndicate_info Application information")
    metrics.append("# TYPE syndicate_info gauge")
    metrics.append('syndicate_info{version="unknown"} 1')
    metrics.append("")
    metrics.append("# HELP syndicate_uptime_seconds Application uptime in seconds")
    metrics.append("# TYPE syndicate_uptime_seconds gauge")
    metrics.append(f"syndicate_uptime_seconds {time.time() - start_time}")

    return "\n".join(metrics) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""

    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(get_metrics().encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def increment_completion():
    """Increment task completion counter."""
    global task_completions, last_execution_time
    task_completions += 1
    last_execution_time = time.time()


def increment_failure():
    """Increment task failure counter."""
    global task_failures, last_execution_time
    task_failures += 1
    last_execution_time = time.time()


def run_server():
    """Start the metrics HTTP server."""
    server = HTTPServer((METRICS_HOST, METRICS_PORT), MetricsHandler)
    print(f"🔬 Metrics server running at http://{METRICS_HOST}:{METRICS_PORT}/metrics")
    server.serve_forever()


def start_metrics_server():
    """Start metrics server in a background thread."""
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


# Track start time for uptime metric
start_time = time.time()


if __name__ == "__main__":
    print("=" * 60)
    print(" Syndicate - Prometheus Metrics Exporter")
    print("=" * 60)
    print("\nEndpoints:")
    print(f"  📊 Metrics: http://{METRICS_HOST}:{METRICS_PORT}/metrics")
    print(f"  💚 Health:  http://{METRICS_HOST}:{METRICS_PORT}/health")
    print("\nPress Ctrl+C to stop.\n")

    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\nShutting down metrics server...")
