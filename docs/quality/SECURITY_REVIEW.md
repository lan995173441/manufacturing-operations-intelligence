# Security and reliability review — portfolio MVP

Date: 2026-09-17. Chinese counterpart: [SECURITY_REVIEW.zh-CN.md](SECURITY_REVIEW.zh-CN.md). Scope: this local, single-user synthetic-data demonstration. This review does not certify a public service or production MES.

## Findings and changes

| Area | Result |
| --- | --- |
| Upload validation and paths | Excel and CSV filenames must be safe basenames with the expected extension; uploaded names are metadata, never filesystem destinations. Existing path-traversal regression rejects `../private.csv`. Four canonical domains and normalized relationships are validated before activation. |
| Size and malformed files | The contract's 10,000,000-byte workbook/total-CSV limit is enforced before CSV parsing. The UI checks uploaded sizes before calling `getvalue()`. Streamlit also caps each file at 10 MiB. XLSX preflight bounds archive expansion, members and cells before read-only parsing; a valid ZIP with an invalid shared-string reference now returns a visible `E-PARSE` result instead of an uncaught exception. Rejected input preserves the active batch. |
| Temporary files | Uploads and report artifacts stay in memory; application code does not create upload/report temporary files. Test databases and fixtures use temporary directories. |
| SQLite failures | Atomic batch replacement and fingerprint/key verification remain in place. Corrupt/incompatible database errors are presented clearly. Persistence-failure results now contain a fixed user-safe message rather than an underlying exception that could include local paths. |
| Environment and API key | `.env.example` has an empty key placeholder; no `.env` exists. AI is off by default, runs only when requested, reads a process environment key, and falls back without exposing provider exception text. Invalid `MOI_AI_ENABLED` now produces a clear configuration error in the UI. |
| Browser exposure | Streamlit remains bound to `127.0.0.1`. Usage telemetry is disabled; full uncaught tracebacks are hidden from the browser. The app has no authentication and must remain a local demo. |
| Credentials and sample data | A pattern scan of 160 project artifacts found no API-key, cloud-key or private-key blocks; it did not print file contents. `.gitignore` excludes `.env`, Streamlit secrets, key files and SQLite files. All four checked-in sample CSVs matched the fixed-seed synthetic generator byte for byte; the ignored local active database fingerprint also matches that sample. The parent Git checkout currently tracks no files from this project, so there is no project commit containing a secret to inspect; future commits still require review. |
| Dependencies | The installed environment passed `pip check`. An isolated [PyPA pip-audit](https://github.com/pypa/pip-audit) scan initially flagged old `pip` and `pytest`; the local environment was updated to pip 26.2.1 and pytest 9.1.1, and a repeat scan reported **no known vulnerabilities**. The project dev requirement now starts at pytest 9.0.3, the patched version in the [pytest advisory](https://github.com/advisories/GHSA-6w46-j5rx-g56g). The Streamlit minimum was raised to 1.54, which also excludes the [patched Windows advisory](https://github.com/streamlit/streamlit/security/advisories/GHSA-7p48-42j8-8846). No new application dependency was added. |

## Failure behavior and limits

- Invalid uploads return source-positioned issues; malformed or oversized files do not activate a partial batch. Database errors leave the previous accepted data intact or stop dependent analysis with a visible error.
- A model timeout, failure or unsupported response yields the deterministic offline summary. API credentials are never included in that summary or reports.
- The 10 MiB server cap is per file; four selected CSVs can occupy memory before the total-batch check. This is acceptable for a loopback portfolio demo, not a public upload service.
- Advisory scans cover the installed Python environment and publicly known issues at review time. Flexible version ranges are intentional for the MVP; a deployment would need a fresh resolution and review. Do not upload confidential client data or expose the unauthenticated app on a network.

## Verification

Regression tests cover over-limit CSV preflight, malformed XLSX cell decoding, persistence-message sanitization and invalid environment settings. Streamlit configuration options resolved to loopback, 10 MiB uploads, telemetry off and error-detail level `type`. `ruff check .` and `pip check` passed; `pytest -q` passed **138 tests in 49.33s** on Python 3.12.2 with pytest 9.1.1.
