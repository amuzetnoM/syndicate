# Contributing to Gold Standard

Thank you for your interest in contributing to Gold Standard! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Security](#security)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Please:

- Be respectful and constructive in discussions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gold_standard.git
   cd gold_standard
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/amuzetnoM/gold_standard.git
   ```

---

## Development Setup

### Prerequisites

- **Python 3.10 - 3.13** (Python 3.14+ not supported due to numba)
- Git

### Setup Steps

**Windows:**
```powershell
.\scripts\setup.ps1
pip install -r requirements-dev.txt
pre-commit install
```

**Unix/macOS/Linux:**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
pip install -r requirements-dev.txt
pre-commit install
```

### Environment Variables

Create a `.env` file from the template:
```bash
cp .env.template .env
```

Add your `GEMINI_API_KEY` for AI features (optional for development with `--no-ai`).

---

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-indicator` - New features
- `fix/rsi-calculation` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/split-main` - Code refactoring

### Commit Messages

Follow conventional commit format:
```
type(scope): brief description

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(indicators): add Bollinger Bands support
fix(api): handle Gemini rate limiting
docs(readme): update installation instructions
test(gemini): add API key validation tests
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_gemini.py -v

# Run tests matching pattern
pytest tests/ -k "test_fetch" -v
```

### Test Categories

| Test File | Purpose |
|-----------|---------|
| `test_core.py` | Core pipeline and bias extraction |
| `test_gemini.py` | AI integration and API handling |
| `test_ta_fallback.py` | Technical analysis with fallbacks |
| `test_split_reports.py` | Report generation |

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use pytest fixtures for common setup
- Mock external APIs (Gemini, yfinance) in unit tests

Example:
```python
def test_extract_bias_bullish():
    """Test that BULLISH bias is correctly extracted."""
    text = "**Bias:** **BULLISH**"
    bias = extract_bias(text)
    assert bias == "BULLISH"
```

---

## Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make your changes** and commit

4. **Run checks locally**:
   ```bash
   pre-commit run --all-files
   pytest tests/ -v
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature
   ```

6. **PR Requirements**:
   - All tests passing
   - Pre-commit hooks passing
   - Clear description of changes
   - Link to related issues (if any)

---

## Code Style

### Formatting

We use **Ruff** for linting and formatting:
```bash
ruff check .           # Check for issues
ruff check . --fix     # Auto-fix issues
ruff format .          # Format code
```

### Type Hints

Use type hints for function signatures:
```python
def calculate_rsi(prices: pd.Series, length: int = 14) -> pd.Series:
    """Calculate RSI indicator."""
    ...
```

### Docstrings

Use Google-style docstrings:
```python
def fetch_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch market data for a ticker.
    
    Args:
        ticker: The stock/futures ticker symbol.
        period: Data period (e.g., "1y", "6mo", "1d").
    
    Returns:
        DataFrame with OHLCV data, or None if fetch fails.
    
    Raises:
        ValueError: If ticker format is invalid.
    """
    ...
```

---

## Security

### Secrets

- **NEVER** commit API keys or secrets
- Use `.env` files (gitignored) for local development
- The `prevent_secrets.py` hook blocks accidental commits

### Reporting Vulnerabilities

If you discover a security vulnerability:
1. **DO NOT** open a public issue
2. Email the maintainers directly
3. Provide detailed reproduction steps

### Dependencies

- Keep dependencies updated
- Run `pip-audit` to check for vulnerabilities
- Pin versions in `requirements.txt`

---

## Architecture Overview

```
gold_standard/
├── main.py           # Core: Config, Cortex, QuantEngine, Strategist
├── run.py            # CLI: Daemon mode, interactive menu
├── gui.py            # GUI: Tkinter dashboard
├── db_manager.py     # Storage: SQLite persistence
└── scripts/          # Utilities: Calendar, reports, analysis
```

### Key Classes

| Class | Purpose |
|-------|---------|
| `Config` | Central configuration (env, thresholds, paths) |
| `Cortex` | Persistent memory (predictions, history, trades) |
| `QuantEngine` | Data fetching, indicators, charting |
| `Strategist` | AI integration, bias generation |

---

## Need Help?

- Check existing [issues](https://github.com/amuzetnoM/gold_standard/issues)
- Read the [README](README.md) and [GUIDE](docs/GUIDE.md)
- Open a discussion for questions

---

Thank you for contributing! 🥇
