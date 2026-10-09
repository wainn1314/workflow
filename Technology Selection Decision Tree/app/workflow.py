"""技术选型工作流：构造 Prompt → 调用 DeepSeek（OpenAI SDK 兼容模式）→ 解析为 SelectionReport。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

try:  # 支持从项目根目录启动：uvicorn app.main:app
    from .models import BusinessConstraints, SelectionReport
except ImportError:  # 支持从 app 目录启动：uvicorn main:app
    from models import BusinessConstraints, SelectionReport


# 无论从哪个目录启动，都加载 app/.env
_ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=_ENV_PATH)

# 大模型返回非法 JSON 时的最大尝试次数（首次 + 一次纠错重试）
MAX_ATTEMPTS = 2

# 从返回文本中提取 ```json ... ``` 代码块
_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

SYSTEM_PROMPT = """你是一位资深的技术选型专家，服务于企业的软件架构决策。
你需要根据用户给出的业务约束（业务场景、性能要求、团队规模、预算等）给出可落地的技术选型建议。

要求：
1. 综合评估业务场景、性能与扩展性要求、团队技术栈与规模、预算与运维成本后，推荐最合适的技术方案。
2. 明确说明选择理由，理由必须紧扣用户给出的约束条件，不要泛泛而谈。
3. 列出该方案的优势与劣势，优势和劣势各不少于 2 条，条目要具体（可包含性能、成本、生态、团队学习成本等维度）。
4. 给出不少于 2 个备选方案，备选方案应说明适用的不同前提。
5. 只输出一个 JSON 对象，不要输出任何解释性文字，不要使用 Markdown 代码块包裹。
6. JSON 必须严格符合以下结构，键名不可更改，列表元素必须为字符串：

{
  "selected_tech": "推荐的技术方案",
  "reason": "选择理由",
  "advantages": ["优势1", "优势2"],
  "disadvantages": ["劣势1", "劣势2"],
  "alternatives": ["备选方案1", "备选方案2"]
}

输出语言与用户输入保持一致（用户用中文提问则用中文回答）。"""


class WorkflowError(RuntimeError):
    """工作流执行失败：配置缺失、大模型调用异常，或返回内容无法解析为选型报告。"""


def _get_required_env(name: str) -> str:
    """读取必需的环境变量，缺失时抛出 WorkflowError。"""
    value = os.getenv(name, "").strip()
    if not value:
        raise WorkflowError(f"缺少环境变量 {name}，请在 {_ENV_PATH} 中配置")
    return value


def _get_client() -> OpenAI:
    """创建 OpenAI SDK 兼容客户端，指向 DeepSeek 服务。"""
    return OpenAI(
        api_key=_get_required_env("LLM_API_KEY"),
        base_url=_get_required_env("LLM_BASE_URL"),
    )


def build_messages(description: str) -> list[dict[str, str]]:
    """构造发给大模型的消息列表。"""
    user_prompt = f"""请根据以下业务约束完成技术选型分析，并严格按约定的 JSON 结构输出结果：

--- 业务约束开始 ---
{description}
--- 业务约束结束 ---

请务必只输出 JSON 对象自身，不要包含 Markdown 代码块标记或额外说明。"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def clean_json_text(content: str) -> str:
    """清洗大模型返回文本，去掉代码块包裹、BOM 及 JSON 之外的说明文字。"""
    if not content:
        return ""

    cleaned = content.lstrip("\ufeff").strip()
    fenced = _CODE_FENCE_PATTERN.search(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return cleaned.strip()


def _snippet(content: str, limit: int = 300) -> str:
    """截取返回内容片段，便于异常信息定位问题。"""
    text = " ".join(content.split())
    return text if len(text) <= limit else f"{text[:limit]}..."


def parse_report(content: str) -> SelectionReport:
    """把大模型返回文本解析为 SelectionReport。"""
    cleaned = clean_json_text(content)
    if not cleaned:
        raise WorkflowError(f"大模型返回内容为空，无法解析 JSON；原始内容：{_snippet(content)}")

    try:
        payload: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise WorkflowError(
            f"大模型返回内容不是合法 JSON（{exc.msg}）；原始内容片段：{_snippet(content)}"
        ) from exc

    if not isinstance(payload, dict):
        raise WorkflowError(f"大模型返回的 JSON 顶层必须是对象；实际为 {type(payload).__name__}")

    try:
        return SelectionReport.model_validate(payload)
    except ValidationError as exc:
        raise WorkflowError(f"大模型返回的 JSON 结构不符合选型报告要求：{exc}") from exc


def _request_completion(client: OpenAI, messages: list[dict[str, str]]) -> str:
    """调用大模型并返回文本内容；调用失败抛出 WorkflowError。"""
    model = _get_required_env("LLM_MODEL")
    try:
        # 说明：按需求不使用 response_format=json_object，改为在 Prompt 中约束 JSON 输出。
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.3,
        )
    except Exception as exc:  # 网络、鉴权、限流、模型不存在等统一包装
        raise WorkflowError(f"调用大模型 {model} 失败：{exc}") from exc

    if not response.choices:
        raise WorkflowError(f"调用大模型 {model} 未返回任何结果（choices 为空）")

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise WorkflowError(f"调用大模型 {model} 返回内容为空")
    return content


def run_workflow(constraints: BusinessConstraints) -> SelectionReport:
    """执行技术选型工作流：输入业务约束，输出技术选型报告。"""
    description = constraints.description.strip()
    if not description:
        raise WorkflowError("业务约束描述不能为空")

    client = _get_client()
    messages = build_messages(description)

    last_error: str = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        content = _request_completion(client, messages)
        try:
            return parse_report(content)
        except WorkflowError as exc:
            last_error = str(exc)
            if attempt == MAX_ATTEMPTS:
                break
            # 上一次返回无法解析时，把原文回传并要求模型只输出合法 JSON 后重试一次
            messages = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "上面的回复无法解析为约定的 JSON（"
                        f"{last_error}）。请重新只输出符合约定的 JSON 对象，"
                        "不要包含 Markdown 代码块或任何额外文字。"
                    ),
                },
            ]

    raise WorkflowError(f"大模型返回内容无法解析为选型报告：{last_error}")
