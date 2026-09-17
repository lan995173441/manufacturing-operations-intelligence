# Manufacturing Operations Intelligence

A local, portfolio-grade manufacturing analytics MVP. It validates four synthetic Excel/CSV datasets, persists one active normalized batch in SQLite, calculates documented KPIs and rule-based anomalies, shows five Streamlit areas, and exports Excel/PDF management reports. An optional AI draft consumes calculated facts only; the core works offline. This is not a production MES or a hosted multi-user service.

Chinese guide: [README.zh-CN.md](README.zh-CN.md).

**Release status:** RC1 verification is recorded in the [release checklist](docs/release/RELEASE_CHECKLIST.md) and [changelog](CHANGELOG.md). RC1 is **not approved for handover**: the PRD's detailed page/upload clauses have open gaps, and product-owner business decisions BA-01–BA-08 remain unresolved. Passing engineering tests validates the synthetic demonstration only.

## Run locally

Requires Python 3.12. From the repository root:

### One-click launch on macOS

Double-click [start.command](start.command) in Finder. On the first run, it creates
`.venv` and installs missing dependencies; it then opens `http://127.0.0.1:8501` and
starts the local app. Keep its Terminal window open while using the app; press
Control-C there to stop it. If macOS prevents the first launch, right-click the file,
choose **Open**, then confirm.

Set `MOI_PORT` before launching if port 8501 is unavailable. Set
`MOI_OPEN_BROWSER=false` to start without opening a browser.

### Manual launch

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/streamlit run streamlit_app.py --server.address=127.0.0.1
```

The default database path is `var/manufacturing_operations_intelligence.db`. Set `MOI_DATABASE_PATH` to another local path if needed. The app reads process environment variables; it does **not** load `.env` automatically. `.env.example` lists supported settings and contains no credential. Keep any real key out of the repository.

The repository also pins Streamlit to `127.0.0.1` in `.streamlit/config.toml`; keep the explicit launch flag. Uploads are limited to 10,000,000 bytes per workbook or total CSV batch. The Streamlit server caps each uploaded file at 10 MiB, disables usage telemetry, and hides full tracebacks from the browser. This local demo has no user authentication; keep it on loopback.

## Three-to-five-minute walkthrough

1. Open the local Streamlit URL and select **Load synthetic demo data**. This activates a deliberately synthetic 90-day batch; replacing an active batch requires acknowledgement.
2. Inspect Overview, Production, Quality and Inventory. Change dates, lines or products; inventory remains site-wide as of the selected end date. Configure a downtime threshold to evaluate anomalies.
3. In Reports & Insights, review anomalies and click **Generate management reports** for Excel/PDF downloads. Reports use existing calculated results.
4. Click **Generate management summary**. With AI disabled or no key, it shows a deterministic offline summary. The optional AI draft requires explicit request and human review.
5. To see a validation failure, upload a synthetic four-file CSV batch or four-sheet workbook with a deliberately missing required value. The error lists dataset, row and field; the prior active batch remains unchanged.

CSV intake requires one file for each `production_plan`, `production_actual`, `quality`, and `inventory`. Excel intake requires one `.xlsx` workbook with exactly those four worksheet names. The precise schemas and accepted normalizations are in [Data Contract](docs/data/DATA_CONTRACT.md). [KPI Definitions](docs/data/KPI_DEFINITIONS.md) and [Anomaly Rules](docs/data/ANOMALY_RULES.md) describe current demo assumptions. Completed Orders and Schedule Adherence remain unavailable because their required lifecycle evidence is absent; AI does not fill that gap.

Optional AI uses the OpenAI Responses adapter. To enable it, set `MOI_AI_ENABLED=true`, `MOI_AI_API_KEY` in the process environment, and optionally `MOI_AI_MODEL` (default `gpt-4.1-mini`). Do not paste a key into files or uploads. API failures return the offline summary. Unit tests make no external API calls.

## Validate and review

```sh
.venv/bin/ruff check .
.venv/bin/pytest -v
```

The [architecture](ARCHITECTURE.md), [PRD](docs/product/PRD.md), [draft acceptance criteria](docs/quality/ACCEPTANCE_CRITERIA.md), [RC1 requirement-by-requirement evidence](docs/release/RELEASE_CHECKLIST.md), [security review](docs/quality/SECURITY_REVIEW.md), and [QA record](docs/exec-plans/active/qa-review-remediation.md) distinguish implemented behavior from open product-owner decisions. Engineering tests do not constitute business acceptance. Use synthetic/demo manufacturing data only. Do not use this MVP for production control, compliance determinations or confidential customer data.
