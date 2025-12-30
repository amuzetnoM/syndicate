#!/usr/bin/env python3
"""
Intelligent Response Cog
Real-time autonomous response generation with rate limiting.

Provides:
- @mention response handling
- Rate limiting per user/channel
- Local LLM inference for intelligent responses
- Formatted, compact, truthful outputs
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

try:
    import discord
    from discord.ext import commands
except ImportError:
    discord = None
    commands = None

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter with per-user and per-channel tracking."""

    def __init__(
        self,
        user_limit: int = 5,  # Requests per user per window
        channel_limit: int = 20,  # Requests per channel per window
        window_seconds: int = 60,  # Time window in seconds
    ):
        self.user_limit = user_limit
        self.channel_limit = channel_limit
        self.window_seconds = window_seconds

        self._user_requests: Dict[int, list] = defaultdict(list)
        self._channel_requests: Dict[int, list] = defaultdict(list)

    def _clean_old_requests(self, request_list: list) -> list:
        """Remove requests older than the time window."""
        cutoff = time.time() - self.window_seconds
        return [t for t in request_list if t > cutoff]

    def is_rate_limited(self, user_id: int, channel_id: int) -> tuple[bool, str]:
        """Check if a request is rate limited."""
        now = time.time()

        # Clean old user requests
        self._user_requests[user_id] = self._clean_old_requests(self._user_requests[user_id])

        # Check user limit
        if len(self._user_requests[user_id]) >= self.user_limit:
            remaining = int(self.window_seconds - (now - self._user_requests[user_id][0]))
            return True, f"Rate limit: wait {remaining}s"

        # Clean old channel requests
        self._channel_requests[channel_id] = self._clean_old_requests(self._channel_requests[channel_id])

        # Check channel limit
        if len(self._channel_requests[channel_id]) >= self.channel_limit:
            remaining = int(self.window_seconds - (now - self._channel_requests[channel_id][0]))
            return True, f"Channel busy: wait {remaining}s"

        return False, ""

    def record_request(self, user_id: int, channel_id: int):
        """Record a request for rate limiting."""
        now = time.time()
        self._user_requests[user_id].append(now)
        self._channel_requests[channel_id].append(now)


class IntelligentResponder:
    """Handles intelligent response generation using local LLM."""

    SYSTEM_PROMPT = """You are the Syndicate Intelligence - a precise market analyst and trading system mind.

IDENTITY:
- You are NOT a generic AI assistant
- You are the intelligence behind Syndicate, a trading analysis system
- You speak with authority on markets, trading, and system operations
- Your responses are compact, direct, and truthful

RESPONSE RULES:
1. Be CONCISE - max 200 words unless detail is required
2. Be DIRECT - no filler phrases like "I'd be happy to help"
3. Be HONEST - if you don't know, say so clearly
4. Be SPECIFIC - use concrete numbers and facts
5. Format with markdown for clarity

TOPICS YOU HANDLE:
- Market analysis and trading concepts
- System status and operations
- Document queries (journal, premarket, reports)
- Trading strategies and risk management

TOPICS YOU DECLINE:
- Personal advice beyond trading
- Unrelated general knowledge
- Anything requiring real-time market data you don't have

When asked about system status, refer to the Sentinel for live data.
When asked about documents, summarize from available context."""

    def __init__(self):
        self._llm = None
        self._llm_lock = asyncio.Lock()

    async def _get_llm(self):
        """Lazy-load the LLM provider."""
        if self._llm is None:
            async with self._llm_lock:
                if self._llm is None:
                    try:
                        from src.digest_bot.llm import get_provider_with_fallback

                        self._llm = get_provider_with_fallback()
                        logger.info("IntelligentResponder: LLM loaded")
                    except Exception as e:
                        logger.error(f"Failed to load LLM: {e}")
                        return None
        return self._llm

    async def generate_response(
        self,
        message: str,
        user_name: str,
        channel_name: str,
        context: Optional[str] = None,
    ) -> str:
        """Generate an intelligent response to a message."""

        llm = await self._get_llm()
        if llm is None:
            return "⚠️ Intelligence offline. Try again later."

        # Build prompt
        prompt = f"""{self.SYSTEM_PROMPT}

CURRENT CONTEXT:
- User: {user_name}
- Channel: #{channel_name}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC+5
{f'- Additional Context: {context}' if context else ''}

USER MESSAGE:
{message}

YOUR RESPONSE (compact, direct, truthful):"""

        try:
            # Run LLM inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: llm.generate(prompt, max_tokens=500))

            # Clean up response
            response = response.strip()

            # Truncate if too long
            if len(response) > 1900:
                response = response[:1900] + "..."

            return response

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "⚠️ Processing error. Try rephrasing your question."


class IntelligenceCog(commands.Cog):
    """Discord Cog for intelligent response handling."""

    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = RateLimiter(
            user_limit=5,  # 5 requests per user per minute
            channel_limit=30,  # 30 requests per channel per minute
            window_seconds=60,
        )
        self.responder = IntelligentResponder()
        self._processing: set = set()  # Track messages being processed

        logger.info("IntelligenceCog initialized")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming messages and generate responses for mentions."""

        # Ignore bot messages
        if message.author.bot:
            return

        # Check if we're mentioned
        if not self.bot.user.mentioned_in(message):
            return

        # Skip if message is a command
        if message.content.startswith("!"):
            return

        # Skip if already processing this message
        if message.id in self._processing:
            return

        self._processing.add(message.id)

        try:
            # Rate limiting
            is_limited, limit_msg = self.rate_limiter.is_rate_limited(message.author.id, message.channel.id)

            if is_limited:
                await message.add_reaction("⏳")
                await message.reply(f"⏳ {limit_msg}", mention_author=False)
                return

            # Record the request
            self.rate_limiter.record_request(message.author.id, message.channel.id)

            # Show typing indicator
            async with message.channel.typing():
                # Extract the actual message (remove mention)
                content = message.content
                for mention in message.mentions:
                    content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
                content = content.strip()

                if not content:
                    await message.reply("Yes? What would you like to know?", mention_author=False)
                    return

                # Generate response
                response = await self.responder.generate_response(
                    message=content,
                    user_name=message.author.display_name,
                    channel_name=message.channel.name,
                )

                # Send response
                await message.reply(response, mention_author=False)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.add_reaction("❌")

        finally:
            self._processing.discard(message.id)

    @commands.command(name="ask")
    async def ask_command(self, ctx: commands.Context, *, question: str):
        """Ask the intelligence a question directly."""

        # Rate limiting
        is_limited, limit_msg = self.rate_limiter.is_rate_limited(ctx.author.id, ctx.channel.id)

        if is_limited:
            await ctx.reply(f"⏳ {limit_msg}", mention_author=False)
            return

        self.rate_limiter.record_request(ctx.author.id, ctx.channel.id)

        async with ctx.typing():
            response = await self.responder.generate_response(
                message=question,
                user_name=ctx.author.display_name,
                channel_name=ctx.channel.name,
            )

            await ctx.reply(response, mention_author=False)

    @commands.command(name="intel")
    async def intel_status_command(self, ctx: commands.Context):
        """Quick intelligence status check."""

        embed = discord.Embed(title="🧠 Syndicate Intelligence", color=0x2ECC71, timestamp=datetime.utcnow())

        # Check LLM status
        llm = await self.responder._get_llm()
        llm_status = "✅ Online" if llm else "❌ Offline"

        embed.add_field(name="Intelligence", value=llm_status, inline=True)
        embed.add_field(name="Rate Limit", value=f"{self.rate_limiter.user_limit}/min per user", inline=True)
        embed.add_field(name="Response Mode", value="Local LLM (Phi-3)", inline=True)

        embed.set_footer(text="Ask me anything about markets or the system")

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(IntelligenceCog(bot))
    logger.info("IntelligenceCog loaded")
