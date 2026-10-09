"""FastAPI 入口：提供前端页面、技术选型分析接口 /analyze 与健康检查接口 /health。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:  # 支持从项目根目录启动：uvicorn app.main:app
    from .models import BusinessConstraints, SelectionReport
    from .workflow import WorkflowError, run_workflow
except ImportError:  # 支持从 app 目录启动：uvicorn main:app
    from models import BusinessConstraints, SelectionReport
    from workflow import WorkflowError, run_workflow


# 前端静态资源目录（app/static），与启动时所在工作目录无关
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="大模型驱动的技术选型工作流",
    description=(
        "输入业务约束（业务场景、性能要求、团队规模、预算等），"
        "由大模型（DeepSeek，OpenAI SDK 兼容模式）分析并输出结构化技术选型报告。"
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """返回前端页面（单页：输入约束 → 展示选型报告）。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", summary="健康检查", tags=["system"])
async def health() -> dict[str, str]:
    """返回服务存活状态。"""
    return {"status": "ok"}


@app.post(
    "/analyze",
    response_model=SelectionReport,
    summary="生成技术选型报告",
    description="接收业务约束，调用大模型完成技术选型分析，返回结构化选型报告。",
    tags=["workflow"],
)
def analyze(constraints: BusinessConstraints) -> SelectionReport:
    """执行选型工作流。使用同步函数，由 FastAPI 放入线程池执行，避免阻塞事件循环。"""
    try:
        return run_workflow(constraints)
    except WorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # 兜底，避免把未处理异常直接暴露为 500 堆栈
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"选型工作流执行异常：{exc}",
        ) from exc


if __name__ == "__main__":  # 便于本地调试：python main.py
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
