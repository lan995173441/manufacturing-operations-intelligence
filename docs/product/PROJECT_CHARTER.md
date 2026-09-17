# Manufacturing Operations Intelligence — Project Charter

Status: Initial MVP scope, critically reviewed  
Date: 2026-09-15  
Project type: Portfolio demonstration of manufacturing analytics and Excel/Python automation

## 1. Problem statement

Manufacturing teams often record production quantities, targets, rejects, and downtime in spreadsheets. Preparing a management update requires repetitive consolidation, correction, calculation, and formatting. Inconsistent columns, duplicate records, missing values, and ambiguous KPI definitions can produce misleading results even when the finished dashboard looks credible.

This project will demonstrate a repeatable workflow that turns a defined manufacturing spreadsheet into validated operational KPIs, an interactive dashboard, an automatically generated report, and an AI-assisted management summary. It will make data limitations visible and allow reported figures to be traced to their source records.

The product is a small portfolio MVP, not a commercial production Manufacturing Execution System (MES). Its credibility depends on a complete, understandable workflow and evidence of correctness rather than feature breadth.

## 2. Target users

| User | Primary need |
| --- | --- |
| Production supervisor | Review output, rejects, and downtime by date, line, and shift. |
| Operations manager | Identify underperforming periods and lines and obtain a concise management report. |
| Operations or manufacturing analyst | Replace recurring spreadsheet consolidation and KPI preparation with a reproducible process. |
| Upwork client or prospective employer | Assess practical Excel/Python automation, data validation, analytics, and engineering skills through a working example. |

The demonstration assumes one analyst operating the application for one fictional manufacturing site. Multiple user accounts and simultaneous team workflows are unnecessary for this MVP.

## 3. Business value

- Reduce repeated manual preparation through a single import-to-report workflow.
- Expose data errors before they become management conclusions.
- Provide consistent KPI definitions across the dashboard, exports, and narrative.
- Help managers locate periods and lines that warrant investigation.
- Demonstrate a reusable approach that a client could adapt to a specific spreadsheet reporting process.

Time savings will be measured on a documented sample workflow. Factory productivity gains, financial returns, and real-client outcomes will not be claimed without evidence.

## 4. Project objectives

1. Deliver one complete path: import spreadsheet → validate → calculate → explore → export → summarize.
2. Establish a documented input contract and transparent rules for rejecting or accepting data.
3. Implement a small KPI set with independently checked calculations and clear aggregation rules.
4. Produce consistent dashboard and report outputs from the same validated dataset.
5. Demonstrate AI-assisted writing grounded in computed facts, with a usable offline fallback.
6. Package the project so a prospective client can understand the value within five minutes and reproduce the demonstration locally.

## 5. Measurable success criteria

These are acceptance targets, not achieved results. The final portfolio must record measured outcomes and any unmet targets.

| Area | Acceptance evidence |
| --- | --- |
| End-to-end completion | A supplied valid workbook produces a dashboard, Excel KPI export, HTML management report, and summary without manual edits to the source or intermediate results. |
| Validation | Seeded examples for every documented validation rule are detected. Blocking errors prevent KPI/report generation and identify the affected sheet, row, field, and reason where applicable. Valid fixtures are accepted. |
| Calculation correctness | All five KPIs match independently calculated fixtures, including aggregation, zero denominators, and empty filters. Counts match exactly; displayed percentages match within 0.01 percentage points. |
| Output consistency | Dashboard, Excel export, HTML report, and summary facts reconcile for the same dataset and filters. The outputs disclose source identity, reporting period, filters, and validation status. |
| Performance | On a documented reference laptop, process a synthetic workbook of 10,000 rows and generate non-AI outputs within 30 seconds, measured over three runs. External model latency is reported separately. |
| Repeatability | Reprocessing identical input with identical settings produces identical validation results and KPIs, allowing differences in run timestamps and AI wording. |
| Automation value | Record preparation time for one fixed manual spreadsheet reporting procedure and the automated equivalent on the same sample. Target at least 50% lower hands-on preparation time; report the actual comparison and its limitations. |
| AI grounding and resilience | Across at least five fixed scenarios, every numerical claim matches supplied KPI facts, unavailable values remain unavailable, and no unsupported causal explanation is presented as fact. Missing credentials, timeout, or API failure produces a labeled deterministic summary while preserving core outputs. |
| Reproducibility and presentation | A fresh local setup following the README completes the offline demonstration. A three-to-five-minute walkthrough shows both a successful run and an invalid-input case. |

## 6. In-scope functionality

### Defined spreadsheet input

- One documented `.xlsx` template with one production-data worksheet; one workbook per run.
- One row represents a date, production line, and shift, with a unique key across those fields.
- Required operational fields: planned output units, total produced units, rejected units, planned production minutes, and unplanned downtime minutes.
- One fictional site with comparable unit definitions across lines; synthetic data covering approximately 90 days, three lines, and two shifts.
- Clean and deliberately invalid example workbooks, plus a data dictionary explaining units and assumptions.

### Validation and normalization

- Check required columns, supported dates and identifiers, numeric types, missing values, duplicate keys, and nonnegative values.
- Require integer unit counts, rejected units no greater than produced units, and unplanned downtime no greater than planned production minutes.
- Normalize only documented harmless formatting differences, such as surrounding whitespace. Record normalization actions; never silently impute, delete, or repair operational values.
- Reject workbooks with blocking errors and provide an actionable validation result. Do not publish partial-data KPIs after dropping invalid rows.
- Treat zero denominators and empty selections explicitly as unavailable where appropriate, rather than producing a misleading zero percentage.

### Five operational KPIs

| KPI | Definition for the selected records |
| --- | --- |
| Total output | Sum of total produced units. |
| Good output | Sum of produced units minus sum of rejected units. |
| Production attainment | Total produced units ÷ planned output units × 100. |
| Reject rate | Rejected units ÷ total produced units × 100. |
| Unplanned downtime rate | Unplanned downtime minutes ÷ planned production minutes × 100. |

Ratios use summed numerators and denominators, never averages of row-level percentages. Production attainment may exceed 100%. A zero denominator yields unavailable. Planned production minutes exclude scheduled breaks; unplanned downtime is a subset of that time. These are demonstration definitions to document explicitly, not claims of universal plant practice.

### One dashboard

- A single local dashboard with date, line, and shift filters.
- KPI cards, daily trends, and line comparison views.
- Visible validation status, data coverage, metric definitions, and unavailable-data states.
- No configurable dashboard builder or separate screens for each user role.

### Automated reporting

- One user-triggered run generates an Excel workbook containing KPI tables and validation results, plus one self-contained HTML management report with fixed charts and a summary.
- Reports use the same selected records and calculation results as the dashboard.
- Include run metadata and source references sufficient to reproduce and investigate a result.
- Automation means repeatable execution without manual report assembly; scheduling and distribution are outside the MVP.

### AI-assisted management summary

- One optional model integration generates a short draft from a bounded set of calculated KPIs, comparisons, and data-quality notes.
- Include observed results, limitations, and suggested questions for investigation. Do not invent causes, missing values, or production instructions.
- Provide only aggregate facts to the model; credentials stay outside the repository.
- Label the narrative as AI-assisted and requiring human review. A deterministic template summary supports offline operation and model failures.
- The model does not calculate KPIs or control any application or factory action.

## 7. Out-of-scope functionality

- Production MES functions: work-order execution, scheduling, dispatching, inventory, maintenance workflows, and machine control.
- Live machine, PLC, SCADA, ERP, or external database integrations; streaming data and real-time alerts.
- Arbitrary spreadsheet interpretation, multiple client templates, scanned documents, and PDF ingestion.
- Multiple sites, mixed-unit product comparisons, multi-tenancy, authentication, role permissions, and approval workflows.
- OEE, predictive maintenance, forecasting, anomaly-detection models, causal analysis, optimization, and financial impact estimates.
- Conversational chat, retrieval systems, autonomous agents, model training, and multiple model providers.
- Scheduled jobs, email delivery, notifications, PDF/PowerPoint exports, mobile applications, and dashboard customization.
- Microservices, message queues, distributed processing, production high availability, enterprise audit systems, and compliance certification.
- Mandatory cloud deployment or a public service accepting client data.

## 8. Project constraints

- **Size:** One developer, one site, one input contract, five KPIs, one dashboard, and two export formats.
- **Planning budget:** Aim for 40–60 focused development hours, including tests, documentation, and demonstration assets. This is an initial estimate; reduce presentation extras before expanding the budget or weakening validation.
- **Architecture:** Prefer one Python application with a small number of clear modules and local files. A separate backend service, frontend framework, or persistent database requires a demonstrated MVP need.
- **Data:** Use clearly labeled synthetic data with disclosed assumptions. Do not imply it represents a real customer or measured factory performance.
- **Operation:** The core workflow must work locally without paid services. AI access is optional at runtime; cost and latency must be bounded and documented.
- **Engineering:** Include dependency setup, meaningful validation and KPI tests, clear error messages, and a short explanation of design tradeoffs. Avoid framework-building and abstractions for hypothetical future clients.
- **Change control:** An added feature must replace an existing feature of similar effort or be deferred. The complete demonstration takes priority over a broader backlog.

## 9. Major risks

| Risk | Impact | MVP mitigation |
| --- | --- | --- |
| Scope expands toward MES or a general analytics platform | Project becomes too large to finish and explain. | Enforce the explicit exclusions and fixed feature counts; defer additions. |
| Input assumptions do not resemble client spreadsheets | Portfolio appears polished but impractical. | Document the contract and illustrate realistic duplicates, missing values, and inconsistent formatting; explain that new templates require adaptation. |
| Incorrect ratios or incompatible units | Outputs mislead users. | Use explicit definitions, comparable sample units, ratio-of-sums aggregation, and independent calculation fixtures. |
| Silent cleaning hides operational data problems | Report appears more trustworthy than its source. | Record normalization and stop publication on blocking errors. |
| AI invents explanations or fails externally | Narrative undermines trust or blocks the demo. | Supply aggregate facts only, evaluate fixed scenarios, require human review, and provide the offline fallback. |
| Synthetic data overstates demonstrated business impact | Client expectations exceed available evidence. | Label all examples and distinguish measured workflow timing from hypothetical business benefits. |
| Setup friction or excessive dashboard polish consumes the budget | Core workflow or portfolio packaging remains unfinished. | Keep local setup simple, demonstrate the full path early, and limit chart and layout variations. |

## 10. Final portfolio deliverables

1. **Runnable repository:** A small Python application with reproducible setup and meaningful tests for validation, KPI correctness, and the end-to-end workflow.
2. **Sample data pack:** Input template, clean synthetic dataset, invalid examples, and a concise data dictionary.
3. **Working dashboard:** The single dashboard described above, with clear metrics and failure states.
4. **Example outputs:** Excel KPI/validation workbook and HTML management report, including labeled AI-assisted and fallback summary examples.
5. **Engineering documentation:** README, this charter, KPI definitions, input/validation rules, a compact architecture explanation, limitations, and acceptance results.
6. **Portfolio case study:** Explain the business problem, workflow, engineering decisions, measured preparation-time comparison, and realistic client adaptation opportunities.
7. **Demonstration assets:** A three-to-five-minute walkthrough and a small set of screenshots showing the successful workflow and an actionable data-quality failure.

Completion requires the integrated workflow and supporting evidence. A deployed service, extra analytics features, or additional export formats are not prerequisites.

## 11. Critical scope review and removals

The scope was reviewed against one question: does this feature materially demonstrate trustworthy spreadsheet automation within a short client walkthrough? The final scope above incorporates these cuts; the candidates below are not commitments.

| Candidate to remove or defer | Reason | Retained alternative |
| --- | --- | --- |
| OEE | Needs reliable ideal cycle times and additional production-time semantics; otherwise it risks a misleading headline metric. | Five transparent metrics supported directly by the input contract. |
| Universal Excel/CSV importer | Mapping arbitrary workbooks creates a second product and an open-ended support burden. | One explicit Excel template. |
| Downtime event and reason analysis | Adds another data grain, joins, and reconciliation work. | Shift-level downtime totals and rate. |
| Forecasting and predictive analytics | Requires credible historical data and evaluation beyond the portfolio objective. | Historical trends and comparisons. |
| PDF and presentation exports | Duplicate report content while adding rendering and layout maintenance. | Excel for analysis and HTML for presentation. |
| Scheduler, email, and notifications | Add operational configuration without improving the central demonstration. | User-triggered automated report generation. |
| Chatbot and autonomous AI actions | Add interaction and reliability complexity unrelated to validated reporting. | One bounded, reviewable management summary. |
| Authentication, cloud infrastructure, and database | Solve multi-user service concerns that the local demonstration does not have. | A reproducible local application using files. |

**Remaining scope pressure:** AI integration is the least predictable component, but a narrow demonstration remains justified by the project purpose. Cap it at one provider and one summary format. Build the deterministic summary first; if the live integration cannot be completed, disclose that gap instead of claiming the AI objective was met. Do not remove validation or calculation checks to make room for AI polish.

**Review conclusion:** No further core functionality needs removal at initiation. If the effort estimate rises, cut chart variations, visual customization, and optional hosting first. Preserve the complete input-to-report path, grounded summary behavior, and evidence of correctness.
