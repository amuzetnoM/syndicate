# Systemd Automation Map for Gold Standard Project

This document provides a detailed map of all `systemd` services and timers that automate various operations within the Gold Standard project. It serves as a central reference for understanding the scheduled tasks, their interdependencies, and their operational parameters.

## Table of Contents

1.  [Overview](#1-overview)
2.  [Systemd Services](#2-systemd-services)
    *   [`gold-standard-compose.service`](#21-gold-standard-compose-service)
    *   [`gold-standard-daily.service`](#22-gold-standard-daily-service)
    *   [`gold-standard-weekly-cleanup.service`](#23-gold-standard-weekly-cleanup-service)
3.  [Systemd Timers](#3-systemd-timers)
    *   [`gold-standard-daily.timer`](#31-gold-standard-daily-timer)
    *   [`gold-standard-weekly-cleanup.timer`](#32-gold-standard-weekly-cleanup-timer)
4.  [Operational Flow and Dependencies](#4-operational-flow-and-dependencies)
5.  [Management and Troubleshooting](#5-management-and-troubleshooting)

---

## 1. Overview

The Gold Standard project leverages `systemd` for robust and reliable scheduling of critical background tasks. This includes managing the Docker Compose stack, executing daily data analysis, and performing weekly system maintenance. The automation ensures the project's continuous operation and data integrity without manual intervention.

## 2. Systemd Services

These are the core executable units defining the actions performed by the systemd automation.

### 2.1. `gold-standard-compose.service`

*   **Description**: Manages the lifecycle of the Gold Standard project's Docker Compose stack. This service is responsible for bringing up and tearing down all Docker containers defined in the `docker-compose.yml` file.
*   **Unit File Location**: `gold_standard/deploy/systemd/gold-standard-compose.service`
*   **Purpose**: Ensures the Gold Standard application and its monitoring/logging infrastructure (Prometheus, Grafana, Loki, etc.) are always running.
*   **Execution Command**:
    ```bash
    ExecStart=/usr/local/bin/docker-compose --profile monitoring --profile logging up -d
    ExecStop=/usr/local/bin/docker-compose --profile monitoring --profile logging down
    ```
*   **Dependencies**:
    *   `Requires=docker.service`: Ensures Docker daemon is active.
    *   `After=docker.service network-online.target`: Starts only after Docker and network are ready.
*   **Restart Policy**: `Restart=on-failure` (ensures service recovers from crashes).
*   **Start Behavior**: `WantedBy=multi-user.target` (starts automatically on system boot).

### 2.2. `gold-standard-daily.service`

*   **Description**: Executes the primary daily data analysis and report generation tasks for the Gold Standard project.
*   **Unit File Location**: `gold_standard/deploy/systemd/gold-standard-daily.service`
*   **Purpose**: Runs the main Gold Standard script daily to process market data, apply AI models, and generate trading reports.
*   **Execution Command**:
    ```bash
    ExecStart=/usr/bin/flock -n /tmp/gold_standard.lock /home/ali_shakil_backup/codex.sh run
    ```
    *   `flock -n /tmp/gold_standard.lock`: Prevents multiple instances of the script from running concurrently, using a file lock.
    *   `/home/ali_shakil_backup/codex.sh run`: The actual script that initiates the daily analysis workflow.
*   **User**: `ali_shakil_backup` (runs under the specified user's context).
*   **Logging**: Standard output and error are redirected to `/home/ali_shakil_backup/gold_standard_config/run.log` for auditing and debugging.
*   **Trigger**: Activated by `gold-standard-daily.timer`.

### 2.3. `gold-standard-weekly-cleanup.service`

*   **Description**: Performs weekly maintenance and cleanup operations to manage disk space and archive old data.
*   **Unit File Location**: `gold_standard/deploy/systemd/gold-standard-weekly-cleanup.service`
*   **Purpose**: Deletes outdated reports, archives historical data, and ensures the system's storage remains optimized.
*   **Execution Command**:
    ```bash
    ExecStart=/usr/local/bin/gold-standard-weekly-cleanup.sh
    ```
*   **Logging**: Standard output and error are redirected to `/home/ali_shakil_backup/gold_standard_config/cleanup.log`.
*   **Trigger**: Activated by `gold-standard-weekly-cleanup.timer`.

## 3. Systemd Timers

These units define the schedule on which the associated services are activated.

### 3.1. `gold-standard-daily.timer`

*   **Description**: Schedules the `gold-standard-daily.service` to run once every day.
*   **Unit File Location**: `gold_standard/deploy/systemd/gold-standard-daily.timer`
*   **Schedule**: `OnCalendar=daily` (e.g., daily at 05:00:00). The exact time might be specified internally within the timer or subject to `RandomDelaySec`.
*   **Behavior**:
    *   `Persistent=true`: If the system is off during a scheduled run, the service will be triggered shortly after the system boots up.
    *   `RandomDelaySec=1800`: Adds a random delay of up to 30 minutes to the scheduled start time, helping to distribute load if multiple timers are set similarly.
*   **Activates**: `gold-standard-daily.service`.

### 3.2. `gold-standard-weekly-cleanup.timer`

*   **Description**: Schedules the `gold-standard-weekly-cleanup.service` to execute once every week.
*   **Unit File Location**: `gold_standard/deploy/systemd/gold-standard-weekly-cleanup.timer`
*   **Schedule**: `OnCalendar=weekly` (e.g., on Sunday at 01:00:00). The exact day and time can be configured in the unit file.
*   **Activates**: `gold-standard-weekly-cleanup.service`.

## 4. Operational Flow and Dependencies

*   The `gold-standard-compose.service` runs continuously to keep the Dockerized application stack operational.
*   The `gold-standard-daily.timer` activates the `gold-standard-daily.service` once every 24 hours.
*   The `gold-standard-weekly-cleanup.timer` activates the `gold-standard-weekly-cleanup.service` once every 7 days.
*   Both `gold-standard-daily.service` and `gold-standard-weekly-cleanup.service` operate independently of `gold-standard-compose.service` but assume the Docker environment (if their tasks involve Docker) is available through the base system configuration (e.g., via `docker.service` dependency in relevant services, though the scripts themselves might directly interact with `docker` cli).

## 5. Management and Troubleshooting

To manage these `systemd` units:

*   **List all active units**: `systemctl list-units --type=service --type=timer`
*   **Check status of a unit**: `systemctl status <unit-name>` (e.g., `systemctl status gold-standard-daily.service`)
*   **Enable/Disable a unit**: `systemctl enable <unit-name>`, `systemctl disable <unit-name>`
*   **Start/Stop a service**: `systemctl start <service-name>`, `systemctl stop <service-name>`
*   **View logs**: `journalctl -u <unit-name>`

For troubleshooting, review the logs specified for each service (e.g., `run.log`, `cleanup.log`) and use `journalctl` for system-level logs.
