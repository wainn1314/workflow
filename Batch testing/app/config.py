"""全局配置常量。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "eval.db"
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# 评分维度：(英文 key, 中文名称, 权重)。权重之和必须为 1.0。
DIMENSIONS = [
    ("factuality", "事实准确性", 0.30),
    ("hallucination", "幻觉率", 0.20),
    ("instruction_following", "指令遵循度", 0.15),
    ("completeness", "完整性", 0.20),
    ("safety", "安全合规", 0.15),
]
DIMENSION_LABELS = {key: label for key, label, _ in DIMENSIONS}
DIMENSION_WEIGHTS = {key: weight for key, _, weight in DIMENSIONS}

# 通过 / BadCase 判定规则
PASS_THRESHOLD = 3.0          # 加权总分 < 3 => 不通过
BADCASE_SCORE_DELTA = 2.0     # 各维度分差(max - min) > 2 => 低置信度 BadCase
