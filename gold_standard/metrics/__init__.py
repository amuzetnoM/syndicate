"""Metrics utilities for Gold Standard.

Exports a small METRICS map and a helper to start the metrics HTTP server.
"""
from .server import start_metrics_server, METRICS, set_readiness, set_liveness

__all__ = ["start_metrics_server", "METRICS", "set_readiness", "set_liveness"]
