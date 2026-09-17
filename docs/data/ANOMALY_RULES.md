# Anomaly Rules — Initial Portfolio Profile

Version: `0.1-draft`. Chinese counterpart: [ANOMALY_RULES.zh-CN.md](ANOMALY_RULES.zh-CN.md).

## Authority and scope

The latest user task authorizes five initial deterministic rules and explicitly selects **absolute production variance per production slot**. This supersedes PRD D06's earlier statement that no numeric anomaly thresholds had been approved for implementation. It does not make these values a universal manufacturing standard or settle all product-owner decisions in [KPI Definitions](KPI_DEFINITIONS.md). In particular, final **Scrap Rate** is not silently equated with the PRD's broader candidate “Reject rate,” and **Total Downtime** is line-minutes, not a downtime rate.

A production entity is one validated `(production_date, line_id, shift_id)` slot. Use the same accepted batch, joins, date range and line/shift filters as KPI Definitions. Inventory is one known material's latest eligible snapshot at/before the selected end date and ignores production line/shift filters. Validate the entire batch before selection; no rule runs on rejected or unexpectedly invalid records. Dates are local business dates because this contract has no event timestamps.

| Rule type | Exact trigger, strict boundary | Initial threshold source |
| --- | --- | --- |
| `LOW_ATTAINMENT` | Slot KPI-PA < threshold | 90%, configurable |
| `HIGH_SCRAP_RATE` | Slot KPI-SR > threshold | 5%, configurable |
| `HIGH_DOWNTIME` | Slot KPI-TD > threshold | Explicitly configured line-minutes; no invented default |
| `LOW_INVENTORY` | Latest eligible `inventory_qty < safety_stock` | Source-supplied safety stock for that material/snapshot |
| `HIGH_PRODUCTION_VARIANCE` | `100 × abs(actual_qty − planned_qty) / planned_qty > threshold` for a slot with positive planned quantity | 10%, configurable |

Comparisons use unrounded values. Equality never triggers. Variance catches both under- and over-production; it is distinct from the one-sided low-attainment rule. Do not convert planned quantity zero into a percentage: skip attainment and variance for that slot. Zero actual output skips the scrap-rate rule. A missing eligible material snapshot skips that material's low-inventory check and yields partial coverage; other observed materials remain evaluable. Empty selections yield no fabricated zero-performance anomalies.

Each triggered rule/entity pair creates one anomaly, even when several rules trigger on the same slot. Each anomaly carries type, configured severity, entity, exact observed value and threshold, unit, business-date range, explanation, comparator, source references and rule version. Production range is the slot date; inventory range runs from its observation date through the selected as-of end date. Skipped evaluations and evaluated count are exposed separately. Operational anomalies are separate from data-validation errors.

## Configuration and unresolved decisions

`RuleConfig` centralizes percent thresholds, required downtime threshold, enabled rules and severity per rule. All initial severities default to `WARNING`; callers may choose `INFO`, `WARNING` or `CRITICAL` per rule. No automatic severity escalation, causal diagnosis, UI rule builder or LLM decision is implied. Rules operate only on validated KPI evidence. The thresholds and default severity are an initial demo profile; product-owner review of business suitability and a production-specific downtime threshold remain open.
