# Manufacturing Operations Intelligence — KPI Definitions

Version: `0.1-draft`  
Date: 2026-09-15  
Status: Candidate specifications for product-owner review; not calculation implementation or release approval.  
Chinese counterpart: [KPI_DEFINITIONS.zh-CN.md](KPI_DEFINITIONS.zh-CN.md)

## 1. Authority and readiness

Based on [PRD](../product/PRD.md) and [Data Contract](DATA_CONTRACT.md), under [AGENTS V0](../../AGENTS.md). The Data Contract remains a draft. This document records explicit proposed metric assumptions; it does not assert universal manufacturing standards or introduce hidden source fields. No external standard is claimed as authority for these formulas.

Six candidates can be calculated from the current proposed contract once their semantics are approved. Completed Orders and Schedule Adherence require additional documented evidence and remain unavailable under the current contract. Specifying them does not authorize an order-management system or a schema change.

Use the new `KPI-*` identifiers below; do not silently renumber the earlier PRD K01–K07 references. This request adds candidate definitions, not an automatic deletion of earlier product requirements.

| ID | Candidate | Current contract readiness | Explicit product-owner approval |
| --- | --- | --- | --- |
| KPI-PA | Production Attainment | Supported conditionally | Gross output versus good output; zero-plan population |
| KPI-GY | Good Yield | Supported conditionally | Final disposition yield, not first-pass yield |
| KPI-SR | Scrap Rate | Supported conditionally | Final scrap, not all rejected/reworked units |
| KPI-TD | Total Downtime | Supported conditionally | Unplanned line-minutes inside planned windows |
| KPI-CO | Completed Orders | Blocked by missing lifecycle evidence | Completion event, census, cancellation and date attribution |
| KPI-SA | Schedule Adherence | Blocked by missing due/completion evidence | On-time order definition, baseline, cohort and cutoff |
| KPI-IR | Inventory Risk | Supported conditionally | Below-buffer material count, equality and incomplete coverage |
| KPI-OL | Output by Production Line | Supported conditionally | Gross piece count and cross-product comparability |

“Supported” means the fields exist, not that results or definitions are approved. All eight candidates require product-owner review because the contract and business assumptions remain provisional. The explicit decisions are summarized in section 4.

## 2. Shared calculation and presentation rules

### Population and lineage

- Use one accepted, coherently read batch with its contract and KPI-definition versions. Never calculate on a rejected or partially accepted batch.
- Join `production_plan`, `production_actual`, and `quality` one-to-one on the full production key documented in DATA_CONTRACT section 5, preserving source references. Do not join on `order_id` alone or multiply rows across lines/shifts.
- Let `P` be the resulting production-slot set selected by the inclusive local business-date range `[d_start, d_end]` and selected line/shift filters. Dates use `production_date`, including the contract's shift-start treatment of overnight shifts. Import timestamps do not filter production performance.
- All production metrics in this document use that same population. Daily, line and shift subgroups apply the formula independently to their contributing slots. Selection and grouping belong to deterministic analytics, not UI/report renderers.
- Use exact counts/decimal source values for aggregation. Compute rates from summed numerators and denominators, not the mean of displayed slot rates. Do not round before comparisons or aggregation.
- Proposed presentation: counts as integers, time totals to three decimal minutes, percentages to two decimal places using decimal half-up rounding. Preserve unrounded results and numerator/denominator evidence. Display rounding does not change validation or anomaly membership.
- Snapshot inventory follows its separate as-of population below. Order lifecycle metrics cannot borrow the production-date filter to manufacture missing event dates.

### Zero, empty and missing are distinct

- `P` empty: production KPI value is **N/A — no selected records**, including additive totals; do not present a zero-performance claim. Nonempty valid records whose measured sum is zero produce numeric zero for additive metrics.
- Any zero denominator yields **N/A — zero denominator**, never infinity, 0%, 100%, or a substituted denominator.
- Required values/relationships missing or invalid at import: reject under DATA_CONTRACT, preserve the prior accepted batch and label its identity. A previously accepted batch must not be presented as the failed new upload.
- If persisted data is unexpectedly invalid or a definition/version is unavailable, stop dependent calculations with an explicit error. Do not silently drop the affected rows and recompute a more favorable denominator.
- Complete matching within an uploaded batch does not prove the file includes every factory shift or every order. Display observed coverage and avoid claims about unobserved operations.
- Result status distinguishes `valid`, `no_data`, `zero_denominator`, `partial_coverage`, `unsupported_schema`, and `invalid_data`. These are proposed result semantics, not new input columns. Unsupported metrics are N/A with reasons, never zero.

No low/high thresholds, traffic-light cutoffs, or composite performance score are introduced. KPI formulas do not themselves approve anomaly thresholds; PRD D06 remains open. Renderers and AI consume the same structured results without recalculating them.

## 3. Candidate specifications

### KPI-PA — Production Attainment

1. **Business definition:** Gross completed output achieved relative to planned output in selected slots. Chosen assumption: use `actual_qty`, including good and final scrap, because the contract defines actual output that way. This is not good-output attainment or order completion. Includes valid zero-plan slots; unplanned output can increase the aggregate numerator.
2. **Mathematical formula:** `PA(P) = 100 × Σ actual_qty / Σ planned_qty`, for nonempty `P` with positive summed plan. Values above 100% are valid and are not capped.
3. **Required source fields:** `production_plan.planned_qty`, `production_actual.actual_qty`; common production key, `order_id`, `product_id`, `qty_unit` and provenance for validated matching. Use the approved joined population, not duplicated plan rows.
4. **Aggregation level:** Slot, day, selected line/shift, or whole selected period. Aggregate quantities first; unit is percent of planned pieces. Cross-product totals rely on the contract's comparable-piece assumption.
5. **Date filtering behavior:** Shared `P` filtering. An order spanning the boundary contributes only selected slots; do not pull its outside-period plan/output into this period.
6. **Zero denominators:** If total plan is zero, N/A even when actual output is positive. If plan is positive and output is zero, 0%. Zero-plan rows are not silently excluded from a larger valid group.
7. **Missing data:** Shared invalid/missing rules apply; no inner-join loss or imputed targets. Empty `P` is N/A.
8. **Example calculation:** Two slots have plans 100 and 300, actuals 80 and 300: `100 × 380 / 400 = 95.00%`.
9. **Validation example:** The unweighted mean of 80% and 100% is 90%, which must fail the expected 95.00% check. Plan 100/actual 120 gives 120.00%; plan 0/actual 20 gives N/A. A group with plans 100/0 and actuals 80/20 gives 100.00%, exposing the chosen zero-plan assumption.
10. **Expected visualization:** Percentage card, daily trend and line comparison, with plan/actual quantities and scope available. A 100% target reference may show the plan basis; do not add an unapproved warning threshold.

### KPI-GY — Good Yield

1. **Business definition:** Share of completed units finally accepted as good. Chosen assumption: final-disposition yield under contract C03; not first-pass yield, throughput yield, or yield after an undocumented rework process.
2. **Mathematical formula:** `GY(P) = 100 × Σ good_qty / Σ actual_qty`, for nonempty `P` with positive output.
3. **Required source fields:** `quality.good_qty`, `production_actual.actual_qty`; `quality.scrap_qty` for contract reconciliation, the shared production key, units and source references.
4. **Aggregation level:** Slot, day, line/shift or selected period. Quantity-weighted ratio; valid unrounded range 0–100% under the contract.
5. **Date filtering behavior:** Shared `P`, based on the production slot's business date, not an assumed inspection or acceptance timestamp.
6. **Zero denominators:** Zero actual output gives N/A, including good=0. Positive actual output with good=0 gives 0%.
7. **Missing data:** Missing disposition invalidates the batch; do not substitute `actual - scrap` for a missing supplied good quantity. Empty `P` is N/A.
8. **Example calculation:** Actual quantities 100 and 300, good quantities 90 and 294: `100 × 384 / 400 = 96.00%`.
9. **Validation example:** Corresponding scrap quantities 10 and 6 satisfy DATA.R04; a naïve average of 90% and 98% is 94%, which must not replace 96.00%. Actual 100/good 101 fails data validation rather than producing 101% yield.
10. **Expected visualization:** Yield card and daily/line trend, with good/actual quantities and a “final disposition” label. No first-pass quality claim or automatic traffic-light band.

### KPI-SR — Scrap Rate

1. **Business definition:** Share of completed units receiving final scrap disposition. Chosen assumption: scrap is irreversible disposition in this demo, not all rejects, recoverable defects or inspection failures. Do not rename the earlier PRD “Reject rate” to Scrap Rate without confirming this scope difference.
2. **Mathematical formula:** `SR(P) = 100 × Σ scrap_qty / Σ actual_qty`, for nonempty `P` with positive output.
3. **Required source fields:** `quality.scrap_qty`, `production_actual.actual_qty`; `quality.good_qty` for reconciliation, shared production key, units and provenance.
4. **Aggregation level:** Slot/day/line/shift/period, using ratio of sums. Valid unrounded range 0–100%.
5. **Date filtering behavior:** Shared `P`; slot date attribution follows the contract rather than an invented scrap-event date.
6. **Zero denominators:** Zero actual output gives N/A; positive actual with zero scrap gives 0%.
7. **Missing data:** Do not map ambiguous `rejected_units` into scrap or calculate missing scrap from actual/good. Invalid source data blocks the batch; empty `P` is N/A.
8. **Example calculation:** Actual 100/300, scrap 10/6: `100 × 16 / 400 = 4.00%`.
9. **Validation example:** For the same population, unrounded GY plus SR equals 100% because of DATA.R04; test before display rounding. A slot with actual 100, good 90, scrap 11 is invalid, not 11% acceptable input. Independently rounded complements may not sum to exactly 100.00%; do not alter values to force display equality.
10. **Expected visualization:** Scrap-rate card, daily trend and line comparison, with scrap counts. No default 5% threshold or inferred cause.

### KPI-TD — Total Downtime

1. **Business definition:** Total recorded unplanned stoppage within planned production windows. Chosen assumption: additive **line-minutes**, not the union of factory wall-clock intervals. Scheduled breaks and unclassified residual time are excluded by source meaning.
2. **Mathematical formula:** `TD(P) = Σ downtime_minutes` for nonempty `P`; unit is line-minutes. Do not derive it from `planned_production_minutes - runtime_minutes`.
3. **Required source fields:** `production_actual.downtime_minutes`; shared key and provenance. `runtime_minutes` and `production_plan.planned_production_minutes` support contract validation, not alternative downtime calculation.
4. **Aggregation level:** Slot/day/line/shift/period. Across lines the total may exceed elapsed time; different lines' minutes are additive. No overlapping-interval deduplication is possible from the contract.
5. **Date filtering behavior:** Shared `P`. An overnight slot's entire downtime belongs to its shift-start date; no minute-level proration.
6. **Zero denominators:** No division. Valid selected records with zero recorded downtime give `0.000` line-minutes; empty `P` gives N/A.
7. **Missing data:** Missing time is not zero. Invalid time relationships block input; do not infer or fill the residual.
8. **Example calculation:** Recorded downtime 10.500 and 20.250 gives `30.750` line-minutes.
9. **Validation example:** Two lines each stopped 30 minutes yield 60.000 line-minutes even if stoppages were simultaneous. Plan 480/runtime 400/downtime 20 gives 20.000, not 80.000. Plan 480/runtime 470/downtime 20 fails DATA.R05 before calculation.
10. **Expected visualization:** Total line-minutes card, downtime by line bars and daily trend; label the time unit. Do not label the aggregate as factory outage duration or downtime rate.

### KPI-CO — Completed Orders

1. **Business definition:** Proposed meaning: number of distinct manufacturing orders first reaching a verified final-completion state during the selected period. Chosen assumption: final accepted completion, not “some output recorded,” “one slot finished,” or “actual quantity reached plan.” Cancellation alone is not completion; reopening/recorrection treatment needs product-owner agreement.
2. **Mathematical formula:** Conceptually, `CO = |{o : o has a verified completion event and d_start ≤ local_date(completion_time(o)) ≤ d_end}|`, counting each order once. **Current result: N/A — unsupported schema.** This is a proposed event-based definition, not a formula over existing slot fields.
3. **Required source fields:** Existing `order_id` only identifies an order. Missing evidence: an authoritative order census, verified completion status/event and completion time, cancellation/reopening interpretation, and assurance that lifecycle history is complete. These are conceptual requirements, not columns added to DATA_CONTRACT. Slot `actual_qty`, `good_qty`, `production_date` do not prove completion.
4. **Aggregation level:** Distinct orders at site level. Proposed default excludes line/shift breakdown: an order can span multiple lines/shifts and must not be counted once per slot. A future attribution rule would require approval.
5. **Date filtering behavior:** Filter the verified event's site-local completion date, including orders begun earlier. Production-date filters cannot substitute. Proposed line/shift filters do not apply and must be labeled as such; cannot produce the metric until event/calendar rules are formalized.
6. **Zero denominators:** No division. With a complete authoritative event source and no events in the period, count zero. Current missing event source means N/A, never zero.
7. **Missing data:** Missing completion evidence/history means unsupported or incomplete coverage, not inferred unfinished/finished orders. Do not count distinct `order_id` in actuals as completions.
8. **Example calculation:** Hypothetical future evidence, **not current schema**: orders A and B have verified completions in the selected period; C completed earlier; D remains open. The result is 2, regardless of how many slots A/B occupied.
9. **Validation example:** An order appears in three slots and has one verified in-period completion: count 1, not 3. The same three actual rows without lifecycle evidence must return N/A. An order producing more than its slot plan is not evidence of final closure.
10. **Expected visualization:** Currently an unavailable card explaining missing lifecycle fields. If approved and supported later, a completed-order count and completion-date trend. Never show a plausible number based on distinct actual-row order IDs.

### KPI-SA — Schedule Adherence

1. **Business definition:** Proposed meaning: percentage of eligible orders due by the evaluation cutoff that achieved verified final completion no later than their committed due time. This is **order-level on-time completion adherence**. Companies may instead measure slot quantity attainment, start-time adherence or sequence adherence; none is silently substituted here.
2. **Mathematical formula:** Let `D` be the complete set of non-cancelled orders with committed local due date in `[d_start,d_end]` and due time not later than explicit cutoff `t_eval`. Let `T = {o ∈ D : verified completion_time(o) ≤ committed_due_time(o)}`. `SA = 100 × |T| / |D|` when `|D| > 0`. **Current result: N/A — unsupported schema.** Equality counts as on time; no grace window is assumed. These are proposed business decisions.
3. **Required source fields:** Existing `order_id` is insufficient. Missing: complete order schedule census, a frozen/identified committed due-time baseline, verified completion time/status, cancellation treatment, evaluation cutoff and defined local timezone. Absence of a completion event can mean “still open” only if the source explicitly guarantees completeness. No source fields are added by this document.
4. **Aggregation level:** Order-weighted site/period percentage, one eligible order one vote; not quantity-weighted and not an average of daily percentages. No default line/shift breakdown without an order attribution rule.
5. **Date filtering behavior:** Due-date cohort, not production-date or completion-date cohort. Exclude orders not yet due at `t_eval`; overdue open orders remain in the denominator. Early completion outside the chosen period still counts if that order's due date belongs to the selected cohort. A revised baseline must not silently rewrite historical adherence.
6. **Zero denominators:** With a complete schedule but no eligible due orders, N/A — zero denominator, not 100%. With no schedule fields, unsupported schema regardless of displayed date range.
7. **Missing data:** An incomplete due-order census or unknown lifecycle status prevents a reliable ratio. Do not drop late/open/unknown orders to improve the denominator. Explicitly known open overdue orders count as not on time; unknown records do not become open by assumption.
8. **Example calculation:** Hypothetical future evidence, **not current schema**: four eligible due orders, two completed on/before their due times, one completed late, one explicitly still open after its due time: `100 × 2 / 4 = 50.00%`.
9. **Validation example:** Incorrectly retaining only three completed orders would yield 66.67%, which fails the required 50.00%. Completion exactly at due time is on time. An order due after `t_eval` is excluded. Current slot plan/actual rows without timestamps produce N/A, even when output meets plan.
10. **Expected visualization:** Currently unavailable with a reason. If the definition and evidence are approved later, an on-time percentage with eligible/on-time counts and due-period trend. Do not present Production Attainment under this label.

### KPI-IR — Inventory Risk

1. **Business definition:** Proposed meaning: count of distinct materials whose latest eligible observed balance is **strictly below** their source-supplied safety stock. This is a low-buffer observation, not a stockout probability, production interruption prediction, monetary risk score or demand forecast. Equality is not risk under this assumption.
2. **Mathematical formula:** Let `U` be distinct materials in the active inventory batch, narrowed only by an explicitly applicable material selection. For each material choose its latest snapshot at/before `d_end`, as specified by DATA_CONTRACT. Let `E ⊆ U` have such a snapshot; `R = {m ∈ E : inventory_qty(m) < safety_stock(m)}`. With nonempty `U` and `E = U`, `IR = |R|`. If `E ≠ U`, headline IR is N/A — partial coverage; disclose observed `|R|` among `|E|` and missing `|U \ E|`, never imply all unknown materials are safe.
3. **Required source fields:** `inventory.material_id`, `snapshot_date`, `inventory_qty`, `safety_stock`, `qty_unit` and provenance. Use the buffer from the same chosen snapshot. No BOM or product relationship is available.
4. **Aggregation level:** One flag per material and one material count for the stated scope. Counting materials across units is valid; summing their quantities or shortfalls across `kg`/`m`/`ea`/`l` is not. Do not sum daily risk counts into a period total.
5. **Date filtering behavior:** As of inclusive `d_end`, not a sum or average over `[d_start,d_end]`. `d_start` only identifies carried-forward snapshots predating the range; show their observation dates. Ignore line/shift filters and label this. Inventory's local material filter applies only where disclosed; Overview/full reports use all materials per the PRD proposal. Scope differences require separate labeled results.
6. **Zero denominators:** No division. Nonempty fully covered material population with none below buffer gives 0. Empty `U` gives N/A — no selected materials. `safety_stock=0` does not cause division; a valid nonnegative balance is not below it.
7. **Missing data:** Required missing values reject import. No eligible as-of snapshot is coverage missing, not zero balance. A material absent entirely from the batch is outside the known universe; do not claim the report covers every factory material. Old carried-forward balances remain observations with visible dates; no unapproved staleness threshold is invented.
8. **Example calculation:** Fully covered materials A: 125.500 kg against 150.000 kg; B: 10 ea against 10 ea; C: 0 m against 0 m. Only A is below buffer; IR = 1 material out of 3 observed materials.
9. **Validation example:** Equality for B and zero buffer for C do not trigger. Add D whose only snapshot is after `d_end`: headline becomes N/A with partial coverage, observed at-risk count 1, observed materials 3, missing materials 1. Never select D's future snapshot or show a full-population risk count of 1.
10. **Expected visualization:** Count/coverage card and per-material table with balance, buffer, unit, observation date and explicit below-buffer status. Partial/no-data states must be visible; no pie implying complete coverage when snapshots are missing.

### KPI-OL — Output by Production Line

1. **Business definition:** Gross completed piece output attributable to each selected production line. Chosen assumption: `actual_qty` includes good and scrap; not good-only output, labor productivity, capacity utilization or standardized equivalent production.
2. **Mathematical formula:** For each observed line `l` in `P`, `OL(l,P) = Σ actual_qty` over selected slots with `line_id=l`.
3. **Required source fields:** `production_actual.actual_qty`, `line_id`, `production_date`, `shift_id`, `product_id`, `qty_unit`, and provenance; validated production joins apply.
4. **Aggregation level:** One count per observed line, optionally line/day/shift. A line's repeated slots add once each. Cross-product comparisons rely on the contract's comparable `ea` assumption; they do not prove equal manufacturing effort or capacity.
5. **Date filtering behavior:** Shared `P`. Line and shift selections narrow records before summation. Do not include outside-period slots of the same order. No master list of all factory lines is assumed.
6. **Zero denominators:** No division. An observed line with valid zero-output slots shows 0; a selected line with no records is N/A/no data, not inferred zero output. Empty `P` is an empty result with an explicit no-data state.
7. **Missing data:** Missing counts/line IDs are invalid; no guessing line assignments or summing an incomplete accepted join. Lines entirely absent from the batch are not manufactured as zero bars.
8. **Example calculation:** LINE-01 selected slots have actual quantities 80 and 120, LINE-02 has 300: outputs are 200 ea and 300 ea; the selected gross total is 500 ea.
9. **Validation example:** Sum of line outputs must reconcile to selected gross output, 500 in this example. Repeated `order_id` across slots does not justify deduplicating output; duplicate slot keys fail contract validation before summation. A filter selecting LINE-01 yields 200, not 500.
10. **Expected visualization:** Labeled bar chart by line and optional line/day trend using the same prepared series. Show scope and `ea` units; avoid treating larger output as evidence of better efficiency.

## 4. Product-owner decisions, conflicts, and verification boundary

| Decision | Required approval / unresolved point |
| --- | --- |
| PO-01 | Approve contract C01–C08 and the comparable-piece, final-disposition and time meanings before implementing supported metrics. |
| PO-02 | Approve PA gross-output numerator, inclusion of zero-plan rows, and no cap above 100%. |
| PO-03 | Approve GY/SR final-disposition semantics; reconcile PRD “Reject rate” with the narrower final scrap field. Do not silently relabel it. |
| PO-04 | Approve TD additive line-minutes and OL gross-output comparisons, with their limitations. |
| PO-05 | Decide whether CO should remain unavailable/deferred or receive an explicitly approved contract extension supplying authoritative completion evidence. No target-achievement proxy is approved. |
| PO-06 | Approve SA on-time order cohort, baseline immutability, exact due boundary, evaluation cutoff and cancellation/reopening rules; separately approve missing data-source scope if delivered. |
| PO-07 | Approve IR strict-below count, source-provided buffer, as-of/material scope and N/A headline when known-material coverage is incomplete. This refines the earlier partial-count presentation proposal. |
| PO-08 | Approve display rounding and empty-population states; finalize release tests in future TEST_PLAN/ACCEPTANCE_CRITERIA. |

Traceability: PA corresponds to prior PRD K03; OL uses the gross-output quantity concept of K01 by line; IR refines K07 using K06's snapshot context. GY is newly specified. SR must not be assumed identical to K04 Reject rate. TD is a time total, not K05 Downtime rate. CO/SA introduce requested candidate definitions but require absent evidence. Prior Good Output and other metrics are not silently removed or given new formulas here.

Each supported result must expose dataset/definition identity, effective scope, coverage, unrounded value, displayed value/unit, ratio evidence where relevant, and contributing source references. CO/SA must expose unsupported status until their evidence is formally available. AI must not fill this gap.

Examples above are arithmetic and hypothetical validation cases inside documentation, not generated datasets or executed calculation tests. Future tests must independently verify weighted aggregation, zero/empty distinctions, rejection of invalid inputs, period boundaries, inventory future-snapshot exclusion, and unsupported CO/SA behavior. No calculation code, data files, contract changes, product-document rewrites or implementation tasks are included in this work.
