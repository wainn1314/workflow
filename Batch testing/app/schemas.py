"""Pydantic 请求/响应模型。"""
from typing import Dict, Optional

from pydantic import BaseModel


class ReviewPayload(BaseModel):
    """人工抽检复核提交的数据。"""
    human_pass: Optional[bool] = None
    human_score: Optional[float] = None
    human_scores: Optional[Dict[str, float]] = None
    human_note: Optional[str] = None
