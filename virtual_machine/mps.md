# Mass Provisioning Script for Google Cloud Ops Agents

[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-SDK-blue.svg)](https://cloud.google.com/sdk)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-repo/actions)

## 1. Overview

This script automates the installation and configuration of Google Cloud's operations agents (Logging and Metrics) on a large number of Google Cloud virtual machines (VMs). It reads a list of target VMs and their desired agent configurations from a CSV file, and then proceeds to provision them concurrently.

The script is designed to be robust, performant, and maintainable, with features like state management, automatic retries, and detailed logging.

## 2. Features

- **Concurrent Execution:** Utilizes a `ThreadPoolExecutor` to run provisioning tasks in parallel, significantly reducing the time required to provision a large number of VMs.
- **State Management:** Maintains a state file (`provisioning_state.json`) to track the provisioning status of each VM. This prevents unnecessary re-installations on already provisioned VMs.
- **Automatic Retries:** Automatically retries failed SSH commands with an exponential backoff strategy, making the script more resilient to transient network issues.
- **Configurable:** Provides command-line arguments to control the number of concurrent workers, the number of retries, and to force re-provisioning.
- **Modular and Maintainable Code:** Refactored into a class-based structure, making the code more organized and easier to maintain.
- **Robust Input Validation:** Provides specific and user-friendly error messages to help users quickly identify and resolve issues in the input file.
- **Detailed Logging:** Generates detailed logs for each run, including a main wrapper script log and individual logs for each VM.
- **Automated Testing:** Includes a suite of unit tests to ensure the script's validation logic and new features are working correctly.

## 3. Prerequisites

- Python 3.6+
- Google Cloud SDK (`gcloud` CLI) installed and authenticated.

## 4. Installation

1. Clone this repository to your local machine.
2. Ensure you have the required prerequisites installed.
3. No additional installation is required.

## 5. Usage

Execute the script from your terminal, providing the path to your input CSV file.

```bash
python3 mass_provision_google_cloud_ops_agents.py --file <path_to_your_vms.csv> [OPTIONS]
```

### Command-Line Arguments

- `--file` (required): The path to the input CSV file that contains a list of VMs to provision the agent on.
- `--max-workers` (optional, default: 10): The maximum number of concurrent workers to use for provisioning.
- `--force` (optional, default: False): If set, the script will re-provision all VMs, even if they have been successfully provisioned before. This is useful if you want to force an update or re-installation of the agents.
- `--max-retries` (optional, default: 3): The maximum number of retries for a failed SSH command.

## 6. Input File Format

The input file must be a CSV file with two columns:

- **Column 1:** The full instance name of the VM in the format `projects/PROJECT_ID/zones/ZONE/instances/INSTANCE_NAME`.
- **Column 2:** A JSON string specifying the agent rules. The JSON should be an array of objects, where each object has a `type` and an optional `version`.

### Agent Rules

- `type`: The type of the agent to install. Valid types are:
    - `"logging"`: The Cloud Logging agent.
    - `"metrics"`: The Cloud Monitoring agent.
    - `"ops-agent"`: The unified Ops Agent, which includes both logging and metrics capabilities.
- `version`: (Optional) The version of the agent to install. It can be:
    - `"latest"`: To install the latest available version.
    - A specific version in the format `MAJOR.MINOR.PATCH` (e.g., `"1.2.3"`).
    - A major version pin in the format `MAJOR.*.*` (e.g., `"1.*.*"`).

### Example `vms.csv`

```csv
"projects/my-project/zones/us-central1-a/instances/instance-1","[{""type"":""ops-agent"",""version"":""1.*.*""}]"
"projects/my-project/zones/us-central1-a/instances/instance-2","[{""type"":""logging"",""version"":""1.*.*""},{""type"":""metrics"",""version"":""6.*.*""}]"
"projects/my-project/zones/us-central1-a/instances/instance-3","[{""type"":""ops-agent"",""version"":""latest""}]"
```

**Note:** When using the `"ops-agent"`, you cannot specify any other agent types for the same VM, as the Ops Agent includes both logging and metrics functionalities.

## 7. State Management

The script maintains a state file named `provisioning_state.json` in the `google_cloud_ops_agent_provisioning/` directory. This file is a JSON object where the keys are the full instance names of the VMs and the values are objects containing the `status` and `last_updated` timestamp.

This state management system allows the script to keep track of the provisioning status of each VM and avoid re-running installations on VMs that have already been successfully provisioned.

You can use the `--force` flag to ignore the state file and force re-provisioning of all VMs.

## 8. Logging

The script generates detailed logs for each run in the `google_cloud_ops_agent_provisioning/` directory. For each run, a new timestamped subdirectory is created, which contains the following:

- `wrapper_script.log`: A log file for the main script, containing high-level information about the provisioning process.
- `<instance_name>.log`: Individual log files for each VM, containing the detailed output of the installation commands.

These logs are essential for debugging and auditing the provisioning process.

## 9. Error Handling and Retries

The script includes a robust error handling and retry mechanism. If an SSH command fails to execute on a VM, the script will automatically retry the command with an exponential backoff strategy. The number of retries can be configured using the `--max-retries` command-line argument.

If the command continues to fail after the maximum number of retries, the script will mark the VM as `FAILURE` in the state file and in the final report.

## 10. Testing

The script includes a suite of unit tests to ensure the validation logic and other components are working correctly. To run the tests, execute the following command:

```bash
python3 test_mass_provision_google_cloud_ops_agents.py
```
