# Docker Data Layout

This directory documents the recommended layout for bind-mounted Docker data and examples for `docker-compose.yml`.

Recommended root on a dedicated disk (example):

- /mnt/newdisk/gold_standard/docker-data/
  - gost_data/         # application persistent data
  - gost_output/       # generated reports and output artifacts
  - prometheus/        # Prometheus TSDB
  - grafana/           # Grafana storage
  - loki/              # Loki indices

Example `docker-compose` volumes (absolute paths strongly recommended):

```yaml
services:
  gost:
    volumes:
      - /mnt/newdisk/gold_standard/docker-data/gost_data:/app/data
      - /mnt/newdisk/gold_standard/docker-data/gost_output:/app/output
  prometheus:
    volumes:
      - /mnt/newdisk/gold_standard/docker-data/prometheus:/prometheus
  grafana:
    volumes:
      - /mnt/newdisk/gold_standard/docker-data/grafana:/var/lib/grafana
```

Permissions:
- Ensure the UID/GID used by your containers or the host Docker daemon can read/write these directories.
- On SELinux systems, add appropriate contexts (e.g., `chcon -R -t container_file_t /mnt/newdisk/gold_standard/docker-data`).
