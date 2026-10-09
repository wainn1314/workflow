# -*- coding: utf-8 -*-
"""Generate updated 竞品Prompt自动生成.yml with all P0-P2 fixes."""
from pathlib import Path

# --- Node IDs (existing) ---
START = "866c0a68-42dc-492b-9b5f-a95ae0e38405"
LLM1 = "dacb1fdb-e831-4a27-bd93-b49f8432260f"
IFELSE = "c9797b16-8ae9-456b-a89d-334f103fef58"
KR1 = "24f494f7-6cf2-402e-bc32-0e2874313d13"
KR2 = "1cfecc1f-af00-4366-b835-5022da034ca6"
KR3 = "8a8e7656-4eac-45f2-8d80-c197440872c7"
KR4 = "6e649d4c-6d0b-4713-9581-392bc87e7361"
KR5 = "4a5eb985-3ee9-4c40-a980-e01d117112c8"
KR6 = "69b7268a-b81b-4383-8420-9aaa6b8494d2"
AGG = "affd5965-35f6-4ae2-88b3-265ffe344c91"
LLM2 = "25c59faf-65cb-417d-8224-ecee7abb2d1b"
LLM3 = "3b1e7295-39a0-4287-9d11-5d2fa6138044"
LLM4 = "11fda064-efe3-4fe5-ad21-f8358b465ac6"
CLS = "cd13786b-5ce4-472a-b7a4-3c8a1095f60d"
LLM5 = "47a2f322-5208-4a79-b64b-0e0001a294f2"
ANSWER = "5159a589-e1e8-4fbf-9a43-7a7c170e7f0b"
ANSWER_OPT = "3ce5c572-2e6a-49c5-948c-39e33d3623a2"
TURN = "7b8d2de4-5937-4c47-b793-72037c052353"
STRIFY = "4e20fcaf-7fd8-416e-b735-20f6c6c41d19"
ASSIGN_CTX = "c50893c3-d192-4791-9e49-21327c959d88"
ASSIGN_PROMPT = "8f759ea5-d5f8-4abc-a915-b70743c06b6f"
ASSIGN_OPT = "1b2f254f-5576-4b66-a16c-9496e7a79bab"
ANSWER_DONE = "a730d6fe-0e5d-458a-a89a-6ed359896aaf"

# --- New node IDs ---
JSON_VALIDATE = "b3c4d5e6-f7a8-490b-9c1d-2e3f4a5b6c7d"
KR_FALLBACK = "e8f9a0b1-c2d3-4e5f-a6b7-c8d9e0f1a2b3"

ENV_T1 = "88096dd7-b21f-4da2-9201-422085b258dc"
ENV_T2 = "25cbcdbb-37da-4c54-a97b-e73a57c1282f"
ENV_T3 = "cf5500db-4f53-4125-b60c-7ac6ae09092f"
ENV_T4 = "1502e823-f432-454b-bae2-fffa618f79e5"
ENV_T5 = "5d7796a4-df9a-4c39-89aa-aaf4b6bb22cd"
ENV_T6 = "a9eb6138-cdea-4a18-a8dc-72b7fe792aa7"
ENV_FALLBACK = "d4e5f6a7-b8c9-4012-d3e4-f5a6b7c8d9e0"
CV_ANALYSIS = "cb59834d-1ef5-4efe-8486-91b985c08486"
CV_TEMPLATE = "ee953eed-9e58-4216-832c-44432fba04c0"
CV_PROMPT = "00bc451d-4577-4a95-8a5f-3db8fdae9921"
CV_VERSION = "f6a7b8c9-d0e1-4234-e5f6-a7b8c9d0e1f2"

C_TURN = "9f4e6a1e-1bde-4319-923b-9315217a0e23"
C_T1 = "2f82f27c-3fcb-4f63-8461-a01c47ca76f0"
C_T2 = "7484d847-8918-449a-9574-21517c5b3dff"
C_T3 = "f991b712-f533-4f78-a2fb-cc1a4f95d902"
C_T4 = "12f7551e-c69b-4329-a242-6be09f0f0e87"
C_T5 = "f45f0c1d-e5e3-42bd-af22-ea6f587a72f0"
C_T6 = "bb366149-93b5-4c9c-9689-f5938df88fe9"
CASE_T2 = "bc880779-17ae-4cea-9f9f-529a63f66360"
CASE_T3 = "cd8f2d96-cec7-44b1-a437-4f47de3a2237"
CASE_T4 = "284f5ac0-51ea-4195-b44b-7c9df4be442a"
CASE_T5 = "59c1ea29-c904-480d-9165-75eb2646b9ba"
CASE_T6 = "190c3dab-181a-4336-a7a8-d84a4841614f"

CLS_OPT = "optimize"
CLS_OK = "confirm"
CLS_RE = "regenerate"

TONGYI = "langgenius/tongyi/tongyi"

PROMPT_IDS = {
    "llm1_sys": "5b13c92b-a47a-4dc9-808f-8c4c7ad12207",
    "llm1_user": "63519684-4f7c-4c6d-a4cc-7564ec6ef93b",
    "llm2_sys": "47bd5a63-ead3-46a2-91d4-2c44a3c5657a",
    "llm3_sys": "16c50fa3-9b08-4372-98f6-cda191728013",
    "llm4_sys": "96dd1d06-b0ce-4504-bf70-2990c24958d9",
    "llm5_sys": "7e82c454-ee32-4075-89aa-928c9f95ae16",
}


def edge(src, tgt, src_type, tgt_type, handle="source"):
    eid = f"{src}-{handle}-{tgt}-target"
    return f"""    - data:
        isInIteration: false
        isInLoop: false
        sourceType: {src_type}
        targetType: {tgt_type}
      id: {eid}
      source: {src}
      sourceHandle: {handle}
      target: {tgt}
      targetHandle: target
      type: custom
      zIndex: 0"""


def llm_model(name, temp=0.3):
    return f"""        model:
          completion_params:
            temperature: {temp}
          mode: chat
          name: {name}
          provider: {TONGYI}"""


def pos(x, y, w=242, h=90):
    return f"""      height: {h}
      position:
        x: {x}
        y: {y}
      positionAbsolute:
        x: {x}
        y: {y}
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: {w}
      zIndex: 0"""


def yaml_block(s: str, indent: int) -> str:
    pad = " " * indent
    lines = s.replace("\r\n", "\n").split("\n")
    return "|\n" + "\n".join(pad + line for line in lines)


def assign_version_increment():
    return """        - input_type: constant
          operation: add
          value: 1
          variable_selector:
          - conversation
          - prompt_version"""


# --- Prompts ---
llm1_sys = """你是一个 Prompt 模版匹配专家。用户会提供一个竞品名称和其基本功能描述，你需要：
1. 分析该竞品的核心功能和使用场景
2. 从以下模版类别中选择最匹配的一个：
   - T1_智能客服：在线客服、售后咨询、FAQ自动回复
   - T2_营销文案：广告文案、社媒运营、种草推广
   - T3_数据分析：数据报表、用户行为分析、商业洞察
   - T4_内容创作：文章写作、视频脚本、故事创作
   - T5_代码助手：编程辅助、技术方案、代码审查
   - T6_角色扮演：虚拟人设、IP对话、情感陪伴
3. 输出一份结构化分析报告
请严格按以下 JSON 格式输出，不要输出其他内容：
{
  "competitor_name": "竞品名称",
  "core_function": "核心功能概括（一句话）",
  "scenario_analysis": "场景分析（2-3句话）",
  "matched_template": "T1/T2/T3/T4/T5/T6",
  "match_reason": "选择该模版的理由",
  "key_features": ["功能点1", "功能点2", "功能点3"],
  "suggested_role": "建议的角色定义",
  "suggested_constraints": ["约束1", "约束2"]
}
注意：matched_template 字段值必须严格为 T1、T2、T3、T4、T5、T6 之一，不得输出其他值。"""

llm2_sys = """你是一个资深 Prompt 工程师。请根据以下信息生成一版高质量的 Prompt：

【竞品分析】
{{#conversation.analysis_report#}}

【参考模版】
{{#conversation.template_content#}}

## 输出格式规范（必须包含以下五个模块）
1. **角色定义**：精准描述 AI 扮演的角色，包含领域、能力边界、服务风格
2. **任务描述**：明确 AI 需要完成的具体任务及适用场景
3. **约束规则**：至少 5 条可执行的约束（禁止行为、边界条件、质量要求）
4. **输出格式**：规定回答的结构、长度、格式（如 Markdown/JSON）
5. **Few-Shot 占位**：预留「示例将在后续步骤嵌入」的占位说明

## 质量标准
- 角色定义必须具体、可辨识，禁止使用「你是一个有用的助手」等泛泛表述
- 约束规则至少 5 条，且与竞品业务场景直接相关
- 输出格式必须可解析、可执行，避免模糊描述
- 任务描述需覆盖竞品核心功能的主要使用场景

## 反模式警告（禁止出现）
- ❌ 「你是一个有用的助手 / AI 助手」
- ❌ 空泛的「请尽力回答用户问题」
- ❌ 与竞品无关的通用约束
- ❌ 缺少输出格式说明

## 其他要求
- 严格参考模版的结构，但内容必须针对用户提供的竞品进行深度定制
- 在 Prompt 末尾预留 {{user_input}} 占位符，表示用户实际输入的位置
- 直接输出完整的 Prompt，用 Markdown 代码块包裹"""

llm3_sys = f"""你是一个 Few-Shot 示例生成专家。你的任务是为给定的 Prompt 自动生成高质量的输入-输出示例对。

【任务背景】
{{{{#conversation.analysis_report#}}}}

【当前 Prompt】
{{{{#{LLM2}.text#}}}}

请生成 3 组 Few-Shot 示例，遵循以下规则：

1. 【覆盖度】3 组示例必须覆盖不同的典型场景：
   - 示例1：最常见/基础的用例（正常路径）
   - 示例2：较复杂或有特殊要求的用例（进阶路径）
   - 示例3：边界情况或容易出错的用例（防御路径）

2. 【格式要求】每组示例包含：
   - Input：模拟用户真实输入（要自然、口语化，像真实用户会说的话）
   - Output：该 Prompt 应该产出的理想回答（要完整、高质量）

3. 【质量标准】
   - Input 要多样化，避免句式雷同
   - Output 必须严格遵循 Prompt 中定义的约束规则
   - **每个 Output 示例长度不少于 200 字**，避免过于简短
   - **示例3（边界场景）必须展示 Prompt 中约束规则的防御效果**（如拒绝不当请求、引导转人工、说明能力边界等）

请严格按以下格式输出：

### Few-Shot 示例

**示例1（基础场景）**
Input:
Output:

**示例2（进阶场景）**
Input:
Output:

**示例3（边界场景）**
Input:
Output:"""

llm4_sys = f"""你是一个 Prompt 交付物整合专家。请将以下 Prompt 初稿和 Few-Shot 示例合并为一份完整的、可直接使用的 Prompt 文档。

【Prompt 初稿】
{{{{#{LLM2}.text#}}}}

【Few-Shot 示例】
{{{{#{LLM3}.text#}}}}

要求：
1. 将 Few-Shot 示例嵌入到 Prompt 的合适位置（通常在约束规则之后、输出格式之前）
2. **一致性检查**：逐条检查 Few-Shot 示例是否与约束规则一致；如有冲突，**以约束规则为准**修正示例内容
3. 最终输出一份结构完整、可直接复制使用的 Prompt
4. 用 Markdown 代码块包裹最终 Prompt
5. 在代码块之后，简要说明这份 Prompt 的设计要点（3-5 条）
6. **在最终 Prompt 末尾（代码块内）添加使用说明**：
   - 说明如何将 {{user_input}} 替换为实际用户输入
   - 说明该 Prompt 的适用场景与注意事项"""

llm5_sys = """你是一个 Prompt 迭代优化专家。用户正在对一版 Prompt 进行优化调整。

【原始竞品分析】
{{#conversation.analysis_report#}}

【当前版本 Prompt】
{{#conversation.current_prompt#}}

【用户优化意见】
{{#sys.query#}}

请按以下步骤执行：
1. 理解用户优化意见的核心诉求，同时参考原始竞品定位，确保优化不偏离产品场景
2. 对当前 Prompt 进行针对性修改（仅修改需要改动的部分，保留其他内容）
3. 如果用户的意见涉及 Few-Shot 示例，同步更新示例
4. 输出修改后的完整 Prompt（用 Markdown 代码块包裹）
5. 在代码块之后，用一句话说明本次修改了什么

注意：不要大幅重写，保持「微创修改」原则；优化时需保持与竞品分析中的角色定位和约束方向一致。"""

json_validate_code = '''import json
import re

VALID_TEMPLATES = {"T1", "T2", "T3", "T4", "T5", "T6"}

DEFAULT = {
    "competitor_name": "未知竞品",
    "core_function": "未能识别核心功能",
    "scenario_analysis": "未能解析竞品场景，将使用通用模版兜底。",
    "matched_template": "T1",
    "match_reason": "JSON 解析失败或格式异常，兜底路由至 T1",
    "key_features": ["待补充"],
    "suggested_role": "专业领域助手",
    "suggested_constraints": ["回答需准确", "不确定时明确说明", "遵守业务边界"],
}


def _extract_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty")

    fence = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\\{.*\\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not object")
    return data


def _normalize_template(value) -> str:
    text = str(value or "").strip().upper()
    if text in VALID_TEMPLATES:
        return text
    match = re.search(r"\\b(T[1-6])\\b", text)
    return match.group(1) if match else "T1"


def main(text: str) -> dict:
    try:
        data = _extract_json(text)
    except Exception:
        data = dict(DEFAULT)

    data["matched_template"] = _normalize_template(data.get("matched_template"))
    if "competitor_name" not in data:
        data["competitor_name"] = DEFAULT["competitor_name"]
    if "core_function" not in data:
        data["core_function"] = DEFAULT["core_function"]
    if "scenario_analysis" not in data:
        data["scenario_analysis"] = DEFAULT["scenario_analysis"]
    if "match_reason" not in data:
        data["match_reason"] = DEFAULT["match_reason"]
    if "key_features" not in data or not isinstance(data["key_features"], list):
        data["key_features"] = DEFAULT["key_features"]
    if "suggested_role" not in data:
        data["suggested_role"] = DEFAULT["suggested_role"]
    if "suggested_constraints" not in data or not isinstance(data["suggested_constraints"], list):
        data["suggested_constraints"] = DEFAULT["suggested_constraints"]

    return {"text": json.dumps(data, ensure_ascii=False, indent=2)}
'''

strify_code = '''DEFAULT_TEMPLATE = """# 通用 Prompt 模版框架（知识库未命中时的兜底）

## 角色定义
你是一位专业的领域助手，能够根据用户需求提供准确、结构化的回答。

## 任务描述
理解用户输入，完成与产品核心功能相关的任务，并在不确定时主动说明限制。

## 约束规则
1. 回答必须基于已知信息，禁止编造数据或虚假承诺
2. 保持语气专业、友好，输出结构清晰
3. 涉及敏感、违法或超出能力范围的请求时礼貌拒绝并说明原因
4. 需要额外信息时，主动列出所需信息点
5. 输出格式应便于阅读，必要时使用列表或分段

## 输出格式
按用户需求组织回答；若 Prompt 要求 JSON/Markdown，严格遵循。

## Few-Shot 占位
（Few-Shot 示例将在后续步骤自动生成并嵌入）

---
用户输入位置：{{user_input}}
"""


def main(result: list) -> dict:
    if not result:
        return {"text": DEFAULT_TEMPLATE}

    parts = []
    for item in result:
        if isinstance(item, dict):
            content = item.get("content") or item.get("title") or ""
            if content:
                parts.append(str(content))
        elif item:
            parts.append(str(item))

    text = "\\n\\n".join(parts).strip()
    if not text:
        return {"text": DEFAULT_TEMPLATE}
    return {"text": text}
'''

KR_DESC = {
    "T1": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T1 智能客服。【优化建议】当前使用固定环境变量 QUERY_T1 作为查询词；可改为引用 LLM①/JSON校验 输出的 core_function 或 scenario_analysis 实现动态检索。",
    "T2": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T2 营销文案。【优化建议】当前使用固定环境变量 QUERY_T2；可改为动态查询以提升匹配精度。",
    "T3": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T3 数据分析。【优化建议】当前使用固定环境变量 QUERY_T3；可改为动态查询以提升匹配精度。",
    "T4": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T4 内容创作。【优化建议】当前使用固定环境变量 QUERY_T4；可改为动态查询以提升匹配精度。",
    "T5": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T5 代码助手。【优化建议】当前使用固定环境变量 QUERY_T5；可改为动态查询以提升匹配精度。",
    "T6": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。检索「Prompt模版知识库」- T6 角色扮演。【优化建议】当前使用固定环境变量 QUERY_T6；可改为动态查询以提升匹配精度。",
    "FALLBACK": "⚠️ 请先在 Dify 知识库中创建对应数据集，然后将 dataset_id 填入 dataset_ids。ELSE 兜底分支：当 matched_template 不在 T1~T6 时使用通用 Prompt 模版检索。【优化建议】确保 LLM① 输出严格限制在 T1~T6；本节点为安全兜底。",
}

# --- Edges ---
edges = []
edges.append(edge(START, TURN, "start", "if-else"))
edges.append(edge(TURN, LLM1, "if-else", "llm", "true"))
edges.append(edge(TURN, CLS, "if-else", "question-classifier", "false"))
edges.append(edge(LLM1, JSON_VALIDATE, "llm", "code"))
edges.append(edge(JSON_VALIDATE, IFELSE, "code", "if-else"))
for h, tgt in [
    ("true", KR1),
    (CASE_T2, KR2),
    (CASE_T3, KR3),
    (CASE_T4, KR4),
    (CASE_T5, KR5),
    (CASE_T6, KR6),
    ("false", KR_FALLBACK),
]:
    edges.append(edge(IFELSE, tgt, "if-else", "knowledge-retrieval", h))
for kid in [KR1, KR2, KR3, KR4, KR5, KR6, KR_FALLBACK]:
    edges.append(edge(kid, AGG, "knowledge-retrieval", "variable-aggregator"))
edges.append(edge(AGG, STRIFY, "variable-aggregator", "code"))
edges.append(edge(STRIFY, ASSIGN_CTX, "code", "assigner"))
edges.append(edge(ASSIGN_CTX, LLM2, "assigner", "llm"))
edges.append(edge(LLM2, LLM3, "llm", "llm"))
edges.append(edge(LLM3, LLM4, "llm", "llm"))
edges.append(edge(LLM4, ASSIGN_PROMPT, "llm", "assigner"))
edges.append(edge(ASSIGN_PROMPT, ANSWER, "assigner", "answer"))
edges.append(edge(CLS, LLM5, "question-classifier", "llm", CLS_OPT))
edges.append(edge(CLS, ANSWER_DONE, "question-classifier", "answer", CLS_OK))
edges.append(edge(CLS, LLM2, "question-classifier", "llm", CLS_RE))
edges.append(edge(LLM5, ASSIGN_OPT, "llm", "assigner"))
edges.append(edge(ASSIGN_OPT, ANSWER_OPT, "assigner", "answer"))

header = f'''# =============================================================================
# 文件名称: 竞品Prompt自动生成.yml
# 用途: 竞品分析 → 模版匹配 → Prompt 初稿/Few-Shot/组装 → 多轮迭代优化
# 应用类型: Chatflow (app.mode = advanced-chat)
# DSL 版本: 0.7.0
# =============================================================================
# 导入后务必手动配置:
# 1. 知识库: 将所有知识检索节点（含 ELSE 兜底节点）的 dataset_ids 填入真实 ID
# 2. 模型: 已统一为通义千问（langgenius/tongyi/tongyi），请确认插件已安装
# 3. 环境变量 QUERY_T1~T6 / QUERY_FALLBACK 已预置固定检索词
# =============================================================================
# 整体流程说明:
# [首轮 current_prompt 为空]
#   开始 → 轮次路由 → LLM①(qwen-max) → JSON校验与修正 → 条件分支(T1~T6/ELSE兜底)
#   → 知识检索 → 汇聚 → 模版文本化(含空结果兜底) → 保存分析与模版
#   → LLM②③④(qwen-plus) → 保存Prompt(+version) → 回答(Prompt vN)
# [后续轮次]
#   轮次路由 → 问题分类器(qwen-turbo) → 优化/完成/重生成
# =============================================================================

app:
  description: 根据竞品名称与功能描述，自动匹配 Prompt 模版并生成可迭代优化的完整 Prompt。
  icon: 📝
  icon_background: '#E4FBCC'
  icon_type: emoji
  mode: advanced-chat
  name: 竞品Prompt自动生成
  use_icon_as_answer_icon: false
dependencies:
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: langgenius/tongyi:0.0.25@6e8f8e8f8e8f8e8f8e8f8e8f8e8f8e8f8e8f8e8f8e8f
    version: null
kind: app
version: 0.7.0
workflow:
  conversation_variables:
  - description: LLM① 竞品分析 JSON 文本（经 JSON 校验节点规范化）
    id: {CV_ANALYSIS}
    name: analysis_report
    value: ''
    value_type: string
  - description: 知识检索得到的模版正文
    id: {CV_TEMPLATE}
    name: template_content
    value: ''
    value_type: string
  - description: 当前完整 Prompt（组装/优化后）
    id: {CV_PROMPT}
    name: current_prompt
    value: ''
    value_type: string
  - description: Prompt 版本号，每次保存/更新时 +1
    id: {CV_VERSION}
    name: prompt_version
    value: 0
    value_type: number
  environment_variables:
  - description: T1 知识检索查询词（固定词，可改为动态）
    id: {ENV_T1}
    name: QUERY_T1
    value: 智能客服 Prompt 模版
    value_type: string
  - description: T2 知识检索查询词
    id: {ENV_T2}
    name: QUERY_T2
    value: 营销文案 Prompt 模版
    value_type: string
  - description: T3 知识检索查询词
    id: {ENV_T3}
    name: QUERY_T3
    value: 数据分析 Prompt 模版
    value_type: string
  - description: T4 知识检索查询词
    id: {ENV_T4}
    name: QUERY_T4
    value: 内容创作 Prompt 模版
    value_type: string
  - description: T5 知识检索查询词
    id: {ENV_T5}
    name: QUERY_T5
    value: 代码助手 Prompt 模版
    value_type: string
  - description: T6 知识检索查询词
    id: {ENV_T6}
    name: QUERY_T6
    value: 角色扮演 Prompt 模版
    value_type: string
  - description: ELSE 兜底分支通用模版检索词
    id: {ENV_FALLBACK}
    name: QUERY_FALLBACK
    value: 通用 Prompt 模版
    value_type: string
  features:
    file_upload:
      allowed_file_extensions:
      - .JPG
      - .JPEG
      - .PNG
      - .GIF
      - .WEBP
      - .SVG
      allowed_file_types:
      - image
      allowed_file_upload_methods:
      - local_file
      - remote_url
      enabled: false
      image:
        enabled: false
        number_limits: 3
        transfer_methods:
        - local_file
        - remote_url
      number_limits: 3
    opening_statement: 你好！请发送「竞品名称 + 功能描述」，我将自动匹配 Prompt 模版并生成可直接使用的 Prompt。生成后你可以继续说修改意见（如「语气活泼一点」），或回复「可以了」结束。
    retriever_resource:
      enabled: true
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions:
    - 竞品：某某智能客服，支持多轮 FAQ 自动回复与工单转接
    - 竞品：某某营销助手，擅长小红书种草文案与活动话术
    - 语气再专业一点，并加一条价格相关约束
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
      language: ''
      voice: ''
  graph:
    edges:
'''

nodes = []

nodes.append(f"""    - data:
        desc: 收集竞品名称及功能描述（首轮也可直接在对话框输入，对应 sys.query）
        selected: false
        title: 开始
        type: start
        variables:
        - label: 竞品名称及功能描述
          max_length: 2000
          options: []
          required: true
          type: text-input
          variable: query
      id: {START}
{pos(40, 420, 242, 90)}""")

nodes.append(f"""    - data:
        cases:
        - case_id: 'true'
          conditions:
          - comparison_operator: empty
            id: {C_TURN}
            value: ''
            varType: string
            variable_selector:
            - conversation
            - current_prompt
          id: 'true'
          logical_operator: and
        desc: current_prompt 为空时走完整生成链路；已有 Prompt 时进入问题分类器
        selected: false
        title: 轮次路由
        type: if-else
      id: {TURN}
{pos(320, 420, 242, 126)}""")

nodes.append(f"""    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 意图识别并匹配 T1~T6 模版类别，输出 JSON
        memory:
          query_prompt_template: '{{{{#sys.query#}}}}'
          role_prefix:
            assistant: ''
            user: ''
          window:
            enabled: false
            size: 10
{llm_model('qwen-max', 0.2)}
        prompt_template:
        - id: {PROMPT_IDS['llm1_sys']}
          role: system
          text: {yaml_block(llm1_sys, 12)}
        - id: {PROMPT_IDS['llm1_user']}
          role: user
          text: '竞品名称及功能描述：{{{{#sys.query#}}}}'
        selected: false
        title: LLM①意图识别&模板匹配
        type: llm
        variables: []
        vision:
          enabled: false
      id: {LLM1}
{pos(600, 420, 242, 115)}""")

nodes.append(f"""    - data:
        code: {yaml_block(json_validate_code, 10)}
        code_language: python3
        desc: 解析并校验 LLM① JSON 输出，规范化 matched_template 至 T1~T6
        outputs:
          text:
            children: null
            type: string
        selected: false
        title: JSON校验与修正
        type: code
        variables:
        - value_selector:
          - {LLM1}
          - text
          variable: text
      id: {JSON_VALIDATE}
{pos(740, 420, 242, 52)}""")

# if-else uses JSON_VALIDATE output
ifelse_cases = f"""        cases:
        - case_id: 'true'
          conditions:
          - comparison_operator: contains
            id: {C_T1}
            value: '"matched_template": "T1"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: 'true'
          logical_operator: and
        - case_id: {CASE_T2}
          conditions:
          - comparison_operator: contains
            id: {C_T2}
            value: '"matched_template": "T2"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: {CASE_T2}
          logical_operator: and
        - case_id: {CASE_T3}
          conditions:
          - comparison_operator: contains
            id: {C_T3}
            value: '"matched_template": "T3"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: {CASE_T3}
          logical_operator: and
        - case_id: {CASE_T4}
          conditions:
          - comparison_operator: contains
            id: {C_T4}
            value: '"matched_template": "T4"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: {CASE_T4}
          logical_operator: and
        - case_id: {CASE_T5}
          conditions:
          - comparison_operator: contains
            id: {C_T5}
            value: '"matched_template": "T5"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: {CASE_T5}
          logical_operator: and
        - case_id: {CASE_T6}
          conditions:
          - comparison_operator: contains
            id: {C_T6}
            value: '"matched_template": "T6"'
            varType: string
            variable_selector:
            - {JSON_VALIDATE}
            - text
          id: {CASE_T6}
          logical_operator: and
        desc: 根据 matched_template 路由；ELSE 走通用模版兜底检索（非 T1）
        selected: false
        title: 条件分支-模版路由
        type: if-else"""

nodes.append(f"""    - data:
{ifelse_cases}
      id: {IFELSE}
{pos(880, 420, 242, 280)}""")

kr_specs = [
    (KR1, "T1 智能客服", "QUERY_T1", 80, "T1"),
    (KR2, "T2 营销文案", "QUERY_T2", 220, "T2"),
    (KR3, "T3 数据分析", "QUERY_T3", 360, "T3"),
    (KR4, "T4 内容创作", "QUERY_T4", 500, "T4"),
    (KR5, "T5 代码助手", "QUERY_T5", 640, "T5"),
    (KR6, "T6 角色扮演", "QUERY_T6", 780, "T6"),
]
for kid, title, env_name, y, key in kr_specs:
    nodes.append(f"""    - data:
        dataset_ids: []
        desc: {KR_DESC[key]}
        multiple_retrieval_config:
          reranking_enable: false
          top_k: 1
        query_variable_selector:
        - env
        - {env_name}
        retrieval_mode: multiple
        selected: false
        title: 知识检索-{title}
        type: knowledge-retrieval
      id: {kid}
{pos(1160, y, 242, 110)}""")

nodes.append(f"""    - data:
        dataset_ids: []
        desc: {KR_DESC['FALLBACK']}
        multiple_retrieval_config:
          reranking_enable: false
          top_k: 1
        query_variable_selector:
        - env
        - QUERY_FALLBACK
        retrieval_mode: multiple
        selected: false
        title: 知识检索-ELSE兜底通用模版
        type: knowledge-retrieval
      id: {KR_FALLBACK}
{pos(1160, 920, 242, 110)}""")

nodes.append(f"""    - data:
        desc: 汇聚 7 路知识检索结果（含 ELSE 兜底；仅执行分支有值）
        output_type: array[object]
        selected: false
        title: 知识检索结果汇聚
        type: variable-aggregator
        variables:
        - - {KR1}
          - result
        - - {KR2}
          - result
        - - {KR3}
          - result
        - - {KR4}
          - result
        - - {KR5}
          - result
        - - {KR6}
          - result
        - - {KR_FALLBACK}
          - result
      id: {AGG}
{pos(1440, 420, 242, 150)}""")

nodes.append(f"""    - data:
        code: {yaml_block(strify_code, 10)}
        code_language: python3
        desc: 将知识检索 result 转为纯文本；空结果时返回通用 Prompt 模版框架
        outputs:
          text:
            children: null
            type: string
        selected: false
        title: 模版结果文本化
        type: code
        variables:
        - value_selector:
          - {AGG}
          - output
          variable: result
      id: {STRIFY}
{pos(1720, 420, 242, 52)}""")

nodes.append(f"""    - data:
        desc: 将校验后的分析报告与模版正文写入会话变量
        items:
        - input_type: variable
          operation: over-write
          value:
          - {JSON_VALIDATE}
          - text
          variable_selector:
          - conversation
          - analysis_report
        - input_type: variable
          operation: over-write
          value:
          - {STRIFY}
          - text
          variable_selector:
          - conversation
          - template_content
        selected: false
        title: 保存分析与模版
        type: assigner
        version: '2'
      id: {ASSIGN_CTX}
{pos(2000, 420, 242, 100)}""")

nodes.append(f"""    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 基于竞品分析与参考模版生成 Prompt 初稿
        memory:
          query_prompt_template: '{{{{#sys.query#}}}}'
          role_prefix:
            assistant: ''
            user: ''
          window:
            enabled: false
            size: 10
{llm_model('qwen-plus', 0.3)}
        prompt_template:
        - id: {PROMPT_IDS['llm2_sys']}
          role: system
          text: {yaml_block(llm2_sys, 12)}
        selected: false
        title: LLM②初稿生成
        type: llm
        variables: []
        vision:
          enabled: false
      id: {LLM2}
{pos(2280, 420, 242, 115)}""")

nodes.append(f"""    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 为初稿自动生成 3 组 Few-Shot 示例
        memory:
          query_prompt_template: '{{{{#sys.query#}}}}'
          role_prefix:
            assistant: ''
            user: ''
          window:
            enabled: false
            size: 10
{llm_model('qwen-plus', 0.5)}
        prompt_template:
        - id: {PROMPT_IDS['llm3_sys']}
          role: system
          text: {yaml_block(llm3_sys, 12)}
        selected: false
        title: LLM③Few-Shot自动生成
        type: llm
        variables: []
        vision:
          enabled: false
      id: {LLM3}
{pos(2560, 420, 242, 115)}""")

nodes.append(f"""    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 合并初稿与 Few-Shot，一致性检查后以约束规则为准
        memory:
          query_prompt_template: '{{{{#sys.query#}}}}'
          role_prefix:
            assistant: ''
            user: ''
          window:
            enabled: false
            size: 10
{llm_model('qwen-plus', 0.2)}
        prompt_template:
        - id: {PROMPT_IDS['llm4_sys']}
          role: system
          text: {yaml_block(llm4_sys, 12)}
        selected: false
        title: LLM④组装输出
        type: llm
        variables: []
        vision:
          enabled: false
      id: {LLM4}
{pos(2840, 420, 242, 115)}""")

nodes.append(f"""    - data:
        desc: 保存组装后的 Prompt 到会话变量，并递增版本号
        items:
        - input_type: variable
          operation: over-write
          value:
          - {LLM4}
          - text
          variable_selector:
          - conversation
          - current_prompt
{assign_version_increment()}
        selected: false
        title: 保存当前Prompt
        type: assigner
        version: '2'
      id: {ASSIGN_PROMPT}
{pos(3120, 420, 242, 100)}""")

nodes.append(f"""    - data:
        answer: |
          **Prompt v{{{{#conversation.prompt_version#}}}}**

          {{{{#{LLM4}.text#}}}}
        desc: 输出首轮/重新生成后的完整 Prompt（含版本号）
        selected: false
        title: 回答-生成结果
        type: answer
        variables: []
      id: {ANSWER}
{pos(3400, 420, 242, 101)}""")

nodes.append(f"""    - data:
        classes:
        - id: {CLS_OPT}
          name: 优化修改
        - id: {CLS_OK}
          name: 确认完成
        - id: {CLS_RE}
          name: 重新生成
        desc: 根据用户反馈路由到优化 / 完成 / 重生成
        instruction: '将用户意图分为三类：1) 优化修改——用户希望调整当前 Prompt；2) 确认完成——用户表示满意或结束；3) 重新生成——用户希望推倒重来。若无法判断，优先选择优化修改。'
        model:
          completion_params:
            temperature: 0.1
          mode: chat
          name: qwen-turbo
          provider: {TONGYI}
        query_variable_selector:
        - sys
        - query
        selected: false
        title: 问题分类器
        type: question-classifier
        vision:
          enabled: false
        _targetBranches:
        - id: {CLS_OPT}
          name: 优化修改
        - id: {CLS_OK}
          name: 确认完成
        - id: {CLS_RE}
          name: 重新生成
      id: {CLS}
{pos(600, 720, 242, 160)}""")

nodes.append(f"""    - data:
        context:
          enabled: false
          variable_selector: []
        desc: 按用户意见微创优化当前 Prompt，参考原始竞品分析
        memory:
          query_prompt_template: '{{{{#sys.query#}}}}'
          role_prefix:
            assistant: ''
            user: ''
          window:
            enabled: false
            size: 10
{llm_model('qwen-plus', 0.3)}
        prompt_template:
        - id: {PROMPT_IDS['llm5_sys']}
          role: system
          text: {yaml_block(llm5_sys, 12)}
        selected: false
        title: LLM⑤迭代优化
        type: llm
        variables: []
        vision:
          enabled: false
      id: {LLM5}
{pos(900, 720, 242, 115)}""")

nodes.append(f"""    - data:
        desc: 用优化后的 Prompt 覆盖会话变量，并递增版本号
        items:
        - input_type: variable
          operation: over-write
          value:
          - {LLM5}
          - text
          variable_selector:
          - conversation
          - current_prompt
{assign_version_increment()}
        selected: false
        title: 更新当前Prompt
        type: assigner
        version: '2'
      id: {ASSIGN_OPT}
{pos(1180, 720, 242, 100)}""")

nodes.append(f"""    - data:
        answer: |
          **Prompt v{{{{#conversation.prompt_version#}}}}**（已优化）

          {{{{#{LLM5}.text#}}}}
        desc: 输出迭代优化后的 Prompt；下一轮用户消息将再次进入问题分类器
        selected: false
        title: 回答-优化结果
        type: answer
        variables: []
      id: {ANSWER_OPT}
{pos(1460, 720, 242, 101)}""")

nodes.append(f"""    - data:
        answer: |
          已确认完成。**Prompt v{{{{#conversation.prompt_version#}}}}** 为最终版本：

          {{{{#conversation.current_prompt#}}}}
        desc: 用户确认完成后输出最近一轮 Prompt（含版本号）
        selected: false
        title: 回答-确认完成
        type: answer
        variables: []
      id: {ANSWER_DONE}
{pos(900, 920, 242, 101)}""")

changelog = '''
# =============================================================================
# 修改摘要 (Changelog)
# =============================================================================
# P0 Bug 修复:
#   [Bug1] LLM②/③/④/⑤ 统一改为 qwen-plus + langgenius/tongyi/tongyi
#   [Bug1] LLM① 改为 qwen-max + langgenius/tongyi/tongyi
#   [Bug2] 问题分类器改为 qwen-turbo + langgenius/tongyi/tongyi
#   [Bug3] 知识检索 dataset_ids 改为 []，desc 增加 ⚠️ 配置提示与动态查询优化建议
#   [Bug4] ELSE 分支改为独立「知识检索-ELSE兜底通用模版」节点（QUERY_FALLBACK）
#
# P1 结构优化:
#   [Opt1] LLM② 增强五模块输出规范、质量标准与反模式警告
#   [Opt2] LLM③ 增加 Output≥200字、示例3须展示约束防御效果
#   [Opt3] LLM④ 增加一致性检查（冲突以约束规则为准）、{{user_input}} 使用说明
#   [Opt4] LLM⑤ 增加 {{#conversation.analysis_report#}} 竞品分析上下文
#
# P2 健壮性增强:
#   [Enh1] 新增「JSON校验与修正」Code 节点（LLM① → 条件分支之间）
#   [Enh2] 「模版结果文本化」空结果时返回通用 Prompt 模版框架
#   [Enh3] LLM② temp 0.3 / LLM③ 0.5 / LLM④ 0.2 / 分类器 0.1
#   [Enh4] 新增会话变量 prompt_version；保存/更新时 +1；回答节点展示 vN
#
# 其他:
#   - dependencies 改为通义千问 marketplace 插件（导入后请确认插件 hash）
#   - 条件分支与保存分析均引用 JSON 校验节点输出
#   - 变量聚合器纳入 ELSE 兜底检索节点
# =============================================================================
'''

out = header + "\n".join(edges) + "\n    nodes:\n" + "\n".join(nodes) + """
    viewport:
      x: -100
      y: 80
      zoom: 0.45
""" + changelog

for name in ["竞品Prompt自动生成.yml", "竞品Prompt自动生成_Chatflow.yml"]:
    path = Path(r"D:\ai_workflow\prompt auto-generate") / name
    path.write_text(out, encoding="utf-8")
    print(f"Wrote {path} ({path.stat().st_size} bytes)")

import yaml
with open(Path(r"D:\ai_workflow\prompt auto-generate") / "竞品Prompt自动生成.yml", encoding="utf-8") as f:
    d = yaml.safe_load(f)
print("YAML OK | nodes:", len(d["workflow"]["graph"]["nodes"]), "| edges:", len(d["workflow"]["graph"]["edges"]))
