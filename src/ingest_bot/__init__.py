"""Ingest Bot skeleton package

This package is intended to host ingest adapters and orchestrators that pull
structured and time-series data from external real-time sources (FRED, Rapid,
MarketFlow, TradingEconomics, etc.) and store normalized outputs in the
`data/` directory for downstream processing by Syndicate.

Design notes and implementation are intentionally skeletal for now; these
modules will be developed in a follow-up cycle once the data API contracts
and operator requirements are finalized.
"""
__all__ = ["blueprint", "adapters", "pipeline"]
