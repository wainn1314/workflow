# AI 工作流项目集 · 各工作流目录栈说明

> 本文档逐条讲解本仓库（`d:\ai_workflow`）中 **8 个工作流** 的目录栈（目录树 / 文件组织结构），
> 说明每个目录、每个文件「是什么、放在哪、起什么作用」，并给出运行入口。
> 所有目录与文件均来自仓库实际内容，行数、节点数等为实测值。

---

## 一、文档约定

本文中的目录树使用如下记法：

- `xxx/`：目录；
- `xxx`：文件；
- 行尾 `# 说明`：该目录/文件的作用（非文件内容）；
- 括号中的行数 / 节点数为实测统计值，用于判断文件体量。

目录栈按「工作流的**交付形态**」分成三类，便于理解为什么目录结构差异很大：

| 形态 | 工作流 | 目录栈特征 |
| --- | --- | --- |
| **Dify 工作流（DSL 为主）** | 竞品动态监控、需求 PRD、用户反馈洞察、四层验证、商品分析、竞品 Prompt | 核心资产是 `*.yml`（Dify DSL 导出文件），通常**单目录平铺**，配套工程脚本或模板语料 |
| **自研 Web 服务** | 批量评测、技术选型决策树 | 标准工程目录：`app/`（后端包）+ `static/`（前端）+ 启动脚本 + 依赖清单 |
| **混合形态（DSL + 自研前后端 + 插件）** | 需求 PRD（DSL + Node 前端 + Dify 插件三件套） | 一个业务目录下并列多个子工程 |

---

## 二、仓库顶层目录栈

```
d:\ai_workflow\
├── AI工作流项目集-简历文档.md              # 简历素材文档（业务目标 / 链路 / 成果点）
├── AI工作流目录结构说明.md                 # 本文档：各工作流目录栈说明
├── Batch testing/                          # 工作流 1：AI 应用批量评测流水线（自研 FastAPI + SQLite）
├── Competitive Intelligence/               # 工作流 2：竞品动态自动监控（Dify Workflow + 工程工具链）
├── Convert requirement to PRD/             # 工作流 3：需求 PRD 自动生成（Dify Workflow + Node 前端 + 自研插件）
├── feedback_insight/                       # 工作流 4：用户反馈需求洞察（Dify Workflow）
├── Four-Level Validation of AI Products/   # 工作流 5：AI 产品化四层验证（Dify Workflow + Dify 源码参考）
├── Product Analysis and Suggestions/       # 工作流 6：商品数据关联洞察与策略建议（Dify Workflow）
├── prompt auto-generate/                   # 工作流 7：竞品 Prompt 自动生成（Dify Chatflow + 前端 + 模板语料）
└── Technology Selection Decision Tree/     # 工作流 8：大模型驱动技术选型决策树（自研 FastAPI + DeepSeek）
```

**顶层无统一构建系统**：这是一个「项目集（Portfolio）」仓库，每个子目录都是**可独立运行/导入**的项目，
没有根级 `package.json` / `requirements.txt`，依赖与启动方式各自维护在子目录内。

---

## 三、通用文件类型约定

在各工作流目录中反复出现的文件，先集中解释一次：

| 文件 / 后缀 | 含义 | 典型内容 |
| --- | --- | --- |
| `*.yml` | **Dify DSL 导出文件**（工作流/应用定义） | `app` 元信息 + `dependencies` + `graph.nodes`（节点）+ `graph.edges`（连线） |
| `*.yml.bak` | 工作流迭代前的**备份** | 上一个可用版本的完整 DSL |
| `*.difypkg` | Dify **插件安装包**（本仓库内为待打包源码，非产物） | manifest + provider + tools |
| `.env` / `.env.example` | 环境配置（密钥 / Base URL / 端口） | `LLM_API_KEY`、`DIFY_API_KEY` 等 |
| `README.md` | 该子工程的**使用说明** | 目录结构、快速开始、配置说明、接口说明 |
| `requirements.txt` / `package.json` | 依赖清单 | Python / Node 依赖与启动脚本 |
| `*.db` / `*.db-wal` / `*.db-shm` | SQLite 数据库及其 WAL 附属文件 | 运行时数据（评测记录 / PRD 历史） |
| `test_*.py`、`*_test.js`、`smoke*.py`、`e2e-*.js` | 测试脚本 | 单元 / 冒烟 / 端到端测试 |

> ⚠️ 安全提示：`Convert requirement to PRD/prd-workflow-app/.env` 与
> `Technology Selection Decision Tree/app/.env` 中保存了**真实可用密钥**。若要把仓库公开或提交到远端，
> 请先轮换密钥并确保 `.env` 被 `.gitignore` 忽略（仅提交 `.env.example`）。

---

## 四、工作流 1：AI 应用批量评测流水线（`Batch testing/`）

**形态**：自研 Web 平台（FastAPI + SQLite + 原生 JS/Chart.js）
**目录栈特征**：标准 Python 包工程，`app/` 承担全部后端逻辑，`app/static/` 为无构建前端，数据与测试集独立成目录。

```
Batch testing/
├── app/                                    # 后端应用包（FastAPI）
│   ├── __init__.py                         # 包标记（空文件，1 行）
│   ├── config.py                           # 评分维度/权重/通过阈值/BadCase 规则等常量（21 行）
│   ├── schemas.py                          # Pydantic 请求模型（人工复核请求，9 行）
│   ├── db.py                               # SQLite 持久化层：runs/test_cases/results/logs（216 行）
│   ├── parser.py                           # CSV/Excel 测试集解析与 conversation 解析（83 行）
│   ├── llm_client.py                       # 统一 LLM 客户端：OpenAI 兼容 + Dify 三路由自适应（810 行，最核心）
│   ├── judge.py                            # LLM-as-Judge 五维评分与加权总分（133 行）
│   ├── evaluator.py                        # 评测编排：asyncio 并发调度、重试、断点续跑（168 行）
│   ├── report.py                           # 汇总统计 + CSV 导出（158 行）
│   ├── main.py                             # FastAPI 路由层（183 行）
│   └── static/                             # 前端（原生 JS + Chart.js，零构建）
│       ├── index.html                      # 单页五页签：运行/日志/报告/BadCase/趋势（131 行）
│       ├── style.css                       # 样式（109 行）
│       ├── app.js                          # 前端交互逻辑（436 行）
│       ├── sample_testset.csv              # 可下载的示例测试集（19 行）
│       └── vendor/
│           └── chart.umd.min.js            # Chart.js 本地化（离线可用）
├── data/                                   # 运行时数据目录
│   ├── eval.db                             # SQLite 主库（评测记录）
│   └── exports/                            # 导出的 CSV 报告
├── testsets/                               # 真实测试集
│   └── workflow-quiz-generate-测试集.csv    # 15 条用例，评测自研「知识库出题」Chatflow（16 行）
├── run.py                                  # 启动入口：python run.py（4 行）
├── generate_sample.py                      # 示例测试集生成器（120 行）
├── requirements.txt                        # 依赖：fastapi/uvicorn/httpx/openpyxl/python-multipart/pydantic
└── README.md                               # 使用说明：目录结构、测试集格式、Dify 变量映射、评分规则（122 行）
```

**分层逻辑**：`config`（规则）→ `parser`（输入）→ `llm_client`（调用）→ `judge`（评分）→ `evaluator`（编排）→
`report`（汇总）→ `db`（落库）→ `main`（HTTP 接口）→ `static`（可视化），职责单一、依赖单向。

**启动**：`pip install -r requirements.txt` → `python run.py`（或 `uvicorn app.main:app`）→ 打开 `http://127.0.0.1:8000`。

---

## 五、工作流 2：竞品动态自动监控（`Competitive Intelligence/`）

**形态**：Dify Workflow（25 节点 / 28 边）+ **DSL as Code 工程工具链**
**目录栈特征**：核心是多个版本的 `.yml` DSL；同目录平铺一整套**验证/测试/仿真/探测脚本**，无子目录。

```
Competitive Intelligence/
├── competitor_monitor.yml                  # 早期版本 DSL（1293 行）
├── 竞品动态自动监控.yml                     # v1 DSL（1438 行）
├── 竞品动态自动监控.yml.bak                 # v1 备份（1337 行）
├── 竞品动态自动监控_v2.yml                  # v2 DSL：URL scheme 加固、webhook 校验升级（1444 行）
├── 竞品动态自动监控_v3.yml                  # v3 DSL（1444 行）
├── 当前运行版.yml                           # 线上实际运行版本（1481 行）
├── 最新版本.yml                             # 最新版本（1481 行）
│   ── 以上为「版本演进链」：v1 → v2 → v3 → 当前运行版，每次改动都有备份与记录 ──
├── analyze_yml.py                          # 输出节点级清单/差异，快速定位变更点（42 行）
├── compare_exports.py                      # 两份导出的全字段递归 diff，忽略坐标等布局噪声（40 行）
├── validate_yml.py                         # 结构断言校验：重复 id/悬空 edge/变量选择器/父子关系/代码可编译（151 行）
├── smoke_v2.py                             # 节点级单测：exec 内嵌 Code 节点代码后断言输入输出（87 行）
├── simulate_workflow.py                    # 端到端联调：真实页面 + 真实 JSONBin 跑「两日比对」场景（102 行）
├── modify_yml.py                           # 按实测 JSONBin 行为外科式修复 yml（单 Bin Map/UA/串行写/截断）（258 行）
├── make_v2.py                              # 生成 v2：scheme 错误加固（74 行）
├── probe_market.py                         # 竞品页面抓取可行性 / Dify 插件 manifest 探测（39 行）
├── test_jsonbin.py                         # JSONBin API 契约探测：create/read/update/header 容忍度（85 行）
├── test_jsonbin2.py                        # 第二轮：bin id 格式约束与响应体形状（67 行）
├── test_jsonbin3.py                        # 第三轮：账号/bin 体积限制与 24-hex bin 行为（56 行）
├── diff_report.txt                         # 版本差异记录（节点 id 清单 + unified diff，82 行）
└── dump.json                               # 该工作流 DSL 的 JSON 形态导出（1658 行）
```

**目录栈设计要点**：
1. **版本即文件**：每个迭代版本独立成 `.yml`，靠文件名区分，配 `.bak` 与 `diff_report.txt` 形成版本可追溯；
2. **测试与工作流同目录**：脚本直接读取同目录下 yml、`exec` 其内嵌代码，实现「DSL 可测试」；
3. **脚本按用途命名**：`analyze_*`（分析）/`validate_*`（校验）/`smoke_*`（单测）/`simulate_*`（仿真）/`probe_*`、`test_*`（探测），
   一眼可知脚本角色。

**运行**：需在 Dify 中导入对应 `.yml`；本目录脚本为本地工程工具（`python validate_yml.py <file.yml>` 等），不参与线上运行。

---

## 六、工作流 3：需求 PRD 自动生成（`Convert requirement to PRD/`）

**形态**：Dify Workflow（8 节点）+ 自研 Dify 插件 + Node.js 前端，**三件套并列在同一个业务目录下**
**目录栈特征**：一个业务目录内含 **3 个独立子工程**（DSL、Node 前端、Dify 插件）+ 2 份抓取产物。

```
Convert requirement to PRD/
├── 需求PRD自动生成工作流.yml               # 主工作流 DSL（587 行，8 节点）
├── prd模板 .md                             # 9 章 PRD 结构化模板（被工作流 Prompt 引用）（82 行）
│
├── prd-workflow-app/                       # 子工程 ①：Node.js Web 前端（对接 Dify API）
│   ├── server.js                           # Express 后端 + Dify SSE 流式代理 + 下载接口（212 行）
│   ├── db.js                               # SQLite 数据访问（node:sqlite，记录保存/查询）（74 行）
│   ├── package.json                        # 依赖：express/dotenv；engines.node >= 22.5.0
│   ├── package-lock.json                   # 依赖锁定（860 行，自动生成）
│   ├── .env                                # 运行配置（真实密钥，勿提交）
│   ├── .env.example                        # 配置模板：DIFY_API_KEY / DIFY_BASE_URL / PORT / DB_PATH
│   ├── .gitignore                          # 忽略 node_modules / .env / *.db
│   ├── prd.db (+ .db-shm / .db-wal)        # SQLite 库及 WAL 附属文件（运行时生成）
│   ├── smoke-test.js                       # 冒烟测试（46 行）
│   ├── e2e-test.js                         # 端到端测试：拉起真实服务走完整生成流程并断言落库（94 行）
│   ├── README.md                           # 使用说明：目录结构/配置/接口/输入字段（56 行）
│   └── public/                             # 前端静态资源
│       ├── index.html                      # 页面（80 行）
│       ├── style.css                       # 样式（169 行）
│       └── app.js                          # 交互逻辑：SSE 进度、PRD 预览、一键下载（376 行）
│
├── text-to-file-plugin/                    # 子工程 ②：自研 Dify 插件「文本转文件」
│   ├── manifest.yaml                       # 插件清单：provider_id = prd/text-to-file（29 行）
│   ├── main.py                             # 插件入口（4 行）
│   ├── pyproject.toml                      # 插件包元信息与依赖（9 行）
│   ├── README.md                           # 插件标识、打包安装、参数说明（27 行）
│   ├── _assets/
│   │   └── icon.svg                        # 插件图标
│   ├── provider/
│   │   ├── text_to_file.py                 # Provider 定义（6 行）
│   │   └── text_to_file.yaml               # Provider 配置（17 行）
│   └── tools/
│       ├── text_to_file.py                 # 工具实现：text(动态) + filename(配置) → files 输出（19 行）
│       └── text_to_file.yaml               # 工具参数声明（37 行）
│
├── _tree.json                              # 抓取的 dify-official-plugins 仓库文件树（73785 行，插件定位用）
├── _dify_tree.json                         # 抓取的 dify 主仓库文件树（134914 行，源码定位用）
└── _tool_py.txt                            # 插件工具源码的逐字节导出（十进制字节序列，15413 行，跨环境检索素材）
```

**目录栈设计要点**：
- **业务与工程分离**：`需求PRD自动生成工作流.yml` + `prd模板 .md` 是「业务资产」（可导入 Dify 直接跑）；
  `prd-workflow-app/` 与 `text-to-file-plugin/` 是「工程资产」（各自可独立构建/测试/打包）；
- **前缀 `_` 标记抓取产物**：`_tree.json` / `_dify_tree.json` / `_tool_py.txt` 均为调研期从 GitHub/API 抓取的中间产物，
  用下划线前缀与业务文件区分，可安全删除。

**启动**：
- 前端：`cd prd-workflow-app` → `npm install` → 确认 `.env` → `npm start` → `http://localhost:3000`；
- 插件：`pip install dify-plugin-cli` → `dify plugin package ./text-to-file-plugin` → 在 Dify 中安装 `.difypkg`。

---

## 七、工作流 4：用户反馈需求洞察（`feedback_insight/`）

**形态**：纯 Dify Workflow（DSL 为主）
**目录栈特征**：**最简目录栈**——只有一个目录、两个版本 DSL，无任何代码与脚本。

```
feedback_insight/
├── feedback_insight_workflow.yml           # v1 DSL：聚类 → JSON 校验 → KANO 分类 → 优先级（370 行）
└── 用户反馈需求洞察工作流.yml               # v2 DSL：加入「当前季度业务约束」参与排序（437 行）
```

**目录栈设计要点**：
- 该工作流逻辑全部内嵌在 DSL 的 Code / LLM 节点里，因此目录栈只有 `.yml`；
- 通过**中文名文件**保留「面向业务的版本」（`用户反馈需求洞察工作流.yml`），
  用**英文名文件**保留「早期版本」（`feedback_insight_workflow.yml`），同一目录双版本对照。

**运行**：在 Dify 中导入对应 `.yml` 应用后通过对话/API 调用。

---

## 八、工作流 5：AI 产品化四层验证（`Four-Level Validation of AI Products/`）

**形态**：Dify Workflow（6 节点串行 / 5 边）
**目录栈特征**：DSL 在根目录，附一个 **`.ref/` 参考源码快照目录**（. 前缀表示「非业务、参考资料」）。

```
Four-Level Validation of AI Products/
├── ai_product_four_level_validation.yml    # 主工作流 DSL（343 行，6 节点串行）
└── .ref/                                   # Dify 源码参考快照（调研 DSL 字段/节点实现时抓取）
    ├── ── 后端 Python（DSL 服务与工作流模型）──
    │   ├── app_dsl_service.py              # DSL 导入/导出服务（969 行）
    │   ├── workflow_service.py             # 工作流运行服务（1805 行）
    │   ├── workflow_model.py               # 工作流数据模型（1923 行）
    │   ├── workflow.py                     # 工作流核心逻辑（1752 行）
    │   ├── graphon_dsl_importer.py         # GraphOn DSL 导入器（752 行）
    │   ├── graphon_llm_entities.py         # LLM 实体定义（84 行）
    │   ├── workflow_app_config_manager.py  # 应用配置管理（52 行）
    │   ├── workflow_init.py                # 工作流初始化（346 行）
    │   ├── app_import.py                   # 应用导入（193 行）
    │   └── dsl_entities.py                 # DSL 实体（29 行）
    ├── ── Python 单元测试（参考写法）──
    │   ├── test_app_dsl_service.py         # DSL 服务测试（512 行）
    │   └── test_workflow_restore.py        # 工作流还原测试（68 行）
    ├── ── 前端 TypeScript / TSX（DSL 字段实现）──
    │   ├── wf_index.tsx / wf_workflow_page.tsx / workflow_app_index.tsx
    │   ├── web_use_workflow.ts / use-config.ts / use-nodes-sync-draft.ts
    │   ├── workflow_types.ts / types.ts / workflow_app_utils.ts / workflow_utils_index.ts
    │   ├── llm_default.ts / llm_types.ts / llm_node.tsx
    │   ├── start_default.ts / start_types.ts / end_default.ts / end_types.ts
    │   ├── wf_constants.ts / utils.ts
    ├── graphon_changelog.md                # GraphOn 变更日志（45 行）
    └── pyproject.toml                      # 参考项目的依赖清单（304 行）
```

**目录栈设计要点**：
- `.ref/` 用**点前缀**命名，约定为「参考/临时」目录，与业务文件 `ai_product_four_level_validation.yml` 明确隔离；
- `.ref/` 内部按**技术分层**组织：后端 `*.py`、前端 `*.ts/*.tsx`、测试 `test_*.py`、文档 `*.md`、依赖 `pyproject.toml`，
  便于在编写 DSL 的 Code 节点或排查字段兼容性时快速查阅官方实现。

**运行**：在 Dify 中导入 `ai_product_four_level_validation.yml` 应用后调用（`.ref/` 不参与运行）。

---

## 九、工作流 6：商品数据关联洞察与策略建议（`Product Analysis and Suggestions/`）

**形态**：纯 Dify Workflow（8 节点 / 7 边）
**目录栈特征**：**单文件目录栈**——整个工作流（含两个内嵌 Python Code 节点）只交付一个 `.yml`。

```
Product Analysis and Suggestions/
└── dify_商品数据关联洞察与策略建议工作流.yml   # 完整工作流 DSL（727 行，8 节点）
                                              #   Start(文件) → 文档提取 → 数据清洗(Code)
                                              #   → 销售分析(LLM) → 关联规则(Code)
                                              #   → 归因(LLM) → 策略建议(LLM) → End
```

**目录栈设计要点**：
- **文件名带 `dify_` 前缀**：显式标注该文件为 Dify DSL，避免与同目录其他产物混淆；
- **精确计算内嵌为 Code 节点**：表头校验、多格式解析、数值清洗、价格带归一、Apriori 式关联规则挖掘
  全部封装在工作流代码节点内，因此无需额外 `.py` 文件即可保证「数值可复现」；
- 该目录体现了「**单一交付物**」的最简工作流组织方式：一个 DSL 就是一个完整业务能力。

**运行**：在 Dify 中导入该 `.yml`，在对话页面上传商品 CSV/XLSX/Markdown 表格即可得到策略报告。

---

## 十、工作流 7：竞品 Prompt 自动生成（`prompt auto-generate/`）

**形态**：Dify Chatflow（31 节点 / 44 边）+ 自研前端 + 模板语料库
**目录栈特征**：DSL + **DSL 生成脚本** + 前端单文件 + **RAG 语料目录**，四类资产平铺。

```
prompt auto-generate/
├── 竞品Prompt自动生成流.yml                  # 主 Chatflow DSL（1929 行，31 节点 / 44 边）
├── _update_dify_yml.py                     # DSL 脚本化生成器：节点/边构造函数式生成 + 校验（921 行）
├── index.html                              # 自研前端：原生 JS 直连 Dify SSE（394 行）
└── prompt_template/                        # Prompt 框架模板语料（Dify 知识库的语料来源）
    ├── 元提示词模板（让AI帮你写Prompt）.md       # G1：元提示词（41 行）
    ├── LangGPT 框架通用模板.md                 # G2：LangGPT 结构化角色框架（54 行）
    ├── CRISPE 框架通用模板.md                  # G3：CRISPE 框架（33 行）
    ├── CO-STAR 框架通用模板.md                 # G4：CO-STAR 框架（34 行）
    └── Agent 工作流模板（ReAct模式）.md         # G5：ReAct Agent 工作流模板（52 行）
```

**目录栈设计要点**：
- `prompt_template/` 是 **RAG 知识库的本地语料源**：知识库在 Dify 内按 G1–G5（垂直业务模板 T1–T6 另有分片）切分，
  本目录保留原始 Markdown 以便人工校对与重新上传；
- `_update_dify_yml.py` 用下划线前缀标记为「生成工具」，把 1929 行的 Chatflow 从「手工编辑」变成「改代码 → 重新生成」；
- `index.html` 是**单文件前端**（样式与脚本内联），零构建、零依赖，直接双击或静态托管即可用。

**运行**：
- 工作流：在 Dify 中导入 `竞品Prompt自动生成流.yml`（含知识库依赖）；
- 前端：直接用浏览器打开 `index.html`（需在页面中填写 Dify Base URL / API Key / 匿名 user 标识）。

---

## 十一、工作流 8：大模型驱动的技术选型决策树（`Technology Selection Decision Tree/`）

**形态**：自研 Web 服务（FastAPI + DeepSeek，单接口最小可用）
**目录栈特征**：**双层结构** `app/`（代码与配置） + `app/static/`（前端），是工作流 1 的精简版组织方式。

```
Technology Selection Decision Tree/
└── app/
    ├── main.py                             # FastAPI 入口：GET / 页面、GET /health、POST /analyze（55 行）
    ├── models.py                           # Pydantic 模型：BusinessConstraints / SelectionReport（43 行）
    ├── workflow.py                         # 工作流：Prompt 构造 → DeepSeek 调用 → 三层 JSON 容错（144 行）
    ├── requirements.txt                    # 依赖：fastapi/uvicorn[standard]/openai/pydantic/python-dotenv
    ├── .env                                # LLM_API_KEY / LLM_BASE_URL / LLM_MODEL（真实密钥，勿提交）
    ├── .gitignore                          # 忽略 .env / __pycache__ 等
    └── static/
        ├── index.html                      # 页面：示例 chips、字符计数、Ctrl+Enter 提交（68 行）
        ├── styles.css                      # 样式（345 行）
        └── app.js                          # 交互逻辑：调用 /analyze、渲染报告、复制 Markdown、健康徽标（331 行）
```

**目录栈设计要点**：
- **扁平三层**：`main`（HTTP 层）/ `models`（数据契约）/ `workflow`（业务+模型调用），无额外抽象层；
- **兼容双启动路径**：`main.py` / `workflow.py` 用 `try: from .models ... except ImportError: from models ...`
  同时支持 `uvicorn app.main:app`（项目根启动）与 `uvicorn main:app`（app 目录启动）；
- **`.env` 定位与启动目录解耦**：`workflow.py` 用 `Path(__file__).resolve().with_name(".env")` 加载配置，
  保证从任意目录启动都能读到密钥；
- `.env` 已列入 `.gitignore`，仓库同时以 `requirements.txt` 固化依赖。

**运行**：`cd "Technology Selection Decision Tree/app"` → `pip install -r requirements.txt` →
确认 `.env` → `uvicorn main:app --reload` → 打开 `http://127.0.0.1:8000`。

---

## 十二、各工作流目录栈速查表

| # | 工作流目录 | 目录层级深度 | 核心文件 | 附属产物 | 交付形态 |
| --- | --- | --- | --- | --- | --- |
| 1 | `Batch testing/` | 4 层（`app/static/vendor/`） | `app/llm_client.py`、`app/evaluator.py` | `data/eval.db`、`testsets/*.csv` | 自研 Web 平台 |
| 2 | `Competitive Intelligence/` | 1 层（全平铺） | `当前运行版.yml`、`最新版本.yml` | 6 个版本 yml + 11 个工程脚本 + `diff_report.txt` + `dump.json` | Dify DSL + 工具链 |
| 3 | `Convert requirement to PRD/` | 4 层（含两个子工程） | `需求PRD自动生成工作流.yml` | `prd-workflow-app/`、`text-to-file-plugin/` | DSL + Node 前端 + 插件 |
| 4 | `feedback_insight/` | 1 层 | `用户反馈需求洞察工作流.yml` | 1 个早期版本 yml | Dify DSL |
| 5 | `Four-Level Validation of AI Products/` | 2 层（`.ref/` 平铺） | `ai_product_four_level_validation.yml` | `.ref/` 源码参考 33 个文件 | Dify DSL |
| 6 | `Product Analysis and Suggestions/` | 1 层 | `dify_商品数据关联洞察与策略建议工作流.yml` | 无 | Dify DSL |
| 7 | `prompt auto-generate/` | 2 层（`prompt_template/`） | `竞品Prompt自动生成流.yml` | `_update_dify_yml.py`、`index.html`、5 份模板 | Dify Chatflow + 前端 |
| 8 | `Technology Selection Decision Tree/` | 3 层（`app/static/`） | `app/workflow.py`、`app/main.py` | `app/static/` 前端 | 自研 Web 服务 |

**整体规律小结**：

1. **越靠近「平台能力」，目录栈越薄**：纯 Dify 工作流（4、6）只需一个 `.yml`；
   需要前端/插件/工具链时（2、3、7）才出现多子工程或平铺脚本。
2. **自研服务统一 `app/` + `app/static/` 结构**（1、8），前后端不分离部署，零构建、可离线。
3. **临时/参考/抓取产物用前缀隔离**：`_`（抓取产物、生成脚本）、`.`（`.ref/`、`.env`）、`.bak`（备份），
   业务主文件不带前缀，一眼可辨。
4. **一目录一交付物**：每个工作流目录都是可独立导入 Dify 或独立启动的完整项目，互不耦合。

