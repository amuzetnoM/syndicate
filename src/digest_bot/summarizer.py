#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
#  Digest Bot - Summarizer Module
#  Copyright (c) 2025 SIRIUS Alpha
# ══════════════════════════════════════════════════════════════════════════════
"""
Summarizer module for generating daily digests.

Features:
- Intelligent prompt engineering
- Document chunking for large inputs
- YAML frontmatter extraction
- Multi-document context synthesis
"""

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

from .config import Config, get_config
from .file_gate import Document, GateStatus
from .llm import GenerationConfig, LLMProvider, get_provider_with_fallback

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a senior financial analyst specializing in precious metals markets.
You produce concise, actionable intelligence briefs for traders and portfolio managers.
Your analysis is sharp, direct, and backed by the data presented.
You avoid speculation and focus on observable patterns and measurable signals."""

DIGEST_PROMPT_TEMPLATE = """# Daily Intelligence Digest Request

## Context
Today's date: {date}

You have access to three documents from the Syndicate analysis system:

---
## Document 1: Pre-Market Plan
{premarket_content}

---
## Document 2: Daily Journal
{journal_content}

---
## Document 3: Weekly Report (Reference)
{weekly_content}

---

## Your Task

Synthesize these documents into a **Daily Digest** with the following structure:

### 1. Key Takeaways (3-5 bullets)
- Focus on the most significant market developments
- Highlight any alignment or divergence between pre-market expectations and actual outcomes
- Note technical levels that were tested or broken

### 2. Actionable Next Steps (2-3 bullets)
- Specific actions for the next trading session
- Include price levels, indicators to watch, or events to monitor
- Be concrete: "Watch gold at $2,400 support" not "Monitor gold levels"

### 3. Rationale (2-3 sentences)
- Explain your reasoning connecting the data to your conclusions
- Reference specific indicators, prices, or events from the documents

## Output Guidelines
- Maximum 300 words total
- No filler phrases ("In conclusion", "It's worth noting", etc.)
- Use bullet points, not paragraphs
- Be direct and actionable
- If data conflicts, note the discrepancy

Begin your digest now:"""


FALLBACK_PROMPT_TEMPLATE = """Summarize the following market analysis documents into a brief digest.

Pre-Market Analysis:
{premarket_content}

Daily Journal:
{journal_content}

Weekly Context:
{weekly_content}

Provide:
1. Key Takeaways (3-5 bullets)
2. Actionable Next Steps (2-3 bullets)
3. Brief Rationale (2 sentences)

Keep response under 300 words. Be direct and specific."""


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT PROCESSING
# ══════════════════════════════════════════════════════════════════════════════


def extract_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find closing ---
    lines = content.split("\n")
    end_idx = None

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    # Parse frontmatter
    frontmatter_lines = lines[1:end_idx]
    frontmatter = {}

    for line in frontmatter_lines:
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Handle lists
            if value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]

            frontmatter[key] = value

    # Return remaining content
    remaining = "\n".join(lines[end_idx + 1 :]).strip()
    return frontmatter, remaining


def truncate_content(content: str, max_tokens: int = 1500) -> str:
    """
    Truncate content to approximate token limit.

    Uses rough estimate of 1 token ≈ 4 characters.

    Args:
        content: Content to truncate
        max_tokens: Maximum tokens

    Returns:
        Truncated content
    """
    max_chars = max_tokens * 4

    if len(content) <= max_chars:
        return content

    # Truncate and add indicator
    truncated = content[: max_chars - 50]

    # Try to break at paragraph or sentence
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.7:
        truncated = truncated[:last_para]
    else:
        last_sentence = truncated.rfind(". ")
        if last_sentence > max_chars * 0.7:
            truncated = truncated[: last_sentence + 1]

    return truncated + "\n\n[... content truncated for length ...]"


def clean_content(content: str) -> str:
    """
    Clean and normalize document content.

    Args:
        content: Raw document content

    Returns:
        Cleaned content
    """
    # Remove frontmatter
    _, content = extract_frontmatter(content)

    # Remove excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Remove image references (we don't need them for text summary)
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

    # Clean up horizontal rules
    content = re.sub(r"^-{3,}$", "", content, flags=re.MULTILINE)
    content = re.sub(r"^={3,}$", "", content, flags=re.MULTILINE)

    return content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARIZER CLASS
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class DigestResult:
    """
    Result of digest generation.

    Attributes:
        content: Generated digest content
        success: Whether generation succeeded
        error: Error message if failed
        metadata: Generation metadata
    """

    content: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Summarizer:
    """
    Generates daily digests from input documents.

    Uses configured LLM provider to synthesize
    pre-market, journal, and weekly documents into
    concise actionable summaries.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        provider: Optional[LLMProvider] = None,
    ):
        """
        Initialize summarizer.

        Args:
            config: Configuration object
            provider: LLM provider (creates from config if None)
        """
        self.config = config or get_config()
        self._provider = provider
        self._provider_loaded = False

    @property
    def provider(self) -> LLMProvider:
        """Get or create LLM provider with automatic fallback."""
        if self._provider is None:
            # Use fallback-enabled provider creation
            self._provider = get_provider_with_fallback(self.config)
            self._provider_loaded = True  # Already loaded by fallback function
        return self._provider

    def _ensure_provider_loaded(self) -> None:
        """Ensure LLM provider is loaded."""
        if not self._provider_loaded:
            # Access provider property which handles loading
            _ = self.provider
            self._provider_loaded = True

    def _prepare_document(
        self,
        doc: Optional[Document],
        max_tokens: int = 1500,
    ) -> str:
        """
        Prepare document content for prompt.

        Args:
            doc: Document to prepare
            max_tokens: Max tokens for this document

        Returns:
            Cleaned and truncated content
        """
        if doc is None or not doc.content:
            return "[Document not available]"

        content = clean_content(doc.content)
        content = truncate_content(content, max_tokens)

        return content

    def build_prompt(
        self,
        status: GateStatus,
        target_date: Optional[date] = None,
    ) -> str:
        """
        Build the LLM prompt from input documents.

        Args:
            status: Gate status with documents
            target_date: Date for the digest

        Returns:
            Formatted prompt string
        """
        target = target_date or date.today()

        # Prepare each document with appropriate token budget
        # Total budget ~4k tokens, reserve ~1k for output
        premarket_content = self._prepare_document(status.premarket_doc, max_tokens=1000)
        journal_content = self._prepare_document(status.journal_doc, max_tokens=1200)
        weekly_content = self._prepare_document(status.weekly_doc, max_tokens=800)

        # Build prompt
        prompt = DIGEST_PROMPT_TEMPLATE.format(
            date=target.isoformat(),
            premarket_content=premarket_content,
            journal_content=journal_content,
            weekly_content=weekly_content,
        )

        # Prepend system prompt for models that support it
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"

        return full_prompt

    def generate(
        self,
        status: GateStatus,
        target_date: Optional[date] = None,
    ) -> DigestResult:
        """
        Generate digest from input documents.

        Args:
            status: Gate status with validated documents
            target_date: Date for the digest

        Returns:
            DigestResult with generated content
        """
        target = target_date or date.today()

        # Validate inputs
        if not status.all_inputs_ready:
            missing = []
            if not status.journal_ready:
                missing.append("journal")
            if not status.premarket_ready:
                missing.append("premarket")
            if not status.weekly_ready:
                missing.append("weekly")

            return DigestResult(
                content="",
                success=False,
                error=f"Missing required inputs: {', '.join(missing)}",
            )

        try:
            # Ensure provider is loaded
            self._ensure_provider_loaded()

            # Build prompt
            prompt = self.build_prompt(status, target)
            logger.debug(f"Prompt length: {len(prompt)} chars")

            # Configure generation
            # Note: Using specific stop sequences to prevent document boundary confusion
            # Avoid "---" alone as it's too common in markdown
            gen_config = GenerationConfig(
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                stop_sequences=["## Document 1:", "## Document 2:", "## Document 3:"],
            )

            # Generate with retry
            response = self.provider.generate_with_retry(
                prompt=prompt,
                config=gen_config,
                max_retries=self.config.llm.max_retries,
                retry_delay=self.config.llm.retry_delay,
            )

            # Validate response
            if not response.text or len(response.text.strip()) < 50:
                return DigestResult(
                    content="",
                    success=False,
                    error="LLM returned empty or too short response",
                    metadata={"raw_response": response.raw_response},
                )

            logger.info(
                f"Generated digest: {response.tokens_used} tokens in "
                f"{response.generation_time:.2f}s "
                f"({response.tokens_per_second:.1f} tok/s)"
            )

            return DigestResult(
                content=response.text.strip(),
                success=True,
                metadata={
                    "tokens_used": response.tokens_used,
                    "generation_time": response.generation_time,
                    "model": response.model,
                    "provider": response.provider,
                    "finish_reason": response.finish_reason,
                },
            )

        except Exception as e:
            logger.error(f"Digest generation failed: {e}")
            return DigestResult(
                content="",
                success=False,
                error=str(e),
            )

    def generate_fallback(
        self,
        status: GateStatus,
        target_date: Optional[date] = None,
    ) -> DigestResult:
        """
        Generate digest with simpler fallback prompt.

        Use when primary generation fails.

        Args:
            status: Gate status with documents
            target_date: Date for digest

        Returns:
            DigestResult
        """
        if not status.all_inputs_ready:
            return DigestResult(
                content="",
                success=False,
                error="Missing required inputs",
            )

        try:
            self._ensure_provider_loaded()

            # Simpler prompt with less context
            prompt = FALLBACK_PROMPT_TEMPLATE.format(
                premarket_content=self._prepare_document(status.premarket_doc, max_tokens=600),
                journal_content=self._prepare_document(status.journal_doc, max_tokens=800),
                weekly_content=self._prepare_document(status.weekly_doc, max_tokens=400),
            )

            gen_config = GenerationConfig(
                max_tokens=400,
                temperature=0.2,
            )

            response = self.provider.generate_with_retry(
                prompt=prompt,
                config=gen_config,
                max_retries=2,
                retry_delay=1.0,
            )

            return DigestResult(
                content=response.text.strip(),
                success=bool(response.text),
                metadata={
                    "fallback": True,
                    "tokens_used": response.tokens_used,
                },
            )

        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
            return DigestResult(
                content="",
                success=False,
                error=f"Fallback failed: {e}",
            )

    def close(self) -> None:
        """Unload LLM provider."""
        if self._provider is not None and self._provider_loaded:
            self._provider.unload()
            self._provider_loaded = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
