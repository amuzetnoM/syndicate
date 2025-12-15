#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Discord Integration
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Discord bot with self-healing and self-guiding capabilities.

Features:
- Auto-reconnect with exponential backoff
- Self-healing error recovery
- Auto-create channels/roles based on bot's purpose
- Server structure management
"""

from .bot import DigestDiscordBot
from .self_guide import ChannelSpec, RoleSpec, SelfGuide, ServerBlueprint
from .self_healer import HealthStatus, SelfHealer

__all__ = [
    "DigestDiscordBot",
    "SelfHealer",
    "HealthStatus",
    "SelfGuide",
    "ServerBlueprint",
    "ChannelSpec",
    "RoleSpec",
]
