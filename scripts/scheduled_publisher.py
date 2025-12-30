#!/usr/bin/env python3
"""
Scheduled Publisher for Discord - Premium Formatting
Publishes documents to Discord with polished, Discord-native formatting.
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()

import discord


class DiscordFormatter:
    """Formats markdown content for Discord with premium styling."""

    @staticmethod
    def clean_markdown(content: str) -> str:
        """Clean and adapt markdown for Discord compatibility."""
        # Remove complex HTML tables and replace with simpler format
        content = re.sub(r"<table>.*?</table>", "[Table removed for Discord]", content, flags=re.DOTALL)

        # Convert markdown tables to Discord-friendly format
        lines = content.split("\n")
        cleaned = []
        in_table = False
        table_data = []

        for line in lines:
            # Detect table start
            if "|" in line and line.strip().startswith("|"):
                in_table = True
                # Skip separator lines
                if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
                    continue
                # Extract cells
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells:
                    table_data.append(cells)
            elif in_table:
                # End of table, format it
                if table_data:
                    cleaned.append("```")
                    for row in table_data:
                        cleaned.append(" | ".join(row))
                    cleaned.append("```")
                    table_data = []
                in_table = False
                cleaned.append(line)
            else:
                cleaned.append(line)

        # Handle any remaining table
        if table_data:
            cleaned.append("```")
            for row in table_data:
                cleaned.append(" | ".join(row))
            cleaned.append("```")

        content = "\n".join(cleaned)

        # Clean up excessive newlines
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Convert headers to Discord bold
        content = re.sub(r"^#{1,3}\s+(.+)$", r"**\1**", content, flags=re.MULTILINE)

        # Clean up bullet points
        content = re.sub(r"^[-*]\s+", "• ", content, flags=re.MULTILINE)

        return content.strip()

    @staticmethod
    def extract_key_info(content: str, doc_type: str) -> dict:
        """Extract key information for embed fields."""
        info = {}

        if doc_type == "premarket":
            # Extract bias
            bias_match = re.search(r"(?:overall\s+)?bias[:\s]+([^\n]+)", content, re.I)
            if bias_match:
                info["bias"] = bias_match.group(1).strip()[:100]

            # Extract key levels
            levels_match = re.search(r"key\s+levels?[:\s]+([^\n]+)", content, re.I)
            if levels_match:
                info["levels"] = levels_match.group(1).strip()[:100]

        elif doc_type == "journal":
            # Extract mood/reflection
            mood_match = re.search(r"(?:mood|reflection)[:\s]+([^\n]+)", content, re.I)
            if mood_match:
                info["mood"] = mood_match.group(1).strip()[:100]

        return info


class ScheduledPublisher:
    """Handles scheduled publishing with premium Discord formatting."""

    CHANNEL_MAP = {
        "premarket": "📈-premarket-plans",
        "catalyst": "🚨-alerts",
        "economic": "📚-research-journal",
        "journal": "📔-trading-journal",
        "digest": "📊-daily-digests",
        "research": "📚-research-journal",
        "report": "📥-reports",
    }

    COLORS = {
        "premarket": 0x3498DB,  # Blue
        "journal": 0x9B59B6,  # Purple
        "catalyst": 0xE74C3C,  # Red
        "economic": 0x2ECC71,  # Green
        "digest": 0xF39C12,  # Orange
        "research": 0x1ABC9C,  # Teal
    }

    EMOJIS = {
        "premarket": "📈",
        "journal": "📔",
        "catalyst": "🚀",
        "economic": "📅",
        "digest": "📊",
        "research": "🔬",
    }

    TITLES = {
        "premarket": "Pre-Market Analysis",
        "journal": "Trading Journal",
        "catalyst": "Live Catalysts",
        "economic": "Economic Calendar",
        "digest": "Daily Digest",
        "research": "Research Report",
    }

    def __init__(self):
        self.output_dir = Path(os.path.expanduser("~/syndicate/output"))
        self.reports_dir = self.output_dir / "reports"
        self.formatter = DiscordFormatter()

    def find_documents(self, doc_type: str, target_date: date) -> List[Path]:
        """Find documents of a given type for a specific date."""
        docs = []
        date_str = target_date.strftime("%Y-%m-%d")

        if doc_type == "premarket":
            docs.extend(self.reports_dir.glob(f"**/PreMarket_{date_str}.md"))
            docs.extend(self.reports_dir.glob(f"premarket_{date_str}.md"))
        elif doc_type == "journal":
            docs.extend(self.output_dir.glob(f"Journal_{date_str}.md"))
            docs.extend(self.output_dir.glob(f"**/Journal_{date_str}.md"))
        elif doc_type == "catalyst":
            docs.extend(self.reports_dir.glob(f"**/Catalysts_{date_str}.md"))
        elif doc_type == "economic":
            docs.extend(self.reports_dir.glob(f"**/EconCalendar_{date_str}.md"))
        elif doc_type == "digest":
            docs.extend((self.output_dir / "digests").glob(f"digest_{date_str}.md"))
        elif doc_type == "research":
            docs.extend(self.reports_dir.glob(f"**/*_{date_str}.md"))

        return list(set(docs))

    def read_document(self, path: Path) -> str:
        """Read document, stripping frontmatter."""
        content = path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content

    def create_embed(self, content: str, doc_type: str, doc_name: str) -> discord.Embed:
        """Create a polished Discord embed from document content."""
        today = date.today()

        # Clean content for Discord
        cleaned = self.formatter.clean_markdown(content)

        # Extract key info
        key_info = self.formatter.extract_key_info(content, doc_type)

        # Truncate if needed (embed description max is 4096)
        if len(cleaned) > 3900:
            cleaned = cleaned[:3900] + "\n\n*[Content truncated - see full report in Notion]*"

        # Create embed
        embed = discord.Embed(
            title=f"{self.EMOJIS.get(doc_type, '📄')} {self.TITLES.get(doc_type, 'Report')}",
            description=cleaned,
            color=self.COLORS.get(doc_type, 0x7289DA),
            timestamp=datetime.utcnow(),
        )

        # Add key info as fields
        for key, value in key_info.items():
            embed.add_field(name=key.title(), value=value, inline=True)

        # Footer
        embed.set_footer(text=f"Syndicate • {today.strftime('%A, %B %d, %Y')}")

        return embed

    def create_text_message(self, content: str, doc_type: str) -> List[str]:
        """Create formatted text messages for longer content."""
        cleaned = self.formatter.clean_markdown(content)

        header = f"{self.EMOJIS.get(doc_type, '📄')} **{self.TITLES.get(doc_type, 'Report')}**\n"
        header += f"*{date.today().strftime('%A, %B %d, %Y')}*\n"
        header += "━" * 30 + "\n\n"

        full_content = header + cleaned

        # Split into chunks (Discord max is 2000)
        max_len = 1950
        chunks = []

        while len(full_content) > max_len:
            # Find good split point
            split_at = full_content.rfind("\n\n", 0, max_len)
            if split_at == -1:
                split_at = full_content.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len

            chunks.append(full_content[:split_at])
            full_content = full_content[split_at:].strip()

        if full_content:
            chunks.append(full_content)

        return chunks

    async def publish(self, doc_type: str, target_date: Optional[date] = None, use_embed: bool = True):
        """Publish documents to Discord with premium formatting."""
        target_date = target_date or date.today()
        channel_name = self.CHANNEL_MAP.get(doc_type)

        if not channel_name:
            print(f"Unknown document type: {doc_type}")
            return

        docs = self.find_documents(doc_type, target_date)
        if not docs:
            print(f"No {doc_type} documents found for {target_date}")
            return

        print(f"Found {len(docs)} {doc_type} document(s) for {target_date}")

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            for guild in client.guilds:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if not channel:
                    print(f"Channel not found: {channel_name}")
                    continue

                for doc_path in docs:
                    print(f"Publishing: {doc_path.name} -> #{channel_name}")
                    content = self.read_document(doc_path)

                    try:
                        if use_embed and len(content) < 4000:
                            # Use embed for shorter content
                            embed = self.create_embed(content, doc_type, doc_path.name)
                            await channel.send(embed=embed)
                        else:
                            # Use text messages for longer content
                            chunks = self.create_text_message(content, doc_type)
                            for i, chunk in enumerate(chunks):
                                await channel.send(chunk)
                                if i < len(chunks) - 1:
                                    await asyncio.sleep(0.5)

                        print(f"  ✓ Published to #{channel_name}")

                    except Exception as e:
                        print(f"  ✗ Error: {e}")

            await client.close()

        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("ERROR: DISCORD_BOT_TOKEN not set")
            return

        await client.start(token)


async def main():
    parser = argparse.ArgumentParser(description="Scheduled Discord Publisher")
    parser.add_argument(
        "type",
        choices=["premarket", "catalyst", "economic", "journal", "digest", "research", "all"],
        help="Type of document to publish",
    )
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--no-embed", action="store_true", help="Use text instead of embeds")

    args = parser.parse_args()
    target_date = date.fromisoformat(args.date) if args.date else date.today()
    publisher = ScheduledPublisher()
    use_embed = not args.no_embed

    if args.type == "all":
        await publisher.publish("premarket", target_date, use_embed)
        await publisher.publish("catalyst", target_date, use_embed)
        await publisher.publish("economic", target_date, use_embed)
    else:
        await publisher.publish(args.type, target_date, use_embed)


if __name__ == "__main__":
    asyncio.run(main())
