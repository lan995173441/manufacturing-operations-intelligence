# AGENTS.md — Manufacturing Operations Intelligence

Version: V0 · Phase: project definition / requirements design · Status: awaiting review.
Chinese companion: [AGENTS.zh-CN.md](AGENTS.zh-CN.md). Keep both versions equivalent; report translation conflicts.

QA status (2026-09-17): Later explicit feature tasks produced an MVP implementation. The V0 phase and file-status inventory below are historical, not a current absence claim. Feature development is now frozen for QA. [Acceptance criteria](docs/quality/ACCEPTANCE_CRITERIA.md) now exist as a draft; V1 remains pending because those criteria and product-owner business decisions are not approved. Do not treat implementation as their approval.

## Mission and phase

- Build a portfolio-grade MVP demonstrating Python automation, manufacturing data processing, Excel/CSV workflows, KPI analytics, deterministic rule-based anomalies, dashboards, Excel/PDF reports, and optional AI summaries.
- Serve Upwork clients, manufacturing companies, operations teams, and buyers of Python/Excel, business-process, analytics, and reporting automation.
- This is not a production MES, ERP, enterprise manufacturing platform, or commercial multi-tenant SaaS.
- Work currently concerns definition and design. Do not implement features without an explicit implementation task.
- Do not treat draft requirements, provisional business rules, or missing design documents as finalized architecture or implementation approval.

## Repository navigation and authority

Read relevant sources before changing files. Dedicated documents own their concerns; AGENTS governs agent behavior, not product details.
The following existence/status inventory is verified for V0; check again when starting a later task.

| Source | Concern | V0 status |
| --- | --- | --- |
| [PROJECT_CHARTER](docs/product/PROJECT_CHARTER.md) | Purpose and boundaries | Exists; conflicts with later requirements remain open |
| [PRD](docs/product/PRD.md) | Required product behavior | Exists as a draft; decisions remain provisional |
| [USER_STORIES](docs/product/USER_STORIES.md) | User-oriented requirements | Exists as a draft |
| `ARCHITECTURE.md` | Major components and their organization | Missing; future source of truth |
| `docs/data/DATA_CONTRACT.md` | Data structures and validation contract | Missing; future source of truth |
| `docs/data/KPI_DEFINITIONS.md` | Metric formulas and business semantics | Missing; future source of truth |
| `docs/design/UI_SPEC.md` | Interface behavior | Missing; future source of truth |
| `docs/quality/TEST_PLAN.md` | Validation approach | Missing; future source of truth |
| `docs/quality/ACCEPTANCE_CRITERIA.md` | Release conditions | Missing; future source of truth |
| `docs/exec-plans/active/`, `docs/exec-plans/completed/` | Phase-specific execution plans | Missing; future planning locations |

- Respect explicit user decisions; a draft or a priority label does not establish approval of its proposed details.
- Report documentation conflicts with the affected sources and decision needed; never silently select the convenient version.
- Known charter/PRD differences include input breadth, inventory, persistence, dashboard areas, and report formats; consult the PRD conflict register before dependent work.
- Keep detailed requirements in their owning document and link to them; do not duplicate authoritative formulas across documents.
- Maintain English and Simplified Chinese document counterparts with aligned IDs and decision status. This does not require bilingual application UI.

## Scope and change discipline

- Prefer simple, understandable solutions. Do not add architecture to make the portfolio look sophisticated.
- Identify the task boundary; do not add unrequested or unapproved features or silently expand scope.
- Avoid unrelated edits, broad refactors, and unjustified module renames/reorganization; record unrelated technical debt instead.
- Do not introduce major dependencies without approval or casually change technology choices.
- Surface ambiguity. Record material assumptions explicitly; unresolved assumptions are not permission to implement business behavior.
- If a major product or architectural decision lacks approval, stop the dependent work, explain the decision, and request resolution.
- Approval already explicit in the task need not be requested again; complete authorized, independent work while dependent decisions remain open.

## Explicitly excluded unless approved later

- User authentication, RBAC, multi-tenancy, and payment systems.
- Microservices, Kafka, Kubernetes, complex cloud infrastructure, and unnecessary distributed systems.
- Real-time MES, ERP, OPC-UA, or IoT device integration; production-machine control.
- Predictive maintenance, complex machine-learning models, autonomous AI agents, and enterprise workflow orchestration.
- Before implementing an exception, explain why it is required, what problem it solves, and why a simpler approach is insufficient; wait for explicit approval.

## Business rules

- Manufacturing logic must come from explicit project documentation, not plausible AI output or invented manufacturing/compliance standards.
- Future schemas belong in DATA_CONTRACT; future KPI formulas belong in KPI_DEFINITIONS at the paths above.
- Those documents are absent in V0. Existing charter examples and PRD proposals remain provisional for implementation until formally documented and their status resolved.
- Do not invent formulas, silently change definitions, or copy authoritative formulas into additional documents.
- If implementation conflicts with business documentation, stop affected work, report the conflict, identify the authoritative source (or unresolved authority), and request resolution before changing behavior.
- Never change authoritative business definitions merely to make tests pass.

## AI boundaries

- AI/LLM functionality is optional; the core application must work without an AI API key.
- Authoritative numerical KPIs and rule-based anomalies must use deterministic program logic when implemented, never an LLM as their source of truth.
- AI may assist summarization, explanation, prioritization, and management-language drafting, grounded in validated facts and subject to human review.
- AI must not independently invent manufacturing rules, calculate authoritative KPIs, alter raw source data, or determine engineering/regulatory compliance.

## Security and data

- Use clearly labeled synthetic/demo manufacturing data only unless other data use is explicitly approved.
- Do not include real company confidential data, customer personal information, credentials, API keys, private database connection strings, or production secrets in repository artifacts, logs, or reports.
- If external services are later added, use environment variables for secrets and a placeholder-only `.env.example`; never commit `.env` or expose credentials.

## Engineering expectations and V0 done

- Future code should be readable and maintainable, favor clarity over cleverness, and avoid unnecessary abstraction.
- Keep business logic independently testable from presentation; critical calculations will need deterministic automated tests.
- Make errors explicit; never silently ignore failures or discard invalid data.
- Do not invent directory-level code rules, stack choices, or test commands before the architecture establishes them.
- A definition/design task is done when the artifact exists, covers the requested scope, records unresolved assumptions and conflicts, and has been checked for consistency.
- Verify that unrelated files were not unnecessarily changed and no application features were implemented without request; report created/modified files and remaining decisions.

## Transition to V1

- Review and upgrade this file before implementation begins, after PRD, Architecture, Data Contract, KPI Definitions, and Acceptance Criteria are sufficiently stable and reviewed.
- V1 may define approved technologies, module boundaries, repository/coding conventions, test/lint commands, dependency and architecture rules, and implementation-specific definition of done.
- V0 does not freeze those decisions. Finish the authorized documentation task, then await review and approval; do not start the next phase automatically.
