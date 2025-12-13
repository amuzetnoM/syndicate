# Gold Standard Setup Log - 2025-12-13 01:47:16

## 1. Introduction
This document serves as a comprehensive log detailing the setup, configuration, issues encountered, and solutions implemented for the Gold Standard system. Its purpose is to provide a complete "source of truth" for anyone seeking to understand the system's current state and operational rationale.

## 2. Initial System State and Goals
The Gold Standard system is deployed on a Virtual Machine (VM) with a specific disk configuration:
* **Root Disk**: A small (e.g., 50GB) disk primarily for the VM's operating system and core functionalities. This disk *must not* be used for persistent application data or Docker-related storage.
* **New Disk (`/mnt/newdisk`)**: A larger (e.g., 500GB) dedicated data disk intended for all application data, logs, Docker volumes, and other persistent storage.

**The primary and critical user requirement throughout this setup was to ensure that absolutely no data is written to the root filesystem.** All persistent operations, especially those involving Docker and logs, must be directed to `/mnt/newdisk`.

The overarching goal was to get the `gold_standard` system running correctly, robustly, and with all data persistently stored on `/mnt/newdisk`, triggered automatically as scheduled by `systemd`.

## 3. Core Project Overview (Pre-Modifications)
The `gold_standard` is a Python-based quantitative analysis system.

* **Application Structure**:
    * Developed in Python, utilizing a virtual environment (`.venv`).
    * Core logic in `main.py` orchestrates `Cortex` (memory), `QuantEngine` (data/TA), and `Strategist` (AI).
    * CLI entry point `run.py` handles various execution modes (daemon, single run, interactive).
* **Configuration**:
    * Relies on environment variables for API keys (`GEMINI_API_KEY`, `NOTION_API_KEY`, `IMGBB_API_KEY`) typically loaded from a `.env` file in the project root.
* **Docker Compose**:
    * `gold_standard/docker-compose.yml` defines multiple services (e.g., `gost` for the main app, `prometheus`, `grafana`, `alertmanager`, `loki`, `promtail` for monitoring/logging, `node-exporter`, `cadvisor`).
    * Initially used Docker named volumes for persistent data storage.
* **Systemd Automations**:
    * `gold-standard-daily.service` (triggering daily analysis).
    * `gold-standard-weekly-cleanup.service` (for weekly cleanup tasks).
    * `gold-standard-compose.service` (manages the Docker Compose stack on boot).
    * Corresponding `.timer` files (`gold-standard-daily.timer`, `gold-standard-weekly-cleanup.timer`) define the scheduling.
* **`codex.sh`**:
    * A shell script (`/home/user/codex.sh`) to simplify interaction with the Docker Compose stack (run, build, monitor, stop).

## 4. Issues Encountered and Solutions Implemented

### 4.1. Issue: Docker Writes to Root Filesystem (Named Volumes)
* **Rationale**: The initial `docker-compose.yml` defined Docker named volumes (e.g., `gost_data`, `prometheus_data`). By default, Docker stores these named volumes under `/var/lib/docker/volumes` on the host, which typically resides on the root filesystem. This directly violated the critical requirement.
* **Solution**:
    1. Created a dedicated directory: `/mnt/newdisk/gold_standard/docker-data`.
    2. Modified `gold_standard/docker-compose.yml` to replace all named volumes with explicit **bind mounts** to subdirectories within `/mnt/newdisk/gold_standard/docker-data`. For example, `gost_data` was changed from a named volume to a bind mount to `./docker-data/gost_data`.
* **Verification**: All Docker-managed persistent data (database, output, Prometheus data, Grafana data, etc.) is now stored on the `/mnt/newdisk` partition, completely avoiding the root filesystem.

### 4.2. Issue: Systemd Service Logs Writing to Root Filesystem
* **Rationale**: The `systemd` service files (`gold-standard-daily.service`, `gold-standard-weekly-cleanup.service`) were configured to append their `StandardOutput` and `StandardError` to log files within `/home/user/gold_standard_config/`. This directory is on the root filesystem.
* **Solution**:
    1. Created the `gold_standard_config` directory on the data disk: `/mnt/newdisk/gold_standard/gold_standard_config`.
    2. Modified `gold-standard-daily.service` and `gold-standard-weekly-cleanup.service` using `sed` to update the `StandardOutput` and `StandardError` paths to point to the new location: `/mnt/newdisk/gold_standard/gold_standard_config/run.log` and `/mnt/newdisk/gold_standard/gold_standard_config/cleanup.log` respectively.
    3. Executed `sudo systemctl daemon-reload` to apply these changes to `systemd`.
* **Verification**: Service logs are now correctly directed to `/mnt/newdisk`.

### 4.3. Issue: API Keys Not Loaded (Empty Environment Variables, incl. IMGBB)
* **Rationale**: Initially, `GEMINI_API_KEY`, `NOTION_API_KEY`, and `IMGBB_API_KEY` were not being correctly passed to the Docker container. This was due to multiple factors:
    * The `docker-compose.yml` `environment` section for the `gost` service initially used `NOTION_TOKEN` instead of `NOTION_API_KEY`.
    * `IMGBB_API_KEY` was entirely missing from the `gost` service's `environment` block.
    * `docker compose run` does not automatically load variables from `.env` for its `environment` section unless they are pre-populated in the shell environment.
* **Solution**:
    1. Modified `gold_standard/.env` to ensure the key was named `NOTION_API_KEY`.
    2. Modified `gold_standard/docker-compose.yml`:
         * Corrected the YAML syntax by properly nesting environment variables under an `environment:` key for the `gost` service.
         * Changed `NOTION_TOKEN=${NOTION_TOKEN:-}` to `NOTION_API_KEY=${NOTION_API_KEY:-}`.
         * Added `- IMGBB_API_KEY=${IMGBB_API_KEY:-}` to the `gost` service's `environment` block.
    3. Modified `/home/user/codex.sh` to explicitly `source "/mnt/newdisk/gold_standard/.env"` before executing the `docker compose run` command. This ensures the shell environment variables are populated, allowing `docker compose` to substitute them correctly.
* **Verification**: All API keys (`GEMINI_API_KEY`, `NOTION_API_KEY`, `IMGBB_API_KEY`) are now correctly loaded and available to the application, enabling Notion publishing and chart uploads.

### 4.4. Issue: `run.py` Entering Autonomous Mode (`--once` flag ignored)
* **Rationale**: The `codex.sh run` command calls `python run.py --once`, which is intended to execute a single analysis cycle and exit. However, `run.py` was observed entering "AUTONOMOUS MODE" (daemon mode) before exiting. This was due to a logic flaw in `run.py`'s `main` function (it defaulted to daemon mode if no other specific run command was matched) and an outdated Docker image.
* **Solution**:
    1. Modified `gold_standard/run.py` to add an explicit conditional check `if args.once: run_all(...) ; _run_post_analysis_tasks() ; return` early in the `main` function, ensuring it exits after a single `run_all` call and also performs post-analysis tasks when `--once` is present.
    2. Removed the `image: ghcr.io/amuzetnom/gold_standard:latest` line from the `gost` service in `docker-compose.yml`. This forced `docker compose` to use the locally built image (reflecting `run.py` changes) instead of pulling a potentially outdated one from a registry.
    3. Rebuilt the Docker image using `codex.sh build`.
* **Verification**: The script now correctly runs a single analysis cycle including all post-analysis tasks (like Notion publishing) and exits cleanly.

### 4.5. Issue: `matplotlib` Cache Directory Permissions
* **Rationale**: `matplotlib` attempted to create its cache directory (e.g., `~/.cache/matplotlib`) in a location inside the container where the `goldstandard` user did not have write permissions.
* **Solution**: Added `MPLCONFIGDIR=/tmp/matplotlib` as an environment variable to the `gost` service in `docker-compose.yml`. This redirects `matplotlib`'s cache directory to `/tmp/matplotlib` within the container, which is always a writable temporary location.
* **Verification**: `matplotlib` chart generation now proceeds without permission errors.

### 4.6. Issue: Persistent `cortex_memory.lock` Permission Denied
* **Rationale**: This was a stubborn permission issue, preventing `Cortex` from writing its memory file and lock file. Despite correcting file/directory ownership and ensuring `cortex_memory.json` was not read-only, the `filelock` library still reported permission denied when trying to create `/app/cortex_memory.lock`. This indicated a deeper interaction issue with `filelock` and Docker bind mounts when the file was directly in the application's root directory.
* **Solution**:
    1. Modified `gold_standard/main.py` to change the `Config.MEMORY_FILE` and `Config.LOCK_FILE` properties. They now point to paths within the `/app/data` directory (`/app/data/cortex_memory.json` and `/app/data/cortex_memory.lock`). This relocates the memory files to the dedicated persistent data volume (`gost_data`).
    2. Removed the explicit `cortex_memory.json` mount from the `gost` service in `docker-compose.yml`, as the file is now expected to be within the `gost_data` volume managed by the application logic.
    3. Reverted the `Dockerfile` changes related to `USER goldstandard` position, ensuring the image builds correctly.
    4. Modified `/home/user/codex.sh` to add `--user "1000:1003"` to the `docker compose run` command. This ensures the ephemeral container created by `docker compose run` explicitly executes as the host's `user` user (UID 1000, GID 1003), matching the ownership of the bind-mounted directories and files.
    5. Rebuilt the Docker image using `codex.sh build`.
* **Verification**: `cortex_memory.lock` permission errors are resolved, and the `Cortex` memory system operates correctly.

### 4.7. Issue: FileOrganizer "File name too long" for `FILE_INDEX.md`
* **Rationale**: The `FileOrganizer` (`scripts/file_organizer.py`) was repeatedly processing and renaming `FILE_INDEX.md` and already dated `FILE_INDEX_YYYY-MM-DD.md` files. Its `generate_standardized_name` function, combined with the lack of robust exclusion, led to date strings being appended multiple times, resulting in excessively long filenames that eventually caused `[Errno 36] File name too long`.
* **Solution**:
    1. Manually cleaned up all existing excessively long `FILE_INDEX*.md` files from the `/mnt/newdisk/gold_standard/output` and `/mnt/newdisk/gold_standard/output/reports` directories using `sudo rm -f`.
    2. Modified `gold_standard/scripts/file_organizer.py` to update the skip logic in `organize_file`. Instead of checking for an exact match to `"FILE_INDEX.md"`, it now checks if `source_path.name.startswith("FILE_INDEX")`. This ensures all variations of `FILE_INDEX` are skipped from organization.
    3. Rebuilt the Docker image using `codex.sh build`.
* **Verification**: The `FileOrganizer` now correctly skips `FILE_INDEX` files from renaming, preventing the "File name too long" error.

### 4.8. Issue: `systemd` `gold-standard-compose.service` `CHDIR` Error
* **Rationale**: The `gold-standard-compose.service` was repeatedly failing to start with a `CHDIR` error. This indicated `systemd` was having trouble changing to the `WorkingDirectory` before executing the `docker compose` command, leading to the service not being able to find the `docker` executable. The `ExecStart` line became corrupted during `sed` attempts.
* **Solution**:
    1. The `gold-standard-compose.service` file (`/etc/systemd/system/gold-standard-compose.service`) was manually recreated with the correct content using `sudo tee`.
    2. The `ExecStart` line was explicitly set to `/bin/bash -c "cd /mnt/newdisk/gold_standard && /usr/bin/docker compose --profile monitoring --profile logging up -d"`. This ensures the `cd` command is part of the shell execution, resolving `systemd`'s `CHDIR` issue.
    3. The service was re-enabled and `systemctl daemon-reload` was executed.
* **Verification**: `gold-standard-compose.service` is now `active (running)`, indicating the Docker Compose stack is managed correctly by `systemd`.

## 5. Current Operational Status
As of **2025-12-13 01:47:16**, the `gold_standard` system is configured and operational as follows:

* **Execution**: The system successfully completes a full analysis run (including post-analysis tasks like insight extraction, file organization, Notion publishing, and ImgBB chart uploads) when triggered via `/home/user/codex.sh run`. The script executes `python run.py --once` inside its Docker container and exits cleanly.
* **Data Persistence**: All persistent data (SQLite database, output reports, charts, `cortex_memory.json`, Docker volumes) and service logs are correctly directed to the `/mnt/newdisk` partition, safeguarding the root filesystem.
* **Configuration**: All API keys (`GEMINI_API_KEY`, `NOTION_API_KEY`, `IMGBB_API_KEY`) are correctly loaded from `gold_standard/.env` and passed to the Docker container, enabling Notion publishing and ImgBB chart uploads.
* **User Context**: Docker containers run with appropriate user permissions (`goldstandard` user internally, explicitly matched to `user` on host for bind mounts), ensuring all file access is correctly handled.
* **Systemd Automations**: The `systemd` service and timer files (`gold-standard-daily.*`, `gold-standard-weekly-cleanup.*`, `gold-standard-compose.service`) are correctly configured, enabled, and running to manage the application's lifecycle and scheduled tasks without manual intervention.
    * `gold-standard-compose.service`: `active (running)`
    * `gold-standard-daily.timer`: `active (running)`
    * `gold-standard-weekly-cleanup.timer`: `active (waiting)`
* **New `codex.sh` Command**: A `heal` command has been added to `codex.sh` to facilitate easy restart and recovery of the Docker Compose services.


# Automation Schedule Overview

This section details the automated scheduling and operational parameters of the Gold Standard system, managed by `systemd` timers. These configurations ensure the system operates autonomously, generating reports and performing maintenance tasks without manual intervention.

## 1. Daily Analysis (`gold-standard-daily.timer`)

* **Purpose**: Triggers the main daily analysis and reporting cycle of the Gold Standard application.
* **Service**: `gold-standard-daily.service`
* **Schedule**: `OnCalendar=daily` (Runs once per day).
* **Execution Time**: The service description indicates "at 5am".
* **Accuracy**: `AccuracySec=1h` (The job will start within 1 hour of the scheduled time).
* **Randomized Delay**: `RandomizedDelaySec=30m` (A random delay of up to 30 minutes is added before execution to prevent load spikes on system start or network congestion if many jobs are scheduled for the same time).
* **Persistence**: `Persistent=true` (If the system is off during the scheduled time, the job will run shortly after the system boots up).
* **Trigger Command**: Executes `/home/user/codex.sh run` inside a Docker container.
* **Logs**: Output is appended to `/mnt/newdisk/gold_standard/gold_standard_config/run.log`.

## 2. Weekly Cleanup (`gold-standard-weekly-cleanup.timer`)

* **Purpose**: Triggers weekly maintenance and cleanup tasks for the Gold Standard system.
* **Service**: `gold-standard-weekly-cleanup.service`
* **Schedule**: `OnCalendar=weekly` (Runs once per week).
* **Execution Time**: The service description indicates "at 1am on Sunday".
* **Accuracy**: `AccuracySec=1h`.
* **Randomized Delay**: `RandomizedDelaySec=30m`.
* **Persistence**: `Persistent=true`.
* **Trigger Command**: Executes `/usr/local/bin/gold-standard-weekly-cleanup.sh`.
* **Logs**: Output is appended to `/mnt/newdisk/gold_standard/gold_standard_config/cleanup.log`.

## 3. Docker Compose Stack Management (`gold-standard-compose.service`)

* **Purpose**: Manages the core Docker Compose stack, including the main Gold Standard application container (`gost`) and the monitoring/logging infrastructure (Prometheus, Grafana, Loki, etc.).
* **Service**: `gold-standard-compose.service`
* **Trigger**: This is a regular `systemd` service, not a timer. It is configured to start automatically on system boot.
* **Execution**: Starts the Docker Compose stack with `--profile monitoring --profile logging up -d`.
* **Restart Policy**: `Restart=on-failure` (Ensures the Docker stack automatically restarts if it crashes).
* **Logs**: Standard output and error are managed by `systemd` and can be viewed with `journalctl -u gold-standard-compose.service`.

## 4. Key Configuration Parameters

* **Application Data Directory**: All persistent application data (SQLite database, `cortex_memory.json`, output reports, charts) is stored under `/mnt/newdisk/gold_standard/docker-data/`.
* **Service Log Directory**: All `systemd` service logs (for daily and weekly operations) are stored in `/mnt/newdisk/gold_standard/gold_standard_config/`.
* **Environment Variables**: API keys and other configurations are loaded from `/mnt/newdisk/gold_standard/.env` and passed securely to the Docker containers.

This automated setup ensures the Gold Standard system operates reliably and autonomously, with all generated data and logs properly managed on the dedicated data disk.
