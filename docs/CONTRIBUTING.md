# Contributing to Syndicate

Thank you for your interest in contributing to Syndicate! This document provides guidelines and instructions for contributing to v3.0 and beyond.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
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
   git clone https://github.com/YOUR_USERNAME/syndicate.git
   cd syndicate
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/amuzetnoM/syndicate.git
   ```

---

## Development Setup

### Prerequisites

- **Python 3.10 - 3.14** (full support including fallback indicators)
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

## Project Architecture

### Directory Structure

```
syndicate/
├── main.py              # Core: Config, Cortex, QuantEngine, Strategist
├── run.py               # CLI: Daemon mode, interactive menu, GUI launcher
├── gui.py               # GUI: Modern dual-pane dashboard (v3.0)
├── db_manager.py        # Storage: SQLite persistence
├── scripts/
│   ├── insights_engine.py    # v3.0: Entity & action extraction
│   ├── task_executor.py      # v3.0: Autonomous task execution
│   ├── file_organizer.py     # v3.0: Intelligent file organization
│   ├── live_analysis.py      # Live analysis suite
│   ├── economic_calendar.py  # Economic calendar
│   ├── pre_market.py         # Pre-market preparation
│   ├── split_reports.py      # Report generation
│   └── init_cortex.py        # Memory initialization
├── tests/                # Test suite
├── docs/                 # Documentation
└── output/               # Generated reports and charts
```

### Key Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `Config` | main.py | Central configuration (env, thresholds, paths) |
| `Cortex` | main.py | Persistent memory (predictions, history, trades) |
| `QuantEngine` | main.py | Data fetching, indicators, charting |
| `Strategist` | main.py | AI integration, bias generation |
| `DBManager` | db_manager.py | SQLite persistence layer |
| `InsightsExtractor` | insights_engine.py | Entity and action extraction (v3.0) |
| `TaskExecutor` | task_executor.py | Autonomous task execution (v3.0) |
| `FileOrganizer` | file_organizer.py | Intelligent file organization (v3.0) |
| `GoldStandardGUI` | gui.py | Desktop dashboard interface (v3.0) |

### v3.0 Modules

The v3.0 release introduces autonomous intelligence:

1. **InsightsExtractor** - Scans reports for entities (Fed, ECB, indicators) and actionable items (research tasks, data to fetch, calculations)

2. **TaskExecutor** - Automatically executes extracted actions with priority-based queuing (critical → high → medium → low)

3. **FileOrganizer** - Organizes output files into structured directories by type, date, and category

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

# Run integration tests for v3.0 modules
pytest tests/test_integration.py -v
```

### Test Categories

The project includes comprehensive tests across multiple files:

| Test File | Tests | Purpose |
|-----------|-------|---------|
| `test_core.py` | 2 | Core pipeline and bias extraction |
| `test_gemini.py` | 27 | AI integration and API handling (includes 4 live API tests) |
| `test_ta_fallback.py` | 2 | Technical analysis with fallbacks |
| `test_split_reports.py` | 2 | Report generation |
| `test_integration.py` | 1+ | v3.0 module integration (InsightsEngine, TaskExecutor, FileOrganizer) |

### Live API Tests

Tests in `TestGeminiLiveConnection` require a valid `GEMINI_API_KEY` in `.env`:
```bash
# Run live Gemini tests
pytest tests/test_gemini.py::TestGeminiLiveConnection -v
```

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

See [Project Architecture](#project-architecture) above for the full module breakdown.

### Core Data Flow

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   Syndicate v3.0                │
                    └─────────────────────────────────────────────────────┘
                                           │
           ┌───────────────────────────────┼───────────────────────────────┐
           ▼                               ▼                               ▼
    ┌─────────────┐               ┌─────────────┐               ┌─────────────┐
    │ QuantEngine │               │  Strategist │               │   Cortex    │
    │ (Data/TA)   │               │    (AI)     │               │  (Memory)   │
    └─────────────┘               └─────────────┘               └─────────────┘
           │                               │                               │
           └───────────────────────────────┼───────────────────────────────┘
                                           ▼
                                  ┌─────────────────┐
                                  │  Report Output  │
                                  └─────────────────┘
                                           │
           ┌───────────────────────────────┼───────────────────────────────┐
           ▼                               ▼                               ▼
    ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
    │ InsightsEngine  │           │  TaskExecutor   │           │  FileOrganizer  │
    │ (Extract)       │    →      │  (Execute)      │    →      │  (Organize)     │
    └─────────────────┘           └─────────────────┘           └─────────────────┘
           │                               │                               │
           └───────────────────────────────┼───────────────────────────────┘
                                           ▼
                                   ┌─────────────┐
                                   │  DBManager  │
                                   │  (Persist)  │
                                   └─────────────┘
```

---

## Need Help?

- Check existing [issues](https://github.com/amuzetnoM/syndicate/issues)
- Read the [README](README.md) and [GUIDE](docs/GUIDE.md)
- Open a discussion for questions

---

Thank you for contributing! 🥇
