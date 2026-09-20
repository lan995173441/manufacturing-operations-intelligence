# 公开作品集部署 — Streamlit Community Cloud

状态：仓库部署配置已就绪；尚未创建公开 URL。英文主文档：[STREAMLIT_COMMUNITY_CLOUD.md](STREAMLIT_COMMUNITY_CLOUD.md)。

## 平台

作品集演示使用 Streamlit Community Cloud。它与现有 Streamlit 入口匹配，不需要付费 AI 服务，并可通过 `requirements.txt` 安装运行依赖、通过 `runtime.txt` 请求 Python 3.12。

公开演示必须以只读展示模式运行。它会自动激活纳入版本控制的合成数据集，且不渲染文件上传控件。这能防止访客把自己的运营文件写入共享的演示进程。

## 部署步骤

1. 审核分支和仅含合成数据的内容后，创建公开 GitHub 仓库。推送选定发布分支和 `v1.0.0` 标签。不要推送 `.env`、本地 SQLite 文件、生成报告或私有数据。
2. 在 Streamlit Community Cloud 中，从该仓库和选定分支创建新应用。
3. 将入口设置为 `streamlit_app.py`。Community Cloud 安装 `requirements.txt`；`runtime.txt` 请求 Python 3.12。
4. 在应用高级设置中添加以下根级环境值。这些是配置值而不是密钥；不要添加 AI 密钥。

   ```toml
   MOI_ENVIRONMENT = "public-demo"
   MOI_DATABASE_PATH = "/tmp/manufacturing-operations-intelligence-demo.sqlite3"
   MOI_AI_ENABLED = "false"
   MOI_PUBLIC_DEMO = "true"
   ```

5. 部署并等待应用健康，然后执行下方冒烟测试。全部通过后，才将公开 URL 记录到 README。

## 所需环境变量

| 变量 | 公开演示值 | 用途 |
| --- | --- | --- |
| `MOI_ENVIRONMENT` | `public-demo` | 标识部署环境。 |
| `MOI_DATABASE_PATH` | `/tmp/manufacturing-operations-intelligence-demo.sqlite3` | 对仅含合成记录的数据使用临时可写存储。 |
| `MOI_AI_ENABLED` | `false` | 禁用所有 AI 提供商；不需要 API 密钥。 |
| `MOI_PUBLIC_DEMO` | `true` | 空数据时加载内置合成批次，并禁用上传。 |

不要设置 `MOI_AI_API_KEY`。即使意外配置了密钥，`MOI_AI_ENABLED=false` 也会阻止 AI 使用，但仍必须从托管设置中删除该密钥。

## 冒烟测试清单

发布后，请在干净浏览器会话中执行以下检查：

| 检查项 | 公开演示的预期结果 | 尚无 URL 时的状态 |
| --- | --- | --- |
| 公开 URL | 应用加载且不显示异常堆栈。 | 无法外部测试 |
| Overview | 显示六个 KPI 卡片、生产趋势和合成数据异常。 | 已本地验证 |
| Production | 显示计划与实际趋势、产线图表和筛选。 | 已本地验证 |
| Quality | 显示良品率、废品率、趋势和异常。 | 已本地验证 |
| Inventory | 显示截至所选日期的库存风险和物料筛选。 | 已本地验证 |
| 筛选 | 日期、产线、班次、产品和适用物料筛选更新可见分析。 | 已本地验证 |
| 样例数据 | 仪表盘自动填充，无需上传。 | 已本地验证 |
| Excel 导出 | Reports & Insights 下载非空 `.xlsx` 文件。 | 已本地验证 |
| PDF 导出 | Reports & Insights 下载非空 `.pdf` 文件。 | 已本地验证 |
| 无 AI 密钥 | 管理摘要明确显示为确定性离线回退。 | 已本地验证 |
| 上传隔离 | 公开演示模式不显示文件上传控件。 | 已本地验证 |

执行外部冒烟测试时，记录浏览器、部署提交、URL、日期和任何不支持的下载行为。

## 托管限制

- `/tmp` 存储是临时的。平台重启会清除 SQLite 文件；应用会在下次启动时重新加载同一份确定性合成数据。
- 公开演示按设计不需要认证。公开演示模式删除上传功能，但仍不适用于真实、机密或受监管数据。
- Excel 和 PDF 在内存中生成。预期可在支持的浏览器中下载，但仍需在发布后检查实际托管平台和浏览器组合。
- Streamlit Community Cloud 的冷启动时间和资源限制由平台管理。内置样例数据约 232 KB；不作生产性能保证。
- 公开演示刻意禁用 AI。确定性离线管理摘要仍可用，权威计算仍然是确定性的。
- 此配置不提供自定义域名、运行监控、备份、用户账户或生产服务保证。

## 仓库保护措施

`.gitignore` 排除 `.env`、Streamlit secrets、密钥文件、本地数据库、日志、报告、上传目录及私有/客户/原始数据。纳入版本控制的样例 CSV 为确定性合成记录。部署包不包含 `.env`、数据库或任何 API 凭据。
