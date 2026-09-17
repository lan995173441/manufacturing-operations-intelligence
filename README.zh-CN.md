# Manufacturing Operations Intelligence（制造运营智能分析）

本地运行的作品集级制造分析 MVP。它校验四类合成 Excel/CSV 数据，在 SQLite 中保存一批有效的规范化记录，计算有文档定义的 KPI 与规则异常，提供五个 Streamlit 区域，并导出 Excel/PDF 管理报告。可选 AI 草稿仅消费已计算事实；核心功能可离线运行。本项目不是生产 MES，也不是托管式多用户服务。

英文指南：[README.md](README.md)。

**发布状态：** RC1 核查记录见[发布清单](docs/release/RELEASE_CHECKLIST.zh-CN.md)和[变更日志](CHANGELOG.zh-CN.md)。RC1 **尚不能交付验收**：PRD 对上传及部分页面的详细条款仍有缺口，产品负责人业务决策 BA-01–BA-08 尚未完成。工程测试通过仅验证合成数据演示。

## 本地运行

需要 Python 3.12。在仓库根目录执行：

### macOS 一键启动

在 Finder 中双击 [start.command](start.command)。首次运行时，它会创建 `.venv` 并安装缺失依赖，随后打开 `http://127.0.0.1:8501` 并启动本地应用。使用期间请保持该 Terminal 窗口打开；在窗口中按 Control-C 可停止应用。若 macOS 首次阻止启动，请右键该文件，选择 **打开**，再确认。

如果 8501 端口已被占用，可在启动前设置 `MOI_PORT`。设置
`MOI_OPEN_BROWSER=false` 可以启动但不自动打开浏览器。

### 手动启动

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/streamlit run streamlit_app.py --server.address=127.0.0.1
```

默认数据库路径为 `var/manufacturing_operations_intelligence.db`。可通过 `MOI_DATABASE_PATH` 指定其他本地路径。应用读取进程环境变量，**不会**自动加载 `.env`。`.env.example` 列出支持的配置且不含凭据；真实密钥不得进入仓库。

仓库还在 `.streamlit/config.toml` 中将 Streamlit 地址固定为 `127.0.0.1`；启动时保留显式参数。单个工作簿或四个 CSV 的总量上限是 10,000,000 字节；Streamlit 对每个上传文件另设 10 MiB 上限，并关闭使用情况遥测及浏览器中的完整错误堆栈。本地演示没有用户认证，应始终仅监听回环地址。

## 三至五分钟演示

1. 打开本地 Streamlit 地址，选择 **Load synthetic demo data**。这会激活明确标识为合成数据的 90 天批次；替换现有批次需要确认。
2. 查看 Overview、Production、Quality、Inventory。调整日期、产线或产品；库存始终按所选结束日期取全站数据。设置停机阈值后可评估异常。
3. 在 Reports & Insights 查看异常，并点击 **Generate management reports** 下载 Excel/PDF。报表使用已计算结果。
4. 点击 **Generate management summary**。AI 关闭或缺少密钥时显示确定性离线摘要；可选 AI 草稿须显式请求并人工复核。
5. 要演示校验失败，可上传一套故意缺失必填值的合成四文件 CSV 或四工作表 Excel。错误列出数据集、行和字段；此前有效批次保持不变。

CSV 输入要求分别提供 `production_plan`、`production_actual`、`quality` 和 `inventory` 四个文件。Excel 输入要求一个 `.xlsx` 工作簿，恰有上述四个同名工作表。字段结构及允许的规范化见[数据契约](docs/data/DATA_CONTRACT.zh-CN.md)；当前演示假设见 [KPI 定义](docs/data/KPI_DEFINITIONS.zh-CN.md)和[异常规则](docs/data/ANOMALY_RULES.zh-CN.md)。由于缺少订单生命周期证据，Completed Orders 和 Schedule Adherence 仍不可用；AI 不会补造这些指标。

可选 AI 使用 OpenAI Responses 适配器。要启用，请在进程环境中设置 `MOI_AI_ENABLED=true`、`MOI_AI_API_KEY`，并可选设置 `MOI_AI_MODEL`（默认 `gpt-4.1-mini`）。不要把密钥写进文件或上传数据。API 失败时返回离线摘要。单元测试不会调用外部 API。

## 验证与审阅

```sh
.venv/bin/ruff check .
.venv/bin/pytest -v
```

[架构](ARCHITECTURE.zh-CN.md)、[PRD](docs/product/PRD.zh-CN.md)、[验收标准草案](docs/quality/ACCEPTANCE_CRITERIA.zh-CN.md)、[RC1 逐项证据](docs/release/RELEASE_CHECKLIST.zh-CN.md)、[安全审查](docs/quality/SECURITY_REVIEW.zh-CN.md)及 [QA 记录](docs/exec-plans/active/qa-review-remediation.zh-CN.md)区分已实现行为与未解决的产品负责人决策。工程测试通过不等于业务验收。仅使用合成/演示制造数据。不要把该 MVP 用于生产控制、合规判定或客户机密数据。
