# RC1 发布清单 — Manufacturing Operations Intelligence

日期：2026-09-17。状态：**候选版已核查；暂不能交付验收**。英文对照：[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)。

本清单逐项核查原版 [PRD](../product/PRD.zh-CN.md) 草案及[验收标准](../quality/ACCEPTANCE_CRITERIA.zh-CN.md)。**PASS** 表示有测试或检查证据，**FAIL** 表示观察到不符，**NOT TESTED** 表示证据不足或仍需业务决策。通过暂定公式的测试不代表产品负责人批准。功能行评估详细行为，其编号验收子条款单独评估。

## 正式发布候选冻结 — 2026-09-19

- **发布分支：** `release/v1.0.0`
- **建议候选版本：** `v1.0.0-rc.1`；尚未创建 Git 标签。
- **冻结状态：** 已生效。禁止新增功能、KPI、AI 范围、集成、基础设施、广泛重构或依赖升级。仅允许发布阻断/高严重度修复、回归测试、安全或可靠性修复、必要的可用性小修正以及发布文档/元数据变更。
- **基线验证：** `.venv/bin/ruff check .` 通过；`.venv/bin/pytest -q` 在 **34.23 秒内通过 138 项测试**；README 规定的 `.venv/bin/pytest -v` 在 Python 3.12.2 上于 **33.34 秒内通过 138 项测试**。
- **待完成事项：** UAT、产品负责人决策 BA-01–BA-08、PRD/项目章程协调及最终发布批准。本次冻结不改变下文 RC1 **暂不交付验收**的结论。

## RC1 验证记录

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 完整测试 | PASS | Python 3.12.2、pytest 9.1.1：`.venv/bin/pytest -v` → **138 passed in 36.69s**。 |
| 静态检查 | PASS | `.venv/bin/ruff check .` → `All checks passed!`。 |
| 应用启动 | PASS | 执行 `.venv/bin/streamlit run streamlit_app.py --server.address=127.0.0.1 --server.port=8766 --server.headless=true`；`lsof` 仅显示 `TCP 127.0.0.1:8766 (LISTEN)`；`/_stcore/health` 返回 HTTP 200。检查后已停止进程。 |
| 合成演示数据 | PASS | 临时 SQLite 上 `load_sample_data()` 接受 **5,220** 行：计划/实际/质量各 **540** 行、库存 **3,600** 行；覆盖 **90 天、3 条产线、20 种成品、40 种材料**。见 `tests/data/test_synthetic.py`。 |
| Excel/PDF | PASS | 同一范围和分析结果生成 **23,190 字节 XLSX**（七张工作表）及 **31,737 字节 PDF**（`%PDF` 签名）。`tests/test_reporting.py` 检查章节、KPI 一致、完整异常列表、长范围分页及单一渲染器失败隔离。此为结构与内容验证；全套视觉样例检查仍列为 NOT TESTED。 |
| AI 关闭 | PASS | `MOI_AI_ENABLED=false`、无密钥，且传入若被调用就抛错的 provider；得到 `fallback_disabled`，包含两项观察和三项限制。模拟失败/虚假声明测试见 `tests/test_management_summary.py`；无真实 API 调用。 |
| 损坏上传 | PASS | 损坏 `.xlsx` 被 `rejected`，返回 `DATA.E-PACKAGE`；不完整 CSV 批次被 `rejected`，返回 13 项错误。两次尝试均未改变有效批次 ID。见 `tests/data/test_ingestion.py` 与 `tests/test_application_service.py`。 |

## PRD 每项 MUST 功能及验收子条款

以下路径均相对仓库根目录。即使某功能为 FAIL，其部分子条款仍可能为 PASS。

| ID | 状态 | 证据或缺口 |
| --- | --- | --- |
| F01 行为 | FAIL | `ui/app.py:_upload_controls` 以固定控件分配数据集，一次按钮即激活；没有汇总所选文件名、大小及检测到的数据域的批次预览，也无独立暂存批次状态。Streamlit 上传控件可能显示单个文件名/大小，但不是批次预览。 |
| F01-AC1 | PASS | `test_valid_csv_and_excel_batches`、`test_equivalent_excel_workbook_is_noop_after_csv_insert`。 |
| F01-AC2 | NOT TESTED | 已测缺失、损坏、超限等情况，但草案要求**每一种**不支持或不完整输入；无包括密码保护在内的穷尽矩阵。 |
| F01-AC3 | PASS | 仅按下激活按钮后 `_upload_controls` 才调用服务；拒收后保留原批次已有测试。 |
| F02 行为 | PASS | `data/readers.py`、`domain/validation.py`、`ui/app.py:_feedback`；校验与 UI 测试覆盖问题字段和计数。 |
| F02-AC1 | NOT TESTED | 已测试大量字段/关系规则，但缺少覆盖数据契约**每条**规则的可追溯样例矩阵。 |
| F02-AC2 | PASS | `test_mixed_valid_invalid_rows_remain_visible_without_partial_acceptance`、`test_rejected_upload_keeps_previous_active_batch`。 |
| F02-AC3 | PASS | `test_field_errors_identify_dataset_row_field_and_severity`；UI 表含文件、工作表、行、字段、规则和原因。 |
| F03 行为 | PASS | `services/ingestion.py` 和规范化问题对象保留原值/规范值；不修改业务数值含义。 |
| F03-AC1 | PASS | `test_excel_typed_dates_and_numeric_quantities_normalize_losslessly`、`test_header_alias_and_literal_identifier_are_preserved`。 |
| F03-AC2 | PASS | `tests/data/test_ingestion.py` 拒绝歧义日期、数值 ID、公式与小数计数。 |
| F03-AC3 | PASS | `test_normalized_duplicate_reports_both_rows`；`_validation_table` 保留来源字段。 |
| F04 行为 | PASS | SQLite 有效批次事务性替换；见 `tests/data/test_repository.py`。 |
| F04-AC1 | PASS | `test_insert_reopen_exact_round_trip_and_relationships`。 |
| F04-AC2 | PASS | `test_rejected_batch_and_failed_write_preserve_previous_active_data`。 |
| F04-AC3 | PASS | `test_equivalent_reimport_is_noop_and_changed_batch_replaces`。 |
| F05 行为 | FAIL | 引擎实现后续候选 KPI 集，但原 PRD 的 K01–K07 包含总产量、合格产量及非计划停机率；这些指定名称并未全部按原要求展示。业务口径亦未批准。 |
| F05-AC1 | PASS | `tests/test_kpi.py` 以手算精确断言验证已实现候选公式；**不**表示 BA-01–BA-05 获批。 |
| F05-AC2 | PASS | `tests/test_kpi.py` 覆盖零分母、空范围和 N/A。 |
| F05-AC3 | PASS | `test_inventory_as_of_carry_forward_and_partial_coverage`；每种材料仅取最近合格快照，不累加每日余额。 |
| F06 行为 | FAIL | 当前实现五条后续规则；原 PRD 的 R01–R04 规则版本/来源展示尚未与新规则目录对齐。异常结果有来源引用，仪表盘异常表未显示。 |
| F06-AC1 | PASS | `test_each_rule_triggers_with_exact_evidence`、`test_exact_threshold_does_not_trigger`。 |
| F06-AC2 | PASS | `domain/anomalies.py:Anomaly` 包含规则、对象、数值、说明和 `source_refs`；异常测试核查证据。 |
| F06-AC3 | PASS | `test_zero_plan_and_zero_output_skip_undefined_ratios`、`test_missing_as_of_inventory_is_skipped_and_partial`。 |
| F07 行为 | FAIL | 总览展示当前六张候选指标卡、趋势及告警，但未完整展示原 K01–K05/K07 指标卡，也缺少草案要求的明确数据覆盖信息。共用 UI 亦无班次筛选。 |
| F07-AC1 | PASS | 卡片和序列由 `get_overview_metrics` 提供；五区域 UI 测试及 `test_product_filter_and_chart_series_share_the_kpi_population`。 |
| F07-AC2 | FAIL | 批次 ID 及日期/产线/产品筛选可见，但 `ui/app.py` 缺少 PRD 要求的班次筛选。 |
| F07-AC3 | PASS | `ui/app.py` 提供空态及库存范围说明；`test_dashboard_empty_state`。 |
| F08 行为 | FAIL | 生产页有趋势、产线及停机图，但缺少指定的 K01–K03/K05 展示、班次控件和 R01/R03 记录行/来源引用。 |
| F08-AC1 | FAIL | `ui/app.py` 没有生产明细表，因此图表无法与要求显示的明细行核对。 |
| F08-AC2 | NOT TESTED | 引擎允许达成率超过 100%，但无 UI 断言或视觉证据证明卡片/图表显示不截断。 |
| F08-AC3 | PASS | `_metric` 以 N/A 标记不可用；`_production_trend` 标记空范围；KPI 零/空测试。 |
| F09 行为 | FAIL | 质量页有良率/废品率卡片及每日良品/废品图，但无产线对比、班次控件、R02 记录/来源引用或单独的产出总量。 |
| F09-AC1 | PASS | 共用序列与 KPI 引擎使用相同连接数据；`test_normal_metrics_and_lineage`、`test_documented_yield_and_scrap_example`。 |
| F09-AC2 | PASS | `test_documented_yield_and_scrap_example` 及不同日量样例验证汇总后求比。 |
| F09-AC3 | PASS | `test_zero_output_distinguishes_rates_and_additive_metrics`、`test_positive_output_can_have_zero_good_or_zero_scrap`。 |
| F10 行为 | FAIL | 库存页有截至日期的材料表及覆盖信息，但没有草案规定的库存页专用材料选择器。 |
| F10-AC1 | PASS | `test_inventory_as_of_carry_forward_and_partial_coverage`。 |
| F10-AC2 | PASS | 上述测试及 `test_inventory_boundary_zero_and_empty_material_selection`；表中标示日期与覆盖信息。 |
| F10-AC3 | FAIL | 已标示产线/产品筛选不影响库存，但缺少要求的本地材料筛选。 |
| F11 行为 | FAIL | 七工作表及确定性摘要已实现，但草案要求重新生成报告时纳入**当前可选摘要**；`export_management_reports` 只接收范围，始终生成自己的确定性摘要。 |
| F11-AC1 | PASS | `test_management_files_and_sections_match_analytics`。 |
| F11-AC2 | PASS | OpenPyXL 可打开文件；`test_renderers_use_supplied_values_and_escape_source_formulas`。 |
| F11-AC3 | PASS | 无有效批次、空域标签、渲染失败与 UI 告警测试。 |
| F11-AC4 | PASS | 报告/摘要会话键包含批次、指纹、范围和规则版本；筛选变化失效测试。 |
| F12 行为 | FAIL | PDF 有管理章节和异常预览，但提供的是 KPI **定义版本**而非所要求的 KPI 定义；重新生成报告也不会加入独立 AI 草稿。 |
| F12-AC1 | PASS | `test_management_files_and_sections_match_analytics` 检查共同范围、数值和章节。 |
| F12-AC2 | NOT TESTED | 导出和长筛选分页测试通过，但 RC1 未完成长、空、满三类 PDF 的有记录视觉检查。 |
| F12-AC3 | PASS | `test_anomaly_detail_is_complete_in_excel_and_pdf_preview_is_labeled`；渲染器失败测试保留另一格式及原数据。 |

## PRD 横向 MUST 条款

| ID | 状态 | 证据或缺口 |
| --- | --- | --- |
| X01 — 离线四域 Excel/CSV 流程与无效批次隔离 | PASS | CSV/Excel 服务集成测试、报表测试及损坏上传实测。 |
| X02 — 独立计算、**全部**校验规则、事务、异常、筛选、导出 | NOT TESTED | 各类别均有专项测试，但没有支持“全部”一词的完整规则—样例矩阵。 |
| X03 — 来源追溯、非 AI 确定性、产物无凭据、合成数据 | PASS | KPI/异常结果来源引用，合成与重导入确定性测试，默认设置及 `.env.example` 为占位值，另见[安全审查](../quality/SECURITY_REVIEW.zh-CN.md)。无密钥结论仅限已审仓库产物。 |
| X04 — 安装、结构、定义、替换、限制、演示、无效输入和离线后备 | PASS | [README](../../README.zh-CN.md)、[数据契约](../data/DATA_CONTRACT.zh-CN.md)、[KPI 定义](../data/KPI_DEFINITIONS.zh-CN.md)、[异常规则](../data/ANOMALY_RULES.zh-CN.md)和上述实测。 |
| X05 — 中英文文档成对 | PASS | 产品、数据、架构、决策、质量及本 RC1 记录均有对应文档；不代表双语 UI 或报表。 |

## 每项工程验收标准

| ID | 状态 | 证据或缺口 |
| --- | --- | --- |
| AC-01 | PASS | 上述回环监听和 HTTP 200 启动实测。 |
| AC-02 | NOT TESTED | 已测试四域接收/拒收、诊断字段、稀疏和压缩文件防护；未运行密集工作簿样例，完整样例集证据不足。 |
| AC-03 | PASS | `tests/data/test_repository.py` 的重开、写入失败保留、孤儿记录及指纹篡改测试。 |
| AC-04 | PASS | `tests/test_kpi.py` 手算候选公式样例；订单完成率/排程遵守率在演示与 UI 测试中为 N/A。业务批准另论。 |
| AC-05 | PASS | `tests/test_anomalies.py` 的精确值、边界、跳过与并发异常样例。 |
| AC-06 | PASS | `tests/test_dashboard.py` 五区域、筛选、空态；源码检查 UI 仅调用服务，不自行计算 KPI。此项不消除 F07–F10 细项缺口。 |
| AC-07 | PASS | `tests/test_reporting.py` 同一结果、长范围分页、单一渲染器强制失败。 |
| AC-08 | PASS | AI 关闭实测与模拟 provider/虚假声明测试；无真实外部调用。 |
| AC-09 | PASS | 本轮 Ruff/pytest 结果；摄入、存储、KPI、异常及报表均有专项测试模块。 |
| AC-10 | PASS | README、明确标记的合成样例、`.env.example` 及[安全审查](../quality/SECURITY_REVIEW.zh-CN.md)。 |

## 业务验收决策

| ID | 状态 | 客户验收前所需 |
| --- | --- | --- |
| BA-01 | NOT TESTED | 批准总产量/良品达成率及跨产品件数可比性。 |
| BA-02 | NOT TESTED | 批准最终良品/废品处置口径。 |
| BA-03 | NOT TESTED | 批准生产槽位/时间、库存及覆盖口径。 |
| BA-04 | NOT TESTED | 批准其余异常阈值、边界与级别；先前逐槽绝对偏差选择不足以解决全部规则。 |
| BA-05 | NOT TESTED | 接受订单完成数/排程遵守率不可用，或批准新数据契约。 |
| BA-06 | NOT TESTED | 按日期协调章程与 PRD 的摄入、持久化、筛选及报表格式差异。 |
| BA-07 | NOT TESTED | 确定性能测试负载、硬件及计时边界。 |
| BA-08 | NOT TESTED | 决定可选 AI 的交付范围及人工复核标签。 |

## 发布阻碍及处理

1. **PRD 不一致：** F01、F05–F10、F11、F12 存在已观察到的详细行为差异。部分原草案细节可能被后续功能任务取代，但尚无经日期确认的 PRD 修订或负责人处置；不能默默豁免。
2. **证据缺口：** F01-AC2、F02-AC1、F08-AC2、F12-AC2、X02、AC-02 仍为 NOT TESTED。
3. **业务关口：** BA-01–BA-08 未决；合成演示不能称为客户验收。需记录获批口径、协调章程/PRD，然后重测受影响部分并更新本清单。

**RC1 决定：暂不交付验收。** 应用可以在上述限制下作为本地合成数据作品集 MVP 演示。本候选版任务未修改任何功能代码。
