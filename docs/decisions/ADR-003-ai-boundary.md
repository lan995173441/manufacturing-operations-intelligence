# ADR-003 — Optional AI consumes calculated results only

Implementation update (2026-09-17): A later explicit user task authorized optional summarization. One OpenAI Responses adapter and deterministic fallback now implement this boundary, with no new dependency. The original decision below records the architecture-design task at its date; it is not the current implementation status. See [phase 13](../exec-plans/completed/phase-13-optional-ai-summary.md).

QA hardening (2026-09-17): The model now returns only IDs of allowlisted KPI, anomaly or daily-trend facts. Application code renders values and labels deterministically and always adds fixed limitations. Free-form model prose and unsupported IDs fall back; numerical token matching is no longer treated as grounding evidence. This narrows AI assistance to fact selection and prioritization.

Date: 2026-09-15  
Status: Optionality and structured-result boundary required by the user; adapter design proposed. Provider and release commitment remain open.  
Chinese counterpart: [ADR-003-ai-boundary.zh-CN.md](ADR-003-ai-boundary.zh-CN.md)

## Context

The project should demonstrate an optional management summary while keeping deterministic analytics and Excel/PDF reporting functional offline. AGENTS V0 prohibits AI from defining manufacturing rules, calculating authoritative KPIs, altering raw data, or determining compliance. PRD D07 leaves the optional feature's release priority open; architecture must not turn it into a core dependency.

## Decision

Implement no AI integration in this task. Reserve a small, optional summary adapter invoked by the application service only on explicit user request. It receives an allowlisted structured projection of an existing validated Analytics result, never raw spreadsheets, full record tables, SQL access, or a repository handle.

Include relevant calculated facts, units, result/fact identifiers, scope, approved comparisons, anomaly evidence summaries and limitations. The domain remains the sole calculation owner. UI and report rendering never call the provider directly. Neither import nor analysis invokes the summary adapter automatically.

One provider callable is sufficient if AI is later delivered. No provider/model/SDK is selected now. Configure secrets through environment variables and a placeholder-only `.env.example`; optional provider initialization must not be necessary to start the core application. Any new major dependency still needs approval. Use finite request/output limits and return a labeled outcome, not an uncaught provider exception.

The deterministic summary path uses supplied result fields and prewritten management language; it does not calculate new metrics. Disabled AI, absent credentials, timeout, network error or unusable response produces that fallback or explicit narrative-unavailable status. Core metrics and report downloads remain usable in all cases.

Each draft carries the originating dataset, effective scope and definition identity. Invalidate it when any changes. Export may attach a matching summary after explicit generation; the export operation itself never triggers AI. Reuse of an older narrative must not silently attach it to new figures.

Check response structure and supported numerical claims against the structured facts; reject unsupported claims. Do not claim that string/number checks prove causal or narrative truth. Human review remains required, and AI text must be labeled. AI may suggest investigation priorities or questions, but has no tool permissions to act, change data, or decide engineering/regulatory compliance.

## Alternatives considered

| Alternative | Disposition |
| --- | --- |
| LLM calculates KPIs from uploaded rows | Rejected: nondeterministic authority and unnecessary raw-data exposure. |
| AI mandatory during report generation | Rejected: makes connectivity, cost and credentials part of the core path. |
| Autonomous agent / database tools | Rejected: no authorized need for actions, and explicitly outside scope. |
| Multi-provider strategy framework | Not selected: one small optional adapter is sufficient. |
| Deterministic text only | Valid core/offline mode; does not falsely claim the optional AI feature is delivered. |

## Consequences and limits

Core tests and demos run without API credentials or installed provider-specific packages. The narrow boundary isolates network failures and allows a fake provider in tests. It cannot guarantee an LLM's narrative correctness; reviewing factual support and clear labeling remain necessary.

No prompts, complete model payloads or secrets belong in routine logs. Use synthetic data as required by AGENTS. Provider cost/timeout/output limits and supported response format must be documented when integration is explicitly scoped. This ADR is not approval to add chat, retrieval, agents, or model training.

## Verification and review triggers

Verify core F01–F12 with provider unavailable; test disabled/key-missing/failure/malformed/unsupported-claim cases through a fake callable, and check stale-identity invalidation. Later live-model evaluation must use approved facts and documented scenarios, not establish business rules from the model's output.

Revisit only after explicit approval for a materially different AI capability or data exposure. The core deterministic boundary must remain intact. See [Architecture section 10](../../ARCHITECTURE.md#10-optional-ai-boundary) and [AGENTS V0](../../AGENTS.md).
