# ADR-001 — Local Python application and constrained technology stack

Date: 2026-09-15  
Status: Stack mandated by the user; application organization proposed for review. No implementation approval.  
Chinese counterpart: [ADR-001-tech-stack.zh-CN.md](ADR-001-tech-stack.zh-CN.md)

## Context

The portfolio MVP must support spreadsheet intake, deterministic analytics, five application areas, and Excel/PDF reporting with minimal setup. The latest architecture task explicitly specifies the technology stack. The PRD's earlier “technology undecided” wording is historical; its open business decisions remain open.

## Decision

Use one local Python application with synchronous service functions, organized by the boundaries in [ARCHITECTURE](../../ARCHITECTURE.md). Use only the specified tools for these responsibilities:

| Technology | Assigned responsibility |
| --- | --- |
| Python | Application services, deterministic rules, standard records, configuration, logging, and standard test facilities |
| Streamlit | Local UI, navigation, input controls, state for current interaction, and downloads |
| Pandas | Tabular parsing/transformation and domain analytics using approved definitions |
| Plotly | Interactive display of already computed analytics series |
| SQLite | Local durable normalized data and provenance; see ADR-002 |
| OpenPyXL | Excel decoding support and value-based Excel report rendering |
| ReportLab | PDF document layout, tables, and simple static charts from calculated series |

Streamlit pages call services and never implement KPIs. Pure domain functions do not import UI or I/O adapters. Renderers consume results, not raw data or repositories. Define compatible package/runtime versions during implementation preparation; this decision does not guess version pins or create dependency files.

For PDF charts, draw from prepared series using ReportLab rather than converting Plotly output. The document layout and graphics capabilities are described in the [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf). No Kaleido/browser-image export dependency is introduced. Streamlit holds transient interaction state; durable records belong in SQLite, consistent with its [session-state model](https://docs.streamlit.io/develop/concepts/architecture/session-state).

## Alternatives considered

| Alternative | Disposition |
| --- | --- |
| Separate API plus JavaScript frontend | Rejected: adds deployment and contracts without a required independent client. |
| All logic inside Streamlit pages | Rejected: duplicates rules and prevents isolated analytics/report tests. |
| Notebook-only demonstration | Rejected: does not provide the required application workflow and areas. |
| Plotly image-export pipeline for PDFs | Not selected: additional rendering dependency; simple ReportLab charts suffice for the proposed layout. |
| Generic plugin system or dependency-injection container | Rejected: ordinary functions and a concrete repository suffice. |

## Consequences and limits

One process and one language reduce operational setup. Simple service boundaries preserve testability without enterprise patterns. Separate interactive/static renderers require visual tests against the same data but do not duplicate metric calculations.

Long-running work occupies the local workflow; no asynchronous service or unmeasured performance promise is implied. If approved workload measurements later show a problem, optimize the relevant function before proposing new infrastructure. A richer report visual requirement must be reviewed rather than silently adding a rendering stack.

This ADR does not freeze schemas, formulas, anomaly thresholds, page layouts, report language, or release scope for optional AI. Those remain in their dedicated documents and PRD decision register.

## Verification and review triggers

Before implementation acceptance, demonstrate the offline F01–F12 flow, verify import dependencies, ensure pages/renderers contain no business calculations, and visually inspect PDF fixtures. No package installation, benchmark, or application execution occurred in this documentation task.

Revisit only when an approved requirement cannot reasonably be satisfied by this stack. Explain the need, simpler alternatives and cost before adding a major dependency. See [ADR-002](ADR-002-database.md) and [ADR-003](ADR-003-ai-boundary.md).
