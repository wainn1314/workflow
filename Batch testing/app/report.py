"""评测报告聚合与 CSV 导出。"""
import csv
import io
import json
from typing import Any, Dict, List

from . import db
from .config import DIMENSION_LABELS, DIMENSIONS


def _json_loads(s, default):
    try:
        return json.loads(s) if s else default
    except (TypeError, json.JSONDecodeError):
        return default


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _score_dict(scores_json):
    return _json_loads(scores_json, {})


def build_report(run_id: int) -> Dict[str, Any]:
    run = db.get_run(run_id)
    results = db.get_results(run_id)
    scored = [r for r in results if r["status"] == "success" and r["scores_json"]]

    def dim_averages(rows):
        avgs = {}
        for key, _label, _w in DIMENSIONS:
            vals = []
            for r in rows:
                s = _score_dict(r["scores_json"])
                if key in s:
                    vals.append(s[key])
            avgs[key] = _avg(vals)
        return avgs

    def group_stats(rows, group_key):
        groups: Dict[str, List] = {}
        for r in rows:
            groups.setdefault(r.get(group_key) or "未分类", []).append(r)
        out = []
        for g, gr in sorted(groups.items()):
            scored_g = [r for r in gr if r["status"] == "success" and r["scores_json"]]
            passed_g = [r for r in scored_g if r["passed"]]
            out.append({
                "group": g,
                "total": len(gr),
                "success": len(scored_g),
                "failed": len([r for r in gr if r["status"] == "failed"]),
                "passed": len(passed_g),
                # 通过率以组内全部用例为分母，失败(未评出分数)的用例同样计入，避免高估通过率
                "pass_rate": round(len(passed_g) / len(gr), 4) if gr else None,
                "avg_score": _avg([r["total_score"] for r in scored_g]),
                "avg_latency_ms": _avg([r["latency_ms"] for r in scored_g]),
                "avg_total_tokens": _avg([r["total_tokens"] for r in scored_g]),
                "dims": dim_averages(scored_g),
            })
        return out

    passed_scored = [r for r in scored if r["passed"]]
    overall = {
        "total": len(results),
        "success": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "failed"]),
        "running": len([r for r in results if r["status"] == "running"]),
        "pending": len([r for r in results if r["status"] == "pending"]),
        "passed": len(passed_scored),
        # 通过率以本次评测全部用例为分母；失败(无评分)的用例视为未通过，避免只统计成功用例导致通过率虚高
        "pass_rate": round(len(passed_scored) / len(results), 4) if results else None,
        "avg_total_score": _avg([r["total_score"] for r in scored]),
        "dims": dim_averages(scored),
        "avg_ttft_ms": _avg([r["ttft_ms"] for r in scored]),
        "avg_latency_ms": _avg([r["latency_ms"] for r in scored]),
        "avg_input_tokens": _avg([r["input_tokens"] for r in scored]),
        "avg_output_tokens": _avg([r["output_tokens"] for r in scored]),
        "avg_total_tokens": _avg([r["total_tokens"] for r in scored]),
    }

    badcases = [r for r in results if r["is_badcase"]]
    return {
        "run": run,
        "overall": overall,
        "by_scenario": group_stats(results, "scenario"),
        "by_difficulty": group_stats(results, "difficulty"),
        "badcases": badcases,
        "results": results,
    }

def _result_rows(results) -> List[Dict[str, Any]]:
    rows = []
    for r in results:
        s = _score_dict(r["scores_json"])
        row = {
            "test_case_id": r["ref_id"],
            "scenario": r["scenario"],
            "difficulty": r["difficulty"],
            "status": r["status"],
            "total_score": r["total_score"],
        }
        for key, _label, _w in DIMENSIONS:
            row[DIMENSION_LABELS[key]] = s.get(key, "")
        row.update({
            "confidence": r["confidence"],
            "passed": "是" if r["passed"] else "否",
            "is_badcase": "是" if r["is_badcase"] else "否",
            "ttft_ms": r["ttft_ms"],
            "latency_ms": r["latency_ms"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "total_tokens": r["total_tokens"],
            "actual_output": r["actual_output"],
            "expected_output": r["expected_output"],
            "error": r["error"],
        })
        rows.append(row)
    return rows


def _to_csv(rows: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    if rows:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue()


def export_csv(run_id: int, kind: str = "results") -> str:
    rep = build_report(run_id)
    if kind == "summary":
        ov = rep["overall"]
        rows = []
        rows.append({"指标": "总用例数", "数值": ov["total"]})
        rows.append({"指标": "成功用例数", "数值": ov["success"]})
        rows.append({"指标": "失败用例数", "数值": ov["failed"]})
        rows.append({"指标": "通过用例数", "数值": ov["passed"]})
        rows.append({"指标": "整体通过率", "数值": ov["pass_rate"]})
        rows.append({"指标": "平均总分", "数值": ov["avg_total_score"]})
        for key, _label, _w in DIMENSIONS:
            rows.append({"指标": f"{DIMENSION_LABELS[key]}平均分", "数值": ov["dims"].get(key)})
        rows.append({"指标": "平均首字响应(ms)", "数值": ov["avg_ttft_ms"]})
        rows.append({"指标": "平均延迟(ms)", "数值": ov["avg_latency_ms"]})
        rows.append({"指标": "平均输入Token", "数值": ov["avg_input_tokens"]})
        rows.append({"指标": "平均输出Token", "数值": ov["avg_output_tokens"]})
        rows.append({"指标": "平均总Token", "数值": ov["avg_total_tokens"]})
        return _to_csv(rows)
    if kind == "scenario":
        rows = []
        for g in rep["by_scenario"]:
            row = {"场景": g["group"], "总数": g["total"], "成功": g["success"], "失败": g["failed"],
                   "通过": g["passed"], "通过率": g["pass_rate"], "平均总分": g["avg_score"],
                   "平均延迟(ms)": g["avg_latency_ms"], "平均总Token": g["avg_total_tokens"]}
            for key, _label, _w in DIMENSIONS:
                row[f"{DIMENSION_LABELS[key]}均分"] = g["dims"].get(key)
            rows.append(row)
        return _to_csv(rows)
    if kind == "difficulty":
        rows = []
        for g in rep["by_difficulty"]:
            rows.append({
                "难度": g["group"], "总数": g["total"], "成功": g["success"], "失败": g["failed"],
                "通过": g["passed"], "通过率": g["pass_rate"], "平均总分": g["avg_score"],
                "平均延迟(ms)": g["avg_latency_ms"], "平均总Token": g["avg_total_tokens"],
            })
        return _to_csv(rows)
    if kind == "badcase":
        badcases = [r for r in rep["results"] if r["is_badcase"]]
        return _to_csv(_result_rows(badcases))
    return _to_csv(_result_rows(rep["results"]))

