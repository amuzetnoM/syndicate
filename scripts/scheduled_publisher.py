#!/usr/bin/env python3
"""
Scheduled Publisher for Discord
Publishes documents to Discord channels on a schedule.

Schedule (UTC+5 / Karachi):
- 7:00 AM: Pre-market, Catalysts, Economic Calendar
- 12:00 PM: Journal (initial)
- 5:00 PM: Digest (comprehensive summary)
- 10:00 PM: Journal (revised with latest news)
- Research: As completed
"""

import argparse
import asyncio
import os
import sys
from datetime import date
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


class ScheduledPublisher:
    """Handles scheduled publishing of documents to Discord."""

    CHANNEL_MAP = {
        "premarket": "📈-premarket-plans",
        "catalyst": "🚨-alerts",
        "economic": "📚-research-journal",
        "journal": "📔-trading-journal",
        "digest": "📊-daily-digests",
        "research": "📚-research-journal",
        "report": "📥-reports",
    }

    def __init__(self):
        self.output_dir = Path(os.path.expanduser("~/syndicate/output"))
        self.reports_dir = self.output_dir / "reports"

    def find_documents(self, doc_type: str, target_date: date) -> List[Path]:
        """Find documents of a given type for a specific date."""
        docs = []
        date_str = target_date.strftime("%Y-%m-%d")

        if doc_type == "premarket":
            # Check organized location
            pattern = f"**/PreMarket_{date_str}.md"
            docs.extend(self.reports_dir.glob(pattern))
            # Check raw location
            docs.extend(self.reports_dir.glob(f"premarket_{date_str}.md"))

        elif doc_type == "journal":
            docs.extend(self.output_dir.glob(f"Journal_{date_str}.md"))
            docs.extend(self.output_dir.glob(f"**/Journal_{date_str}.md"))

        elif doc_type == "catalyst":
            docs.extend(self.reports_dir.glob(f"**/Catalysts_{date_str}.md"))
            docs.extend(self.reports_dir.glob(f"catalysts_{date_str}.md"))

        elif doc_type == "economic":
            docs.extend(self.reports_dir.glob(f"**/EconCalendar_{date_str}.md"))
            docs.extend(self.reports_dir.glob(f"economic_calendar_{date_str}.md"))

        elif doc_type == "digest":
            docs.extend((self.output_dir / "digests").glob(f"digest_{date_str}.md"))

        elif doc_type == "research":
            # All research reports for today
            docs.extend(self.reports_dir.glob(f"**/*_{date_str}.md"))

        return list(set(docs))  # Remove duplicates

    def read_document(self, path: Path) -> str:
        """Read document content, stripping frontmatter if present."""
        content = path.read_text(encoding="utf-8")

        # Strip YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def format_for_discord(self, content: str, doc_type: str, max_length: int = 1900) -> List[str]:
        """Format content for Discord, splitting if necessary."""
        # Add header based on type
        headers = {
            "premarket": "📈 **Pre-Market Analysis**",
            "journal": "📔 **Trading Journal**",
            "catalyst": "🚀 **Live Catalysts**",
            "economic": "📅 **Economic Calendar**",
            "digest": "📊 **Daily Digest**",
            "research": "🔬 **Research Report**",
        }

        header = headers.get(doc_type, "📄 **Report**")
        today = date.today().strftime("%A, %B %d, %Y")
        full_content = f"{header}\n*{today}*\n\n{content}"

        # Split into chunks if too long
        chunks = []
        while len(full_content) > max_length:
            # Find a good split point
            split_at = full_content.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = max_length
            chunks.append(full_content[:split_at])
            full_content = full_content[split_at:].strip()

        if full_content:
            chunks.append(full_content)

        return chunks

    async def publish(self, doc_type: str, target_date: Optional[date] = None):
        """Publish documents of a given type to Discord."""
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

        # Connect to Discord
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
                    chunks = self.format_for_discord(content, doc_type)

                    for i, chunk in enumerate(chunks):
                        try:
                            await channel.send(chunk)
                            if i < len(chunks) - 1:
                                await asyncio.sleep(1)  # Rate limiting
                        except Exception as e:
                            print(f"Error sending message: {e}")

                    print(f"  ✓ Published to #{channel_name}")

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
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD), defaults to today")

    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    publisher = ScheduledPublisher()

    if args.type == "all":
        # Morning batch
        await publisher.publish("premarket", target_date)
        await publisher.publish("catalyst", target_date)
        await publisher.publish("economic", target_date)
    else:
        await publisher.publish(args.type, target_date)


if __name__ == "__main__":
    asyncio.run(main())
