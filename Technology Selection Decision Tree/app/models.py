"""数据模型定义：工作流输入（业务约束）与输出（技术选型报告）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BusinessConstraints(BaseModel):
    """用户用自然语言描述的业务约束和需求。"""

    description: str = Field(
        ...,
        min_length=1,
        description="用户用自然语言描述的业务约束和需求（业务场景、性能要求、团队规模、预算等）",
        examples=[
            "我们是一个 5 人的后端小团队，要做一个日活 10 万的电商订单系统，"
            "要求高并发写入、强一致性事务、预算有限、团队熟悉 Python 和 Java，"
            "请推荐合适的关系型数据库与后端框架组合。"
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": (
                    "我们是一个 5 人的后端小团队，要做一个日活 10 万的电商订单系统，"
                    "要求高并发写入、强一致性事务、预算有限，请推荐最合适的数据库方案。"
                )
            }
        }
    )


class SelectionReport(BaseModel):
    """大模型输出的技术选型报告。"""

    selected_tech: str = Field(..., description="选了什么技术")
    reason: str = Field(..., description="为什么选它")
    advantages: list[str] = Field(..., description="优势列表")
    disadvantages: list[str] = Field(..., description="劣势列表")
    alternatives: list[str] = Field(..., description="备选方案")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "selected_tech": "PostgreSQL 16 + FastAPI",
                "reason": "团队熟悉 Python，订单场景需要强一致性事务，PostgreSQL 在写入并发与事务能力上满足要求，且运维成本低于分布式方案。",
                "advantages": ["事务与一致性能力强", "生态成熟、社区活跃", "单机即可支撑目标规模，成本低"],
                "disadvantages": ["超大规模写入时需引入分库分表", "复杂分析场景性能弱于列式数据库"],
                "alternatives": ["MySQL 8 主从 + 读写分离", "TiDB 分布式数据库", "MongoDB 副本集"],
            }
        }
    )
