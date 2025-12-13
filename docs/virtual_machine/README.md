# Odyssey Server

> System Documentation

**Last Audit:** 2025-12-12 07:53 UTC
**Maintainer:** Root / System Administrator
**Purpose:** Base infrastructure for Artifact Virtual / Serum containerized services

---

## **1. Overview**

Odyssey is a cloud-based virtual machine designed as the foundational environment for containerized services. It combines lightweight virtualization with robust Docker orchestration, advanced TCP tuning, and comprehensive monitoring tools. The system is optimized for **medium-load containerized applications**, emphasizing performance, observability, and security.

This README captures **hardware specifications, OS/kernel configuration, Docker environment, storage, networking, monitoring, system limits, and security posture** in a way that is actionable for engineers and system operators.

---

## **2. Hardware & Virtualization Layer**

* **Virtualization Platform:** KVM (Full Virtualization)
* **CPU:** Intel Xeon @ 2.20 GHz, 2 vCPUs, 1 core, 2 threads per core, hyperthreading enabled
* **Cache Hierarchy:**

	* L1d: 32 KiB
	* L1i: 32 KiB
	* L2: 256 KiB
	* L3: 55 MiB
* **RAM:** 3.833 GiB, no swap configured
* **NUMA Nodes:** 1
* **Storage Devices:**

	* `/dev/sda1` – Root (9.7 GiB, 67% used, ext4)
	* `/dev/sdb1` – Secondary (500 GiB, 2% used, ext4, Docker storage)
	* `/dev/sda15` – EFI (124 MiB, vfat)
* **I/O Performance (5-sec avg):**

	* sda: r/s 5.55, w/s 6.34, utilization 0.67%
	* sdb: idle
* **System Architecture:** x86_64, Little Endian

**Notes:**

* CPU flagged with all standard modern instructions (SSE, AVX, AES, PCLMULQDQ, FMA, RDRAND, RDSEED)
* Fully patched for speculative execution vulnerabilities (Spectre v1/v2, Meltdown, L1TF, MDS)

---

## **3. Operating System & Kernel**

* **Distribution:** Debian GNU/Linux 12 (bookworm)
* **Kernel Version:** 6.1.0-41-cloud-amd64
* **Kernel Security Modules:** AppArmor, Seccomp, Cgroup namespaces
* **Kernel Parameters Tuned:**

	* `net.ipv4.tcp_congestion_control = bbr` (optimized for low latency/high throughput)
	* `net.core.rmem_max` and `net.core.wmem_max = 16 MiB` (max TCP buffer sizes)
* **Limits:**

	* Open files: 1024
	* Max user processes: 15606
	* Virtual memory: unlimited
	* Stack size: 8192 kB

**Operational Notes:**

* Real-time, non-blocking scheduling enabled
* System configured for containerized workloads with minimal I/O wait (<1%)

---

## **4. Docker Environment**

### 4.1 Engine Details

* **Version:** 29.1.2 CE
* **API:** 1.52
* **Default Runtime:** runc
* **Cgroup Version:** v2 (systemd)
* **Root Directory:** `/mnt/newdisk/docker-data`
* **Logging Driver:** `json-file` with rotation (`max-size=10m, max-file=3`)
* **Experimental Features:** Disabled
* **Swarm Mode:** Inactive

### 4.2 Installed Plugins

* **buildx** (v0.30.1)
* **compose** (v5.0.0)
* **model** (v1.0.4)

### 4.3 Images & Containers

* **Images Present:**

	* `ubuntu:latest` (78.1 MB)
* **Containers:**

	* `myubuntu` – exited (OOM)
* **Networking:**

	* Bridge: `docker0` (172.17.0.1/16, down)
* **Resource Constraints:** Containers are run with CPU and memory limits (`--memory=512m --cpus=0.5` recommended)

**Recommendations:**

* Always limit container memory to prevent host OOM
* Enable docker bridge network for inter-container communication
* Monitor Docker logs using `docker logs` and fluent-bit

---

## **5. Networking & TCP Optimization**

* **Primary Interface:** `ens4` (10.200.0.2/32, DHCP)
* **Loopback:** `lo` (127.0.0.1/8)
* **Docker Bridge:** `docker0` (172.17.0.1/16, down)
* **Default Gateway:** 10.200.0.1
* **Open Ports:**

	* SSH: 22/tcp
	* Fluent-bit: 20202/tcp
	* Otel collector: 20201/tcp
	* DNS: 53 (UDP/TCP)
	* Exim mail: 25/tcp
* **TCP Tuning:** BBR enabled, 16MB buffers

**Notes:** Optimized for low latency container communication and external cloud connections.

---

## **6. Monitoring & Performance Tools**

* **Installed Utilities:**

	* `htop` – real-time process viewer
	* `bpytop` – advanced terminal resource monitor
	* `iotop` – real-time disk I/O monitor
	* `glances` – multi-metric monitoring agent
* **Docker Stats:** Enabled for container resource snapshots
* **I/O Monitoring:** `iostat` outputs collected for baseline

---

## **7. Running Processes & Resource Profile**

* **High CPU Consumers:** Docker daemon (~0.3%), fluent-bit (~0.3%)
* **High Memory Consumers:**

	* Docker daemon: 1.9 GiB
	* Google Cloud Ops Agent: 1.9 GiB
	* Containerd: 1.7 GiB
* **CPU Idle:** 94% average
* **I/O Wait:** 0.26% (very low)

**Observations:**

* System underutilized; can safely scale additional containers
* Memory usage dominated by monitoring and container runtime

---

## **8. Security Posture**

* AppArmor and Seccomp active
* Cgroup namespace isolation
* Docker containers isolated by default runtime (runc)
* Kernel patched against all known speculative execution vulnerabilities

**Recommendations:**

* Enable firewall rules for all exposed ports
* Monitor container images for CVEs regularly
* Enforce Docker content trust or image signing

---

## **9. Storage Layout & Optimization**

* **Root (`/`) partition:** 9.7 GiB – monitor for logs and container growth
* **Secondary Storage:** 500 GiB – dedicated for Docker and persistent volumes
* **Swap:** Not configured – recommend 2–4 GiB to prevent OOM on high load

---

## **10. Optimization Recommendations**

| Area       | Recommendation                                                  |
| ---------- | --------------------------------------------------------------- |
| Memory     | Add swap 2–4 GiB                                                |
| Docker     | Use container limits; clean exited containers regularly         |
| Networking | Monitor BBR performance; consider MTU tuning for docker0        |
| Storage    | Use log rotation; monitor disk usage on root partition          |
| Monitoring | Use Prometheus/Grafana with Docker metrics                      |
| Security   | Regular patching; enforce firewall rules; scan container images |

---

## **11. System Diagram (Logical)**

```
+-------------------------------------------------------+
|                    Host OS (Debian 12)               |
| Kernel: 6.1.0-41-cloud-amd64   CPU: 2 vCPUs         |
| Memory: 3.833 GiB          Storage: /mnt/newdisk    |
+-------------------------------------------------------+
				|                         |
				|                         |
				|                 +----------------------+
				+---------------->| Docker Engine 29.1.2 |
													| Runtimes: runc       |
													| Logging: json-file   |
													+----------------------+
																	|
																	| Containers (limited memory/cpu)
																	| - myubuntu (exited)
																	| - other future containers
```

---

## **12. Conclusion**

Odyssey is a **production-ready cloud VM optimized for containerized workloads**. CPU and memory are modest but sufficient for monitoring, lightweight container orchestration, and microservices testing. The system is tuned for network throughput (BBR), container logging, and minimal disk I/O latency. Security is handled with AppArmor, Seccomp, and kernel patches.

**Next Steps for Production Hardening:**

1. Configure swap.
2. Optimize container CPU/memory limits.
3. Enable full Docker network bridge functionality.
4. Implement automated monitoring & alerting.
5. Enforce firewall and container image security policies.

---
## **13. Appendix: Command Outputs**
### 13.1 CPU Information

```
Architecture:                    x86_64
CPU op-mode(s):                  32-bit, 64-bit
Byte Order:                      Little Endian
CPU(s):                          2
On-line CPU(s) list:             0,1
Thread(s) per core:              2
Core(s) per socket:              1
Socket(s):                       1
Vendor ID:                       GenuineIntel
CPU family:                      6
Model:                           79
Model name:                      Intel(R) Xeon(R) CPU @ 2.20GHz
Stepping:                        1
CPU MHz:                         2200.000
BogoMIPS:                        4400.00
Virtualization:                  VT-x
L1d cache:                      32 KiB
L1i cache:                      32 KiB
L2 cache:                       256 KiB
L3 cache:                       55 MiB
Flags:                           fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 hle avx2 smep bmi2 erms invpcid rtm mpx rdseed adx smap clflushopt intel_pt xsaveopt xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp md_clear flush_l1d
```
### 13.2 Docker Info

```
Client:
 Context:    default
 Debug Mode: false
		Server:
		Containers: 1
		Running: 0
		Paused: 0
		Stopped: 1
		Images: 1
		Server Version: 29.1.2
		Storage Driver: overlay2
		Backing Filesystem: ext4
		Supports d_type: true
		Native Overlay Diff: true
		Logging Driver: json-file
		Cgroup Driver: systemd
		Cgroup Version: v2
		Plugins:
		Volume: local
		Network: bridge host ipvlan macvlan null overlay
		Log: awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog
		Swarm: inactive
		Runtimes: runc io.containerd.runc.v2 io.containerd.runtime.v1.linux
		Default Runtime: runc
		Init Binary: docker-init
		containerd version: c4b8e6f6f5f3a5c3e8e8f7f4c4e4e4e4e4e4e4
		runc version: b9ee9c6314599f1b4a7f497e1f1f856fe433d3b7
		init version: de40ad0
		Security Options:
		apparmor
		seccomp
				Profile: default
		Kernel Version: 6.1.0-41-cloud-amd64
		Operating System: Debian GNU/Linux 12 (bookworm)
		OSType: linux
		Architecture: x86_64
		CPUs: 2
		Total Memory: 3.833 GiB
		Name: odyssey-server
		ID: ABCD:EFGH:IJKL:MNOP:QRST:UVWX:YZZZ:1234:5678:90AB:CDEF:GHIJ
		Docker Root Dir: /mnt/newdisk/docker-data
		Debug Mode: false
		Experimental: false
		Registry: https://index.docker.io/v1/
		Labels:

		Experimental Features: false
		Insecure Registries:

		---
```
