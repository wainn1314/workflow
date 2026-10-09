# AI 工作流项目集（AI Workflow Portfolio）

> 本仓库是一个 **AI 工作流项目集（Portfolio）**：8 个**可独立运行 / 可导入 Dify** 的 AI 工作流，
> 覆盖 **AI 应用评测、竞品情报、需求→PRD、用户反馈洞察、AI 产品化验证、商品数据洞察、Prompt 工程、技术选型决策** 等典型 AI 产品经理场景。
>
> 交付形态横跨三类：**Dify Workflow / Chatflow DSL**、**自研 Web 服务（FastAPI / Node.js）**、**Dify 插件**，
> 既有「业务可导入即用」的工作流，也有「可单测、可校验、可打包」的工程化配套。

---

## 一、项目一览

| # | 目录 | 场景 | 交付形态 | 关键实现 |
| --- | --- | --- | --- | --- |
| 1 | [`Batch testing/`](./Batch%20testing/) | **AI 应用批量评测流水线** | 自研 Web 服务（FastAPI + SQLite） | LLM-as-Judge 五维评分与加权总分、多路由 LLM 客户端（OpenAI 兼容 / Dify 自适应）、asyncio 并发调度与断点续跑、BadCase 管理、趋势看板（原生 JS + Chart.js，零构建） |
| 2 | [`Competitive Intelligence/`](./Competitive%20Intelligence/) | **竞品动态自动监控** | Dify Workflow + DSL-as-Code 工具链 | 25 节点 / 28 边工作流；`validate_yml.py` 结构断言、`smoke_v2.py` 节点级单测、`simulate_workflow.py` 端到端联调、版本链 `v1→v2→v3→当前运行版` 全程可追溯 |
| 3 | [`Convert requirement to PRD/`](./Convert%20requirement%20to%20PRD/) | **需求自动生成 PRD** | Dify Workflow + Node.js 前端 + 自研 Dify 插件 | 8 节点工作流 + 9 章结构化 PRD 模板；Express 后端做 Dify SSE 流式代理与一键下载；自研 `text-to-file` 插件把文本落成文件 |
| 4 | [`feedback_insight/`](./feedback_insight/) | **用户反馈需求洞察** | 纯 Dify Workflow（DSL） | 聚类 → JSON 校验 → KANO 分类 → 优先级排序；v2 引入「当前季度业务约束」参与排序 |
| 5 | [`Four-Level Validation of AI Products/`](./Four-Level%20Validation%20of%20AI%20Products/) | **AI 产品化四层验证** | Dify Workflow（6 节点串行） | 附 `.ref/` 参考源码快照（Dify DSL 服务、工作流模型、前端 DSL 字段实现），用于核对 DSL 字段兼容性 |
| 6 | [`Product Analysis and Suggestions/`](./Product%20Analysis%20and%20Suggestions/) | **商品数据关联洞察与策略建议** | 纯 Dify Workflow（单一 DSL） | 8 节点：文件解析 → 数据清洗(Code) → 销售分析(LLM) → Apriori 式关联规则(Code) → 归因(LLM) → 策略建议(LLM)，计算内嵌 Code 节点保证数值可复现 |
| 7 | [`prompt auto-generate/`](./prompt%20auto-generate/) | **竞品 Prompt 自动生成** | Dify Chatflow + 前端 + 语料库 | 31 节点 / 44 边 Chatflow；DSL 生成脚本 `_update_dify_yml.py`；内置 CO-STAR / CRISPE / LangGPT / ReAct 等 Prompt 框架模板语料 |
| 8 | [`Technology Selection Decision Tree/`](./Technology%20Selection%20Decision%20Tree/) | **大模型驱动技术选型决策树** | 自研 Web 服务（FastAPI + DeepSeek） | 业务约束 → 结构化 `SelectionReport`（推荐方案 / 理由 / 优劣势 / 备选方案），含非法 JSON 纠错重试 |

---

## 二、三类交付形态

| 形态 | 对应项目 | 目录特征 |
| --- | --- | --- |
| **Dify DSL 为主** | 2、4、5、6、7 | 核心资产是 `*.yml`（Dify 导出文件），通常单目录平铺，配套验证/仿真脚本或模板语料 |
| **自研 Web 服务** | 1、8 | 标准工程目录：`app/`（后端包）+ `static/`（前端）+ 启动脚本 + 依赖清单 |
| **混合形态** | 3 | 一个业务目录下并列 `DSL + Node 前端 + Dify 插件` 三个独立子工程 |

> **顶层无统一构建系统**：这是一个项目集仓库，每个子目录都可**独立运行 / 独立导入**，
> 没有根级 `package.json` / `requirements.txt`，依赖与启动方式各自维护在子目录内。

---

## 三、快速开始

### 1）自研 Web 服务

```bash
# 项目 1：AI 应用批量评测流水线
cd "Batch testing"
pip install -r requirements.txt
python run.py                 # 或 uvicorn app.main:app
# 浏览器打开 http://127.0.0.1:8000

# 项目 8：技术选型决策树
cd "Technology Selection Decision Tree"
pip install -r app/requirements.txt
cp app/.env.example app/.env  # 填入 LLM_API_KEY（DeepSeek）
uvicorn app.main:app --reload
```

### 2）Node.js 前端（项目 3）

```bash
cd "Convert requirement to PRD/prd-workflow-app"
npm install
cp .env.example .env          # 填入 DIFY_API_KEY / DIFY_BASE_URL
npm start                     # 打开 http://localhost:3000
```

### 3）Dify 工作流 / 插件

```text
- 工作流：在 Dify 中「导入 DSL 文件」，选择对应目录下的 *.yml 即可运行；
  在 Dify 的「环境变量」中补齐工作流引用的 Key（如 JSONBIN_API_KEY）。
- 插件（text-to-file-plugin）：pip install dify-plugin-cli
  → dify plugin package ./text-to-file-plugin → 在 Dify 中安装生成的 .difypkg。
```

---

## 四、安全与密钥

- 仓库内**不包含任何真实密钥**：所有 `.env` 均被根级 [`.gitignore`](./.gitignore) 忽略，仅保留 `.env.example` 模板；
- 各项目需要配置的环境变量：

| 项目 | 配置文件 | 变量 |
| --- | --- | --- |
| `Batch testing/` | 代码内配置 / 界面填写 | LLM / Dify 路由参数 |
| `Convert requirement to PRD/prd-workflow-app/` | `.env` | `DIFY_API_KEY`、`DIFY_BASE_URL`、`DIFY_USER`、`PORT` |
| `Technology Selection Decision Tree/app/` | `.env` | `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` |
| `Competitive Intelligence/` 工作流 | Dify 环境变量 | `JSONBIN_API_KEY` |

- `.gitignore` 同时排除了：`node_modules/`、`__pycache__/`、`*.db`（含 WAL 附属文件）等依赖与运行时数据，
  以及 `_tree.json` / `_dify_tree.json` / `_tool_py.txt` 等调研期抓取的中间产物。

> ⚠️ 若你 fork / 二次使用本仓库，请**先轮换自己的密钥**，不要复用仓库历史中的任何凭证。

---

## 五、相关文档

| 文档 | 内容 |
| --- | --- |
| [`AI工作流目录结构说明.md`](./AI工作流目录结构说明.md) | 逐个工作流讲解目录栈：每个目录/文件是什么、放在哪、起什么作用、如何启动 |
| [`AI工作流项目集-简历文档.md`](./AI工作流项目集-简历文档.md) | 项目集的业务目标、链路设计与成果点（简历 / 面试素材） |
| [`AIPM面试-工作流讲解手册.md`](./AIPM面试-工作流讲解手册.md) | AI 产品经理面试口径的工作流讲解手册 |
