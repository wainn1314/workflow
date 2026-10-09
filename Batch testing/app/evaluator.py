"""评测编排：并发调度、重试、断点续跑、多轮上下文维护。"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from . import db
from .judge import conversation_to_text, judge_case
from .llm_client import LLMClient, NonRetryableError, is_transient_error

RUN_TASKS: Dict[int, asyncio.Task] = {}
CANCEL_FLAGS: Dict[int, bool] = {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def log(run_id: int, level: str, message: str) -> None:
    db.add_log(run_id, level, message)


async def run_evaluation(run_id: int) -> None:
    run = db.get_run(run_id)
    if not run:
        return
    config = json.loads(run["config_json"])
    CANCEL_FLAGS[run_id] = False
    db.update_run(run_id, status="running", started_at=_now())

    model_client = LLMClient({
        **config.get("model", {}),
        "temperature": config.get("temperature", 0.0),
        "stream": config.get("stream", True),
        "timeout_seconds": config.get("timeout_seconds", 120.0),
    })
    judge_cfg = config.get("judge") or config.get("model") or {}
    judge_client = LLMClient({
        **judge_cfg,
        "temperature": config.get("judge_temperature", 0.0),
        "stream": False,
        "timeout_seconds": config.get("timeout_seconds", 120.0),
    })

    cases = db.get_test_cases(run_id)
    pending = [c for c in cases if c["result_status"] != "success"]
    total = len(cases)
    done = total - len(pending)
    log(run_id, "info",
        f"开始评测：共 {total} 条用例，已成功 {done} 条（断点续跑跳过），待处理 {len(pending)} 条。")
    if not pending:
        _finish_run(run_id)
        return

    concurrency = max(1, int(config.get("concurrency", 5)))
    sem = asyncio.Semaphore(concurrency)

    async def worker(case):
        async with sem:
            if not CANCEL_FLAGS.get(run_id):
                await process_case(run_id, case, model_client, judge_client, config)

    await asyncio.gather(*(worker(c) for c in pending))

    if CANCEL_FLAGS.get(run_id):
        db.update_run(run_id, status="cancelled", finished_at=_now())
        log(run_id, "warn", "评测已取消。")
    else:
        _finish_run(run_id)

def _finish_run(run_id: int) -> None:
    counts = db.result_counts(run_id)
    db.update_run(run_id, status="completed", finished_at=_now(),
                  stats_json=json.dumps(counts, ensure_ascii=False))
    log(run_id, "info",
        f"评测完成：成功 {counts['success']}，失败 {counts['failed']}，总计 {counts['total']}。")


def retry_delay(err: str, attempt: int) -> float:
    """重试冷却时间：限流/额度类错误需要更长冷却（Dify 免费额度常按分钟限流）。"""
    if is_transient_error(err):
        return 20.0
    return float(min(2 ** attempt, 8))


async def process_case(run_id: int, case, model_client, judge_client, config) -> None:
    result_id = case["result_id"]
    ref = case["ref_id"]
    max_retries = max(1, int(config.get("max_retries", 3)))
    for attempt in range(1, max_retries + 1):
        try:
            db.update_result(result_id, status="running",
                             attempt_count=(case["attempt_count"] or 0) + attempt, error=None)
            actual_output, turns, metrics = await invoke_model(model_client, case)
            conv_text = conversation_to_text(json.loads(case["conversation_json"]))
            judge = await judge_case(judge_client, conv_text, case["expected_output"], actual_output)
            db.update_result(
                result_id,
                status="success",
                actual_output=actual_output,
                turns_json=json.dumps(turns, ensure_ascii=False),
                ttft_ms=metrics["ttft_ms"],
                latency_ms=metrics["latency_ms"],
                input_tokens=metrics["input_tokens"],
                output_tokens=metrics["output_tokens"],
                total_tokens=metrics["total_tokens"],
                judge_json=json.dumps(judge, ensure_ascii=False),
                scores_json=json.dumps(judge["scores"], ensure_ascii=False),
                total_score=judge["total_score"],
                confidence=judge["confidence"],
                passed=judge["pass"],
                is_badcase=judge["is_badcase"],
                error=None,
            )
            log(run_id, "info",
                f"[{ref}] 完成，总分 {judge['total_score']}，{'通过' if judge['pass'] else '不通过'}。")
            return
        except Exception as e:
            if CANCEL_FLAGS.get(run_id):
                db.update_result(result_id, status="failed", error="已取消")
                return
            err = str(e)
            if isinstance(e, NonRetryableError):
                db.update_result(result_id, status="failed", error=err)
                log(run_id, "error", f"[{ref}] 失败（不可重试）：{err}")
                return
            if attempt < max_retries:
                log(run_id, "warn", f"[{ref}] 第 {attempt} 次失败，将重试：{err}")
                await asyncio.sleep(retry_delay(err, attempt))
            else:
                db.update_result(result_id, status="failed", error=err)
                log(run_id, "error", f"[{ref}] 最终失败：{err}")

async def invoke_model(model_client, case) -> Tuple[str, List[Dict], Dict[str, Any]]:
    conversation = json.loads(case["conversation_json"])
    history: List[Dict[str, str]] = [m for m in conversation if m.get("role") == "system"]
    turns: List[Dict[str, Any]] = []
    final = None
    agg = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    ttft_vals: List[float] = []
    latency_total = 0.0
    user_count = 0

    def record_turn(content_in: str, res) -> None:
        nonlocal final, latency_total, user_count
        user_count += 1
        final = res.content
        turns.append({
            "turn": user_count,
            "input": content_in,
            "output": res.content,
            "ttft_ms": res.ttft_ms,
            "latency_ms": res.latency_ms,
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "total_tokens": res.total_tokens,
        })
        agg["input_tokens"] += res.input_tokens
        agg["output_tokens"] += res.output_tokens
        agg["total_tokens"] += res.total_tokens
        latency_total += res.latency_ms
        if res.ttft_ms is not None:
            ttft_vals.append(res.ttft_ms)

    for m in conversation:
        role = m.get("role")
        if role == "system":
            continue
        if role == "user":
            history.append({"role": "user", "content": str(m.get("content", ""))})
            res = await model_client.chat(history)
            history.append({"role": "assistant", "content": res.content})
            record_turn(str(m.get("content", "")), res)
        elif role == "assistant":
            history.append({"role": "assistant", "content": str(m.get("content", ""))})

    if user_count == 0:
        text = conversation_to_text(conversation)
        res = await model_client.chat([{"role": "user", "content": text}])
        record_turn(text, res)

    if final is None:
        raise ValueError("conversation 中无 user 消息，无法评测")

    metrics = {
        "ttft_ms": round(sum(ttft_vals) / len(ttft_vals), 1) if ttft_vals else None,
        "latency_ms": round(latency_total, 1),
        "input_tokens": agg["input_tokens"],
        "output_tokens": agg["output_tokens"],
        "total_tokens": agg["total_tokens"],
        "turn_count": user_count,
    }
    return final, turns, metrics


