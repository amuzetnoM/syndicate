#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Configuration Module
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Configuration management for Digest Bot.

Loads settings from environment variables with sensible defaults.
Supports both file-based and database-based document retrieval.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


def _get_project_root() -> Path:
    """Find the syndicate project root directory."""
    current = Path(__file__).resolve().parent
    # Walk up until we find pyproject.toml or main.py
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "main.py").exists():
            return current
        current = current.parent
    # Fallback to 2 levels up from src/digest_bot
    return Path(__file__).resolve().parent.parent.parent


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv

        env_path = _get_project_root() / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv not installed, rely on system env


# Load environment on module import
_load_dotenv()


def _env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Get float environment variable."""
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _env_path(key: str, default: Path) -> Path:
    """Get path environment variable."""
    val = os.environ.get(key, "")
    if val:
        path = Path(val).expanduser()
        return path if path.is_absolute() else _get_project_root() / path
    return default


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    # Provider selection: "local" (llama.cpp) or "ollama"
    provider: Literal["local", "ollama", "gemini"] = field(default_factory=lambda: _env("LLM_PROVIDER", "local"))

    # llama.cpp settings
    local_model_path: Path = field(
        default_factory=lambda: _env_path(
            "LOCAL_LLM_MODEL", _get_project_root() / "models" / "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        )
    )
    local_gpu_layers: int = field(default_factory=lambda: _env_int("LOCAL_LLM_GPU_LAYERS", 0))
    local_context: int = field(default_factory=lambda: _env_int("LOCAL_LLM_CONTEXT", 4096))
    local_threads: int = field(default_factory=lambda: _env_int("LOCAL_LLM_THREADS", 0))

    # Ollama settings
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: _env("OLLAMA_MODEL", "mistral"))
    ollama_timeout: float = field(default_factory=lambda: _env_float("OLLAMA_TIMEOUT", 20.0))

    # Gemini settings (cloud primary provider)
    gemini_model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "models/gemini-pro-latest"))
    gemini_rate_limit_sec: int = field(default_factory=lambda: _env_int("GEMINI_RATE_LIMIT_SEC", 60))

    # Generation settings
    max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 768))
    temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.3))

    # Retry settings
    max_retries: int = field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 3))
    retry_delay: float = field(default_factory=lambda: _env_float("LLM_RETRY_DELAY", 2.0))


@dataclass
class PathConfig:
    """File and directory path configuration."""

    project_root: Path = field(default_factory=_get_project_root)

    # Output directories (where reports are stored)
    output_dir: Path = field(default_factory=lambda: _env_path("OUTPUT_DIR", _get_project_root() / "output"))
    reports_dir: Path = field(
        default_factory=lambda: _env_path("REPORTS_DIR", _get_project_root() / "output" / "reports")
    )

    # Specific report locations
    journals_dir: Path = field(
        default_factory=lambda: _env_path("JOURNALS_DIR", _get_project_root() / "output" / "reports" / "journals")
    )
    premarket_dir: Path = field(
        default_factory=lambda: _env_path("PRE_MARKET_DIR", _get_project_root() / "output" / "reports" / "premarket")
    )
    weekly_dir: Path = field(
        default_factory=lambda: _env_path("WEEKLY_DIR", _get_project_root() / "output" / "reports" / "weekly")
    )

    # Digest output
    digest_output_dir: Path = field(
        default_factory=lambda: _env_path("DIGEST_OUTPUT_DIR", _get_project_root() / "output" / "digests")
    )

    # Database
    database_path: Path = field(
        default_factory=lambda: _env_path("DATABASE_PATH", _get_project_root() / "data" / "syndicate.db")
    )

    # Log file
    log_file: Path = field(
        default_factory=lambda: _env_path(
            "DIGEST_LOG_FILE", _get_project_root() / "output" / "digests" / "digest_bot.log"
        )
    )


@dataclass
class GateConfig:
    """File gate and retry configuration."""

    # Retry settings
    retry_interval_sec: int = field(default_factory=lambda: _env_int("RETRY_INTERVAL_SEC", 300))
    max_retries: int = field(default_factory=lambda: _env_int("MAX_RETRIES", 48))

    # Staleness thresholds
    max_staleness_days: int = field(default_factory=lambda: _env_int("MAX_STALENESS_DAYS", 1))
    weekly_lookback_days: int = field(default_factory=lambda: _env_int("WEEKLY_LOOKBACK_DAYS", 14))

    # Minimum file size (bytes) to consider valid
    min_file_size: int = field(default_factory=lambda: _env_int("MIN_FILE_SIZE", 100))

    # Enable database fallback for missing files
    use_database_fallback: bool = field(default_factory=lambda: _env_bool("USE_DATABASE_FALLBACK", True))

    # Enable fuzzy file matching
    fuzzy_matching: bool = field(default_factory=lambda: _env_bool("FUZZY_MATCHING", True))


@dataclass
class DiscordConfig:
    """Discord bot configuration."""

    bot_token: str = field(default_factory=lambda: _env("DISCORD_BOT_TOKEN", ""))
    guild_id: Optional[int] = field(default_factory=lambda: _env_int("DISCORD_GUILD_ID", 0) or None)
    digest_channel_id: Optional[int] = field(default_factory=lambda: _env_int("DISCORD_DIGEST_CHANNEL_ID", 0) or None)
    log_channel_id: Optional[int] = field(default_factory=lambda: _env_int("DISCORD_LOG_CHANNEL_ID", 0) or None)
    admin_role_id: Optional[int] = field(default_factory=lambda: _env_int("DISCORD_ADMIN_ROLE_ID", 0) or None)
    auto_refactor: bool = field(default_factory=lambda: _env_bool("DISCORD_AUTO_REFACTOR", False))

    @property
    def is_configured(self) -> bool:
        """Check if Discord is properly configured."""
        return bool(self.bot_token and self.guild_id)


@dataclass
class Config:
    """
    Master configuration for Digest Bot.

    Aggregates all sub-configurations and provides utility methods.
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    gate: GateConfig = field(default_factory=GateConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)

    # Runtime flags
    debug: bool = field(default_factory=lambda: _env_bool("DEBUG", False))
    dry_run: bool = False
    once: bool = False

    def __post_init__(self):
        """Ensure directories exist."""
        self.paths.digest_output_dir.mkdir(parents=True, exist_ok=True)
        self.paths.log_file.parent.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check LLM configuration
        if self.llm.provider == "local":
            if not self.llm.local_model_path.exists():
                issues.append(
                    f"Local LLM model not found: {self.llm.local_model_path}\n"
                    f"  Download a GGUF model or set LOCAL_LLM_MODEL env var"
                )
        elif self.llm.provider == "ollama":
            # Ollama validation happens at runtime
            pass

        # Check output directories
        if not self.paths.output_dir.exists():
            issues.append(f"Output directory not found: {self.paths.output_dir}")

        # Check database if fallback enabled
        if self.gate.use_database_fallback:
            if not self.paths.database_path.exists():
                issues.append(
                    f"Database not found: {self.paths.database_path}\n"
                    f"  Disable fallback with USE_DATABASE_FALLBACK=0"
                )

        return issues

    def summary(self) -> str:
        """Generate human-readable configuration summary."""
        lines = [
            "═" * 60,
            "  DIGEST BOT CONFIGURATION",
            "═" * 60,
            "",
            "LLM Provider:",
            f"  Provider: {self.llm.provider}",
        ]

        if self.llm.provider == "local":
            lines.extend(
                [
                    f"  Model: {self.llm.local_model_path.name}",
                    f"  GPU Layers: {self.llm.local_gpu_layers}",
                    f"  Context: {self.llm.local_context}",
                ]
            )
        elif self.llm.provider == "gemini":
            lines.extend(
                [
                    f"  Model: {self.llm.gemini_model}",
                    f"  Rate Limit: {self.llm.gemini_rate_limit_sec}s",
                ]
            )
        else:
            lines.extend(
                [
                    f"  Host: {self.llm.ollama_host}",
                    f"  Model: {self.llm.ollama_model}",
                ]
            )

        lines.extend(
            [
                "",
                "Paths:",
                f"  Output: {self.paths.output_dir}",
                f"  Reports: {self.paths.reports_dir}",
                f"  Digests: {self.paths.digest_output_dir}",
                f"  Database: {self.paths.database_path}",
                "",
                "Gate Settings:",
                f"  Retry Interval: {self.gate.retry_interval_sec}s",
                f"  Max Retries: {self.gate.max_retries}",
                f"  DB Fallback: {self.gate.use_database_fallback}",
                f"  Fuzzy Matching: {self.gate.fuzzy_matching}",
                "",
                "Flags:",
                f"  Debug: {self.debug}",
                f"  Dry Run: {self.dry_run}",
                f"  Once Mode: {self.once}",
                "",
                "═" * 60,
            ]
        )

        return "\n".join(lines)


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global configuration (for testing)."""
    global _config
    _config = None
