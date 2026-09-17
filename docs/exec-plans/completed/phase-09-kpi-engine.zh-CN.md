# Phase 09——确定性 KPI 引擎

状态：已完成。权威依据：`docs/data/KPI_DEFINITIONS.md`，并遵循 `DATA_CONTRACT.md` 和 `ARCHITECTURE.md`。

- 在 `domain.analytics` 实现六个受支持指标，使用统一生产范围、精确算术、包含端点的日期、生产线/班次筛选、来源、覆盖率和明确的不可用状态。
- Completed Orders 和 Schedule Adherence 返回 `unsupported_schema`。权威定义禁止从槽位产量推断生命周期事件；未来假设示例不能成为当前模式的数值测试。
- 筛选前复用领域验证检查规范记录及关系，避免缺失或无效行因连接或筛选而消失。
- 库存使用已知物料全集及结束日期当天或之前的最新观察，保留期初之前的延用观察；生产线/班次筛选不影响库存。
- 为八个函数使用手工计算夹具，覆盖正常、边界、缺失和适用的零分母。CO/SA 检查不可用状态（包括零产量和空筛选），不发明生命周期字段。
- 运行 `pytest tests/test_kpi.py -v`、`pytest -q`、`ruff check .`，记录精确结果，通过后归档计划。

本任务不修改数据库、UI、LLM、异常阈值或权威公式。

## 完成证据

- `pytest tests/test_kpi.py -v`：21 项通过。手工计算夹具覆盖八项候选指标、可计算指标的边界、无效数据、零分母、四舍五入（half-up）显示、来源、日期/生产线/班次筛选及库存截至日覆盖情况。
- `pytest -q`：61 项通过。
- `ruff check .`：全部检查通过。
- 当前数据契约下，Completed Orders 和 Schedule Adherence 保持 `unsupported_schema`；未用产量代替订单生命周期证据，也未发明字段。
- KPI_DEFINITIONS 中的产品负责人决策 PO-01–PO-08 仍待确认；测试验证已记录的草案语义，不代表业务批准。
