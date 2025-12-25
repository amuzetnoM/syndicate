"""Prometheus metrics instrumentation for Syndicate.

Expose counters and histograms for the executor and LLM usage.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry
from typing import Optional

# Executor metrics
executor_tasks_total = Counter("syndicate_executor_tasks_total", "Total tasks executed")
executor_tasks_succeeded = Counter("syndicate_executor_tasks_succeeded", "Total tasks succeeded")
executor_tasks_failed = Counter("syndicate_executor_tasks_failed", "Total tasks failed")
executor_task_duration_seconds = Histogram(
    "syndicate_executor_task_duration_seconds", "Task execution duration seconds", buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 300)
)

# LLM metrics
llm_tokens_total = Counter("syndicate_llm_tokens_total", "Total LLM tokens consumed", ['provider'])
llm_cost_total = Counter("syndicate_llm_cost_total", "Total LLM cost (USD)", ['provider'])

# DB metrics
db_busy_total = Gauge("syndicate_db_busy_total", "SQLite busy count (indicative)")


def expose_metrics():
    return generate_latest()
