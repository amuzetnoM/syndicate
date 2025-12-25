# 🐳 Syndicate Docker Suite

Complete containerized deployment with full monitoring stack.

## Quick Start

```bash
# Start core services (Syndicate + Monitoring)
docker compose up -d

# Start with full monitoring (cAdvisor, Node Exporter)
docker compose --profile monitoring up -d

# Start with logging (Loki + Promtail)
docker compose --profile logging up -d

# Start development environment
docker compose --profile dev up -d
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Syndicate | - | Main application (daemon mode) |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Visualization dashboards |
| Alertmanager | 9093 | Alert routing |
| cAdvisor | 8080 | Container metrics (profile: monitoring) |
| Node Exporter | 9100 | Host metrics (profile: monitoring) |
| Loki | 3100 | Log aggregation (profile: logging) |

## Default Credentials

- **Grafana**: `admin` / `goldstandard`

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Grafana (optional)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

### Volumes

| Volume | Purpose |
|--------|---------|
| `syndicate-data` | SQLite database, cached data |
| `syndicate-output` | Reports, charts, research |
| `syndicate-prometheus` | Metrics storage (30 days) |
| `syndicate-grafana` | Dashboards, settings |

## Commands

```bash
# View logs
docker compose logs -f gost

# Check status
docker compose ps

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild after code changes
docker compose build --no-cache gost

# Run one-off command
docker compose run --rm gost python run.py --once
```

## Accessing Services

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

## Dashboards

Pre-configured Grafana dashboards:
- **Syndicate Overview** - Application health, task metrics
- Container resource usage (CPU, Memory)
- Task execution rates and duration percentiles

## Alerting

Configure alerts in `docker/alertmanager/alertmanager.yml`:
- Slack webhooks
- Email notifications
- PagerDuty integration
- Custom webhooks

## Production Deployment

```bash
# Pull latest image
docker pull ghcr.io/amuzetnom/syndicate:latest

# Or build locally
docker build -t syndicate:local .

# Run with production settings
docker compose -f docker-compose.yml up -d
```

## Profiles

| Profile | Services Added |
|---------|----------------|
| `monitoring` | cAdvisor, Node Exporter |
| `logging` | Loki, Promtail |
| `dev` | Development container with mounted source |

```bash
# Example: Full stack
docker compose --profile monitoring --profile logging up -d
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐  │
│  │    Gold      │────▶│  Prometheus  │────▶│  Grafana   │  │
│  │  Standard    │     │    :9090     │     │   :3000    │  │
│  │   (daemon)   │     └──────────────┘     └────────────┘  │
│  └──────────────┘            │                    │        │
│         │                    │                    │        │
│         │              ┌─────▼─────┐              │        │
│         │              │Alertmanager│◀────────────┘        │
│         │              │   :9093   │                       │
│         │              └───────────┘                       │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────┐     ┌──────────────┐                    │
│  │    Data      │     │    Output    │                    │
│  │   Volume     │     │    Volume    │                    │
│  └──────────────┘     └──────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Container won't start
```bash
docker compose logs gost
docker compose run --rm gost python -c "from db_manager import get_db; get_db()"
```

### No metrics in Prometheus
```bash
curl http://localhost:9090/api/v1/targets
```

### Reset everything
```bash
docker compose down -v
docker volume prune -f
docker compose up -d
```
