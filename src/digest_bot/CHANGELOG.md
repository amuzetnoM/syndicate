# Digest Bot Changelog

## 1.0.0 - 2025-12-15
- Enforced strict same-day gating for journals and premarket (filename date must equal target; frontmatter date, if present, must match).
- Added ops-visible logging for skipped candidates (mismatched filename/frontmatter dates).
- Hardened database fallback handling and schema expectations.
- Modernized test suite to current config/path defaults and gate behavior.
- Refreshed documentation (README, architecture, plan) to reflect new rules and defaults.

## 0.6.0 - 2025-08-10
- Introduced multi-provider LLM abstraction (local llama.cpp default, Ollama fallback).
- Added structured digest template with metadata and backups on overwrite.
- Expanded CLI commands (run/check/history/cleanup) and retryable wait mode.
- Implemented database fallback for missing files.

## 0.4.0 - 2025-05-02
- Added weekly report lookback selection and size-based validation of inputs.
- Improved directory discovery across reports root/journals/premarket/weekly.
- Added idempotency checks to skip existing digests.

## 0.2.0 - 2025-03-15
- Completed initial file gate, summarizer prompt builder, and writer with atomic writes.
- Established pytest-based test suite and fixtures.

## 0.1.0 - 2025-02-01
- Initial scaffold: configuration layer, CLI entry point, basic digest generation pipeline.
