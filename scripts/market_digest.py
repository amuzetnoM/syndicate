#!/usr/bin/env python3
"""
Market Digest Generator
Creates a proper market-focused digest from the day's documents.
This is the PUBLIC-FACING digest - no audit logs, no sanitizer info.
"""

import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root
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


class MarketDigestGenerator:
    """Generates a market-focused digest from daily documents."""

    def __init__(self):
        self.output_dir = Path(os.path.expanduser("~/syndicate/output"))
        self.reports_dir = self.output_dir / "reports"

    def find_todays_documents(self, target_date: date) -> Dict[str, Path]:
        """Find all market documents for today."""
        date_str = target_date.strftime("%Y-%m-%d")
        docs = {}

        # Premarket
        for p in self.reports_dir.glob(f"**/PreMarket_{date_str}.md"):
            docs["premarket"] = p
            break

        # Journal
        for p in self.output_dir.glob(f"Journal_{date_str}.md"):
            docs["journal"] = p
            break
        if "journal" not in docs:
            for p in self.output_dir.glob(f"**/Journal_{date_str}.md"):
                docs["journal"] = p
                break

        # Catalysts
        for p in self.reports_dir.glob(f"**/Catalysts_{date_str}.md"):
            docs["catalysts"] = p
            break

        # Economic Calendar
        for p in self.reports_dir.glob(f"**/EconCalendar_{date_str}.md"):
            docs["economic"] = p
            break

        # Research reports
        research = []
        for p in self.reports_dir.glob(f"**/*_{date_str}.md"):
            if "PreMarket" not in p.name and "Catalysts" not in p.name and "EconCalendar" not in p.name:
                research.append(p)
        if research:
            docs["research"] = research

        return docs

    def extract_key_points(self, content: str, doc_type: str) -> List[str]:
        """Extract key points from document content."""
        points = []

        # Strip frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]

        if doc_type == "premarket":
            # Extract bias
            bias_match = re.search(r"(?:overall\s+)?bias[:\s]+([^\n]+)", content, re.I)
            if bias_match:
                points.append(f"**Bias:** {bias_match.group(1).strip()}")

            # Extract key levels
            levels_match = re.search(r"key\s+levels?[:\s]+([^\n]+)", content, re.I)
            if levels_match:
                points.append(f"**Levels:** {levels_match.group(1).strip()}")

            # Extract watchlist
            watch_match = re.search(r"watch(?:list)?[:\s]+([^\n]+)", content, re.I)
            if watch_match:
                points.append(f"**Watch:** {watch_match.group(1).strip()}")

        elif doc_type == "journal":
            # Extract trades or reflection
            reflection_match = re.search(r"(?:reflection|summary|key\s+takeaway)[:\s]+([^\n]+)", content, re.I)
            if reflection_match:
                points.append(reflection_match.group(1).strip())

        elif doc_type == "catalysts":
            # Count catalysts
            catalyst_count = len(re.findall(r"^[-*]\s+", content, re.M))
            if catalyst_count:
                points.append(f"**{catalyst_count}** live catalysts identified")

        elif doc_type == "economic":
            # Count events
            event_count = len(re.findall(r"\d{1,2}:\d{2}", content))
            if event_count:
                points.append(f"**{event_count}** economic events scheduled")

        # Fallback: extract first meaningful sentence
        if not points:
            sentences = re.split(r"[.!?]\s+", content[:500])
            for s in sentences:
                s = s.strip()
                if len(s) > 20 and not s.startswith("#"):
                    points.append(s[:150])
                    break

        return points[:3]  # Max 3 points per doc

    def generate_digest(self, target_date: Optional[date] = None) -> str:
        """Generate a market-focused digest."""
        target_date = target_date or date.today()
        docs = self.find_todays_documents(target_date)

        if not docs:
            return ""

        lines = []
        lines.append("# 📊 Market Digest")
        lines.append(f"*{target_date.strftime('%A, %B %d, %Y')}*")
        lines.append("")
        lines.append("━" * 35)
        lines.append("")

        # Pre-market section
        if "premarket" in docs:
            content = docs["premarket"].read_text(encoding="utf-8")
            points = self.extract_key_points(content, "premarket")
            lines.append("## 📈 Pre-Market")
            for p in points:
                lines.append(f"• {p}")
            lines.append("")

        # Catalysts section
        if "catalysts" in docs:
            content = docs["catalysts"].read_text(encoding="utf-8")
            points = self.extract_key_points(content, "catalysts")
            lines.append("## 🚀 Catalysts")
            for p in points:
                lines.append(f"• {p}")
            lines.append("")

        # Economic section
        if "economic" in docs:
            content = docs["economic"].read_text(encoding="utf-8")
            points = self.extract_key_points(content, "economic")
            lines.append("## 📅 Economic Calendar")
            for p in points:
                lines.append(f"• {p}")
            lines.append("")

        # Journal section
        if "journal" in docs:
            content = docs["journal"].read_text(encoding="utf-8")
            points = self.extract_key_points(content, "journal")
            lines.append("## 📔 Journal Highlights")
            for p in points:
                lines.append(f"• {p}")
            lines.append("")

        # Research section
        if "research" in docs and isinstance(docs["research"], list):
            lines.append("## 🔬 Research")
            lines.append(f"• **{len(docs['research'])}** reports generated today")
            lines.append("")

        # Footer
        lines.append("━" * 35)
        lines.append(f"*Generated by Syndicate • {datetime.now().strftime('%H:%M')} UTC+5*")

        return "\n".join(lines)

    def generate_llm_digest(self, target_date: Optional[date] = None) -> str:
        """Use LLM to generate a narrative digest from documents."""
        target_date = target_date or date.today()
        docs = self.find_todays_documents(target_date)

        if not docs:
            return self.generate_digest(target_date)  # Fallback

        # Collect document content
        doc_contents = {}
        for doc_type, path in docs.items():
            if doc_type == "research":
                continue  # Skip research list
            if isinstance(path, Path):
                content = path.read_text(encoding="utf-8")
                # Strip frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                doc_contents[doc_type] = content[:2000]  # Truncate

        if not doc_contents:
            return self.generate_digest(target_date)

        # Build LLM prompt
        prompt = f"""You are creating a daily market digest for {target_date.strftime('%A, %B %d, %Y')}.

Analyze the following documents and create a CONCISE, professional digest that:
1. Summarizes the key market outlook and bias
2. Highlights important catalysts or events
3. Notes any trading opportunities or risks
4. Is written in an engaging, professional tone

DOCUMENTS:
"""
        for doc_type, content in doc_contents.items():
            prompt += f"\n--- {doc_type.upper()} ---\n{content[:1500]}\n"

        prompt += """

Create a digest that is:
- 150-250 words maximum
- Professional but engaging
- Focuses on actionable insights
- Uses bullet points for clarity
- Does NOT mention system operations, errors, or technical details

OUTPUT FORMAT:
📊 **Market Digest - [Date]**

[Brief market overview paragraph]

**Key Points:**
• Point 1
• Point 2
• Point 3

**Watch Today:**
• Item 1
• Item 2

*Syndicate Intelligence*
"""

        try:
            from src.digest_bot.llm import get_provider_with_fallback

            llm = get_provider_with_fallback()
            response = llm.generate(prompt, max_tokens=600)
            return response.strip()
        except Exception as e:
            print(f"LLM generation failed: {e}, using template digest")
            return self.generate_digest(target_date)


async def publish_market_digest(target_date: Optional[date] = None):
    """Publish the market digest to Discord."""
    import discord

    target_date = target_date or date.today()
    generator = MarketDigestGenerator()

    # Try LLM digest first, fallback to template
    digest = generator.generate_llm_digest(target_date)
    if not digest:
        print(f"No documents found for {target_date}")
        return

    print(f"Generated digest ({len(digest)} chars)")

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        for guild in client.guilds:
            channel = discord.utils.get(guild.text_channels, name="📊-daily-digests")
            if not channel:
                print("Digest channel not found")
                continue

            # Create embed
            embed = discord.Embed(
                title="📊 Daily Market Digest", description=digest, color=0xF39C12, timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Syndicate • {target_date.strftime('%B %d, %Y')}")

            try:
                await channel.send(embed=embed)
                print(f"✓ Published digest to #{channel.name}")
            except Exception as e:
                print(f"Error: {e}")

        await client.close()

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not set")
        return

    await client.start(token)


if __name__ == "__main__":
    import asyncio

    asyncio.run(publish_market_digest())
