# Phase 06 Execution Plan — Deterministic Synthetic Data

Status: Completed  
Scope: Synthetic/demo data generation only  
Sources: `AGENTS.md`, `ARCHITECTURE.md`, `docs/data/DATA_CONTRACT.md`, and `docs/data/KPI_DEFINITIONS.md`

## Objective

Create a deterministic generator and canonical CSV samples for 90 days of manufacturing data covering three production lines, twenty finished products, and forty materials. The four datasets must follow the current Data Contract and include reproducible normal operations and controlled abnormal scenarios.

## Boundaries and assumptions

- Generate canonical business input columns only; import provenance remains the future import workflow's responsibility.
- Use two shifts per line per day, producing 540 matched rows in each production dataset and 3,600 daily inventory snapshots.
- Scenario values are synthetic fixture controls, not approved application anomaly thresholds or manufacturing standards.
- An “incomplete order” means a deliberately large plan-versus-actual quantity gap for the generated order. It is not authoritative lifecycle completion evidence; Completed Orders and Schedule Adherence remain unsupported under the current contract.
- Do not implement validation services, KPI calculations, dashboards, persistence, or anomaly-detection features in this phase.

## Implementation steps

1. Add a generator under the Data layer using a fixed default seed and fixed default start date.
2. Generate matching `production_plan`, `production_actual`, and `quality` slot keys and consistent identifiers, quantities, units, quality disposition, and time values.
3. Generate daily material inventory snapshots with stable per-material units.
4. Deliberately generate temporary underperformance, downtime spikes, increased scrap, below-safety inventory, and plan-versus-actual incomplete-order examples.
5. Expose a scenario manifest separately from the four canonical dataset schemas.
6. Add a CSV writer and materialize the four deterministic sample files under `data/samples/clean/`.
7. Add tests for schemas, cardinality, date coverage, referential integrity, contract ranges, determinism, CSV output, and every requested scenario.
8. Run `ruff check .` and `pytest -q`. Move this plan to `completed/` only if both pass.

## Acceptance criteria

- Exactly four datasets use the documented canonical columns.
- Production keys are unique and equal across plan, actual, and quality; shared identifiers agree.
- `good_qty + scrap_qty = actual_qty` and time constraints hold for every slot.
- Inventory keys are unique, units are stable per material, and all values meet quantity rules.
- Generated scope contains exactly 90 dates, 3 lines, 20 products, and 40 materials.
- Repeated generation with the same seed is identical.
- Tests prove that each controlled scenario exists at its declared dates and entities.
- Generated CSV files are clearly synthetic and contain no secrets or real company data.
- Ruff and pytest pass.

## Risks and controls

- **Fixture thresholds mistaken for product rules:** keep scenario metadata in the generator and document that analytics thresholds remain unapproved.
- **Order shortfall mistaken for lifecycle state:** use plan/actual wording and retain KPI-CO/KPI-SA as unsupported.
- **Random drift breaks test intent:** clamp normal ranges and override scenario windows deterministically.
- **Cross-dataset inconsistency:** build all production domains from one slot identity and verify exact key equality.

## Validation evidence

- `ruff check .`: passed.
- `pytest -q`: 7 tests passed.
- Production datasets: 540 records each; inventory: 3,600 records; 5,220 business records total.
- Coverage: 2025-01-01 through 2025-03-31; 3 lines, 20 products, and 40 materials.
- Controlled underperformance attainment: 73.52% in the declared window.
- Controlled downtime range: 167.000–210.000 minutes in the declared spike window.
- Controlled scrap rate: 11.61% in the declared increase window.
- Controlled low inventory: all 28 declared material/date records are below safety stock.
- Four declared order quantity gaps have attainment from 54.38% to 57.00%.
- Repeated generation with seed `2606` is byte-stable for the materialized CSV outputs and frame-equal in automated tests.
