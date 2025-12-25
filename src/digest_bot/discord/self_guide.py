#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Self-Guiding System
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Self-guiding capabilities for the Discord bot.

Features:
- Auto-create channels with descriptions
- Auto-create roles with permissions
- Server structure blueprints
- Purpose-aware channel organization
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import discord

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# BLUEPRINT SPECIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════


class ChannelType(Enum):
    """Discord channel types."""

    TEXT = "text"
    VOICE = "voice"
    CATEGORY = "category"
    FORUM = "forum"
    ANNOUNCEMENT = "announcement"


@dataclass
class RoleSpec:
    """
    Specification for a Discord role.

    Defines a role to be created with specific
    permissions and appearance.
    """

    name: str
    color: int = 0x3498DB  # Default blue
    hoist: bool = False  # Show separately in member list
    mentionable: bool = False
    permissions: List[str] = field(default_factory=list)
    position_priority: int = 0  # Higher = higher in role list
    reason: str = "Auto-created by Digest Bot"

    # Permission presets
    @classmethod
    def admin(cls, name: str = "Bot Admin") -> "RoleSpec":
        """Create admin role spec."""
        return cls(
            name=name,
            color=0xE74C3C,  # Red
            hoist=True,
            mentionable=True,
            permissions=[
                "administrator",
            ],
            position_priority=100,
            reason="Bot admin role for full control",
        )

    @classmethod
    def moderator(cls, name: str = "Digest Moderator") -> "RoleSpec":
        """Create moderator role spec."""
        return cls(
            name=name,
            color=0x9B59B6,  # Purple
            hoist=True,
            mentionable=True,
            permissions=[
                "manage_messages",
                "kick_members",
                "ban_members",
                "manage_channels",
                "view_audit_log",
            ],
            position_priority=50,
            reason="Moderator role for digest management",
        )

    @classmethod
    def operators(cls, name: str = "operators") -> "RoleSpec":
        """Create the lightweight operators role used by command gating."""
        return cls(
            name=name,
            color=0xF39C12,  # Orange
            hoist=False,
            mentionable=False,
            permissions=[
                "send_messages",
                "embed_links",
                "read_message_history",
                "add_reactions",
            ],
            position_priority=45,
            reason="Operators role for command execution and digest approvals",
        )

    @classmethod
    def analyst(cls, name: str = "Market Analyst") -> "RoleSpec":
        """Create analyst role spec."""
        return cls(
            name=name,
            color=0x2ECC71,  # Green
            hoist=True,
            mentionable=True,
            permissions=[
                "send_messages",
                "embed_links",
                "attach_files",
                "add_reactions",
                "use_external_emojis",
            ],
            position_priority=25,
            reason="Analyst role for market analysis access",
        )

    @classmethod
    def subscriber(cls, name: str = "Digest Subscriber") -> "RoleSpec":
        """Create subscriber role spec."""
        return cls(
            name=name,
            color=0x3498DB,  # Blue
            hoist=False,
            mentionable=False,
            permissions=[
                "view_channel",
                "read_message_history",
                "add_reactions",
            ],
            position_priority=10,
            reason="Subscriber role for digest access",
        )


@dataclass
class ChannelSpec:
    """
    Specification for a Discord channel.

    Defines a channel to be created with specific
    properties and permissions.
    """

    name: str
    channel_type: ChannelType = ChannelType.TEXT
    topic: str = ""
    category: Optional[str] = None  # Category name to place under
    position: int = 0
    slowmode: int = 0  # Seconds
    nsfw: bool = False

    # Permission overwrites (role_name -> allow/deny permissions)
    permission_overwrites: Dict[str, Dict[str, bool]] = field(default_factory=dict)

    reason: str = "Auto-created by Digest Bot"

    # Channel presets for Digest Bot
    @classmethod
    def digests_channel(cls) -> "ChannelSpec":
        """Create the main digests channel."""
        return cls(
            name="📊-daily-digests",
            channel_type=ChannelType.TEXT,
            topic="🤖 Automated daily market intelligence digests. "
            "Generated by Syndicate Digest Bot using local AI.",
            position=1,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"view_channel": False, "send_messages": False},
                "Digest Bot": {"send_messages": True, "embed_links": True, "mention_everyone": False},
                "Market Analyst": {"send_messages": True, "embed_links": True},
                "operators": {"send_messages": True, "embed_links": True, "read_message_history": True},
                "Digest Subscriber": {"view_channel": True, "read_message_history": True},
            },
            reason="Main channel for automated digest delivery",
        )

    @classmethod
    def premarket_channel(cls) -> "ChannelSpec":
        """Create pre-market analysis channel."""
        return cls(
            name="📈-premarket-plans",
            channel_type=ChannelType.TEXT,
            topic="🌅 Daily pre-market analysis and trading plans. " "Posted before market open.",
            position=2,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"send_messages": False},
                "Market Analyst": {"send_messages": True},
            },
            reason="Channel for pre-market analysis",
        )

    @classmethod
    def journal_channel(cls) -> "ChannelSpec":
        """Create trading journal channel."""
        return cls(
            name="📔-trading-journal",
            channel_type=ChannelType.TEXT,
            topic="📝 Daily trading journal entries and reflections. " "Track decisions and learn from experience.",
            position=3,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"send_messages": False},
                "Market Analyst": {"send_messages": True},
            },
            reason="Channel for trading journal entries",
        )

    @classmethod
    def discussion_channel(cls) -> "ChannelSpec":
        """Create discussion channel."""
        return cls(
            name="💬-market-discussion",
            channel_type=ChannelType.TEXT,
            topic="💭 Open discussion about markets, analysis, and trading ideas. " "Be respectful and constructive.",
            position=5,
            slowmode=5,  # 5 second slowmode
            permission_overwrites={
                "Digest Subscriber": {"send_messages": True},
            },
            reason="Channel for community discussion",
        )

    @classmethod
    def bot_logs_channel(cls) -> "ChannelSpec":
        """Create bot logs channel."""
        return cls(
            name="🤖-bot-logs",
            channel_type=ChannelType.TEXT,
            topic="⚙️ Bot status, health checks, and system logs. " "Admin visibility only.",
            position=10,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"view_channel": False},
                "Bot Admin": {"view_channel": True, "send_messages": True},
                "operators": {"view_channel": True, "send_messages": False},
                "Digest Bot": {"send_messages": True},
            },
            reason="Channel for bot operational logs",
        )

    @classmethod
    def reports_channel(cls) -> "ChannelSpec":
        """Create an admin-only reports channel where all reports are routed."""
        return cls(
            name="📥-reports",
            channel_type=ChannelType.TEXT,
            topic="📥 Central admin inbox for generated reports (premarket, journal, research). Visible to Bot Admins only.",
            position=11,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"view_channel": False},
                "Bot Admin": {"view_channel": True, "send_messages": True},
                "operators": {"view_channel": True, "send_messages": True},
                "Digest Bot": {"send_messages": True},
            },
            reason="Admin inbox for generated reports",
        )

    @classmethod
    def commands_codex_channel(cls) -> "ChannelSpec":
        """Create a public command codex channel for users to learn bot commands."""
        return cls(
            name="📋-bot-commands",
            channel_type=ChannelType.TEXT,
            topic="📋 Bot command codex — how to use bot services. Readable by all users.",
            position=6,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"view_channel": True, "send_messages": False},
                "Digest Bot": {"send_messages": True},
            },
            reason="Public command codex for bot usage",
        )

    @classmethod
    def alerts_channel(cls) -> "ChannelSpec":
        """Create alerts channel."""
        return cls(
            name="🚨-alerts",
            channel_type=ChannelType.TEXT,
            topic="⚠️ Important market alerts and notifications. " "Configure your notification settings!",
            position=0,
            slowmode=0,
            permission_overwrites={
                "@everyone": {"send_messages": False},
                "Digest Bot": {"send_messages": True, "mention_everyone": True},
            },
            reason="Channel for important alerts",
        )


@dataclass
class CategorySpec:
    """
    Specification for a Discord category.
    """

    name: str
    position: int = 0
    channels: List[ChannelSpec] = field(default_factory=list)
    permission_overwrites: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    reason: str = "Auto-created by Digest Bot"


@dataclass
class ServerBlueprint:
    """
    Complete server structure blueprint.

    Defines the ideal server structure for the
    Digest Bot, including categories, channels, and roles.
    """

    name: str = "Syndicate Trading"
    description: str = "AI-powered market intelligence and trading community"

    roles: List[RoleSpec] = field(default_factory=list)
    categories: List[CategorySpec] = field(default_factory=list)
    standalone_channels: List[ChannelSpec] = field(default_factory=list)

    @classmethod
    def default(cls) -> "ServerBlueprint":
        """Create the default Digest Bot server blueprint."""
        return cls(
            name="Syndicate Trading",
            description="AI-powered market intelligence and trading community",
            roles=[
                RoleSpec.admin("Bot Admin"),
                RoleSpec.moderator("Digest Moderator"),
                RoleSpec.operators("operators"),
                RoleSpec.analyst("Market Analyst"),
                RoleSpec.subscriber("Digest Subscriber"),
                RoleSpec(
                    name="Digest Bot",
                    color=0xF1C40F,  # Gold
                    hoist=True,
                    mentionable=False,
                    permissions=[
                        "send_messages",
                        "embed_links",
                        "attach_files",
                        "manage_messages",
                        "read_message_history",
                        "add_reactions",
                        "use_external_emojis",
                        "create_instant_invite",
                    ],
                    position_priority=75,
                    reason="Bot service role",
                ),
            ],
            categories=[
                CategorySpec(
                    name="📊 MARKET INTELLIGENCE",
                    position=0,
                    channels=[
                        ChannelSpec.alerts_channel(),
                        ChannelSpec.digests_channel(),
                        ChannelSpec.premarket_channel(),
                        ChannelSpec.journal_channel(),
                        ChannelSpec(
                            name="📚-research-journal",
                            topic="🔬 Research journal and working notes. Published research and drafts.",
                            position=4,
                        ),
                        ChannelSpec(
                            name="📈-day-charts",
                            topic="📊 Daily charts and visualizations (auto-posted). Pins are used to keep latest charts visible.",
                            position=7,
                        ),
                    ],
                    reason="Category for automated market intelligence",
                ),
                CategorySpec(
                    name="💬 COMMUNITY",
                    position=1,
                    channels=[
                        ChannelSpec.discussion_channel(),
                        ChannelSpec(
                            name="🎓-learning-resources",
                            topic="📚 Educational resources, tutorials, and guides "
                            "for improving your trading skills.",
                            position=6,
                        ),
                        ChannelSpec(
                            name="📚-resources",
                            topic="📚 Changelog, documentation, and pinned command guide. Read-only for most users.",
                            position=7,
                            permission_overwrites={
                                "@everyone": {"send_messages": False},
                            },
                        ),
                        ChannelSpec.commands_codex_channel(),
                    ],
                    reason="Category for community interaction",
                ),
                CategorySpec(
                    name="⚙️ ADMIN",
                    position=10,
                    channels=[
                        ChannelSpec.bot_logs_channel(),
                        ChannelSpec(
                            name="📋-admin-commands",
                            topic="🔧 Admin-only bot commands and configuration.",
                            permission_overwrites={
                                "@everyone": {"view_channel": False},
                                "Bot Admin": {"view_channel": True, "send_messages": True},
                            },
                        ),
                        ChannelSpec.reports_channel(),
                        ChannelSpec(
                            name="🔧-service",
                            topic="🔧 Private service/test channel for operator posts (visible to Bot Admins).",
                            permission_overwrites={
                                "@everyone": {"view_channel": False},
                                "Bot Admin": {"view_channel": True, "send_messages": True},
                            },
                        ),
                    ],
                    permission_overwrites={
                        "@everyone": {"view_channel": False},
                        "Bot Admin": {"view_channel": True},
                    },
                    reason="Category for admin operations",
                ),
            ],
        )


# ══════════════════════════════════════════════════════════════════════════════
# SELF-GUIDE IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════


class SelfGuide:
    """
    Self-guiding system for the Discord bot.

    Automatically creates and manages server structure
    based on blueprints.
    """

    def __init__(self, blueprint: Optional[ServerBlueprint] = None):
        """
        Initialize self-guide.

        Args:
            blueprint: Server blueprint to apply (uses default if None)
        """
        self.blueprint = blueprint or ServerBlueprint.default()
        self._created_roles: Dict[str, Any] = {}  # name -> discord.Role
        self._created_channels: Dict[str, Any] = {}  # name -> discord.Channel
        self._created_categories: Dict[str, Any] = {}  # name -> discord.Category

    async def analyze_server(self, guild: "discord.Guild") -> Dict[str, Any]:
        """
        Analyze current server structure.

        Args:
            guild: Discord guild to analyze

        Returns:
            Analysis report
        """
        existing_roles = {r.name: r for r in guild.roles}
        existing_channels = {c.name: c for c in guild.channels}
        existing_categories = {c.name: c for c in guild.categories}

        # Check what needs to be created
        missing_roles = []
        missing_channels = []
        missing_categories = []

        for role_spec in self.blueprint.roles:
            if role_spec.name not in existing_roles:
                missing_roles.append(role_spec.name)

        for cat_spec in self.blueprint.categories:
            if cat_spec.name not in existing_categories:
                missing_categories.append(cat_spec.name)

            for chan_spec in cat_spec.channels:
                if chan_spec.name not in existing_channels:
                    missing_channels.append(chan_spec.name)

        return {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "member_count": guild.member_count,
            "existing_roles": list(existing_roles.keys()),
            "existing_channels": list(existing_channels.keys()),
            "existing_categories": list(existing_categories.keys()),
            "missing_roles": missing_roles,
            "missing_channels": missing_channels,
            "missing_categories": missing_categories,
            "needs_setup": bool(missing_roles or missing_channels or missing_categories),
        }

    async def create_role(
        self,
        guild: "discord.Guild",
        spec: RoleSpec,
    ) -> Optional["discord.Role"]:
        """
        Create a role from specification.

        Args:
            guild: Discord guild
            spec: Role specification

        Returns:
            Created role or None if exists/failed
        """
        import discord

        # Check if exists
        existing = discord.utils.get(guild.roles, name=spec.name)
        if existing:
            logger.info(f"Role '{spec.name}' already exists")
            self._created_roles[spec.name] = existing
            return existing

        try:
            # Build permissions
            permissions = discord.Permissions()
            for perm_name in spec.permissions:
                if hasattr(permissions, perm_name):
                    setattr(permissions, perm_name, True)

            role = await guild.create_role(
                name=spec.name,
                color=discord.Color(spec.color),
                hoist=spec.hoist,
                mentionable=spec.mentionable,
                permissions=permissions,
                reason=spec.reason,
            )

            logger.info(f"Created role: {spec.name}")
            self._created_roles[spec.name] = role
            return role

        except discord.Forbidden:
            logger.error(f"No permission to create role: {spec.name}")
            return None
        except Exception as e:
            logger.error(f"Failed to create role {spec.name}: {e}")
            return None

    async def create_category(
        self,
        guild: "discord.Guild",
        spec: CategorySpec,
    ) -> Optional["discord.CategoryChannel"]:
        """
        Create a category from specification.

        Args:
            guild: Discord guild
            spec: Category specification

        Returns:
            Created category or None
        """
        import discord

        # Check if exists
        existing = discord.utils.get(guild.categories, name=spec.name)
        if existing:
            logger.info(f"Category '{spec.name}' already exists")
            self._created_categories[spec.name] = existing
            return existing

        try:
            # Build permission overwrites
            overwrites = await self._build_overwrites(guild, spec.permission_overwrites)

            category = await guild.create_category(
                name=spec.name,
                overwrites=overwrites,
                reason=spec.reason,
                position=spec.position,
            )

            logger.info(f"Created category: {spec.name}")
            self._created_categories[spec.name] = category
            return category

        except discord.Forbidden:
            logger.error(f"No permission to create category: {spec.name}")
            return None
        except Exception as e:
            logger.error(f"Failed to create category {spec.name}: {e}")
            return None

    async def create_channel(
        self,
        guild: "discord.Guild",
        spec: ChannelSpec,
        category: Optional["discord.CategoryChannel"] = None,
    ) -> Optional["discord.TextChannel"]:
        """
        Create a channel from specification.

        Args:
            guild: Discord guild
            spec: Channel specification
            category: Parent category (optional)

        Returns:
            Created channel or None
        """
        import discord

        # Check if exists
        existing = discord.utils.get(guild.text_channels, name=spec.name)
        if existing:
            logger.info(f"Channel '{spec.name}' already exists")
            self._created_channels[spec.name] = existing
            return existing

        try:
            # Build permission overwrites
            overwrites = await self._build_overwrites(guild, spec.permission_overwrites)

            channel = await guild.create_text_channel(
                name=spec.name,
                topic=spec.topic,
                category=category,
                overwrites=overwrites,
                slowmode_delay=spec.slowmode,
                nsfw=spec.nsfw,
                reason=spec.reason,
                position=spec.position,
            )

            logger.info(f"Created channel: {spec.name}")
            self._created_channels[spec.name] = channel
            return channel

        except discord.Forbidden:
            logger.error(f"No permission to create channel: {spec.name}")
            return None
        except Exception as e:
            logger.error(f"Failed to create channel {spec.name}: {e}")
            return None

    async def _build_overwrites(
        self,
        guild: "discord.Guild",
        overwrite_specs: Dict[str, Dict[str, bool]],
    ) -> Dict:
        """Build permission overwrites from specifications."""
        import discord

        overwrites = {}

        for target_name, perms in overwrite_specs.items():
            # Find target (role or @everyone)
            if target_name == "@everyone":
                target = guild.default_role
            else:
                target = discord.utils.get(guild.roles, name=target_name)
                if target is None:
                    target = self._created_roles.get(target_name)

            if target is None:
                logger.warning(f"Could not find role for overwrites: {target_name}")
                continue

            # Build permission overwrite
            allow = discord.Permissions()
            deny = discord.Permissions()

            for perm_name, allowed in perms.items():
                if hasattr(allow, perm_name):
                    if allowed:
                        setattr(allow, perm_name, True)
                    else:
                        setattr(deny, perm_name, True)

            overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)

        return overwrites

    async def apply_blueprint(
        self,
        guild: "discord.Guild",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply the blueprint to a server.

        Args:
            guild: Discord guild
            dry_run: If True, only report what would be created

        Returns:
            Report of actions taken
        """
        report = {
            "roles_created": [],
            "categories_created": [],
            "channels_created": [],
            "errors": [],
            "dry_run": dry_run,
        }

        if dry_run:
            analysis = await self.analyze_server(guild)
            report["would_create"] = {
                "roles": analysis["missing_roles"],
                "categories": analysis["missing_categories"],
                "channels": analysis["missing_channels"],
            }
            return report

        # Clean up duplicate "service" channels and known mis-typed names before applying blueprint
        try:
            # 1) Remove obvious mis-typed channel names
            misnames = ["sevuce", "sevice", "sevre", "sevrce"]
            for ch in list(guild.text_channels):
                if ch.name in misnames:
                    try:
                        await ch.delete(reason="Cleanup mis-typed duplicate channel by SelfGuide")
                        logger.info(f"Deleted mis-typed channel: {ch.name}")
                        report["channels_created"].append(f"deleted:{ch.name}")
                    except Exception as e:
                        report["errors"].append(f"Failed to delete channel {ch.name}: {e}")

            # 2) Detect duplicate 'service' channels (keep canonical '🔧-service')
            service_candidates = []
            import re

            for ch in list(guild.text_channels):
                # Normalize: remove non-letters and lower-case
                norm = re.sub(r"[^a-z]", "", ch.name.lower())
                if norm == "service":
                    service_candidates.append(ch)

            if len(service_candidates) > 1:
                # Prefer to keep the canonical '🔧-service' if present
                keep = next((c for c in service_candidates if c.name == "🔧-service"), None)
                if keep is None:
                    keep = service_candidates[0]

                for ch in service_candidates:
                    if ch is keep:
                        continue
                    try:
                        await ch.delete(reason="Remove duplicate service channel; keep canonical '🔧-service'")
                        logger.info(f"Deleted duplicate service channel: {ch.name}")
                        report["channels_created"].append(f"deleted:{ch.name}")
                    except Exception as e:
                        report["errors"].append(f"Failed to delete channel {ch.name}: {e}")

        except Exception as e:
            logger.warning(f"Cleanup step failed: {e}")

        # Create roles first
        for role_spec in self.blueprint.roles:
            try:
                role = await self.create_role(guild, role_spec)
                if role:
                    report["roles_created"].append(role.name)
            except Exception as e:
                report["errors"].append(f"Role {role_spec.name}: {e}")

        # Small delay to let Discord process
        await asyncio.sleep(0.5)

        # Create categories and their channels
        for cat_spec in self.blueprint.categories:
            try:
                category = await self.create_category(guild, cat_spec)
                if category:
                    report["categories_created"].append(category.name)

                    # Create channels in this category
                    for chan_spec in cat_spec.channels:
                        try:
                            channel = await self.create_channel(guild, chan_spec, category)
                            if channel:
                                report["channels_created"].append(channel.name)
                            await asyncio.sleep(0.3)  # Rate limit protection
                        except Exception as e:
                            report["errors"].append(f"Channel {chan_spec.name}: {e}")

            except Exception as e:
                report["errors"].append(f"Category {cat_spec.name}: {e}")

        logger.info(
            f"Blueprint applied: {len(report['roles_created'])} roles, "
            f"{len(report['categories_created'])} categories, "
            f"{len(report['channels_created'])} channels"
        )

        return report

    async def create_invite(
        self,
        channel: "discord.TextChannel",
        max_age: int = 86400,  # 24 hours
        max_uses: int = 0,  # Unlimited
        unique: bool = True,
        reason: str = "Digest Bot invite",
    ) -> Optional[str]:
        """
        Create an invite link for the server.

        Args:
            channel: Channel to create invite for
            max_age: Invite expiry in seconds (0 = never)
            max_uses: Max uses (0 = unlimited)
            unique: Create unique invite
            reason: Audit log reason

        Returns:
            Invite URL or None if failed
        """
        import discord

        try:
            invite = await channel.create_invite(
                max_age=max_age,
                max_uses=max_uses,
                unique=unique,
                reason=reason,
            )

            logger.info(f"Created invite: {invite.url}")
            return invite.url

        except discord.Forbidden:
            logger.error("No permission to create invite")
            return None
        except Exception as e:
            logger.error(f"Failed to create invite: {e}")
            return None

    def get_channel(self, name: str) -> Optional[Any]:
        """Get a created channel by name."""
        return self._created_channels.get(name)

    def get_role(self, name: str) -> Optional[Any]:
        """Get a created role by name."""
        return self._created_roles.get(name)
