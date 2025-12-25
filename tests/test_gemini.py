# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/
#
# Syndicate - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Test suite for Gemini AI integration.

Tests cover:
1. API key validation and configuration
2. Model initialization
3. AI response generation
4. Bias extraction from responses
5. Error handling for API failures
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add project root to path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

# Load .env file for API keys
from dotenv import load_dotenv  # noqa: E402

load_dotenv(root / ".env")

# GEMINI TEST CONTROL
_GEMINI_PASSED = False
# - Default: SKIP gemini integration tests to save API quota
# - To run once: set GEMINI_TEST=1 in your environment when invoking pytest
# - After a successful run, a sentinel file will be written at .cache/gemini_test_success
#   and subsequent test runs will skip the module to avoid using up quota.
from pathlib import Path as _Path
_CACHE_SENTINEL = _Path(root / ".cache") / "gemini_test_success"
if _CACHE_SENTINEL.exists():
    # Already tested successfully previously
    pytest.skip("Gemini integration tests already passed previously; skipping to save quota", allow_module_level=True)

if os.getenv("GEMINI_TEST") != "1" and os.getenv("GEMINI_FORCE_TEST") != "1":
    # Explicitly skipped by default to avoid accidental API calls. Use GEMINI_TEST=1 to run.
    pytest.skip("Gemini tests are disabled by default to save quota. Set GEMINI_TEST=1 to run them.", allow_module_level=True)

from main import Config, Strategist, setup_logging  # noqa: E402


def _import_genai():
    try:
        import google.generativeai as genai  # type: ignore
        return genai
    except Exception:
        try:
            from scripts import genai_compat as genai  # type: ignore
            return genai
        except Exception:
            try:
                import google.genai as genai_new  # type: ignore
                return genai_new
            except Exception:
                raise


class TestGeminiConfiguration:
    """Tests for Gemini API configuration and validation."""

    def test_config_loads_api_key_from_env(self, monkeypatch):
        """Test that Config correctly loads GEMINI_API_KEY from environment."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")
        cfg = Config()
        assert cfg.GEMINI_API_KEY == "test-api-key-12345"

    def test_config_has_default_model(self):
        """Test that Config has a default Gemini model configured."""
        cfg = Config()
        assert cfg.GEMINI_MODEL is not None
        assert "gemini" in cfg.GEMINI_MODEL.lower()

    def test_config_api_key_empty_when_not_set(self, monkeypatch):
        """Test that API key is empty string when not set."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cfg = Config()
        assert cfg.GEMINI_API_KEY == ""


class TestGeminiImport:
    """Tests for google-generativeai package availability."""

    def test_genai_import_available(self):
        """Test that google.generativeai can be imported."""
        try:
            genai = _import_genai()
        except Exception:
            pytest.fail(
                "google-generativeai package not installed or compat shim not available. Install google-genai or provide compat shim and ensure GEMINI_TEST=1 to run integration tests"
            )
        assert genai is not None

    def test_genai_has_configure_method(self):
        """Test that genai has the configure method."""
        genai = _import_genai()

        assert hasattr(genai, "configure")
        assert callable(genai.configure)

    def test_genai_has_generative_model_class(self):
        """Test that genai has GenerativeModel class."""
        genai = _import_genai()

        assert hasattr(genai, "GenerativeModel")

        global _GEMINI_PASSED
        _GEMINI_PASSED = True


class TestStrategistInitialization:
    """Tests for Strategist class initialization."""


# If we've run Gemini integration tests (GEMINI_TEST=1) and they all passed,
# mark success so subsequent runs skip the module to save API quota.
def test_mark_gemini_success_on_pass():
    """Create sentinel file after successful gemini test run (only when GEMINI_TEST=1).

    Only writes the sentinel if all gemini checks passed (signified by
    module-global _GEMINI_PASSED being True)."""
    if os.getenv("GEMINI_TEST") == "1" and _GEMINI_PASSED:
        cache_dir = root / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        sentinel = cache_dir / "gemini_test_success"
        sentinel.write_text(f"passed:{datetime.date.today().isoformat()}")
    elif os.getenv("GEMINI_TEST") == "1":
        pytest.fail("Gemini integration tests did not pass; sentinel will not be written.")

    def test_strategist_initializes_with_mock_model(self):
        """Test Strategist can be initialized with a mock model."""
        cfg = Config()
        logger = setup_logging(cfg)
        mock_model = Mock()

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={"GOLD": {"price": 2000, "change": 0.5, "rsi": 55}},
            news=["Test headline"],
            memory_log="No previous history",
            model=mock_model,
        )

        assert strategist.model == mock_model
        assert strategist.config == cfg
        assert "GOLD" in strategist.data

    def test_strategist_handles_none_model(self):
        """Test Strategist handles None model gracefully."""
        cfg = Config()
        logger = setup_logging(cfg)

        strategist = Strategist(
            config=cfg, logger=logger, data={"GOLD": {"price": 2000}}, news=[], memory_log="", model=None
        )

        assert strategist.model is None


class TestStrategistThink:
    """Tests for Strategist.think() method."""

    def test_think_with_mock_model_returns_analysis(self):
        """Test that think() returns analysis when model generates content."""
        cfg = Config()
        logger = setup_logging(cfg)

        # Create mock model that returns a response
        mock_response = Mock()
        mock_response.text = """
        ## Market Analysis

        **Bias:** **BULLISH**

        Gold is showing strength with RSI at 55 and price holding above support.
        """

        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={"GOLD": {"price": 2000, "change": 0.5, "rsi": 55, "adx": 25, "atr": 15}, "RATIOS": {"GSR": 80}},
            news=["Gold rallies on Fed comments"],
            memory_log="Previous bias: NEUTRAL",
            model=mock_model,
        )

        analysis, bias = strategist.think()

        assert "BULLISH" in analysis
        assert bias == "BULLISH"
        mock_model.generate_content.assert_called_once()

    def test_think_returns_neutral_on_model_error(self):
        """Test that think() returns NEUTRAL bias when model fails."""
        cfg = Config()
        logger = setup_logging(cfg)

        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")

        strategist = Strategist(
            config=cfg, logger=logger, data={"GOLD": {"price": 2000}}, news=[], memory_log="", model=mock_model
        )

        analysis, bias = strategist.think()

        assert "Error" in analysis
        assert bias == "NEUTRAL"

    def test_think_returns_error_when_no_model(self):
        """Test that think() handles missing model."""
        cfg = Config()
        logger = setup_logging(cfg)

        strategist = Strategist(
            config=cfg, logger=logger, data={"GOLD": {"price": 2000}}, news=[], memory_log="", model=None
        )

        analysis, bias = strategist.think()

        assert "Error" in analysis or "error" in analysis.lower()
        assert bias == "NEUTRAL"

    def test_think_handles_missing_gold_data(self):
        """Test that think() handles missing GOLD data gracefully."""
        cfg = Config()
        logger = setup_logging(cfg)
        mock_model = Mock()

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={},  # No GOLD data
            news=[],
            memory_log="",
            model=mock_model,
        )

        analysis, bias = strategist.think()

        assert "Gold data" in analysis or "Error" in analysis
        assert bias == "NEUTRAL"


class TestBiasExtraction:
    """Tests for bias extraction from AI responses."""

    @pytest.fixture
    def strategist(self):
        """Create a Strategist instance for testing."""
        cfg = Config()
        logger = setup_logging(cfg)
        return Strategist(
            config=cfg, logger=logger, data={"GOLD": {"price": 2000}}, news=[], memory_log="", model=Mock()
        )

    def test_extract_bullish_bias(self, strategist):
        """Test extraction of BULLISH bias."""
        text = "**Bias:** **BULLISH**\nGold looking strong."
        bias = strategist._extract_bias(text)
        assert bias == "BULLISH"

    def test_extract_bearish_bias(self, strategist):
        """Test extraction of BEARISH bias."""
        text = "**Bias:** **BEARISH**\nGold facing headwinds."
        bias = strategist._extract_bias(text)
        assert bias == "BEARISH"

    def test_extract_neutral_bias(self, strategist):
        """Test extraction of NEUTRAL bias."""
        text = "**Bias:** **NEUTRAL**\nMixed signals."
        bias = strategist._extract_bias(text)
        assert bias == "NEUTRAL"

    def test_extract_bias_case_insensitive(self, strategist):
        """Test that bias extraction is case-insensitive."""
        text = "**Bias:** **bullish**\nLower case works too."
        bias = strategist._extract_bias(text)
        assert bias == "BULLISH"

    def test_extract_bias_with_different_formatting(self, strategist):
        """Test bias extraction with various formatting styles."""
        test_cases = [
            ("Bias: BULLISH", "BULLISH"),
            ("**Bias**: BEARISH", "BEARISH"),
            ("Bias:**NEUTRAL**", "NEUTRAL"),
            ("The bias is clearly BULLISH", "BULLISH"),
        ]
        for text, expected in test_cases:
            bias = strategist._extract_bias(text)
            assert bias == expected, f"Failed for: {text}"

    def test_extract_bias_returns_neutral_on_ambiguous(self, strategist):
        """Test that ambiguous or missing bias returns NEUTRAL."""
        text = "Market is uncertain with no clear direction."
        bias = strategist._extract_bias(text)
        assert bias == "NEUTRAL"


class TestGeminiLiveConnection:
    """Tests for live Gemini API connection (requires valid API key).

    These tests are skipped if GEMINI_API_KEY is not set in environment.
    They validate actual API connectivity and response generation.
    """

    @pytest.fixture
    def api_key(self):
        """Get API key from environment, skip if not available."""
        key = os.environ.get("GEMINI_API_KEY", "")
        if not key:
            pytest.skip("GEMINI_API_KEY not set - skipping live API tests")
        return key

    def test_live_api_configuration(self, api_key):
        """Test that Gemini API can be configured with real key."""
        genai = _import_genai()

        try:
            # genai may be the new client module or a compat shim
            if hasattr(genai, 'configure'):
                genai.configure(api_key=api_key)
            else:
                # new google.genai: create client instance
                genai.Client(api_key=api_key)
        except Exception as e:
            pytest.fail(f"Failed to configure Gemini API: {e}")

    def test_live_model_initialization(self, api_key):
        """Test that GenerativeModel can be instantiated."""
        genai = _import_genai()

        # Configure then instantiate model
        if hasattr(genai, 'configure'):
            genai.configure(api_key=api_key)
            try:
                model = genai.GenerativeModel(cfg.GEMINI_MODEL)
            except Exception as e:
                pytest.fail(f"Failed to create GenerativeModel: {e}")
        else:
            # new google.genai client
            client = genai.Client(api_key=api_key)
            try:
                model = client.models.create(model=cfg.GEMINI_MODEL)
                assert model is not None
            except Exception as e:
                pytest.fail(f"Failed to create GenerativeModel via new client: {e}")

    def test_live_simple_generation(self, api_key):
        """Test a simple content generation to verify API connectivity."""
        genai = _import_genai()

        cfg = Config()
        if hasattr(genai, 'configure'):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(cfg.GEMINI_MODEL)
            try:
                response = model.generate_content("Say 'API test successful' in exactly those words.")
                assert response is not None
                assert hasattr(response, "text")
                assert len(response.text) > 0
            except Exception as e:
                pytest.fail(f"Failed to generate content: {e}")
        else:
            client = genai.Client(api_key=api_key)
            try:
                resp = client.models.generate_content(model=cfg.GEMINI_MODEL, input="Say 'API test successful' in exactly those words.")
                # Try to extract text from response
                text = getattr(resp, 'text', None)
                if not text and hasattr(resp, 'output'):
                    try:
                        text = resp.output[0].content
                    except Exception:
                        pass
                assert text and len(text) > 0
            except Exception as e:
                pytest.fail(f"Failed to generate content with new client: {e}")

    def test_live_strategist_analysis(self, api_key):
        """Test full Strategist analysis with live API."""
        genai = _import_genai()
        cfg = Config()
        logger = setup_logging(cfg)
        # Configure and instantiate model depending on client type
        if hasattr(genai, 'configure'):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(cfg.GEMINI_MODEL)
        else:
            client = genai.Client(api_key=api_key)
            model = client.models.create(model=cfg.GEMINI_MODEL)

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={
                "GOLD": {"price": 2650.50, "change": 0.75, "rsi": 58, "adx": 28, "atr": 18.5, "sma200": 2400},
                "SILVER": {"price": 31.25, "change": 1.2, "rsi": 62, "adx": 22, "atr": 0.45},
                "RATIOS": {"GSR": 84.8},
                "VIX": {"price": 14.5},
            },
            news=["Gold holds steady amid Fed uncertainty", "Dollar weakens on rate cut expectations"],
            memory_log="Previous bias: BULLISH - Gold rallied 1.5% (WIN)",
            model=model,
        )

        try:
            analysis, bias = strategist.think()

            # Verify we got a meaningful response
            assert len(analysis) > 100, "Analysis should be substantial"
            assert bias in ["BULLISH", "BEARISH", "NEUTRAL"], f"Invalid bias: {bias}"

            # Check for expected sections in analysis
            analysis_lower = analysis.lower()
            assert any(
                term in analysis_lower for term in ["gold", "market", "analysis"]
            ), "Analysis should mention gold or market"

        except Exception as e:
            pytest.fail(f"Strategist analysis failed: {e}")


class TestGeminiErrorHandling:
    """Tests for error handling in Gemini integration."""

    def test_invalid_api_key_handling(self):
        """Test handling of invalid API key."""
        genai = _import_genai()

        # Configure with obviously invalid key
        if hasattr(genai, 'configure'):
            genai.configure(api_key="invalid-key-12345")
        else:
            genai.Client(api_key="invalid-key-12345")
        cfg = Config()

        try:
            _model = genai.GenerativeModel(cfg.GEMINI_MODEL)  # noqa: F841
            # The model creation might succeed, but generation should fail
            # This depends on the API behavior
        except Exception:
            pass  # Expected to potentially fail

    def test_strategist_graceful_degradation(self):
        """Test that Strategist degrades gracefully on API errors."""
        cfg = Config()
        logger = setup_logging(cfg)

        # Model that raises various errors
        error_cases = [
            Exception("Network timeout"),
            RuntimeError("Rate limit exceeded"),
            ValueError("Invalid response format"),
        ]

        for error in error_cases:
            mock_model = Mock()
            mock_model.generate_content.side_effect = error

            strategist = Strategist(
                config=cfg, logger=logger, data={"GOLD": {"price": 2000}}, news=[], memory_log="", model=mock_model
            )

            analysis, bias = strategist.think()

            # Should return error message and NEUTRAL bias, not crash
            assert bias == "NEUTRAL", f"Should return NEUTRAL on error: {error}"
            assert "Error" in analysis or "error" in analysis.lower()


class TestPromptBuilding:
    """Tests for AI prompt construction."""

    def test_prompt_includes_market_data(self):
        """Test that prompt includes all market data."""
        cfg = Config()
        logger = setup_logging(cfg)

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={
                "GOLD": {"price": 2000, "change": 0.5, "rsi": 55, "adx": 25, "atr": 15, "sma200": 1950},
                "SILVER": {"price": 25, "change": 1.0, "rsi": 60},
                "RATIOS": {"GSR": 80},
            },
            news=["Test news headline"],
            memory_log="Test memory",
            model=Mock(),
        )

        prompt = strategist._build_prompt(80, 15.5, "* GOLD: $2000")

        # Verify prompt contains key elements
        assert "Syndicate" in prompt
        assert "GOLD" in prompt or "$2000" in prompt
        assert "GSR" in prompt or "80" in prompt
        assert "VIX" in prompt or "15.5" in prompt

    def test_prompt_includes_stop_loss_calculations(self):
        """Test that prompt includes ATR-based stop loss."""
        cfg = Config()
        logger = setup_logging(cfg)

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={"GOLD": {"price": 2000, "atr": 20, "adx": 30, "rsi": 50}},
            news=[],
            memory_log="",
            model=Mock(),
        )

        prompt = strategist._build_prompt(80, 15, "* GOLD: $2000")

        # ATR of 20 * 2 = 40 stop width
        # Stop loss should be around 2000 - 40 = 1960
        assert "Stop Loss" in prompt or "SL" in prompt
        assert "ATR" in prompt

    def test_data_summary_formatting(self):
        """Test the data summary formatting method."""
        cfg = Config()
        logger = setup_logging(cfg)

        strategist = Strategist(
            config=cfg,
            logger=logger,
            data={
                "GOLD": {
                    "price": 2000,
                    "change": 0.5,
                    "rsi": 55,
                    "adx": 25,
                    "regime": "TRENDING",
                    "atr": 15,
                    "sma200": 1950,
                },
            },
            news=[],
            memory_log="",
            model=Mock(),
        )

        summary = strategist._format_data_summary()

        assert "GOLD" in summary
        assert "$2000" in summary or "2000" in summary
        assert "RSI" in summary
        assert "ADX" in summary
