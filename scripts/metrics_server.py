#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__            
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____   
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \  
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/ 
#
# Gold Standard - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Prometheus Metrics Endpoint for Gold Standard

Exposes system health metrics via HTTP for Prometheus scraping.
Run alongside the daemon with: python scripts/metrics_server.py
"""

import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from db_manager import get_system_health


# Metrics configuration
METRICS_PORT = int(os.environ.get('METRICS_PORT', 8080))
METRICS_HOST = os.environ.get('METRICS_HOST', '0.0.0.0')

# Metric counters (in-memory, reset on restart)
task_completions = 0
task_failures = 0
last_execution_time = 0


def get_metrics():
    """Generate Prometheus-formatted metrics."""
    global task_completions, task_failures, last_execution_time
    
    # Get current system health
    health = get_system_health()
    
    # Build metrics output
    metrics = []
    
    # Application info
    metrics.append('# HELP gold_standard_info Application information')
    metrics.append('# TYPE gold_standard_info gauge')
    metrics.append('gold_standard_info{version="3.2.1"} 1')
    
    # Task counts
    metrics.append('')
    metrics.append('# HELP gold_standard_tasks_ready Number of tasks ready for execution')
    metrics.append('# TYPE gold_standard_tasks_ready gauge')
    metrics.append(f'gold_standard_tasks_ready {health.get("ready_count", 0)}')
    
    metrics.append('')
    metrics.append('# HELP gold_standard_tasks_scheduled Number of tasks scheduled for future')
    metrics.append('# TYPE gold_standard_tasks_scheduled gauge')
    metrics.append(f'gold_standard_tasks_scheduled {health.get("scheduled_count", 0)}')
    
    metrics.append('')
    metrics.append('# HELP gold_standard_stuck_tasks Number of tasks stuck in execution')
    metrics.append('# TYPE gold_standard_stuck_tasks gauge')
    metrics.append(f'gold_standard_stuck_tasks {health.get("stuck_count", 0)}')
    
    # Execution counters
    metrics.append('')
    metrics.append('# HELP gold_standard_task_completions_total Total number of completed tasks')
    metrics.append('# TYPE gold_standard_task_completions_total counter')
    metrics.append(f'gold_standard_task_completions_total {task_completions}')
    
    metrics.append('')
    metrics.append('# HELP gold_standard_task_failures_total Total number of failed tasks')
    metrics.append('# TYPE gold_standard_task_failures_total counter')
    metrics.append(f'gold_standard_task_failures_total {task_failures}')
    
    # Timing
    metrics.append('')
    metrics.append('# HELP gold_standard_last_execution_timestamp Unix timestamp of last execution')
    metrics.append('# TYPE gold_standard_last_execution_timestamp gauge')
    metrics.append(f'gold_standard_last_execution_timestamp {last_execution_time}')
    
    # Uptime
    metrics.append('')
    metrics.append('# HELP gold_standard_uptime_seconds Application uptime in seconds')
    metrics.append('# TYPE gold_standard_uptime_seconds gauge')
    metrics.append(f'gold_standard_uptime_seconds {time.time() - start_time}')
    
    return '\n'.join(metrics) + '\n'


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(get_metrics().encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
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


if __name__ == '__main__':
    print("=" * 60)
    print(" Gold Standard - Prometheus Metrics Exporter")
    print("=" * 60)
    print(f"\nEndpoints:")
    print(f"  📊 Metrics: http://{METRICS_HOST}:{METRICS_PORT}/metrics")
    print(f"  💚 Health:  http://{METRICS_HOST}:{METRICS_PORT}/health")
    print("\nPress Ctrl+C to stop.\n")
    
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\nShutting down metrics server...")
