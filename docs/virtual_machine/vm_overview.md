# System Documentation

This document provides a comprehensive overview of the system's configuration, purpose, and the operational parameters of the agent managing it.

---

## 1. System Infrastructure

This section details the physical and software-defined resources of the machine.

### 1.1. Hardware

*   **CPU:** 2-core Intel(R) Xeon(R) CPU @ 2.20GHz
*   **RAM:** 3.8Gi
*   **Disk:** 9.7G (`/dev/sda1`)

### 1.2. Software & Security

*   **Operating System:** Debian GNU/Linux 12 (bookworm)
*   **Container Engine:** Docker version 29.1.2
*   **Automated Security Updates:** `unattended-upgrades` is installed and enabled, ensuring the system receives timely security patches.
*   **SSH Access:** Hardened configuration (`PermitRootLogin no`, `PasswordAuthentication no`) ensures access is restricted to key-based authentication.

---

## 2. System Purpose & Operations

This section defines the system's primary goal and the automated tasks configured to achieve it.

### 2.1. Core Objective

The system is dedicated to managing and operating the `gold_standard` Python project for autonomous data analysis, market analysis, and trade simulation on a continuous basis, requiring zero manual intervention. This includes ensuring its proper setup, dependency management, and execution within a dedicated virtual environment.

### 2.2. Autonomous Tasks

The system uses `systemd` timers to schedule and manage three critical operations:

#### 2.2.1. Daily Analysis (Gold Standard Python Project)

*   **Process:** The `gold_standard` Python project is executed directly from `/mnt/newdisk/gold_standard` within its dedicated Python 3.12 virtual environment (`/mnt/newdisk/gold_standard/.venv`).
*   **Execution:** The primary entry point is `run.py`, typically executed in daemon mode (`python run.py`) to manage daily, weekly, monthly, and yearly analysis tasks, as well as insights extraction, task execution, and file organization.
*   **Configuration:** AI functionality (Gemini, Ollama) requires proper configuration of `GEMINI_API_KEY` environment variable and/or an active Ollama server.
*   **Logging:** Detailed operational logs are generated at `/mnt/newdisk/gold_standard/output/gold_standard.log`.
*   **Notion Integration:** Publishing to Notion requires the `notion-client` Python package to be installed in the project's virtual environment.


#### 2.2.2. Weekly Cleanup

*   **Service:** `gold-standard-weekly-cleanup.service`
*   **Timer:** `gold-standard-weekly-cleanup.timer`
*   **Schedule:** Every Sunday at 1:00 AM.
*   **Process:**
    1.  Executes `/usr/local/bin/gold-standard-weekly-cleanup.sh`.
    2.  The script runs `docker system prune -af` to remove all unused Docker objects, which is critical for managing disk space.
    3.  Appends logs to `/home/ali_shakil_backup/gold_standard_config/cleanup.log`.

#### 2.2.3. Hourly Monitoring (Gemini Agent)

*   **Service:** `gemini-monitor.service`
*   **Timer:** `gemini-monitor.timer`
*   **Schedule:** Runs hourly.
*   **Process:**
    1.  Executes `/usr/local/bin/gemini-monitor.sh`.
    2.  The script performs health checks and reports its findings to `/home/ali_shakil_backup/gold_standard_config/gemini-monitor.log`.
    3.  This serves as the Gemini agent's proactive monitoring mechanism.

---
