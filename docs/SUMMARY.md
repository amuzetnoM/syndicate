# Gold Standard Documentation

[![Latest](https://img.shields.io/badge/latest-v3.4.0-blue.svg)](https://github.com/amuzetnoM/gold_standard/releases/tag/v3.4.0)
[![Stable](https://img.shields.io/badge/stable-v3.3.1-green.svg)](https://github.com/amuzetnoM/gold_standard/releases/tag/v3.3.1)
[![Docs](https://img.shields.io/badge/changelog-gitbook-blue.svg)](https://artifact-virtual.gitbook.io/gold-standard)

## Documentation Index

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, installation, and quick start |
| [Changelog](changelog/CHANGELOG.md) | Release history and engineering roadmap |
| [Architecture](ARCHITECTURE.md) | System design and component overview |
| [LLM Providers](LLM_PROVIDERS.md) | Gemini, Ollama, and llama.cpp configuration |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines and development setup |
| [Guide](GUIDE.md) | Comprehensive user and operator manual |

## VM Deployment

| Document | Description |
|----------|-------------|
| [Setup Log](virtual_machine/setup_log.md) | Complete VM deployment reference with troubleshooting |
| [README](virtual_machine/README.md) | VM-specific installation instructions |

## Web Documentation

| File | Description |
|------|-------------|
| [index.html](index.html) | Main landing page |
| [guide.html](guide.html) | Interactive user guide |
| [index_docs.html](index_docs.html) | Documentation portal |

## Release Information

**Current Release:** v3.4.0 (December 13, 2025)
- Standalone Task Executor Daemon (`scripts/executor_daemon.py`)
- Docker Compose with separate executor service
- Orphan recovery and graceful shutdown
- Dry-run mode and task limits for testing

**Stable Release:** v3.3.1
- Container robustness and VM deployment fixes
- Environment variable naming fixes
- Cortex memory persistence improvements

## Docker Images

```bash
# Latest release
docker pull ghcr.io/amuzetnom/gold_standard:v3.4.0

# Stable release
docker pull ghcr.io/amuzetnom/gold_standard:v3.3.1

# Latest main branch
docker pull ghcr.io/amuzetnom/gold_standard:latest
```

## Links

- [GitHub Repository](https://github.com/amuzetnoM/gold_standard)
- [GitBook Documentation](https://artifact-virtual.gitbook.io/gold-standard)
- [Container Registry](https://ghcr.io/amuzetnom/gold_standard)
