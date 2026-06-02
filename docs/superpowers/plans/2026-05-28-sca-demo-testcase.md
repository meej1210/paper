# SCA Demo Testcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible SCA demo input file and a Chinese test/demo guide for the existing Flask + Vue DevSecOps platform.

**Architecture:** This is a documentation and fixture-only change. The demo fixture lives under `tests/sca_demo/`, while the user-facing demonstration guide lives under `主文档层/` with the existing Chinese project manuals.

**Tech Stack:** Python requirements file, pip-audit, PowerShell CI wrapper, existing Flask/Vue platform.

---

### Task 1: Add SCA Demo Fixture

**Files:**
- Create: `tests/sca_demo/requirements-vulnerable.txt`
- Create: `tests/sca_demo/README.md`

- [ ] **Step 1: Create a vulnerable requirements fixture**

Use old Python package versions that are commonly detected by `pip-audit`.

```text
Django==2.2.0
Flask==0.12.2
requests==2.19.1
urllib3==1.24.1
PyYAML==5.1
Jinja2==2.10
```

- [ ] **Step 2: Add a fixture README**

Explain that the file is only for SCA demonstration, should not be installed into a real environment, and can be uploaded directly to the SCA task page.

- [ ] **Step 3: Verify the files exist**

Run:

```powershell
Test-Path tests\sca_demo\requirements-vulnerable.txt
Test-Path tests\sca_demo\README.md
```

Expected: both commands print `True`.

### Task 2: Add Chinese Testcase And Demo Guide

**Files:**
- Create: `主文档层/a26-SCA测试用例与演示说明.md`

- [ ] **Step 1: Write the test guide**

Include test objective, preconditions, test data, Web UI demo steps, CI/CD command demo, expected results, display talking points, screenshot suggestions, and failure explanations.

- [ ] **Step 2: Verify key command references**

The guide must use the existing script path:

```powershell
.\scripts\ci_security_scan.ps1
```

and the existing platform API:

```text
http://127.0.0.1:5000/api
```

- [ ] **Step 3: Check document presence**

Run:

```powershell
Test-Path 主文档层\a26-SCA测试用例与演示说明.md
```

Expected: prints `True`.

### Task 3: Optional Scanner Smoke Check

**Files:**
- Read: `tests/sca_demo/requirements-vulnerable.txt`

- [ ] **Step 1: Check whether pip-audit is installed**

Run:

```powershell
D:\anaconda\python.exe -m pip_audit --version
```

Expected: a version number if installed. If not installed, skip the smoke scan and document that validation was limited to static file checks.

- [ ] **Step 2: Run pip-audit against the fixture when available**

Run:

```powershell
D:\anaconda\python.exe -m pip_audit -r tests\sca_demo\requirements-vulnerable.txt -f json
```

Expected: command reports known dependency vulnerabilities. A non-zero exit code is acceptable when vulnerabilities are found.

### Task 4: Final Verification

**Files:**
- Read: `tests/sca_demo/requirements-vulnerable.txt`
- Read: `tests/sca_demo/README.md`
- Read: `主文档层/a26-SCA测试用例与演示说明.md`

- [ ] **Step 1: Confirm final files**

Run:

```powershell
Get-ChildItem tests\sca_demo
Test-Path 主文档层\a26-SCA测试用例与演示说明.md
```

Expected: the fixture directory contains the two demo files and the guide path exists.

- [ ] **Step 2: Report verification results**

Summarize which files were created and whether `pip-audit` verification was run successfully.
