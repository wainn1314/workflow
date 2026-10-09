# AI 应用评测流水线 (MVP)

一个基于 **FastAPI + SQLite** 的轻量级大模型 / Chatflow 输出质量评测工具，覆盖：

- **批量调用**：并发调用被测模型，支持多轮对话、流式（测量 TTFT）与非流式、失败重试、断点续跑
- **LLM-as-Judge 评分**：五个维度独立评分（事实准确性、幻觉率、指令遵循度、完整性、安全合规），加权总分 + 置信度
- **指标统计**：延迟（TTFT / 总延迟）、Token（输入 / 输出 / 总）
- **报告生成**：整体通过率、各维度平均分、按场景 / 难度分组统计、CSV 导出
- **BadCase 人工抽检**：低分或维度分差过大自动标记，支持人工复核
- **历史趋势对比**：多轮评测的通过率 / 平均分 / 延迟 / Token 趋势可视化

## 目录结构

```
app/
  config.py        评分维度、权重、通过阈值、BadCase 规则
  schemas.py       人工复核请求模型
  db.py            SQLite 持久化层
  parser.py        Excel/CSV 测试集解析
  llm_client.py    OpenAI 兼容客户端（流式/非流式/Mock）
  judge.py         LLM-as-Judge 评分
  evaluator.py     评测编排
  report.py        汇总统计 + CSV 导出
  main.py          FastAPI 路由
  static/          前端页面（原生 JS + Chart.js）
    index.html  style.css  app.js
    vendor/chart.umd.min.js
    sample_testset.csv
run.py              启动入口
generate_sample.py  示例测试集生成器
requirements.txt
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python run.py
# 或
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. 浏览器打开
http://127.0.0.1:8000
```

打开页面后，点击「下载示例测试集」得到 `sample_testset.csv`，再在「运行评测」Tab 上传该文件，默认勾选 **Mock 模式**，无需真实 API Key 即可跑通完整流程。

## 测试集格式

支持 `.csv` / `.xlsx` / `.xls`，必填列：

| 列名 | 说明 |
| --- | --- |
| `test_case_id` | 用例唯一标识 |
| `scenario` | 场景（如 知识问答、代码生成） |
| `difficulty` | 难度（如 简单 / 中等 / 困难） |
| `conversation` | 对话消息数组的 JSON 字符串（也可用 Python 字面量） |
| `expected_output` | 标准答案 / 期望输出 |

`conversation` 示例：

```json
[{"role": "system", "content": "你是助手"}, {"role": "user", "content": "你好"}]
```

也支持 `{"messages": [...]}` 包裹格式，以及多轮 `user` / `assistant` 交替（多轮会逐轮调用并累计延迟与 Token）。

## 配置真实模型

在「运行评测」Tab 填写被测模型与裁判模型的 **Base URL / 模型名 / API Key**，取消勾选 Mock 即可。系统支持两大类接口协议：

- **OpenAI 兼容**（默认）：Base URL 会自动规范化到 `/v1/chat/completions` 端点，适用于 DeepSeek、OpenAI、Ollama、LM Studio、vLLM 等。
- **Dify 应用**：当 API Key 以 `app-` 开头、或 Base URL 中包含 `dify` 时自动识别。Dify 会把不同应用类型挂到不同端点上，本工具会按应用类型自动选择：

  | 应用类型（`GET /v1/info` 的 `mode`） | 请求端点 | 说明 |
  | --- | --- | --- |
  | `chat` / `agent` / `agent-chat` / `advanced-chat` | `POST /v1/chat-messages` | 取用户消息作为 `query`（阻塞模式） |
  | `workflow` | `POST /v1/workflows/run` | `inputs` 由 Start 变量映射生成，结果取 `data.outputs` |
  | `completion` | `POST /v1/completion-messages` | 文本生成应用 |

  「接口类型」下拉框可选 `Dify 应用（自动判别）` 或强制指定 `dify-chat` / `dify-workflow` / `dify-completion`。
  若路由判断有误，Dify 会返回 400 `not_chat_app` / `not_workflow_app` / `not_completion_app`，
  本工具会自动改试其它端点并在该次评测内记住正确路由（因此旧的 `provider=dify` 配置无需修改即可继续用）。

> 注意：Dify 对话类应用没有 system/user 角色分离，系统指令需在 Dify 应用内配置；评测时会取用户消息作为 `query`，并把测试集中的 system 消息拼到 `query` 前以保证评测自包含。

### Dify 工作流应用：Start 变量自动映射

工作流没有自由文本入口，输入必须是 Start 节点声明的变量。工具会先调用 `GET /v1/parameters`
读取变量定义，再把测试集里的用户指令解析后填入 `inputs`：

| 变量语义（按变量名识别） | 取值来源 |
| --- | --- |
| `count` / `num` / 数量 | 指令中的题量（"生成3道" → 3、"出一道" → 1），解析不到则用变量的 `default` |
| `difficulty` / `level` / 难度 | 指令中的难度（简单/中等/困难 ↔ easy/medium/hard，含 select 枚举匹配），否则 `default` |
| `type` / `types` / 题型 | 指令中的题型（如"单选、判断、简答" → `单选题、判断题、简答题`），select 变量则匹配选项 |
| `topic` / `query` / 主题 | 指令中的主题（"关于特征选择的单选题" → `特征选择`），解析不到则用原始指令 |
| `context` / `material` / 内容 | 指令中"："后的正文（"根据以下材料出2道题：xxx" → `xxx`） |
| 其它变量 | 必填时填原始指令兜底，选填时留空不发送 |

若某个变量需要固定值（例如常量化的 `type`、或变量名无法被识别），可在「工作流输入变量」
文本框里手工指定 JSON 覆盖自动映射，取值为 `"$query"` 代表用户原话，取值为 `null`/`""` 表示不发送该变量：

```json
{ "topic": "$query", "difficulty": "medium", "count": 3, "context": null }
```

工作流返回的 `data.outputs` 会汇总为评测输出（优先取 `questions` / `result` / `answer` 等正文字段，
并保留 `error`、`success` 等状态字段便于排查）。失败语义：

- `data.status` 非 `succeeded`（工作流自身异常）→ 记为一次失败并按 `max_retries` 重试；
- `status=succeeded` 但应用内部判定失败且无正文（如 `{"success": "False", "questions": "[]", "error": "questions 为空或格式不正确"}`）
  → 同样记为失败并重试，并把应用返回的原因（含实际 `inputs`）写入结果 `error` 字段与实时日志，
  不会拿一句错误提示去参加评分。

> **Dify 免费额度限流**：上面的 `questions 为空或格式不正确` 多半是应用内知识库检索被限流
> （日志里可能直接看到 `you have reached the knowledge base request rate limit of your subscription`）——
> 检索拿不到资料，应用自然出不了题。实测同一组 `inputs` 会在"成功"与"questions 为空"之间跳变，
> 属应用侧瞬时问题，因此客户端把它当作**可重试**错误。客户端与评测器已处理：
> 限流类错误与"未产出内容"错误会自动以 **20 秒冷却**重试（其它错误按 2/4/8 秒递增退避），
> 错误信息里也会提示"请降低 concurrency"。批量跑知识库类应用时建议把并发降到 **1~2**，
> 并适当调大 `max_retries`。
>
> 注意：**裁判应用也在消耗同一账号的知识库额度**（若裁判是带知识库的 Dify 应用，日志里会出现
> `裁判模型评分失败: ... knowledge base request rate limit`）。想让 15 条用例都能拿到分数，
> 裁判最好换成不带知识库的模型（如 OpenAI 兼容接口），或等额度恢复后**断点续跑**。
>
> 自查建议：① 用对话应用直接问一句"请根据你的知识库说明「xxx」"，确认该主题在知识库里；
> ② 核对映射——每条用例失败时 `error` 字段里会带上实际发送的 `inputs`，可与
> `GET /parameters` 返回的 Start 变量定义比对（客户端就是用这套定义自动映射的）。

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/runs` | 上传测试集 + 配置，创建并启动评测 |
| GET | `/api/runs` | 评测列表 |
| GET | `/api/runs/{id}/progress` | 进度 + 实时日志（增量） |
| GET | `/api/runs/{id}/report` | 汇总报告 |
| GET | `/api/runs/{id}/results` | 明细结果 |
| GET | `/api/runs/{id}/export?kind=...` | 导出 CSV（results/summary/scenario/difficulty/badcase） |
| POST | `/api/runs/{id}/cancel` | 取消 |
| POST | `/api/runs/{id}/resume` | 断点续跑 |
| DELETE | `/api/runs/{id}` | 删除评测记录（连同用例、结果、日志） |
| POST | `/api/results/{id}/review` | BadCase 人工复核 |
| GET | `/api/history/trend` | 历史趋势 |

## 评分规则

- 加权总分 = Σ(维度分 × 权重)；权重：事实准确性 0.30、幻觉率 0.20、完整性 0.20、指令遵循度 0.15、安全合规 0.15
- **通过**：加权总分 ≥ 3.0
- **BadCase**：加权总分 < 3.0，或各维度分差 > 2.0（低置信度）
