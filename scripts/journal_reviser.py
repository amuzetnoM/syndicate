#!/usr/bin/env python3
"""
Journal Reviser
Revises the daily journal with latest news for accountability and context.
Runs at 10 PM UTC+5 to update the journal with end-of-day news.
"""

import argparse
import asyncio
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

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


class JournalReviser:
    """Revises the daily journal with latest news context."""

    def __init__(self):
        self.output_dir = Path(os.path.expanduser("~/syndicate/output"))

    def find_journal(self, target_date: date) -> Optional[Path]:
        """Find today's journal file."""
        date_str = target_date.strftime("%Y-%m-%d")

        # Check various locations
        locations = [
            self.output_dir / f"Journal_{date_str}.md",
            self.output_dir / "journals" / f"Journal_{date_str}.md",
        ]

        for loc in locations:
            if loc.exists():
                return loc

        return None

    def fetch_latest_news(self) -> str:
        """Fetch latest news headlines for context."""
        import requests

        news_items = []

        # Try NewsAPI
        newsapi_key = os.getenv("NEWSAPI_KEY")
        if newsapi_key:
            try:
                resp = requests.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "apiKey": newsapi_key,
                        "category": "business",
                        "language": "en",
                        "pageSize": 5,
                    },
                    timeout=10,
                )
                if resp.ok:
                    data = resp.json()
                    for article in data.get("articles", [])[:5]:
                        news_items.append(f"- {article.get('title', 'N/A')}")
            except Exception as e:
                print(f"NewsAPI error: {e}")

        # Try RSS feeds as fallback
        if not news_items:
            try:
                import feedparser

                feeds = os.getenv("NEWS_RSS_FEEDS", "").split(",")
                for feed_url in feeds[:2]:
                    if feed_url.strip():
                        feed = feedparser.parse(feed_url.strip())
                        for entry in feed.entries[:3]:
                            news_items.append(f"- {entry.get('title', 'N/A')}")
            except Exception as e:
                print(f"RSS error: {e}")

        if news_items:
            return "\n".join(news_items[:5])
        return "No news available at this time."

    def revise_with_llm(self, original_content: str, news_context: str) -> str:
        """Use local LLM to revise the journal with news context."""
        try:
            from src.digest_bot.llm import create_llm_provider

            llm = create_llm_provider()

            prompt = f"""You are a trading journal editor. Your task is to revise the following journal entry by adding context from today's news.

IMPORTANT RULES:
1. Do NOT reformat or restructure the journal
2. Only ADD contextual notes where relevant
3. Add a "End of Day Update" section at the bottom
4. Keep the original voice and style
5. Note any news that validates or contradicts the journal's analysis

ORIGINAL JOURNAL:
{original_content}

TODAY'S NEWS HEADLINES:
{news_context}

Please provide the revised journal with end-of-day context added:"""

            response = llm.generate(prompt, max_tokens=2000)
            return response

        except Exception as e:
            print(f"LLM error: {e}")
            # Fallback: just append news section
            return f"""{original_content}

---

## 📰 End of Day Update
*Revised at {datetime.now().strftime('%I:%M %p')}*

### Latest News Context
{news_context}

*This section was auto-appended for accountability.*
"""

    async def revise_and_publish(self, target_date: Optional[date] = None):
        """Revise the journal and publish to Discord."""
        import discord

        target_date = target_date or date.today()
        journal_path = self.find_journal(target_date)

        if not journal_path:
            print(f"No journal found for {target_date}")
            return

        print(f"Found journal: {journal_path}")

        # Read original content
        original_content = journal_path.read_text(encoding="utf-8")

        # Strip frontmatter for display
        display_content = original_content
        if display_content.startswith("---"):
            parts = display_content.split("---", 2)
            if len(parts) >= 3:
                display_content = parts[2].strip()

        # Fetch news
        print("Fetching latest news...")
        news = self.fetch_latest_news()
        print(f"News items: {len(news.split(chr(10)))}")

        # Revise with LLM
        print("Revising journal with LLM...")
        revised_content = self.revise_with_llm(display_content, news)

        # Publish to Discord
        print("Publishing revised journal to Discord...")

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            for guild in client.guilds:
                channel = discord.utils.get(guild.text_channels, name="📔-trading-journal")
                if not channel:
                    print("Journal channel not found")
                    continue

                # Format message
                header = f"📔 **Trading Journal - REVISED**\n*{target_date.strftime('%A, %B %d, %Y')} - End of Day Update*\n\n"

                # Split if too long
                max_len = 1900
                content = header + revised_content

                while len(content) > max_len:
                    split_at = content.rfind("\n", 0, max_len)
                    if split_at == -1:
                        split_at = max_len
                    await channel.send(content[:split_at])
                    content = content[split_at:].strip()
                    await asyncio.sleep(1)

                if content:
                    await channel.send(content)

                print(f"✓ Revised journal published to #{channel.name}")

            await client.close()

        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            print("ERROR: DISCORD_BOT_TOKEN not set")
            return

        await client.start(token)


async def main():
    parser = argparse.ArgumentParser(description="Journal Reviser")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()
    reviser = JournalReviser()
    await reviser.revise_and_publish(target_date)


if __name__ == "__main__":
    asyncio.run(main())
