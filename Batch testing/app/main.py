"""FastAPI 应用：评测流水线 API + 静态前端托管。"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import db
from .config import BASE_DIR, DIMENSION_WEIGHTS, DIMENSIONS
from .evaluator import CANCEL_FLAGS, RUN_TASKS, run_evaluation
from .parser import parse_file
from .report import build_report, export_csv
from .schemas import ReviewPayload

STATIC_DIR = BASE_DIR / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    # 重启后把遗留的 running 状态标记为中断
    db.execute("UPDATE runs SET status='failed' WHERE status='running'")
    db.execute("UPDATE results SET status='failed', error='服务中断' WHERE status='running'")
    yield


app = FastAPI(title="AI 应用评测流水线 (MVP)", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def normalize_config(cfg: dict) -> dict:
    model = cfg.get("model") or {}
    judge = cfg.get("judge") or {}
    if not judge.get("base_url") and not judge.get("model_name"):
        judge = dict(model)
    return {
        "model": model,
        "judge": judge,
        "concurrency": int(cfg.get("concurrency", 5) or 5),
        "max_retries": int(cfg.get("max_retries", 3) or 3),
        "timeout_seconds": float(cfg.get("timeout_seconds", 120) or 120),
        "temperature": float(cfg.get("temperature", 0.0) or 0.0),
        "judge_temperature": float(cfg.get("judge_temperature", 0.0) or 0.0),
        "stream": bool(cfg.get("stream", True)),
    }


def _start_run(run_id: int) -> None:
    task = asyncio.create_task(run_evaluation(run_id))
    RUN_TASKS[run_id] = task

@app.post("/api/runs")
async def create_run(
    name: str = Form(""),
    config: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        cfg = json.loads(config)
    except json.JSONDecodeError:
        raise HTTPException(400, "配置 JSON 解析失败")
    cfg = normalize_config(cfg)
    content = await file.read()
    if not content:
        raise HTTPException(400, "上传文件为空")
    try:
        cases = parse_file(content, file.filename or "")
    except Exception as e:
        raise HTTPException(400, f"测试集解析失败：{e}")
    if not cases:
        raise HTTPException(400, "测试集中没有有效用例")
    run_id = db.create_run((name or file.filename or "未命名").strip(), cfg)
    db.add_test_cases(run_id, cases)
    db.create_results_for_run(run_id)
    db.add_log(run_id, "info", f"已解析测试集 {file.filename}，共 {len(cases)} 条用例。")
    _start_run(run_id)
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    runs = db.list_runs()
    for r in runs:
        r["_counts"] = db.result_counts(r["id"])
    return runs


@app.get("/api/runs/{run_id}")
def get_run_detail(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "评测不存在")
    run["counts"] = db.result_counts(run_id)
    return run


@app.get("/api/runs/{run_id}/progress")
def progress(run_id: int, after_seq: int = 0):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "评测不存在")
    return {
        "status": run["status"],
        "counts": db.result_counts(run_id),
        "logs": db.get_logs(run_id, after_seq),
        "last_seq": db.last_log_seq(run_id),
    }


@app.get("/api/runs/{run_id}/report")
def report(run_id: int):
    if not db.get_run(run_id):
        raise HTTPException(404, "评测不存在")
    return build_report(run_id)


@app.get("/api/runs/{run_id}/results")
def results(run_id: int):
    return db.get_results(run_id)


@app.get("/api/runs/{run_id}/export")
def export(run_id: int, kind: str = "results"):
    data = export_csv(run_id, kind)
    filename = f"eval_report_{run_id}_{kind}.csv"
    return Response(
        content=data.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/runs/{run_id}/cancel")
def cancel(run_id: int):
    if not db.get_run(run_id):
        raise HTTPException(404, "评测不存在")
    CANCEL_FLAGS[run_id] = True
    db.update_run(run_id, status="cancelled")
    return {"ok": True}


@app.post("/api/runs/{run_id}/resume")
async def resume(run_id: int):
    if not db.get_run(run_id):
        raise HTTPException(404, "评测不存在")
    db.update_run(run_id, status="running")
    _start_run(run_id)
    return {"ok": True}


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "评测不存在")
    if run["status"] == "running":
        raise HTTPException(400, "评测正在运行，请先取消后再删除")
    CANCEL_FLAGS.pop(run_id, None)
    task = RUN_TASKS.pop(run_id, None)
    if task and not task.done():
        task.cancel()
    db.delete_run(run_id)
    return {"ok": True}


@app.post("/api/results/{result_id}/review")
def review(result_id: int, payload: ReviewPayload):
    res = db.get_result(result_id)
    if not res:
        raise HTTPException(404, "结果不存在")
    fields = {"human_reviewed": 1}
    if payload.human_pass is not None:
        fields["human_pass"] = int(payload.human_pass)
        fields["passed"] = int(payload.human_pass)
        fields["is_badcase"] = 0 if payload.human_pass else 1
    if payload.human_note is not None:
        fields["human_note"] = payload.human_note
    if payload.human_scores:
        cleaned = {}
        for key, _label, _w in DIMENSIONS:
            if key in payload.human_scores:
                try:
                    cleaned[key] = max(1.0, min(5.0, float(payload.human_scores[key])))
                except (TypeError, ValueError):
                    continue
        if cleaned:
            total = round(sum(cleaned[k] * DIMENSION_WEIGHTS[k] for k in cleaned), 3)
            fields["human_scores_json"] = json.dumps(cleaned, ensure_ascii=False)
            fields["human_score"] = total
    elif payload.human_score is not None:
        fields["human_score"] = float(payload.human_score)
    db.update_result(result_id, **fields)
    return {"ok": True}


@app.get("/api/history/trend")
def trend():
    runs = db.list_runs()
    out = []
    for r in runs:
        if r["status"] != "completed":
            continue
        rep = build_report(r["id"])
        ov = rep["overall"]
        out.append({
            "id": r["id"], "name": r["name"], "created_at": r["created_at"],
            "pass_rate": ov["pass_rate"], "avg_score": ov["avg_total_score"],
            "avg_latency_ms": ov["avg_latency_ms"], "avg_total_tokens": ov["avg_total_tokens"],
            "total": ov["total"],
        })
    out.reverse()
    return out

