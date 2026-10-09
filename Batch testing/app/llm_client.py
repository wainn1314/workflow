"""LLM 客户端：OpenAI 兼容接口 + Dify 应用（对话 / 工作流 / 文本生成）。

支持流式 / TTFT / token 统计 / Mock，并提供 Dify 应用类型的自动判别与路由自愈。
"""
import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

# ---------------------------------------------------------------- Dify 路由 ---
# Dify Service API 按应用类型提供不同端点，用错端点会返回 400（如 not_chat_app）
_DIFY_ROUTES = {
    "chat": "chat-messages",
    "workflow": "workflows/run",
    "completion": "completion-messages",
}
# GET /info 返回的应用 mode -> 本客户端内部路由
_DIFY_MODE_ROUTE = {
    "chat": "chat",
    "agent": "chat",
    "agent-chat": "chat",
    "advanced-chat": "chat",
    "workflow": "workflow",
    "completion": "completion",
}
# 路由不匹配错误码 -> 需要改试的路由（按顺序尝试）
_DIFY_ROUTE_HINTS = {
    "not_chat_app": ("workflow", "completion"),
    "not_workflow_app": ("chat", "completion"),
    "not_completion_app": ("chat", "workflow"),
}
_DIFY_EXPLICIT_ROUTES = {"dify-chat": "chat", "dify-workflow": "workflow", "dify-completion": "completion"}

# 工作流 outputs 里优先作为"答案正文"的输出字段（按先后顺序）
_PRIMARY_OUTPUT_KEYS = (
    "questions", "question", "quiz", "quiz_list", "results", "result",
    "output", "outputs", "text", "answer", "content", "data", "summary",
)
# 需要保留的状态/提示类字段（即使是 true/false 这种标记）
_WARN_OUTPUT_KEYS = ("error", "errors", "message", "warning", "warnings", "success", "status", "reason")
_FLAG_VALUES = {
    "true", "false", "yes", "no", "ok", "success", "succeeded", "failed",
    "none", "null", "1", "0",
}
# 应用内部判定失败的标记值（success/status 字段）
_FAILURE_FLAG_VALUES = {"false", "no", "failed", "fail", "error", "0"}
# 视为"没有正文"的取值
_EMPTY_BODY_VALUES = {"[]", "{}", "null", "none", "0"}
# 用于说明失败原因的字段
_DETAIL_OUTPUT_KEYS = ("error", "errors", "message", "reason", "warning", "warnings")

# ------------------------------------------------- 工作流 Start 变量自动映射 ---
_DIFFICULTY_GROUPS = (
    ("easy", ("简单", "容易", "基础", "低难度", "简单难度", "easy", "low")),
    ("medium", ("中等", "一般", "中等难度", "medium", "middle")),
    ("hard", ("困难", "高难度", "复杂", "hard", "high")),
)
_QUESTION_TYPE_GROUPS = (
    ("单选题", ("单选题", "单项选择", "单选", "single_choice", "single")),
    ("多选题", ("多选题", "多项选择", "多选", "multiple_choice", "multiple")),
    ("判断题", ("判断题", "判断", "对错题", "true_false", "true/false", "judge")),
    ("填空题", ("填空题", "填空", "fill_blank", "fill")),
    ("简答题", ("简答题", "简答", "问答", "short_answer", "short")),
)
_CN_DIGITS = {"零": 0, "一": 1, "两": 2, "二": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

# 变量名语义分组（用于把用户指令映射到工作流 Start 变量）
_COUNT_NAMES = ("count", "num", "number", "question_count", "quiz_count", "题目数量", "数量")
_DIFFICULTY_NAMES = ("difficulty", "level", "difficulty_level", "难度")
_TYPE_NAMES = ("type", "types", "question_type", "question_types", "题型")
_TOPIC_NAMES = ("topic", "subject", "theme", "keywords", "keyword", "query", "question",
                "user_input", "userinput", "input", "prompt", "instruction", "requirement",
                "主题", "问题", "需求", "关键词")
_MATERIAL_NAMES = ("context", "material", "materials", "knowledge", "reference",
                   "reference_material", "source", "资料", "材料", "内容", "文本")
_SKIP_VAR_TYPES = ("file", "file-list", "files", "image")

_TEXT_VAR_TYPES = ("text-input", "paragraph", "text")


class NonRetryableError(RuntimeError):
    """执行类失败，重试也不会成功（例如应用内部直接判定失败、参数不合法），

    评测器遇到该异常会立即记为失败，不再消耗重试次数与额度。
    """


@dataclass
class LLMResult:
    content: str
    ttft_ms: Optional[float] = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


def estimate_tokens(text: str) -> int:
    """粗略 token 估算：CJK 字符约 1 token，其余约 4 字符 1 token。"""
    if not text:
        return 0
    cjk = sum(1 for c in text if ord(c) > 0x2E7F)
    other = len(text) - cjk
    return max(1, cjk + (other // 4))


def normalize_base_url(base_url: str) -> str:
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return url
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"


def detect_provider(base_url: str, api_key: str, provider: str = "") -> str:
    """识别接口协议：openai，或 dify / dify-chat / dify-workflow / dify-completion。

    显式传入的 provider 优先；否则按 Dify 的典型特征自动识别：
    - API Key 以 app- 开头（Dify 应用密钥格式）；
    - Base URL 中包含 "dify"。

    provider = "dify" 表示"自动判别应用类型"：运行时用 GET /info 的 mode 字段
    判断走 chat / workflow / completion 哪条路由，遇到 not_chat_app 等错误自动改试。
    """
    if provider:
        return provider.strip().lower()
    if (api_key or "").strip().startswith("app-"):
        return "dify"
    if base_url and "dify" in base_url.lower():
        return "dify"
    return "openai"


def _dify_root_url(base_url: str) -> str:
    """把用户填写的 Dify 地址收敛为 API 根地址（如 https://api.dify.ai/v1）。"""
    url = (base_url or "").strip().rstrip("/")
    for suffix in ("/chat-messages", "/completion-messages", "/workflows/run", "/parameters", "/info"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            break
    if not url:
        return "https://api.dify.ai/v1"
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


class _DifyRouteMismatch(RuntimeError):
    """Dify 返回"应用类型与端点不匹配"错误（not_chat_app 等），用于内部改试路由。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# 限流/额度类错误特征（Dify 免费额度常按分钟限流，属瞬时错误，值得重试）
_RATE_LIMIT_HINTS = ("rate limit", "too many requests", "quota exceeded", "429")
# 应用接口调用成功但内部没产出内容的错误标记（多由知识库检索失败/限流引起，属瞬时问题）
_NO_CONTENT_MARKER = "未产出可用内容"


def is_rate_limit_error(text: str) -> bool:
    """判断错误信息是否属于限流/额度类（评测器据此使用更长的重试冷却时间）。"""
    low = (text or "").lower()
    return any(hint in low for hint in _RATE_LIMIT_HINTS)


def is_transient_error(text: str) -> bool:
    """限流/额度类，或"应用跑完但没产出内容"——都值得拉长冷却后重试。"""
    return is_rate_limit_error(text) or _NO_CONTENT_MARKER in (text or "")


def _dify_error_hint(status_code: int, body: str) -> Optional[str]:
    """从 Dify 错误响应体中提取路由不匹配的错误码。"""
    if status_code != 400:
        return None
    low = (body or "").lower()
    for code in _DIFY_ROUTE_HINTS:
        if code in low:
            return code
    return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, indent=2)


def _looks_like_flag(text: str) -> bool:
    return text.strip().lower() in _FLAG_VALUES


def workflow_output_failure(outputs: Any) -> Optional[str]:
    """识别\"接口调用成功、但应用内部判定失败且没有正文\"的情况。

    例如工作流返回 {"success": "False", "questions": "[]", "error": "questions 为空或格式不正确"}，
    此时应用并未产出任何可用内容（多为应用内知识库检索/JSON 解析节点配置问题），
    应作为执行失败上报，而不是拿一句错误提示去参加评分。
    """
    if not isinstance(outputs, dict):
        return None
    flag = ""
    for key in ("success", "status", "ok"):
        if key in outputs:
            text = _stringify(outputs[key]).strip().lower()
            if text:
                flag = text
                break
    if flag not in _FAILURE_FLAG_VALUES:
        return None
    body = ""
    for key in _PRIMARY_OUTPUT_KEYS:
        if key in outputs:
            body = _stringify(outputs[key]).strip()
            break
    if body and body not in _EMPTY_BODY_VALUES:
        return None
    detail = ""
    for key in _DETAIL_OUTPUT_KEYS:
        if key in outputs and _stringify(outputs[key]).strip():
            detail = _stringify(outputs[key]).strip()
            break
    return detail or f"应用返回 success={flag}，且未产出正文"


def flatten_workflow_outputs(outputs: Any) -> str:
    """把 Dify 工作流的 outputs 汇总为评测文本（保留失败/提示类字段）。"""
    if isinstance(outputs, str):
        return outputs.strip()
    if not isinstance(outputs, dict):
        return _stringify(outputs)
    texts = {str(k): _stringify(v) for k, v in outputs.items()}
    texts = {k: v for k, v in texts.items() if v}
    if not texts:
        return ""
    primary = next(
        (k for k in _PRIMARY_OUTPUT_KEYS if k in texts and not _looks_like_flag(texts[k])), None
    )
    if primary is None:
        primary = max(texts, key=lambda k: (not _looks_like_flag(texts[k]), len(texts[k])))
    parts = [texts.pop(primary)]
    for key, value in texts.items():
        if key not in _WARN_OUTPUT_KEYS and len(value) < 20:
            continue
        if _looks_like_flag(value) and value.strip().lower() in {"true", "yes", "ok", "success", "succeeded"}:
            continue
        parts.append(f"{key}: {value}")
    return "\n\n".join(parts)


def _cn_number(token: str) -> Optional[int]:
    """中文数字转阿拉伯数字（支持"一"到"十"及"十几"）。"""
    if not token:
        return None
    if token in _CN_DIGITS:
        return _CN_DIGITS[token]
    if "十" in token:
        head, _, tail = token.partition("十")
        tens = _CN_DIGITS.get(head, 1) if head else 1
        ones = _CN_DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    return None


def _extract_count(text: str) -> Optional[int]:
    """从用户指令里解析题目数量，如"生成3道""出5题""各2道""出一道"。"""
    m = re.search(r"(\d+)\s*(?:道|题|个)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"([一二两三四五六七八九十]+)\s*(?:道|题|个)", text)
    if m:
        return _cn_number(m.group(1))
    return None


def _extract_difficulty_key(text: str) -> Optional[str]:
    """解析难度关键词，返回 easy / medium / hard。"""
    low = text.lower()
    for key, tokens in _DIFFICULTY_GROUPS:
        if any(tok in low for tok in tokens):
            return key
    return None


def _extract_types(text: str) -> List[str]:
    """按出现顺序解析题型关键词，返回中文题型名（如 ['单选题', '判断题']）。"""
    low = text.lower()
    hits: List[Tuple[int, str]] = []
    for label, tokens in _QUESTION_TYPE_GROUPS:
        positions = [low.find(tok) for tok in tokens]
        positions = [p for p in positions if p >= 0]
        if positions:
            hits.append((min(positions), label))
    hits.sort(key=lambda item: item[0])
    ordered: List[str] = []
    for _, label in hits:
        if label not in ordered:
            ordered.append(label)
    return ordered


_TOPIC_PATTERNS = (
    r"关于[“\"']?([^，。；;、\s]{2,30}?)[”\"']?的?(?:单选题|多选题|判断题|填空题|简答题|题|问题|内容)",
    r"针对[“\"']([^”\"']{2,40})[”\"']",
    r"针对([^，。；;、]{2,30}?)(?:各?出\d*道|出\d*题|的题)",
    r"主题(?:围绕|是|为|：|:)?\s*([^，。；;]+)",
    r"(?:围绕|聚焦于?|涉及)([^，。；;]{2,30}?)(?:的?(?:题|内容|主题|出题))",
    r"知识库中关于([^，。；;]{2,30}?)的内容",
)
# 兜底规则：多段引号主题（如 知识库中"用户画像"和"个性化推荐"两段内容），
# 排在引号合并规则之后，避免把"两段内容"等修饰语吃进主题里。
_TOPIC_FALLBACK_PATTERNS = (
    r"知识库中([^“”\"']{2,30}?)的?内容",
    r"知识库中([^，。；;]{2,30}?)的?内容",
)


def _clean_topic(value: str) -> str:
    return re.sub(r"^(关于|针对|围绕|主题)", "", (value or "").strip()).strip()


def _extract_topic(text: str) -> Optional[str]:
    """尽力从用户指令里解析出题主题；解析不到返回 None，由调用方决定兜底策略。"""
    for pattern in _TOPIC_PATTERNS:
        m = re.search(pattern, text)
        if m:
            topic = _clean_topic(m.group(1))
            if topic:
                return topic
    quoted = re.findall(r"[“\"']([^”\"']{2,40})[”\"']", text)
    topics = [q.strip() for q in quoted if q.strip()]
    if topics:
        return "、".join(dict.fromkeys(topics))
    for pattern in _TOPIC_FALLBACK_PATTERNS:
        m = re.search(pattern, text)
        if m:
            topic = _clean_topic(m.group(1))
            if topic:
                return topic
    return None


def _extract_material(text: str) -> Optional[str]:
    """"根据以下材料出2道题：xxx" 类用例：冒号后的正文作为工作流 context/材料变量。"""
    for sep in ("：", ":"):
        if sep in text:
            tail = text.rsplit(sep, 1)[1].strip().rstrip("。").strip()
            if len(tail) >= 8 and not tail.endswith(("？", "?")):
                return tail
    return None


def parse_workflow_intent(text: str) -> Dict[str, Any]:
    """把一条自然语言出题指令解析为工作流入参意图（供 Start 变量自动映射使用）。"""
    text = str(text or "")
    return {
        "count": _extract_count(text),
        "difficulty": _extract_difficulty_key(text),
        "types": _extract_types(text),
        "topic": _extract_topic(text),
        "material": _extract_material(text),
    }


def _match_by_alias(candidate: str, groups: Sequence[Tuple[str, Sequence[str]]]) -> Optional[str]:
    """在候选项（变量名、枚举值等）中匹配语义分组，返回分组 key（easy/单选题...）。"""
    low = (candidate or "").strip().lower()
    if not low:
        return None
    for key, tokens in groups:
        if low == key.lower():
            return key
        for token in tokens:
            token_low = token.lower()
            if low == token_low or token_low in low or low in token_low:
                return key
    return None


def _match_option(options: Sequence[Any], groups: Sequence[Tuple[str, Sequence[str]]], wanted: str) -> Optional[str]:
    """在 select 变量的 options 里找出与 wanted（如 easy/单选题）语义一致的取值。"""
    for option in options or []:
        if _match_by_alias(str(option), groups) == wanted:
            return str(option)
    return None


def _var_kind(name: str) -> str:
    """按变量名猜测语义：count / difficulty / type / topic / material / unknown。"""
    low = (name or "").strip().lower()
    for key, names in (("count", _COUNT_NAMES), ("difficulty", _DIFFICULTY_NAMES), ("type", _TYPE_NAMES)):
        if low in names:
            return key
    for key, names in (("count", _COUNT_NAMES), ("difficulty", _DIFFICULTY_NAMES), ("type", _TYPE_NAMES),
                       ("material", _MATERIAL_NAMES), ("topic", _TOPIC_NAMES)):
        if any(n in low for n in names):
            return key
    return "unknown"


def _spec_of(item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """把 user_input_form 的一项拆成 (变量类型, 变量定义)。"""
    if not isinstance(item, dict):
        return "", {}
    for var_type, spec in item.items():
        if isinstance(spec, dict):
            return str(spec.get("type") or var_type), spec
    return "", {}


def _coerce_number(value: Any, spec: Dict[str, Any]) -> Optional[Any]:
    """把值转成 number 类型变量能接受的数值，失败时退回变量 default。"""
    try:
        num = float(str(value).strip())
    except (TypeError, ValueError):
        try:
            num = float(str(spec.get("default")).strip())
        except (TypeError, ValueError):
            return None
    return int(num) if num.is_integer() else num


def _truncate(value: str, spec: Dict[str, Any]) -> str:
    try:
        limit = int(spec.get("max_length") or 0)
    except (TypeError, ValueError):
        limit = 0
    return value[:limit] if limit > 0 and len(value) > limit else value


def build_workflow_inputs(
    user_input_form: Sequence[Dict[str, Any]],
    raw_query: str,
    override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """按 Start 变量定义把用户指令映射为 Dify 工作流 inputs。

    映射规则（未识别的必填文本变量兜底填原始指令，保证应用能被调用起来）：
    - count / 数量       -> 指令中解析出的题目数，否则用变量 default；
    - difficulty / 难度  -> 解析出的难度（中英文均可），否则用 default 或首个选项；
    - type / 题型        -> 解析出的题型（如"单选题、判断题"），select 变量则匹配选项；
    - topic / 主题       -> 解析出的主题，否则原始指令；
    - context / 材料/内容 -> 指令中"："后（或"材料/内容"）的正文；
    - 其他变量           -> 必填时填原始指令，选填时留空不发送。

    override（界面里手工配置的 workflow_inputs）优先级最高；取值为 "$query"
    代表原始用户指令，取值为 null / "" 表示不发送该变量。
    """
    intent = parse_workflow_intent(raw_query)
    inputs: Dict[str, Any] = {}
    for item in user_input_form or []:
        var_type, spec = _spec_of(item)
        name = str(spec.get("variable") or "").strip()
        if not name or var_type in _SKIP_VAR_TYPES:
            continue
        kind = _var_kind(name)
        required = bool(spec.get("required"))
        options = spec.get("options") or []
        default = spec.get("default")
        value: Any = None

        if var_type == "select":
            if kind == "difficulty":
                if intent["difficulty"]:
                    value = _match_option(options, _DIFFICULTY_GROUPS, intent["difficulty"])
                if value is None and default:
                    value = _match_option(options, _DIFFICULTY_GROUPS, str(default)) or default
                if value is None and required and options:
                    value = options[0]
            elif kind == "type":
                for label in intent["types"]:
                    value = _match_option(options, _QUESTION_TYPE_GROUPS, label)
                    if value:
                        break
                if value is None and required and options:
                    value = default or options[0]
            elif required and options:
                value = default or options[0]
        elif var_type == "number":
            if kind == "count" and intent["count"] is not None:
                value = _coerce_number(intent["count"], spec)
            if value is None and default not in (None, ""):
                value = _coerce_number(default, spec)
        elif var_type in _TEXT_VAR_TYPES:
            if kind == "count" and intent["count"] is not None:
                value = str(intent["count"])
            elif kind == "difficulty" and intent["difficulty"]:
                value = intent["difficulty"]
            elif kind == "type":
                value = "、".join(intent["types"]) or (raw_query if required else None)
            elif kind == "material":
                value = intent["material"] or (raw_query if required else None)
            elif kind == "topic":
                value = intent["topic"] or raw_query
            elif required:
                value = raw_query
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        is_text = var_type in _TEXT_VAR_TYPES
        inputs[name] = _truncate(value, spec) if isinstance(value, str) and is_text else value
    _apply_input_overrides(inputs, user_input_form, raw_query, override)
    return inputs


def _apply_input_overrides(
    inputs: Dict[str, Any],
    user_input_form: Sequence[Dict[str, Any]],
    raw_query: str,
    override: Optional[Dict[str, Any]],
) -> None:
    """把界面手工配置的 workflow_inputs 覆盖到自动映射结果上（就地修改 inputs）。"""
    specs = {str(s.get("variable") or "").strip(): s for _, s in (_spec_of(i) for i in user_input_form or [])}
    for key, raw in (override or {}).items():
        name = str(key).strip()
        if not name:
            continue
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            inputs.pop(name, None)
            continue
        if isinstance(raw, str) and raw.strip() == "$query":
            inputs[name] = raw_query
            continue
        spec = specs.get(name) or {}
        if str(spec.get("type") or "") == "number":
            coerced = _coerce_number(raw, spec)
            if coerced is not None:
                inputs[name] = coerced
            continue
        if isinstance(raw, str) and str(spec.get("type") or "") in _TEXT_VAR_TYPES:
            inputs[name] = _truncate(raw, spec)
        else:
            inputs[name] = raw


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        raw_base = (config.get("base_url", "") or "").strip().rstrip("/")
        self.api_key = config.get("api_key", "")
        self.provider = detect_provider(raw_base, self.api_key, config.get("provider", ""))
        self.is_dify = self.provider == "dify" or self.provider in _DIFY_EXPLICIT_ROUTES
        # Dify 应用不走 OpenAI 兼容端点，而是 /chat-messages、/workflows/run 等
        self.dify_root = _dify_root_url(raw_base) if self.is_dify else ""
        self.dify_mode = _DIFY_EXPLICIT_ROUTES.get(self.provider, "")
        self.workflow_inputs_override = dict(config.get("workflow_inputs") or {})
        self.user_id = str(config.get("user") or "eval-pipeline")
        self._workflow_form: Optional[List[Dict[str, Any]]] = None
        self.base_url = f"{self.dify_root}/{_DIFY_ROUTES['chat']}" if self.is_dify else normalize_base_url(raw_base)
        self.model = config.get("model_name", "")
        self.timeout = float(config.get("timeout_seconds", 120.0))
        self.temperature = float(config.get("temperature", 0.0))
        self.stream = bool(config.get("stream", True))
        self.mock = bool(config.get("mock", False))

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(self, messages, stream: bool, max_tokens: Optional[int]):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    async def chat(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None) -> LLMResult:
        if self.mock:
            return await self._mock_chat(messages)
        if self.is_dify:
            return await self._dify_generate(messages, max_tokens)
        if self.stream:
            try:
                return await self._chat_stream(messages, max_tokens)
            except Exception:
                return await self._chat_once(messages, max_tokens)
        return await self._chat_once(messages, max_tokens)

    async def _chat_once(self, messages, max_tokens: Optional[int]) -> LLMResult:
        start = time.perf_counter()
        payload = self._payload(messages, False, max_tokens)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.base_url, json=payload, headers=self._headers())
            latency = (time.perf_counter() - start) * 1000
            if resp.status_code != 200:
                raise RuntimeError(f"LLM API 返回 {resp.status_code}: {resp.text[:400]}")
            obj = resp.json()
        return self._parse_response(obj, messages, latency)

    async def _chat_stream(self, messages, max_tokens: Optional[int]) -> LLMResult:
        start = time.perf_counter()
        payload = self._payload(messages, True, max_tokens)
        ttft: Optional[float] = None
        parts: List[str] = []
        usage: Dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", self.base_url, json=payload, headers=self._headers()) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode("utf-8", "ignore")[:400]
                    raise RuntimeError(f"LLM API 返回 {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("usage"):
                        usage = obj["usage"]
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        if ttft is None:
                            ttft = (time.perf_counter() - start) * 1000
                        parts.append(content)
        latency = (time.perf_counter() - start) * 1000
        content = "".join(parts)
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        if input_tokens is None:
            input_tokens = estimate_tokens(self._messages_text(messages))
        if output_tokens is None:
            output_tokens = estimate_tokens(content)
        if total_tokens is None:
            total_tokens = int(input_tokens) + int(output_tokens)
        return LLMResult(content=content, ttft_ms=ttft, latency_ms=latency,
                         input_tokens=int(input_tokens), output_tokens=int(output_tokens),
                         total_tokens=int(total_tokens))

    def _parse_response(self, obj: Dict[str, Any], messages, latency: float) -> LLMResult:
        choices = obj.get("choices") or []
        content = ""
        if choices:
            content = (choices[0].get("message") or {}).get("content") or ""
        usage = obj.get("usage") or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        if input_tokens is None:
            input_tokens = estimate_tokens(self._messages_text(messages))
        if output_tokens is None:
            output_tokens = estimate_tokens(content)
        if total_tokens is None:
            total_tokens = int(input_tokens) + int(output_tokens)
        return LLMResult(content=content, ttft_ms=None, latency_ms=latency,
                         input_tokens=int(input_tokens), output_tokens=int(output_tokens),
                         total_tokens=int(total_tokens))

    @staticmethod
    def _messages_text(messages) -> str:
        return "\n".join(str(m.get("content", "")) for m in messages)

    # ------------------------------------------------------------ Dify 应用 ---
    async def _dify_generate(self, messages, max_tokens: Optional[int] = None) -> LLMResult:
        """调用 Dify 应用：自动判别应用类型并请求对应端点。

        - chat（chat / agent / advanced-chat）-> POST /chat-messages
        - workflow                            -> POST /workflows/run（blocking，读 outputs）
        - completion                          -> POST /completion-messages

        若 Dify 返回 not_chat_app / not_workflow_app / not_completion_app，说明路由
        判断有误，自动改试其它端点，并把确定下来的路由缓存到 self.dify_mode。
        """
        query, last_user = self._collect_dify_queries(messages)
        if not (self.api_key or "").strip():
            raise NonRetryableError("未配置 Dify 应用的 API Key（Base URL 或 Key 命中 dify 特征时会走 Dify 协议）")
        mode = await self._resolve_dify_mode()
        attempted: List[str] = []
        last_error: Optional[Exception] = None
        while mode and mode not in attempted:
            attempted.append(mode)
            try:
                return await self._dify_request(mode, query, last_user)
            except _DifyRouteMismatch as exc:
                last_error = exc
                nxt = next((m for m in _DIFY_ROUTE_HINTS.get(exc.code, ()) if m not in attempted), None)
                if not nxt:
                    break
                self.dify_mode = nxt
                mode = nxt
        # 三条路由都被 Dify 拒绝：说明该 Key 不是应用密钥/应用已删除，重试没有意义
        raise NonRetryableError(
            f"Dify 应用类型无法确定（已尝试 {attempted}），请检查 API Key 是否与 Base URL 匹配、应用是否存在："
            f"{last_error or '无响应详情'}"
        )

    async def _resolve_dify_mode(self) -> str:
        """确定走哪条 Dify 路由：显式配置优先，否则读 GET /info 的 mode 字段。"""
        if self.dify_mode:
            return self.dify_mode
        app_mode = await self._fetch_dify_app_mode()
        if app_mode:
            self.dify_mode = _DIFY_MODE_ROUTE.get(app_mode.lower(), "chat")
            return self.dify_mode
        # /info 读不到（网络抖动/额度受限等）：按 provider 显式提示兜底为 chat，
        # 但**不写入** self.dify_mode，避免把一次失败的结果固化影响后续调用。
        return _DIFY_EXPLICIT_ROUTES.get(self.provider, "chat")

    async def _fetch_dify_app_mode(self, attempts: int = 3) -> Optional[str]:
        """GET /info 读取应用基本信息（含 mode 字段），失败重试几次，仍失败返回 None。"""
        for i in range(max(1, attempts)):
            try:
                obj = await self._dify_get("info")
            except Exception:
                if i + 1 < attempts:
                    await asyncio.sleep(1.5)
                continue
            if isinstance(obj, dict):
                return str(obj.get("mode") or "").strip() or None
            return None
        return None

    @staticmethod
    def _collect_dify_queries(messages) -> Tuple[str, str]:
        """Dify 应用没有 system/user 角色分离，只有一个 query 输入。

        把 system 消息内容拼到 query 前面（保证评测自包含，即使应用未内置
        系统提示词也能拿到指令），多轮对话取最后一条 user 消息。同时返回
        最后一条 user 消息原文，供工作流 Start 变量映射解析（题型/数量/难度）。
        """
        system_parts: List[str] = []
        user_parts: List[str] = []
        for m in messages:
            role = m.get("role")
            content = str(m.get("content", "") or "").strip()
            if not content:
                continue
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                user_parts.append(content)
        last_user = user_parts[-1] if user_parts else ""
        query = last_user or (system_parts[-1] if system_parts else "")
        if system_parts:
            query = "\n\n".join(system_parts) + "\n\n" + query
        return query.strip(), last_user

    def _dify_route_url(self, mode: str) -> str:
        return f"{self.dify_root}/{_DIFY_ROUTES[mode]}"

    async def _dify_request(self, mode: str, query: str, last_user: str) -> LLMResult:
        """按路由分发到具体的 Dify 端点请求实现。"""
        if mode == "workflow":
            return await self._dify_workflow_request(query, last_user)
        if mode == "completion":
            return await self._dify_completion_request(query, last_user)
        return await self._dify_chat_request(query)

    async def _dify_get(self, path: str) -> Any:
        """GET /info、GET /parameters 等只读接口。"""
        url = f"{self.dify_root}/{path}"
        async with httpx.AsyncClient(timeout=min(self.timeout, 30.0)) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise RuntimeError(self._describe_failure("GET", path, resp.status_code, resp.text))
            return resp.json()

    @staticmethod
    def _describe_failure(method: str, route: str, status_code: int, body: str) -> str:
        message = f"LLM API 返回 {status_code}（{method} /v1/{route}）: {body[:400]}"
        if is_rate_limit_error(body):
            return f"{message}；Dify 触发限流，请降低 concurrency 或稍后重试。"
        return message

    async def _dify_post(self, mode: str, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """POST 到对应 Dify 端点，返回 (响应体, 耗时毫秒)。"""
        route = _DIFY_ROUTES[mode]
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self._dify_route_url(mode), json=payload, headers=self._headers())
            latency = (time.perf_counter() - start) * 1000
            if resp.status_code != 200:
                hint = _dify_error_hint(resp.status_code, resp.text)
                if hint:
                    raise _DifyRouteMismatch(hint, self._describe_failure("POST", route, resp.status_code, resp.text))
                raise RuntimeError(self._describe_failure("POST", route, resp.status_code, resp.text))
            return resp.json(), latency

    def _finish_dify_result(
        self,
        content: str,
        latency: float,
        query: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        fallback_input: Optional[int] = None,
    ) -> LLMResult:
        """统一补齐 token 统计（Dify 各端点返回的 usage 字段并不一致）。"""
        in_tokens = input_tokens
        if in_tokens is None:
            in_tokens = fallback_input if fallback_input is not None else estimate_tokens(query)
        out_tokens = output_tokens if output_tokens is not None else estimate_tokens(content)
        if total_tokens is not None and int(total_tokens) > int(in_tokens):
            out_tokens = int(total_tokens) - int(in_tokens)
        total = int(total_tokens) if total_tokens is not None else int(in_tokens) + int(out_tokens)
        return LLMResult(content=content, ttft_ms=None, latency_ms=latency,
                         input_tokens=int(in_tokens), output_tokens=int(out_tokens),
                         total_tokens=int(total))

    async def _dify_chat_request(self, query: str) -> LLMResult:
        """调用 Dify 对话类应用（chat / agent / advanced-chat，阻塞模式）。"""
        payload = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "conversation_id": "",
            "user": self.user_id,
        }
        obj, latency = await self._dify_post("chat", payload)
        answer = obj.get("answer") or ""
        usage = (obj.get("metadata") or {}).get("usage") or {}
        return self._finish_dify_result(
            answer, latency, query,
            usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens"),
        )

    async def _dify_workflow_request(self, query: str, last_user: str) -> LLMResult:
        """调用 Dify 工作流应用（POST /workflows/run，阻塞模式，读 data.outputs）。

        工作流没有自由文本入口，输入是 Start 节点的结构化变量（如
        difficulty / count / type / topic / context），因此这里先取
        GET /parameters 的变量定义，再把用户指令映射为 inputs。
        """
        form = await self._dify_workflow_parameters()
        inputs = build_workflow_inputs(form, last_user or query, self.workflow_inputs_override)
        payload = {"inputs": inputs, "response_mode": "blocking", "user": self.user_id}
        obj, latency = await self._dify_post("workflow", payload)
        data = obj.get("data") or {}
        status = str(data.get("status") or "").lower()
        outputs = data.get("outputs")
        content = flatten_workflow_outputs(outputs)
        if status and status not in ("succeeded", "success"):
            detail = data.get("error") or content[:300] or "无错误详情"
            raise RuntimeError(f"Dify 工作流执行失败（status={status}）: {detail}")
        app_failure = workflow_output_failure(outputs)
        if app_failure:
            # 接口 200 但应用内部判定失败且没有正文（多为知识库检索失败/限流、或 JSON 解析不通过），
            # 属于瞬时问题，交给评测器按 max_retries 重试，并把应用给的原因写进错误信息。
            raise RuntimeError(
                f"Dify 工作流未产出可用内容（inputs={json.dumps(inputs, ensure_ascii=False)}）：{app_failure}"
            )
        if not content.strip():
            raise RuntimeError("Dify 工作流未返回任何输出（data.outputs 为空）")
        fallback = estimate_tokens(query) + estimate_tokens(json.dumps(inputs, ensure_ascii=False))
        return self._finish_dify_result(content, latency, query, total_tokens=data.get("total_tokens"),
                                        fallback_input=fallback)

    async def _dify_completion_request(self, query: str, last_user: str) -> LLMResult:
        """调用 Dify 文本生成应用（POST /completion-messages，阻塞模式）。"""
        form = await self._dify_workflow_parameters()
        inputs = build_workflow_inputs(form, last_user or query, self.workflow_inputs_override)
        payload = {"inputs": inputs, "query": query, "response_mode": "blocking", "user": self.user_id}
        obj, latency = await self._dify_post("completion", payload)
        answer = obj.get("answer") or ""
        usage = (obj.get("metadata") or {}).get("usage") or {}
        return self._finish_dify_result(
            answer, latency, query,
            usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens"),
        )

    async def _dify_workflow_parameters(self) -> List[Dict[str, Any]]:
        """GET /parameters 取 Start 节点的输入变量定义（失败时返回空列表）。"""
        if self._workflow_form is None:
            try:
                obj = await self._dify_get("parameters")
                form = obj.get("user_input_form") if isinstance(obj, dict) else None
                self._workflow_form = [i for i in (form or []) if isinstance(i, dict)]
            except Exception:
                self._workflow_form = []
        return self._workflow_form

    async def _mock_chat(self, messages) -> LLMResult:
        await asyncio.sleep(0.05)
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = str(m.get("content", ""))
                break
        content = (
            f"【Mock 回答】针对您的问题“{last_user[:60]}”，"
            "根据相关规则与资料，回复如下：这是一段用于评测演示的模拟回答内容，"
            "已覆盖主要信息点，格式规范、语义清晰，符合安全合规要求。"
        )
        input_tokens = estimate_tokens(self._messages_text(messages))
        output_tokens = estimate_tokens(content)
        return LLMResult(content=content, ttft_ms=40.0, latency_ms=120.0,
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         total_tokens=input_tokens + output_tokens)

