# Public portfolio deployment — Streamlit Community Cloud

Status: deployment-ready repository configuration; no public URL has been created yet. Chinese companion: [STREAMLIT_COMMUNITY_CLOUD.zh-CN.md](STREAMLIT_COMMUNITY_CLOUD.zh-CN.md).

## Platform

Use Streamlit Community Cloud for the portfolio demo. It matches the existing Streamlit entry point, needs no paid AI service, and can install the runtime from `requirements.txt` with Python 3.12 from `runtime.txt`.

The public demo must run in read-only presentation mode. It automatically activates only the version-controlled synthetic dataset and does not render file-upload controls. This prevents visitors from storing their own operational files in the shared demo process.

## Deployment steps

1. Create a public GitHub repository after reviewing the branch and its synthetic-data-only contents. Push the selected release branch and the `v1.0.0` tag. Do not push `.env`, local SQLite files, generated reports, or private data.
2. In Streamlit Community Cloud, create a new app from that repository and selected branch.
3. Set the entry point to `streamlit_app.py`. Community Cloud installs `requirements.txt`; `runtime.txt` requests Python 3.12.
4. In the app's advanced settings, add these root-level environment values. They are configuration values, not secrets; do not add an AI key.

   ```toml
   MOI_ENVIRONMENT = "public-demo"
   MOI_DATABASE_PATH = "/tmp/manufacturing-operations-intelligence-demo.sqlite3"
   MOI_AI_ENABLED = "false"
   MOI_PUBLIC_DEMO = "true"
   ```

5. Deploy, wait for the app to become healthy, and record the public URL in the README only after the smoke tests below pass.

## Required environment variables

| Variable | Public-demo value | Purpose |
| --- | --- | --- |
| `MOI_ENVIRONMENT` | `public-demo` | Identifies the deployment context. |
| `MOI_DATABASE_PATH` | `/tmp/manufacturing-operations-intelligence-demo.sqlite3` | Uses ephemeral writable storage for synthetic records only. |
| `MOI_AI_ENABLED` | `false` | Keeps all AI providers disabled; no API key is required. |
| `MOI_PUBLIC_DEMO` | `true` | Seeds the bundled synthetic batch when empty and disables uploads. |

Do not set `MOI_AI_API_KEY`. If an API key is accidentally configured, `MOI_AI_ENABLED=false` prevents AI use, but the key must still be removed from the hosting settings.

## Smoke-test checklist

Run these checks after publishing, in a clean browser session:

| Check | Expected public-demo result | Status before URL exists |
| --- | --- | --- |
| Public URL | The app loads without a traceback. | Not testable externally |
| Overview | Six KPI cards, production trend, and synthetic-data alerts render. | Locally validated |
| Production | Plan-versus-actual trend, line charts, and filters render. | Locally validated |
| Quality | Yield, scrap, trend, and alerts render. | Locally validated |
| Inventory | As-of inventory risk view and material selector render. | Locally validated |
| Filters | Date, line, shift, product, and applicable material filters update the visible analysis. | Locally validated |
| Sample data | Dashboard is populated automatically; no upload is required. | Locally validated |
| Excel export | The Reports & Insights download produces a non-empty `.xlsx` file. | Locally validated |
| PDF export | The Reports & Insights download produces a non-empty `.pdf` file. | Locally validated |
| No AI key | Management summary is an explicitly labeled deterministic offline fallback. | Locally validated |
| Upload isolation | No file-upload control is available in public-demo mode. | Locally validated |

Record browser, deployment commit, URL, date, and any unsupported download behavior when the external smoke test is executed.

## Hosting limitations

- `/tmp` storage is ephemeral. A platform restart removes the SQLite file; the application reseeds the same deterministic synthetic data at next startup.
- The public demo is unauthenticated by design. Public-demo mode removes uploads, but it is still unsuitable for real, confidential, or regulated data.
- Excel and PDF artifacts are built in memory. They are expected to download through supported browsers, but the deployed platform/browser combination must be checked after publication.
- Streamlit Community Cloud cold-start time and resource limits are platform-managed. The bundled sample data is approximately 232 KB; no production performance guarantee is made.
- AI is intentionally disabled in the public demo. The offline management summary remains available and authoritative calculations remain deterministic.
- This configuration does not create a custom domain, uptime monitoring, backups, user accounts, or production service guarantees.

## Repository safeguards

`.gitignore` excludes `.env`, Streamlit secrets, key files, local databases, logs, reports, upload directories, and private/client/raw data. The checked-in sample CSVs are deterministic synthetic records. The deployment package does not include an `.env`, a database, or any API credential.
