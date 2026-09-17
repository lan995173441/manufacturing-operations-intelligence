# Manufacturing Operations Intelligence — Data Contract

Contract version: `0.1-draft`  
Date: 2026-09-15  
Status: Concrete design for review; business assumptions below are proposed, not previously approved. No datasets or implementation are created.  
Chinese counterpart: [DATA_CONTRACT.zh-CN.md](DATA_CONTRACT.zh-CN.md)

## 1. Authority, scope, and decision status

Read [AGENTS V0](../../AGENTS.md), [Architecture](../../ARCHITECTURE.md), and [PRD](../product/PRD.md). This document owns the proposed RAW/CLEAN data definitions. It supports PRD F01–F06 and the data consumed by the five application areas. It does not define KPI formulas, anomaly thresholds, SQL DDL, or UI layouts. `KPI_DEFINITIONS.md` remains a missing future source for metric semantics.

The latest request establishes the canonical dataset names `production_plan`, `production_actual`, `quality`, and `inventory`. They replace earlier draft labels such as `production_planning` and `production_actuals` in this contract. Input files use the canonical names; no automatic legacy dataset-name aliases are proposed.

The following decisions make the contract testable without claiming user approval. Approval of this document should explicitly address C01–C08 before business implementation. Prior PRD/AGENTS statements that this document is missing are historical; their other conflicts remain unresolved.

| ID | Proposed decision | Relationship to earlier requirements / limitation |
| --- | --- | --- |
| C01 | One Excel workbook with four sheets, or four assigned CSV files; complete batches only | Refines PRD D01/D10. One file per domain for CSV; no mixed-format batch. |
| C02 | One production record per date/line/shift, with one order and product in that slot | Retains D02 grain while adding requested order identification. Multiple orders/products per slot require a revised contract; not silently aggregated. |
| C03 | Quality is final good/scrap disposition of all actual output, without rework or inspection backlog | New explicit simplification. Earlier “rejected” wording may include more than scrap; do not assume equivalence. |
| C04 | Runtime and downtime are non-overlapping portions of planned production time | Adds requested runtime. Unclassified residual time is allowed and never inferred as downtime. No OEE or utilization formula is established. |
| C05 | Inventory is one site-wide material balance per date; no warehouses, movements, BOM, or product-stock mapping | Refines D04. Material-only inventory narrows the earlier generic item proposal and needs review. |
| C06 | All four domains pass together; matched production keys; equivalent active re-import is a no-op; changed batch replaces active data | Refines D03/D05. No partial merge or history UI. |
| C07 | Strict formats, fixed units, bounded values and file limits below | Refines D10. Bounds are proposed MVP constraints, not manufacturing standards. |
| C08 | Explicit as-of stock coverage and no line/shift filtering of inventory | Refines D08. KPI definitions still own any stock indicator or low-stock rule. |

## 2. RAW file interface

RAW means decoded source values before business normalization. CLEAN means values passing this contract, suitable for persistence. Source files are immutable; normalization never writes back into them.

### Packaging and structure

- Accept one `.xlsx` workbook with exactly four sheets named after the canonical datasets, or four UTF-8 comma-delimited `.csv` files explicitly assigned one-to-one to those datasets. CSV filenames are descriptive, not the only domain detector.
- Header row is row 1; records start at row 2. Column order is irrelevant. All business columns specified in section 4 are required headers. No metadata columns are supplied by users. No extra or duplicate headers, merged cells, subtotal rows, explanatory title rows, formulas, macros, password protection, external-reference evaluation, or additional sheets.
- Excel hidden rows/columns are still source data and must be inspected, not silently skipped. Formula cells fail even if a cached value exists. Numeric Excel cells are allowed for quantities, not identifiers.
- CSV may have a UTF-8 BOM and standard quoted fields. Preserve text tokens; do not let automatic NA/type inference consume identifiers or blanks. Invalid encoding, malformed quoting, inconsistent field counts, or embedded line breaks in a field block the file. With multiline fields excluded, CSV source row equals its physical line number.
- Proposed limits: total uploaded file bytes ≤ 10,000,000; total data-region rows across four domains ≤ 10,000; every domain has at least one candidate record. Exceeding a limit rejects the batch, never truncates it. These limits do not replace later parser resource-safety checks.
- QA implementation note (2026-09-17): before openpyxl loads cells, the XLSX reader bounds expanded archive content to 40,000,000 bytes, archive entries to 256, and populated worksheet cells to 200,000. It then streams sheets and rejects dimensions above 10,001 physical rows (including the header) or 100 columns. Sparse, dense and highly compressed files fail visibly rather than consuming unbounded parser resources. These are parser safety guards, not manufacturing rules.
- Excel data region ends at the last row with any value, ignoring formatting-only tail rows. An empty row inside that region is an invalid missing record. CSV blank records are invalid; the normal final line terminator is not a record. No empty separators are silently dropped.

### RAW schema and finite header mapping

For each dataset, RAW business columns are exactly the CLEAN business fields in section 4, represented as source tokens/cells. The only permitted header transformations are trimming outside whitespace and converting ASCII header letters to lowercase. The aliases below may then be applied. Alias and canonical header occurring together is a duplicate-column error, even if values agree.

| Dataset | Allowed RAW header | CLEAN field | Condition |
| --- | --- | --- | --- |
| Production datasets | `date` | `production_date` | Source must use the shift-start business date defined below. |
| `production_plan` | `planned_units` | `planned_qty` | Same discrete piece-count meaning. |
| `production_plan` | `planned_minutes` | `planned_production_minutes` | Same planned time meaning; scheduled breaks excluded. |
| `production_actual` | `produced_units` | `actual_qty` | Same completed-output meaning. |
| `production_actual` | `unplanned_downtime_minutes` | `downtime_minutes` | Only unplanned downtime within planned production time. |
| `inventory` | `on_hand_qty` | `inventory_qty` | Same material/site/date balance meaning. |
| `inventory` | `minimum_qty` | `safety_stock` | Source explicitly uses the supplied minimum buffer meaning in C05. |

Canonical headers always work. No other aliases, fuzzy matching, automatic translation or mapping UI. `rejected_units` is deliberately **not** an alias for `scrap_qty`; `item_id` is not automatically `material_id`. The analyst must supply the new fields or prepare a correctly interpreted source; no order, runtime, good quantity, scrap quantity or unit is fabricated from old examples.

Each RAW field retains its original header, cell/token value and source location during validation. A field's accepted lexical forms and conversion are specified in sections 3 and 6; decoding is not evidence that the value is valid.

## 3. Shared types and conventions

The bounds below are inclusive. `Required` means the header and each value must exist; zero is a value, not missing. All CLEAN business fields are required; there are no nullable business fields in this version.

| Type | Canonical representation / valid range | RAW acceptance and validation |
| --- | --- | --- |
| `ID` | Case-sensitive string, 1–64 characters; ASCII letters/digits plus `_`, `-`, `.`; starts with letter/digit | Text only; trim outside whitespace; preserve leading zeroes and case; reject numeric Excel IDs and internal whitespace. No padding or case repair. |
| `DATE` | Calendar date, `YYYY-MM-DD`, from `2000-01-01` through `2100-12-31` | Strict ISO text or Excel date-typed cell at midnight; real calendar date required. Untyped serial numbers, ambiguous dates and non-midnight timestamps rejected. |
| `COUNT` | Integer, 0–1,000,000,000 | Excel finite numeric whole value or ASCII digit text; text may have a fractional suffix consisting only of zeroes. Reject negatives, booleans, fractional counts, commas, exponents, units, NaN and infinity. |
| `MINUTES` | Exact decimal with at most 3 fractional places, 0–1440 | Finite numeric Excel value or unsigned dot-decimal text; reject nonzero precision beyond 3 places, exponents in text, commas, booleans and units. No rounding. |
| `STOCK` | Exact decimal with at most 3 fractional places, 0–999,999,999.999 | Same lexical rules as MINUTES, with this range; for `ea`, fractional stock is forbidden. |
| `UNIT` | Lowercase enumeration: production `ea`; inventory `ea`, `kg`, `m`, `l` | Trim and lowercase these tokens only; no conversion from `pcs`, `ton`, currencies, packs or other aliases. |

For decimal text use digits with an optional dot followed by digits; signs and an empty integer part are rejected. Trailing fractional zeroes beyond the supported scale may be removed losslessly and logged. Excel numeric values must convert losslessly to the supported business precision; an ambiguous rounding requirement fails, not approximates. Canonical decimal serialization uses exactly three fractional places, e.g. `450.000`, independent of visual formatting. Storage must round-trip these values exactly; this is a logical type contract, not a mandated SQL type or a new dependency.

### Time and quantity meaning

- One fictional site uses one local business calendar. `production_date` is the local date on which the shift starts; an overnight shift remains wholly assigned to that date. No splitting into calendar days, clock times, daylight-saving conversion or timezone inference from filenames.
- `shift_id` identifies a site-defined shift label; this contract does not prescribe shift duration or an approved label list. It is consistent across the production datasets. Unknown-but-valid ID strings are not rejected against an invented master list.
- `snapshot_date` is the site-local end-of-day stock date, not an event timestamp. At most one material snapshot per date; no intraday movement semantics. All supplied snapshots are observations, not forward-filled records.
- Only system import timestamps are UTC instants (`YYYY-MM-DDTHH:MM:SSZ`). They do not alter business dates. Future production dates within the DATE range are not invalid solely relative to the machine clock; planning is allowed in principle, but this complete-batch profile still requires explicit matching actual/quality rows.
- Production quantities count comparable pieces (`ea`) for this demo. `actual_qty` includes both final good and scrapped output. There is no mass-based production, conversion factor, mixed packaging, yield equivalence across products, or monetary quantity.
- Inventory quantities are site-wide on-hand material balances, not available-to-promise stock. `safety_stock` is a supplied minimum buffer in the same unit as the balance; the system does not optimize or calculate it. No reservations, valuation or negative adjustment records. Never aggregate incompatible units.

## 4. CLEAN canonical business schemas

Composition is exact: each production dataset contains **all six common fields below plus its dataset-specific fields**. Inventory uses its own five fields. Every record also references the generated provenance fields in section 5. No hidden derived business fields are added.

### 4.1 Common fields for `production_plan`, `production_actual`, and `quality`

| Field name | Business meaning | Data type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `production_date` | Shift-start business date | DATE | Required | DATE range | `2026-09-14` | T-DATE; part of production key; same across joined records |
| `line_id` | Production line identifier | ID | Required | ID grammar | `LINE-01` | T-ID; part of key, exact match across datasets |
| `shift_id` | Shift identifier on that line/date | ID | Required | ID grammar | `DAY` | T-ID; part of key, exact match across datasets |
| `order_id` | Manufacturing order allocated to this slot | ID | Required | ID grammar | `MO-0007` | T-ID; R03 agreement; one order per slot |
| `product_id` | Product produced in this slot | ID | Required | ID grammar | `PRD-001` | T-ID; R03 agreement; an order refers to one product within the batch |
| `qty_unit` | Unit of production counts | UNIT | Required | `ea` only | `ea` | T-UNIT; R03 agreement; counts are comparable pieces by demo assumption |

### 4.2 `production_plan`

Grain: one planned slot per `(production_date, line_id, shift_id)`. This is a snapshot plan, not order creation, dispatch or version history.

| Field name | Business meaning | Data type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `planned_qty` | Target output for this slot | COUNT | Required | 0–1,000,000,000 | `1000` | T-COUNT; actual output may exceed it without making input invalid |
| `planned_production_minutes` | Planned production window excluding scheduled breaks | MINUTES | Required | 0–1440 | `480.000` | T-MINUTES; time consistency R05/R06 |

### 4.3 `production_actual`

Grain: one completed actual-output record for each planned slot, not machine events or operation passes.

| Field name | Business meaning | Data type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `actual_qty` | Completed units receiving final quality disposition | COUNT | Required | 0–1,000,000,000 | `960` | T-COUNT; quality reconciliation R04 |
| `runtime_minutes` | Recorded productive running time inside the planned window | MINUTES | Required | 0–1440 | `450.000` | T-MINUTES; time consistency R05; never derived from planned minus downtime |
| `downtime_minutes` | Recorded unplanned stoppage inside that window | MINUTES | Required | 0–1440 | `30.000` | T-MINUTES; excludes scheduled breaks; time consistency R05 |

### 4.4 `quality`

Grain: one final disposition record for all output of the corresponding actual slot. No separate inspected quantity or rework state.

| Field name | Business meaning | Data type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `good_qty` | Units accepted as final good output | COUNT | Required | 0–1,000,000,000 | `940` | T-COUNT; supplied, not imputed; R04 |
| `scrap_qty` | Units finally scrapped, not pending or recoverable rejects | COUNT | Required | 0–1,000,000,000 | `20` | T-COUNT; supplied, not inferred from generic rejected count; R04 |

### 4.5 `inventory`

Grain: one end-of-day material balance at the single site per `(snapshot_date, material_id)`. There is no line, order, product or warehouse foreign key.

| Field name | Business meaning | Data type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `snapshot_date` | End-of-day observation date | DATE | Required | DATE range | `2026-09-14` | T-DATE; part of inventory key |
| `material_id` | Material whose site balance is recorded | ID | Required | ID grammar | `MAT-001` | T-ID; part of key, independent of product namespace |
| `qty_unit` | Unit for balance and buffer | UNIT | Required | `ea`, `kg`, `m`, `l` | `kg` | T-UNIT; same material retains one unit within batch, R07 |
| `inventory_qty` | Observed on-hand balance | STOCK | Required | 0–999,999,999.999 | `125.500` | T-STOCK; fractional `ea` rejected; below buffer is valid data |
| `safety_stock` | Source-supplied minimum stock buffer for that observation | STOCK | Required | 0–999,999,999.999 | `150.000` | T-STOCK; same unit as balance; may vary by date; not a model-derived quantity |

Examples are individual documentation values, not generated datasets or evidence of factory performance.

## 5. Primary identifiers, relationships, and provenance

### Business identifiers and integrity rules

Logical persisted record identity is `(batch_id, dataset, business_key)`; dataset tables may express this without a literal dataset column. A source row number is provenance, not a business key. Do not add a random ID as a substitute for duplicate checks.

| Rule ID | Constraint | On failure |
| --- | --- | --- |
| R01 | Production key is `(production_date, line_id, shift_id)`; inventory key is `(snapshot_date, material_id)`; unique after normalization | Block entire batch; show all conflicting source locations, even identical duplicates |
| R02 | Key sets of plan, actual and quality are equal within the batch; join is exactly 1:1:1 | Block; report missing and orphan records, never join only the intersection |
| R03 | At each production key, `order_id`, `product_id`, `qty_unit` agree; one order has one product in the batch | Block inconsistent references; same order may span dates/lines/shifts, but multiple orders cannot share one slot |
| R04 | For each slot, `good_qty + scrap_qty = actual_qty` exactly | Block; do not repair any of the three supplied quantities. This is reconciliation, not a KPI formula |
| R05 | `runtime_minutes + downtime_minutes <= planned_production_minutes` | Block excess. A positive residual is permitted unclassified time, not imputed downtime; exact decimal comparison |
| R06 | For each date/line, summed planned production minutes over shift records do not exceed 1440 | Block overlapping-capacity evidence for this one-line profile; without start/end times this does not prove schedules never overlap |
| R07 | Each `material_id` uses one inventory unit throughout the batch | Block conflicting units; do not convert or add quantities |

No constraint requires actual quantity to be below plan. Zero plan, zero output, zero buffer and zero times are legal when the other constraints hold. Do not infer an output-versus-runtime relation without an approved domain rule. Zero output requires explicit zero good/scrap records; missing rows are not zero rows. Plan-only future slots are unsupported by this complete-batch profile (C01/C06).

```text
production_plan  -- same slot key, R02/R03 --> production_actual
       |                                           |
       +----------- same slot key ----------------> quality

inventory (snapshot_date, material_id) -- independent material snapshots
No product-to-material mapping, BOM join, or production-stock reconciliation.
```

Production datasets must join on the full key, not only order or product. Inventory dates need not match production dates. For an as-of request, select the latest observed snapshot at or before the end date per material; never use future stock or insert forward-filled CLEAN rows. Missing eligible snapshots remain unavailable with a coverage count. Expose older carried-forward dates and do not apply line/shift filters to inventory. The user-visible item selector refers to `material_id`; no new selector capability is added. Indicator formulas and low-stock comparisons belong to future KPI Definitions, not this contract.

### Generated source and record metadata

These fields are system-generated and are never expected as input columns. Metadata may be normalized into batch/source records rather than repeated per business row. Values must be recoverable by reference after restart. RAW and CLEAN records use `(source_id, source_row)` to connect to the source; each CLEAN record maps to exactly one RAW row in this profile.

| Field name | Business meaning | Type | Nullability | Valid range | Example | Validation rule |
| --- | --- | --- | --- | --- | --- | --- |
| `batch_id` | Identifier of one import attempt / accepted batch | UUID string | Required | Canonical UUID representation | `550e8400-e29b-41d4-a716-446655440000` | Generated once per attempt; accepted rows reference the committed batch |
| `contract_version` | Rules used for validation | String | Required | Supported contract version | `0.1-draft` | Unknown version blocks processing; draft identifier does not authorize deployment |
| `imported_at_utc` | Successful commit time | UTC timestamp | Required on accepted batch; null before commit | Valid UTC instant | `2026-09-15T02:00:00Z` | Set only for committed data |
| `source_id` | Identifier for one domain source in a batch | UUID string | Required | Canonical UUID, unique within batch | `550e8400-e29b-41d4-a716-446655440001` | Generated; source must belong to record's batch |
| `source_filename` | Uploaded basename | String | Required | 1–255 characters, no path separators/control characters | `demo.xlsx` | Preserve display name, never use it as a destination path |
| `source_sha256` | Digest of original uploaded bytes | Lowercase hex string | Required | 64 hex characters | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` | Calculate from bytes; same workbook hash may appear for four sheets |
| `source_dataset` | Domain assigned to source | Enumeration | Required | Four canonical names | `production_plan` | Matches domain and sheet/CSV assignment |
| `source_sheet` | Original Excel sheet name | String | Required for Excel; null for CSV | Exact canonical sheet name | `production_plan` | Null only for CSV; never invent a CSV sheet |
| `source_row` | Original data row / CSV line | Integer | Required on row, not source manifest | 2–10001 | `2` | Preserve physical position before transformations |
| `normalized_fingerprint` | Identity of accepted business content | Lowercase hex string | Required after successful normalization | 64 hex characters | `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` | Computed as specified in section 8; excludes generated provenance |

Retain normalization evidence for accepted data: source reference, field/header, original representation, normalized representation and transformation ID. Evidence is metadata, not an additional business dataset. Persist only changes needed to explain normalization; do not duplicate full raw files. Rejected RAW values and diagnostics remain visible for the current attempt and are not a permanent rejected-data archive.

## 6. RAW → CLEAN transformation rules

The process is validation-aware: inspect RAW structure/lexical validity, perform only these allowed conversions, then validate CLEAN types, keys and relationships. A parseable value is not automatically accepted.

| ID | RAW input / condition | CLEAN output / action | Evidence / failure behavior |
| --- | --- | --- | --- |
| N01 | UTF-8 BOM at file start | Remove encoding marker before header parsing | Record file-level action; other decoding errors block |
| N02 | Header outside spaces / ASCII case / listed alias | Canonical header | Record original/new header; collisions or unsupported columns block |
| N03 | ID text ` 0012 ` | String `0012` | Preserve case and zeroes; numeric Excel ID cannot be recovered by guessing |
| N04 | ISO date text or valid Excel midnight date cell | Canonical DATE | Record original type/date representation; no locale guess or arbitrary serial conversion |
| N05 | COUNT text `0960` or numeric whole `960.0` | Integer `960` | Lossless parse; never round a fractional count |
| N06 | MINUTES/STOCK text `125.5` or equivalent Excel number | Exact decimal `125.500` | Lossless scale normalization; excess nonzero precision blocks |
| N07 | UNIT token ` KG ` | `kg` | Log trim/case normalization; only approved unit tokens |
| N08 | Entire required field blank | No CLEAN record accepted | Missing-value diagnostic; no zero, mean, forward-fill or default |
| N09 | Successful record | Attach source references and batch metadata | No business quantity or identifier generated |

Do not derive `good_qty`, `scrap_qty`, `runtime_minutes`, `downtime_minutes` or `safety_stock` from other fields. R04/R05 verify supplied values; they do not authorize repair. Do not merge rows, aggregate slots, infer units, drop duplicates, enrich through AI, or replace source cells. Canonical datasets remain separate; analytics may form validated joins without rewriting stored records.

## 7. Missing, invalid, and duplicate-value policy

- A missing required column is a schema failure. Empty Excel cells, empty CSV fields, or whitespace-only required values are missing-value failures.
- Reserved text tokens `NULL`, `NONE`, `N/A`, `NA`, `NAN` (case-insensitive after trimming) are treated as explicit missing markers in all business fields and rejected. Actual NaN/NaT and nonfinite numbers are rejected, never persisted. Boolean cells are not quantities. An identifier legitimately using a reserved marker requires a later contract change; it is not guessed.
- There is no imputation. Canonical business fields never contain null. A missing observation for an analytics period is an analytics coverage state, not a manufactured canonical row.
- Detect duplicates after all permitted normalization. Identical duplicates and conflicting duplicates are both blocking R01 errors. Preserve every affected RAW location; do not choose first/last, sum duplicates or silently deduplicate.
- A malformed or invalid row blocks its entire batch, not just its domain. Correct valid-looking rows are not partially published. Present syntactically readable issues together; if parsing cannot continue safely, state where it stopped and that later records were not validated.

### Observable validation outcome

Expose the attempted batch, source filenames/domains, validation stage, total observed rows, evaluated rows, unevaluated rows, error count, affected-row count, normalization-action count and status. Multiple errors may refer to one row; do not confuse error and row counts. If a malformed file prevents a reliable total, show “unknown,” not zero. Never claim all records passed after a parser stops.

Each diagnostic includes a stable rule code, severity (`ERROR` for rejection; `INFO` for allowed normalization), source ID/file/domain, sheet when applicable, row and field when locatable, original value or safe representation, reason, and suggested source correction. File-level errors use no invented row/field. Show counterpart locations for duplicate or relationship errors. Detailed layout is left to UI_SPEC, but users must be able to inspect all diagnostics for the attempt, not only a success/failure badge or an undisclosed first-N subset.

Type rules are `T-ID`, `T-DATE`, `T-COUNT`, `T-MINUTES`, `T-STOCK`, `T-UNIT`; other stable categories are `E-PACKAGE`, `E-SCHEMA`, `E-PARSE`, `E-LIMIT`, `E-MISSING`, and `E-PERSIST`. Integrity rules use R01–R07. These R-codes belong to the **data-validation namespace**, not PRD candidate anomaly rules with similar labels. Display the namespace, e.g. `DATA.R04`, to avoid confusing invalid data with operational anomalies.

Below-target production or stock below its buffer can pass validation. Operational anomaly results are calculated later under approved KPI/rule definitions, never used as reasons to erase otherwise valid input.

## 8. Import identity and persistence policy

Proposed C06 behavior: a successful different batch replaces the complete active dataset in one SQLite transaction with its associated provenance. Validation happens before the transaction; all domains and active identity commit together. On failure keep the previous active dataset and state that the new attempt was not activated. If commit outcome is uncertain, inspect stored identity before retrying. No SQL DDL or migration code is created here.

Define business-content equivalence independently of filenames and file format:

1. After successful validation, sort domain names and each domain's records by its full business key (canonical string order).
2. Serialize a UTF-8 JSON object with `contract_version` and a `datasets` object: canonical dataset names map to ordered record lists; record properties are only the business fields in section 4. Sort object keys, use compact separators and no trailing newline, and emit unescaped Unicode.
3. Serialize IDs/dates/units as strings, COUNT as integer numbers, and MINUTES/STOCK as strings with exactly three fractional places. Exclude batch/source IDs, timestamps, diagnostics and original headers.
4. SHA-256 of those bytes is `normalized_fingerprint`. The active fingerprint and contract version must both match for an “already imported” no-op. Do not infer equivalence from the raw file hash.

An equivalent active re-import preserves the original accepted batch/provenance and creates no duplicate business rows; its current attempt reports the existing active identity. Re-importing an older, different dataset is treated as a new full replacement, not a silent history match. A contract-version change prevents equivalence even when values look alike. Active content must never include mixed contract versions or a partial set of domains.

Persistence must preserve exact types, business keys and source references and must enforce agreed uniqueness/relationships in addition to pre-write validation. How logical decimal types map to SQLite is an implementation detail that must preserve exact round-trip values. Analytics receives only a coherently read accepted batch; UI, reports and optional AI cannot write CLEAN business data or redefine it.

## 9. Data lineage diagram

```text
Synthetic source files (.xlsx or .csv; immutable)
  file bytes/hash + domain/sheet + original row + header/value
                         |
                         v
RAW candidates -> VALIDATION (package/schema/lexical checks)
                         |
                         v
                 NORMALIZATION (N01-N09)
                         |
                         v
                 CLEAN VALIDATION (types + DATA.R01-R07)
                         |
           any ERROR ----+----> attempt diagnostics visible to user
                         |      no publication; prior active data kept
                      PASS
                         |
                         v
             PERSISTENCE (one SQLite transaction)
       normalized records + batch/source references + change evidence
                         |
                         v
              ANALYTICS (accepted coherent batch only)
       result identity + filters + definition versions + source refs
                         |
                         v
           Dashboard / Excel / PDF / optional AI summary
```

Each accepted record traces back to one physical RAW row. Each analytic output must retain or expose the contributing dataset/business keys and source references, including all three production sources where a calculation joins them. Aggregation may have many contributing rows; never imply a single source row explains an aggregate. Persistence of provenance does not retain source file bytes; users must keep original files to reopen them. AI consumes structured results only and has no path to rewrite RAW or CLEAN data.

## 10. Contract review and future validation

Review C01–C08, especially complete production coverage, final good/scrap disposition, runtime meaning, and material-only inventory. No assumption is represented as a manufacturing standard. Once approved, align the PRD and user stories by reference, not by copying schemas or introducing conflicting definitions.

Future validation should cover every type and integrity rule, aliases/collisions, preservation of leading zeroes and physical rows, missing markers, equivalent Excel/CSV normalization, duplicate-after-trim, atomic failure/restart, fingerprint invariance under file/row/column ordering, and observable incomplete parsing. Include a mismatched quality total and time overrun to verify rejection without repair. No datasets, executable tests, KPI formulas or application features are generated in this task.
