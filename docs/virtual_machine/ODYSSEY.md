# Technical Documentation

This is a comprehensive technical overview of the Odyssey virtual machine, including hardware specs, OS details, Docker configuration, and system health.

## **1. System Overview**

* **Hostname:** `odyssey`
* **Operating System:** Debian GNU/Linux 12 (bookworm)
* **Kernel Version:** 6.1.0-41-cloud-amd64
* **Architecture:** x86_64
* **Hypervisor:** KVM (Full Virtualization)
* **Deployment Type:** Virtual Machine / Cloud Instance
* **Purpose:** Artifact Virtual / Serum infrastructure; containerized services via Docker

---

## **2. CPU Specifications**

* **Model:** Intel(R) Xeon(R) CPU @ 2.20GHz
* **Cores / Threads:** 2 vCPUs, 2 threads (1 core, 2 threads per core)
* **Hyperthreading:** Enabled
* **Flags / Capabilities:**
  SSE, SSE2, SSE3, SSE4.1, SSE4.2, AVX, AVX2, FMA, AES, PCLMULQDQ, RDRAND, RDSEED, Hypervisor, etc.
* **Cache Sizes:**

  * L1d: 32 KiB
  * L1i: 32 KiB
  * L2: 256 KiB
  * L3: 55 MiB
* **Vulnerability Mitigation:**
  Mitigated for L1TF, MDS, Meltdown, Spectre v1/v2, TSX Async Abort, etc.

---

## **3. Memory Specifications**

* **Total RAM:** 3.8 GiB
* **Used RAM:** 741 MiB
* **Available RAM:** 3.1 GiB
* **Buffers / Cache:** 2.1 GiB
* **Swap:** None configured (recommend adding 2–4 GiB)
* **Memory Details:**

  * DirectMap4k: 162616 kB
  * DirectMap2M: 4028416 kB
  * DirectMap1G: 2097152 kB
* **Max Memory Limits:** unlimited (no system cgroup restrictions)

---

## **4. Disk & Storage**

* **Root Partition (`/`)**

  * Size: 9.7 GiB
  * Used: 6.1 GiB (≈67%)
  * Filesystem: ext4
* **Secondary Storage**

  * Device: `/dev/sdb1`
  * Size: 500 GiB
  * Used: 5 GiB (≈2%)
  * Mount Point: `/mnt/newdisk`
* **Boot EFI Partition**

  * Size: 124 MiB
  * Filesystem: vfat
* **Docker Storage**

  * Root Dir: `/mnt/newdisk/docker-data`
  * Storage Driver: overlay2
  * Backing Filesystem: extfs
* **Disk I/O Stats (5 sec snapshot)**

  * `sda` avg r/s: 5.55, w/s: 6.34, %util: 0.67
  * `sdb` idle, very low utilization

---

## **5. Operating System & Kernel**

* **OS:** Debian 12 (bookworm)
* **Kernel:** 6.1.0-41-cloud-amd64
* **Kernel Modules:** Standard cloud-optimized modules
* **Security Options:** AppArmor, Seccomp, cgroupns

---

## **6. Docker Configuration**

* **Engine Version:** 29.1.2 (Community Edition)
* **API Version:** 1.52
* **Runtime:** runc (default), containerd
* **Cgroup Version:** v2
* **Logging Driver:** json-file (max-size 10MB, max-file 3)
* **Container Status:**

  * 1 container present (`myubuntu`), exited due to OOM
* **Images:**

  * `ubuntu:latest` (78.1MB)
* **Networking:** Bridge network `docker0` (down)
* **Plugins Installed:** buildx, compose, model

---

## **7. Networking**

* **Interfaces:**

  * `ens4` – 10.200.0.2/32 (primary, DHCP)
  * `docker0` – 172.17.0.1/16 (bridge, no carrier)
  * `lo` – 127.0.0.1/8
* **Routing Table:**

  * Default gateway via 10.200.0.1
* **TCP Settings:**

  * Congestion Control: BBR
  * Max rmem/wmem: 16MB
* **Open Ports:**

  * SSH: 22/tcp
  * Fluent-bit: 20202/tcp
  * Otel collector: 20201/tcp
  * DNS: 53 (UDP/TCP)
  * Exim: 25/tcp
  * Systemd-resolved: 5355/tcp/udp

---

## **8. Processes & Resource Usage**

* **Top CPU Consumers:**

  * Docker daemon: ~0.3% CPU, 1.9 GiB VSZ
  * Google Cloud Ops Agent: 0.3% CPU, 1.9 GiB VSZ
* **Top Memory Consumers:**

  * Docker daemon, Ops Agent, containerd, Google OS config agent
* **I/O Wait:** ~0.26% (low)
* **Average CPU Idle:** ~94%

---

## **9. System Limits & Kernel Parameters**

| Limit              | Value     |
| ------------------ | --------- |
| Open files         | 1024      |
| Max user processes | 15606     |
| Stack size         | 8192 kB   |
| Max locked memory  | 502360 kB |
| Virtual memory     | unlimited |
| Pending signals    | 15606     |

---

## **10. Monitoring Tools Installed**

* **htop** – process monitoring
* **bpytop** – real-time resource monitor
* **iotop** – I/O monitoring
* **Glances** – multi-metric system agent
* **Docker Stats** – container resource monitoring

**Recommendation:** Consider Prometheus/Grafana integration for production monitoring.

---

## **11. Security**

* AppArmor: Enabled
* Seccomp: Enabled (builtin profile)
* Firewall: iptables backend active
* Kernel security: Speculative execution vulnerabilities patched

**Recommendation:** Enable regular container image scanning and enforce Docker content trust.

---

## **12. Recommendations for Optimization**

| Area       | Recommendation                                         |
| ---------- | ------------------------------------------------------ |
| Swap       | Configure 2–4 GiB for stability                        |
| Docker     | Set CPU/memory limits for all containers               |
| Storage    | Monitor `/` usage, clean logs regularly                |
| Networking | Enable Docker bridge if container communication needed |
| Monitoring | Add alerting for high memory/CPU usage                 |
| Security   | Regular image CVE scanning and firewall enforcement    |

---

## **13. System Diagram (Logical)**

```
+------------------------+
|      Host (VM)         |
|------------------------|
| OS: Debian 12          |
| Kernel: 6.1            |
| CPU: 2 vCPUs           |
| RAM: 3.8 GiB           |
+------------------------+
        |   |
        |   +-> Storage: /mnt/newdisk (Docker data)
        |
        +-> Network: ens4 (10.200.0.2)
        |
        +-> Docker Engine 29.1.2
              |
              +-> Container: myubuntu (Exited)
              +-> Networking: docker0 (bridge)
```

---


# Technical Server Report

**Audit Timestamp:** 2025-12-12 07:53
**Maintainer:** System Administrator
**Purpose:** Artifact Virtual containerized infrastructure

---

## **1. System Overview**

| Property        | Value                             |
| --------------- | --------------------------------- |
| Hostname        | `odyssey`                         |
| OS              | Debian GNU/Linux 12 (bookworm)    |
| Kernel          | 6.1.0-41-cloud-amd64              |
| Architecture    | x86_64                            |
| Hypervisor      | KVM (Full Virtualization)         |
| Deployment Type | Virtual Machine / Cloud Instance  |
| Purpose         | Containerized services via Docker |

**Health Highlight:** System is stable, CPU and memory underutilized, ready for scaling container workloads.

---

## **2. CPU Specifications**

| Property                 | Value                                          |
| ------------------------ | ---------------------------------------------- |
| Model                    | Intel(R) Xeon(R) CPU @ 2.20GHz                 |
| vCPUs / Threads          | 2 vCPUs, 2 threads (1 core, 2 threads)         |
| Hyperthreading           | Enabled                                        |
| L1 Cache                 | 32 KiB (d), 32 KiB (i)                         |
| L2 Cache                 | 256 KiB                                        |
| L3 Cache                 | 55 MiB                                         |
| Flags / Features         | SSE, AVX, FMA, AES, RDRAND, RDSEED, Hypervisor |
| Vulnerability Mitigation | Spectre v1/v2, Meltdown, L1TF, MDS patched     |

**Health Highlight:** CPU idle ~94%; system optimized for low-latency container workloads.

---

## **3. Memory Specifications**

| Property          | Value                               |
| ----------------- | ----------------------------------- |
| Total RAM         | 3.8 GiB                             |
| Used RAM          | 741 MiB                             |
| Available RAM     | 3.1 GiB                             |
| Buffers / Cache   | 2.1 GiB                             |
| Swap              | None configured (recommend 2–4 GiB) |
| Max Memory Limits | unlimited                           |

**Memory Health:** Low utilization, no memory pressure. Adding swap recommended for stability under high load.

---

## **4. Disk & Storage**

| Partition / Device | Size    | Used    | Filesystem | Mount Point  | Notes                     |
| ------------------ | ------- | ------- | ---------- | ------------ | ------------------------- |
| `/`                | 9.7 GiB | 6.1 GiB | ext4       | /            | Root filesystem           |
| `/dev/sdb1`        | 500 GiB | 5 GiB   | ext4       | /mnt/newdisk | Docker persistent storage |
| `/dev/sda15`       | 124 MiB | 124 MiB | vfat       | /boot/efi    | EFI boot partition        |

**Docker Storage:**

* Root Dir: `/mnt/newdisk/docker-data`
* Storage Driver: `overlay2`
* Disk I/O: Low utilization (<1%)

**Health Highlight:** Root partition approaching 70% usage; monitor logs and container growth.

---

## **5. Operating System & Kernel**

* **content truncated for brevity in this preview**
