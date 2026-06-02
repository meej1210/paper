# Thesis Test Summary

## 6.2 Functional Test Results

| Module | Cases | Passed | Failed | Failure summary |
|---|---:|---:|---:|---|
| Auth | 3 | 3 | 0 | - |
| Task Management | 6 | 6 | 0 | - |
| SAST | 6 | 6 | 0 | - |
| DAST | 6 | 6 | 0 | - |
| SCA | 13 | 13 | 0 | - |
| Report Export | 3 | 3 | 0 | - |
| Audit Logs | 2 | 2 | 0 | - |
| Admin Dashboard | 13 | 13 | 0 | - |
| AI Analysis | 5 | 5 | 0 | - |

Functional verification covered 57 module-level cases; 57 passed and 0 failed in the final run.
Figure: `fig_6_2_functional.png`.

## 6.3 Security Test Results

| Category | Case | Payload | HTTP status | Expected | Actual | Passed |
|---|---|---|---:|---|---|---|
| Access Control | User A reads User B task | `task_id=232` | 404 | [403, 404] blocked | task not found | yes |
| Access Control | User A downloads User B report | `task_id=232` | 404 | [403, 404] blocked | task not found | yes |
| Access Control | Normal user opens admin dashboard | `/api/admin/dashboard` | 403 | [403] forbidden | permission denied | yes |
| Injection | Login SQL payload | `' OR '1'='1` | 401 | [400, 401, 429] not authenticated | unauthorized | yes |
| Injection | Task type SQL payload | `task_type=' OR '1'='1` | 400 | [400] invalid value | invalid parameters | yes |
| Injection | Audit keyword XSS payload | `<script>alert(1)</script>` | 200 | [200] handled as data | ok | yes |
| File Upload | Oversized file | `21MB .py` | 400 | [400, 413] rejected | file size exceeds limit | yes |
| File Upload | Executable extension | `.exe` | 400 | [400] unsupported type | unsupported file type | yes |
| File Upload | Path traversal filename | `../../etc/passwd` | 400 | [400] rejected or neutralized | unsupported file type | yes |
| File Upload | Empty file | `0 byte .py` | 400 | [400, 422] rejected | empty file | yes |
| Token Invalid | Expired token | `expires_delta=-1s` | 401 | [401] token expired | {'msg': 'Token has expired'} | yes |
| Token Invalid | Forged signature token | `modified signature` | 422 | [401, 422] token rejected | {'msg': 'Signature verification failed'} | yes |
| Token Invalid | Missing Authorization | `no header` | 401 | [401] missing token | {'msg': 'Missing Authorization Header'} | yes |
| Token Invalid | Wrong auth scheme | `Token abc` | 401 | [401, 422] malformed header | {'msg': "Missing 'Bearer' type in 'Authorization' header. Expected 'Authorization: Bearer <JWT>'"} | yes |

Security checks blocked or safely handled 14 of 14 cases.
Figure: `fig_6_3_security.png`.

## 6.4 Performance Test Results

### API Latency

| Endpoint | N | Min ms | P50 ms | P95 ms | Max ms | Mean ms |
|---|---:|---:|---:|---:|---:|---:|
| POST /api/auth/login | 50 | 38.37 | 164.03 | 433.38 | 1677.16 | 214.81 |
| GET /api/tasks?page=1&page_size=20 | 50 | 9.43 | 30.36 | 34.08 | 42.25 | 26.89 |
| GET /api/sast/tasks/{id} | 50 | 15.8 | 29.99 | 35.84 | 42.92 | 27.43 |
| GET /api/admin/dashboard | 50 | 27.52 | 45.71 | 50.16 | 60.31 | 42.34 |
| GET /api/audit-logs?page=1 | 50 | 26.18 | 45.1 | 53.85 | 108.83 | 42.56 |
| GET /api/sast/tasks/{id}/export?format=pdf | 50 | 1010.18 | 1163.42 | 1350.63 | 3175.04 | 1205.24 |

The highest measured API P95 latency was 1350.63 ms.
Figure: `fig_6_4a_api_latency.png`.

### Scan Duration

| Type | Runs | Mean duration ms | Median duration ms | Results |
|---|---:|---:|---:|---|
| SAST | 5 | 334.64 | 336.26 | `{"SUCCESS": 5}` |
| SCA | 3 | 20966.89 | 20247.84 | `{"SUCCESS": 3}` |
| DAST | 3 | 5968.52 | 5932.59 | `{"SUCCESS": 3}` |

Scan durations were refreshed by invoking the real scanner services after the fixes.
Figure: `fig_6_4b_scan_duration.png`.

### Concurrency

| Parallel | Submitted | Created | Success rate % | Avg response ms | Status counts |
|---:|---:|---:|---:|---:|---|
| 1 | 1 | 1 | 100.0 | 107.08 | `{"201": 1}` |
| 5 | 5 | 5 | 100.0 | 472.51 | `{"201": 5}` |
| 10 | 10 | 10 | 100.0 | 935.99 | `{"201": 10}` |
| 20 | 20 | 20 | 100.0 | 1482.3 | `{"201": 20}` |

At 20 concurrent submissions, task creation success rate was 100.0% and average response time was 1482.3 ms; all 20 created responses returned HTTP 201 in this run.
Figure: `fig_6_4c_concurrency.png`.

## Compatibility Asset Loading

| Asset | Bytes | Read/download ms | Measured | Note |
|---|---:|---:|---|---|
| index.html | 412 | 0.19 | filesystem |  |
| index-CiBccP6L.js | 808941 | 1.46 | filesystem |  |
| index-Cqs8A24M.css | 88574 | 0.68 | filesystem |  |

| Browser | Version | DOMContentLoaded ms | Evidence |
|---|---|---:|---|
| Chrome | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |
| Edge | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |
| Firefox | To be measured on user's local browser |  | Lighthouse or F12 Performance screenshot |

Browser versions and GUI DOMContentLoaded values were not fabricated; they require manual measurement in local browsers.
Figure: `fig_6_4d_compat_assets.png`.

## Test Environment

| Item | Value |
|---|---|
| OS | Windows-11-10.0.22631-SP0 |
| Python | 3.12.7 |
| CPU | Intel64 Family 6 Model 154 Stepping 3, GenuineIntel |
| Docker | Docker version 28.5.1, build e180ab8 |
| Backend URL | http://127.0.0.1:5000/api |
| DAST target | http://127.0.0.1:3000 |

## Issues Found During Testing

- Initial failures were traced to stale smoke scripts, HTTP 429 being wrapped as 500, empty-file upload validation, and concurrent `user_task_no` allocation. These were fixed before the final data refresh.
- Requested routes `/api/metrics/dashboard` and `/api/tasks/{id}/report?format=pdf` were not present; measured equivalents were `/api/admin/dashboard` and `/api/sast/tasks/{id}/export?format=pdf`.
- Browser GUI timing values are intentionally left for local browser measurement instead of being fabricated from command-line asset reads.