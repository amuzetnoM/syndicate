<div align="center">

```

   _____ _____________________.___________________  ____________________
  /  _  \\______   \__    ___/|   \_   _____/  _  \ \_   ___ \__    ___/
 /  /_\  \|       _/ |    |   |   ||    __)/  /_\  \/    \  \/ |    |
/    |    \    |   \ |    |   |   ||     \/    |    \     \____|    |
\____|__  /____|_  / |____|   |___|\___  /\____|__  /\______  /|____|
        \/       \/                    \/         \/        \/
      .__         __               .__
___  _|__|_______/  |_ __ _______  |  |
\  \/ /  \_  __ \   __\  |  \__  \ |  |
 \   /|  ||  | \/|  | |  |  // __ \|  |__
  \_/ |__||__|   |__| |____/(____  /____/
                                 \/

```

# FLEX AUDIT REPORT

### Enterprise Software Security & Quality Analysis

---

**Project:** `syndicate`
**Version:** `1.0`
**Generated:** `2025-12-05 12:34:41 UTC`
**Framework:** Flex Audit v2.0

---

</div>

---



## Executive Summary

<table>
<tr>
<td width="50%">

### Overall Security Score

<div align="center">

# 0/100

**F - Critical**

</div>

</td>
<td width="50%">

### Risk Distribution

| Severity | Count |
|:---------|------:|
| [!!] Critical | 727 |
| [!] High | 94 |
| [*] Medium | 3119 |
| [-] Low | 32660 |
| [.] Info | 4017 |

</td>
</tr>
</table>

### Assessment Overview

**CRITICAL:** The codebase has severe security vulnerabilities that must be addressed immediately. Production deployment should be blocked until critical issues are resolved.

---


## Code Metrics Dashboard

<table>
<tr>
<td width="33%">

### Repository Stats

| Metric | Value |
|:-------|------:|
| Total Files | 8998 |
| Lines of Code | 5,288,748 |
| Languages | Other, YAML, JSON, XML, Python +13 more |
| Dependencies | N/A |

</td>
<td width="33%">

### Security Metrics

| Metric | Value |
|:-------|------:|
| Secrets Found | 0 |
| Vulnerabilities | 821 |
| Misconfigs | 59 |
| Risk Score | 100 |

</td>
<td width="34%">

### Quality Metrics

| Metric | Value |
|:-------|------:|
| Code Smells | 37749 |
| Open Action Items | 4017 |
| Test Coverage | N/A |
| Doc Coverage | N/A |

</td>
</tr>
</table>

---

## 🔎 Detailed Findings


### [SEC] Security

<details>
<summary><b>1726 issues found</b> - Click to expand</summary>

| Severity | Location | Issue | Description |
|:---------|:---------|:------|:------------|
| [!!] CRITICAL | `.env:8` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `.env:14` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `.env:25` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `.env:8` | **GOOGLE_API_KEY** | Potential secret detected: GOOGLE_API_KEY |
| [!!] CRITICAL | `db_manager.py:1087` | **SQL_INJECTION_FSTRING** | F-strings in SQL queries lead to injection |
| [!!] CRITICAL | `db_manager.py:1089` | **SQL_INJECTION_FSTRING** | F-strings in SQL queries lead to injection |
| [!!] CRITICAL | `db_manager.py:1091` | **SQL_INJECTION_FSTRING** | F-strings in SQL queries lead to injection |
| [!!] CRITICAL | `db_manager.py:1093` | **SQL_INJECTION_FSTRING** | F-strings in SQL queries lead to injection |
| [!!] CRITICAL | `main.py:1438` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `README.md:523` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `docker\README.md:45` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `docs\GUIDE.md:1035` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `scripts\chart_publisher.py:281` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `scripts\setup.ps1:193` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `src\gost\init.py:29` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `src\gost\init.py:32` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `src\gost.egg-info\PKG-INFO:563` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `tests\test_gemini.py:48` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `tests\test_gemini.py:386` | **API_KEY** | Potential secret detected: API_KEY |
| [!!] CRITICAL | `venv312\Lib\site-packages\peewee.py:174` | **EXEC_USAGE** | Use of exec() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\peewee.py:3632` | **SQL_INJECTION_FORMAT** | String formatting in SQL queries leads to injection |
| [!!] CRITICAL | `venv312\Lib\site-packages\peewee.py:3638` | **SQL_INJECTION_FORMAT** | String formatting in SQL queries leads to injection |
| [!!] CRITICAL | `venv312\Lib\site-packages\peewee.py:4279` | **SQL_INJECTION_FORMAT** | String formatting in SQL queries leads to injection |
| [!!] CRITICAL | `venv312\Lib\site-packages\six.py:740` | **EXEC_USAGE** | Use of exec() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:1485` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:4029` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:4034` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:4081` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:4093` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:4116` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\typing_extensions.py:1485` | **EXEC_USAGE** | Use of exec() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\anyio\to_interpreter.py:123` | **EXEC_USAGE** | Use of exec() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\anyio\to_interpreter.py:130` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |
| [!!] CRITICAL | `venv312\Lib\site-packages\anyio\to_process.py:92` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |
| [!!] CRITICAL | `venv312\Lib\site-packages\anyio\to_process.py:216` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |
| [!!] CRITICAL | `venv312\Lib\site-packages\cffi\recompiler.py:78` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\cffi\setuptools_ext.py:26` | **EXEC_USAGE** | Use of exec() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\cffLib\__init__.py:1267` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\cffLib\__init__.py:2498` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\misc\symfont.py:241` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\M_E_T_A_.py:286` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otBase.py:945` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otBase.py:983` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otBase.py:1087` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otBase.py:1129` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otConverters.py:80` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\otTables.py:1725` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\fontTools\ttLib\tables\S_I_N_G_.py:66` | **EVAL_USAGE** | Use of eval() can lead to arbitrary code execution |
| [!!] CRITICAL | `venv312\Lib\site-packages\frozendict-2.4.7.dist-info\METADATA:257` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |
| [!!] CRITICAL | `venv312\Lib\site-packages\frozendict-2.4.7.dist-info\METADATA:469` | **UNSAFE_PICKLE** | Unpickling untrusted data can execute arbitrary code |

*... and 1676 more findings in this category*


</details>

---

### [CODE] Code Quality

<details>
<summary><b>37749 issues found</b> - Click to expand</summary>

| Severity | Location | Issue | Description |
|:---------|:---------|:------|:------------|
| [!] HIGH | `run.py:448` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\purge.py:78` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\purge.py:99` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\purge.py:141` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\purge.py:151` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\split_reports.py:96` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `scripts\task_executor.py:677` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `tests\test_gemini.py:393` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\peewee.py:59` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\cffi\pkgconfig.py:41` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\dateutil\tz\tz.py:1748` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\google\auth\pluggable.py:185` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\googleapiclient\discovery_cache\__init__.py:42` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\matplotlib\backend_bases.py:1543` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\matplotlib\font_manager.py:1631` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\matplotlib\tests\test_font_manager.py:342` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\cloudpickle\cloudpickle.py:237` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\core\compiler.py:789` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\misc\numba_sysinfo.py:463` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\tests\test_exceptions.py:436` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\tests\test_extending.py:515` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\tests\test_flow_control.py:212` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numba\tests\test_try_except.py:729` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\capi_maps.py:296` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:1155` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:1169` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:1179` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:1968` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2314` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2356` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2653` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2662` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2924` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:2931` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\f2py\crackfortran.py:3491` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\ma\core.py:1090` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\ma\core.py:1232` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\_core\function_base.py:483` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\numpy\_core\tests\test_nditer.py:3123` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\pandas\core\apply.py:972` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\pandas\core\indexes\base.py:6409` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\pandas\plotting\_matplotlib\converter.py:327` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\pandas\tests\io\conftest.py:106` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\EpsImagePlugin.py:246` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\Image.py:3944` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\ImageFont.py:110` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\ImageTk.py:142` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\ImageTk.py:230` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\JpegImagePlugin.py:89` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |
| [!] HIGH | `venv312\Lib\site-packages\PIL\PngImagePlugin.py:463` | **SILENT_EXCEPTION** | Silently swallowing exceptions hides bugs |

*... and 37699 more findings in this category*


</details>

---

### [DEP] Dependencies

<details>
<summary><b>1083 issues found</b> - Click to expand</summary>

| Severity | Location | Issue | Description |
|:---------|:---------|:------|:------------|
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\acceleratedmobilepageurl.v1.json:160` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\adexperiencereport.v1.json:161` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directoryv1.json:4883` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directoryv1.json:5620` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directoryv1.json:5691` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directory_v1.json:4883` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directory_v1.json:5620` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\admin.directory_v1.json:5691` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\adsense.v2.json:1062` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\adsense.v2.json:1441` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\adsense.v2.json:2294` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1.json:41423` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1.json:49091` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1.json:49237` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1.json:49598` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1.json:50940` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1beta1.json:52562` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1beta1.json:62539` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1beta1.json:62685` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1beta1.json:63204` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\aiplatform.v1beta1.json:64546` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:1735` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:2019` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:2132` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:2340` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:3992` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:4785` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:5082` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:5440` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:5647` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6038` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6101` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6236` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6356` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6437` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1.json:6496` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:1753` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:2042` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:2155` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:2392` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:4252` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:5045` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:5342` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:5700` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:5907` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:6298` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:6361` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:6496` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:6637` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |
| [*] MEDIUM | `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\alloydb.v1alpha.json:6718` | **UNPINNED_DEPENDENCY** | Unpinned dependency - pin to specific version |

*... and 1033 more findings in this category*


</details>

---

### [CFG] Configuration

<details>
<summary><b>59 issues found</b> - Click to expand</summary>

| Severity | Location | Issue | Description |
|:---------|:---------|:------|:------------|
| [*] MEDIUM | `venv312\Lib\site-packages\matplotlib\transforms.py:116` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\core\compiler.py:147` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\compiler.py:311` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\decorators.py:78` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\recursion_usecases.py:66` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_compiler.py:104` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_compiler.py:112` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_cuda_jit_no_types.py:84` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:45` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:71` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:78` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:107` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:116` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:120` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:144` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_debuginfo.py:177` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_exception.py:25` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_exception.py:37` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_exception.py:127` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_exception.py:163` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_fastmath.py:201` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_fastmath.py:202` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_lineinfo.py:188` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_userexc.py:25` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_warning.py:113` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_warning.py:120` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_warning.py:127` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:46` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:170` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:184` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:321` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:369` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:374` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:399` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:433` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:495` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:530` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:622` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:623` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:624` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:669` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:721` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_debuginfo.py:739` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_gdb_bindings.py:40` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_gdb_bindings.py:41` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_obj_lifetime.py:465` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_obj_lifetime.py:466` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_obj_lifetime.py:468` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_obj_lifetime.py:470` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |
| [*] MEDIUM | `venv312\Lib\site-packages\numba\tests\test_optimisation_pipelines.py:20` | **DEBUG_ENABLED** | Debug mode enabled - disable in production |

*... and 9 more findings in this category*


</details>

---

## Prioritized Recommendations

### Immediate Actions (0-3 days)

- 🔴 **Address all critical security vulnerabilities** - Block deployment until resolved
- ⚠️ **Remove eval/exec usage** - Replace with safe alternatives

### Short-term Actions (1-2 weeks)

- 🟠 **Address high-severity findings** - Schedule for next sprint
- 🐛 **Fix bare except clauses** - Use specific exception types
- 📝 **Improve code quality** - Address code smells and remaining open action items

### Long-term Actions (1-3 months)

- 📊 **Implement continuous security scanning** in CI/CD pipeline
- 🧪 **Increase test coverage** to catch regressions
- 📚 **Improve documentation** and code comments

---

## 📁 Files Analyzed

<details>
<summary><b>Click to expand file list</b></summary>

| File | Language | Lines | Issues |
|:-----|:---------|------:|-------:|
| `venv312\Lib\site-packages\matplotlib\tests\test_axes.py` | Python | 9666 | 🔴 610 |
| `venv312\Lib\site-packages\pandas\tests\dtypes\test_inference.py` | Python | 2073 | 🔴 368 |
| `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\compute.alpha.json` | JSON | 123687 | 🔴 364 |
| `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\compute.beta.json` | JSON | 110431 | 🔴 299 |
| `venv312\Lib\site-packages\pandas\tests\copy_view\test_methods.py` | Python | 2080 | 🔴 285 |
| `venv312\Lib\site-packages\pandas\tests\reductions\test_reductions.py` | Python | 1723 | 🔴 281 |
| `venv312\Lib\site-packages\pandas\tests\scalar\period\test_period.py` | Python | 1159 | 🔴 279 |
| `venv312\Lib\site-packages\pandas\tests\dtypes\test_dtypes.py` | Python | 1235 | 🔴 276 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\test_format.py` | Python | 2290 | 🔴 269 |
| `venv312\Lib\site-packages\pandas\tests\computation\test_eval.py` | Python | 2007 | 🔴 268 |
| `venv312\Lib\site-packages\googleapiclient\discovery_cache\documents\compute.v1.json` | JSON | 97441 | 🔴 267 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timestamp\test_timestamp.py` | Python | 929 | 🔴 260 |
| `venv312\Lib\site-packages\pandas\tests\scalar\period\test_asfreq.py` | Python | 829 | 🔴 238 |
| `venv312\Lib\site-packages\numpy\f2py\tests\test_symbolic.py` | Python | 495 | 🔴 237 |
| `venv312\Lib\site-packages\pandas\tests\frame\test_constructors.py` | Python | 3388 | 🔴 237 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timedelta\test_arithmetic.py` | Python | 1184 | 🔴 222 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_multiarray.py` | Python | 10381 | 🔴 220 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\style\test_style.py` | Python | 1589 | 🔴 220 |
| `venv312\Lib\site-packages\pandas\tests\io\test_sql.py` | Python | 4388 | 🔴 213 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timedelta\test_timedelta.py` | Python | 667 | 🔴 201 |
| `venv312\Lib\site-packages\pandas\tests\series\test_constructors.py` | Python | 2297 | 🔴 199 |
| `venv312\Lib\site-packages\matplotlib\tests\test_figure.py` | Python | 1822 | 🔴 194 |
| `venv312\Lib\site-packages\matplotlib\tests\test_widgets.py` | Python | 1760 | 🔴 188 |
| `venv312\Lib\site-packages\pandas\tests\dtypes\test_common.py` | Python | 866 | 🔴 186 |
| `venv312\Lib\site-packages\pandas\tests\plotting\test_datetimelike.py` | Python | 1761 | 🔴 172 |
| `venv312\Lib\site-packages\matplotlib\tests\test_colors.py` | Python | 1748 | 🔴 163 |
| `venv312\Lib\site-packages\pandas\tests\internals\test_internals.py` | Python | 1423 | 🔴 151 |
| `venv312\Lib\site-packages\mpl_toolkits\mplot3d\tests\test_axes3d.py` | Python | 2689 | 🔴 144 |
| `venv312\Lib\site-packages\matplotlib\tests\test_ticker.py` | Python | 1940 | 🔴 139 |
| `venv312\Lib\site-packages\numba\core\ir.py` | Python | 1703 | 🔴 136 |
| `venv312\Lib\site-packages\matplotlib\tests\test_ft2font.py` | Python | 944 | 🔴 132 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_simd.py` | Python | 1336 | 🔴 130 |
| `venv312\Lib\site-packages\pandas\tests\plotting\frame\test_frame.py` | Python | 2625 | 🔴 128 |
| `venv312\Lib\site-packages\matplotlib\tests\test_cbook.py` | Python | 1050 | 🔴 126 |
| `venv312\Lib\site-packages\pandas\tests\io\json\test_ujson.py` | Python | 1088 | 🔴 126 |
| `venv312\Lib\site-packages\pandas\pyproject.toml` | TOML | 820 | 🔴 124 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timestamp\test_constructors.py` | Python | 1078 | 🔴 123 |
| `venv312\Lib\site-packages\pandas\tests\dtypes\test_missing.py` | Python | 924 | 🔴 121 |
| `run.py` | Python | 830 | 🔴 119 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_dtype.py` | Python | 1964 | 🔴 119 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\test_to_string.py` | Python | 1217 | 🔴 118 |
| `venv312\Lib\site-packages\pandas\tests\tools\test_to_datetime.py` | Python | 3927 | 🔴 118 |
| `venv312\Lib\site-packages\numba\parfors\parfor_lowering.py` | Python | 2069 | 🔴 112 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_numeric.py` | Python | 4211 | 🔴 109 |
| `venv312\Lib\site-packages\pandas\tests\copy_view\test_functions.py` | Python | 398 | 🔴 107 |
| `venv312\Lib\site-packages\pandas\tests\libs\test_hashtable.py` | Python | 749 | 🔴 107 |
| `venv312\Lib\site-packages\matplotlib\tests\test_collections.py` | Python | 1394 | 🔴 104 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\test_to_html.py` | Python | 1178 | 🔴 103 |
| `venv312\Lib\site-packages\pandas\tests\tseries\offsets\test_offsets.py` | Python | 1186 | 🔴 103 |
| `venv312\Lib\site-packages\pandas\tests\indexes\test_base.py` | Python | 1735 | 🔴 101 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_casting_unittests.py` | Python | 819 | 🔴 100 |
| `venv312\Lib\site-packages\pandas\tests\frame\indexing\test_indexing.py` | Python | 2034 | 🔴 100 |
| `venv312\Lib\site-packages\numba\cuda\tests\cudapy\test_atomics.py` | Python | 1621 | 🔴 99 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\style\test_format.py` | Python | 563 | 🔴 99 |
| `venv312\Lib\site-packages\pandas\tests\indexes\interval\test_interval.py` | Python | 919 | 🔴 98 |
| `venv312\Lib\site-packages\numpy\random\tests\test_randomstate.py` | Python | 2125 | 🔴 97 |
| `venv312\Lib\site-packages\numba\parfors\parfor.py` | Python | 5250 | 🔴 96 |
| `venv312\Lib\site-packages\numba\tests\test_typeof.py` | Python | 602 | 🔴 96 |
| `venv312\Lib\site-packages\numpy\random\tests\test_generator_mt19937.py` | Python | 2798 | 🔴 96 |
| `venv312\Lib\site-packages\pandas\tests\indexes\ranges\test_range.py` | Python | 623 | 🔴 96 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timedelta\test_constructors.py` | Python | 699 | 🔴 96 |
| `venv312\Lib\site-packages\numpy\f2py\tests\test_array_from_pyobj.py` | Python | 678 | 🔴 95 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_umath.py` | Python | 4898 | 🔴 94 |
| `venv312\Lib\site-packages\pandas\tests\groupby\test_groupby.py` | Python | 3364 | 🔴 94 |
| `venv312\Lib\site-packages\pydantic\types.py` | Python | 3296 | 🔴 94 |
| `venv312\Lib\site-packages\numpy\f2py\tests\test_f2py2e.py` | Python | 965 | 🔴 93 |
| `venv312\Lib\site-packages\pandas\tests\arrays\test_datetimelike.py` | Python | 1361 | 🔴 93 |
| `venv312\Lib\site-packages\pandas\tests\indexes\multi\test_indexing.py` | Python | 1002 | 🔴 91 |
| `venv312\Lib\site-packages\matplotlib\tests\test_pyplot.py` | Python | 486 | 🔴 90 |
| `venv312\Lib\site-packages\matplotlib\tests\test_legend.py` | Python | 1487 | 🔴 88 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_stringdtype.py` | Python | 1834 | 🔴 87 |
| `venv312\Lib\site-packages\pandas\tests\copy_view\test_replace.py` | Python | 496 | 🔴 87 |
| `venv312\Lib\site-packages\pandas\tests\indexes\period\test_indexing.py` | Python | 816 | 🔴 87 |
| `venv312\Lib\site-packages\matplotlib\tests\test_text.py` | Python | 1138 | 🔴 86 |
| `venv312\Lib\site-packages\numba\tests\test_try_except.py` | Python | 850 | 🔴 86 |
| `venv312\Lib\site-packages\pandas\tests\indexes\datetimes\test_date_range.py` | Python | 1722 | 🔴 86 |
| `venv312\Lib\site-packages\matplotlib\tests\test_transforms.py` | Python | 1132 | 🔴 85 |
| `venv312\Lib\site-packages\pandas\tests\scalar\period\test_arithmetic.py` | Python | 487 | 🔴 84 |
| `venv312\Lib\site-packages\pandas\tests\indexing\test_loc.py` | Python | 3412 | 🔴 83 |
| `venv312\Lib\site-packages\google\ai\generativelanguage_v1alpha\services\retriever_service\transports\rest.py` | Python | 4068 | 🔴 82 |
| `venv312\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\transports\rest.py` | Python | 4068 | 🔴 82 |
| `venv312\Lib\site-packages\pandas\tests\indexes\numeric\test_numeric.py` | Python | 554 | 🔴 82 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_array_coercion.py` | Python | 912 | 🔴 81 |
| `venv312\Lib\site-packages\pandas\tests\tseries\offsets\test_business_hour.py` | Python | 1446 | 🔴 81 |
| `venv312\Lib\site-packages\matplotlib\tests\test_dates.py` | Python | 1414 | 🔴 80 |
| `venv312\Lib\site-packages\numpy\f2py\crackfortran.py` | Python | 3747 | 🔴 80 |
| `venv312\Lib\site-packages\numpy\_core\tests\test_ufunc.py` | Python | 3202 | 🔴 79 |
| `venv312\Lib\site-packages\pandas\tests\config\test_config.py` | Python | 438 | 🔴 79 |
| `venv312\Lib\site-packages\pandas\tests\indexes\datetimelike_\test_equals.py` | Python | 182 | 🔴 79 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\style\test_to_latex.py` | Python | 1091 | 🔴 79 |
| `venv312\Lib\site-packages\numba\parfors\array_analysis.py` | Python | 3208 | 🔴 76 |
| `venv312\Lib\site-packages\pandas\tests\scalar\timestamp\test_comparisons.py` | Python | 314 | 🔴 76 |
| `venv312\Lib\site-packages\matplotlib\tests\test_artist.py` | Python | 599 | 🔴 74 |
| `venv312\Lib\site-packages\pandas\tests\arrays\sparse\test_libsparse.py` | Python | 552 | 🔴 74 |
| `venv312\Lib\site-packages\fontTools\subset\__init__.py` | Python | 4097 | 🔴 73 |
| `venv312\Lib\site-packages\pandas\tests\indexes\datetimes\test_scalar_compat.py` | Python | 330 | 🔴 73 |
| `venv312\Lib\site-packages\pandas\tests\io\formats\style\test_html.py` | Python | 1010 | 🔴 73 |
| `venv312\Lib\site-packages\pandas\tests\io\json\test_pandas.py` | Python | 2189 | 🔴 73 |
| `venv312\Lib\site-packages\numpy\random\tests\test_random.py` | Python | 1752 | 🔴 72 |
| `venv312\Lib\site-packages\pandas\tests\resample\test_datetime_index.py` | Python | 2226 | 🔴 72 |

*... and 8898 more files*


</details>



---

<div align="center">

---

## Report Metadata

| Property | Value |
|:---------|:------|
| **Generator** | Flex Audit v2.0 |
| **Framework** | ARTIFACT virtual Enterprise |
| **Generated** | 2025-12-05 12:34:42 UTC |
| **Standards** | OWASP, CWE, SANS Top 25 |

---

```

   _____ _____________________.___________________  ____________________
  /  _  \\______   \__    ___/|   \_   _____/  _  \ \_   ___ \__    ___/
 /  /_\  \|       _/ |    |   |   ||    __)/  /_\  \/    \  \/ |    |
/    |    \    |   \ |    |   |   ||     \/    |    \     \____|    |
\____|__  /____|_  / |____|   |___|\___  /\____|__  /\______  /|____|
        \/       \/                    \/         \/        \/
      .__         __               .__
___  _|__|_______/  |_ __ _______  |  |
\  \/ /  \_  __ \   __\  |  \__  \ |  |
 \   /|  ||  | \/|  | |  |  // __ \|  |__
  \_/ |__||__|   |__| |____/(____  /____/
                                 \/

```

**© 2025 ARTIFACT virtual - Enterprise Software Intelligence**

*This report was generated automatically by Flex Audit.*
*For questions or support, visit: https://github.com/amuzetnoM*

---

</div>
