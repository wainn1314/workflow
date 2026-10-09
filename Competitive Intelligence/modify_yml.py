# -*- coding: utf-8 -*-
"""Surgically fix 竞品动态自动监控.yml based on tested JSONBin behavior.

Key fixes:
  1) JSONBin bin ids are server-assigned -> single snapshot Map bin (keyed by url md5).
  2) Add browser User-Agent on JSONBin requests (Cloudflare blocks default UA).
  3) Standardize header formatting.
  4) Serialize iteration writes (parallel_nums=1) to avoid lost updates.
  5) Cap stored page text (100KB free limit).
"""
import json
import os
import shutil
import sys
import yaml

from _env import load_env  # 同目录极简 .env 加载器（仅标准库）

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "竞品动态自动监控.yml"
BAK = "竞品动态自动监控.yml.bak"

MAP_BIN_ID = "6a9bb95ef5f4af5e296cdd93"

load_env()  # 从同目录 .env 读取 JSONBIN_API_KEY（无 .env 时回退到系统环境变量）
API_KEY = os.environ.get("JSONBIN_API_KEY", "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
GET_HEADERS = "Content-Type: application/json\nUser-Agent: %s\nX-Master-Key: %s\nX-Bin-Meta: false" % (UA, API_KEY)
PUT_HEADERS = "Content-Type: application/json\nUser-Agent: %s\nX-Master-Key: %s" % (UA, API_KEY)

shutil.copyfile(SRC, BAK)
with open(SRC, encoding="utf-8") as f:
    doc = yaml.safe_load(f)

nodes = doc["workflow"]["graph"]["nodes"]
edges = doc["workflow"]["graph"]["edges"]
by_id = {str(n["id"]): n for n in nodes}


def get_data(nid):
    return by_id[str(nid)]["data"]


def set_edge_attr(edge_id, **kw):
    for e in edges:
        if str(e["id"]) == edge_id:
            for k, v in kw.items():
                e[k] = v
            return e
    raise KeyError("edge not found: %s" % edge_id)


def add_edge(eid, source, target, source_type, target_type, iteration_id):
    edges.append({
        "data": {
            "isInIteration": True,
            "isInLoop": False,
            "iteration_id": str(iteration_id),
            "sourceType": source_type,
            "targetType": target_type,
        },
        "id": eid,
        "selected": False,
        "source": str(source),
        "sourceHandle": "source",
        "target": str(target),
        "targetHandle": "target",
        "type": "custom",
        "zIndex": 1001,
    })


# ---------- 1) iteration: serialize writes ----------
it = get_data("1900000000002")
assert it["type"] == "iteration"
it["parallel_nums"] = 1

# ---------- 2) HTTP nodes headers / urls / body ----------
g = get_data("1900000000014")  # GET map
assert g["type"] == "http-request"
g["headers"] = GET_HEADERS
g["url"] = "https://api.jsonbin.io/v3/b/%s/latest" % MAP_BIN_ID
g["desc"] = "从 JSONBin 读取全部竞品 URL 的快照 Map"
g["title"] = "读取快照Map"

for nid in ("1900000000017", "1900000000020"):
    p = get_data(nid)
    assert p["type"] == "http-request"
    p["headers"] = PUT_HEADERS
    p["url"] = "https://api.jsonbin.io/v3/b/%s" % MAP_BIN_ID
    p["body"]["data"][0]["value"] = "{{#1900000000042.merged_map_json#}}"
    if nid == "1900000000017":
        p["desc"] = "PUT 将合并后的快照 Map 写回 JSONBin"
        p["title"] = "更新今日快照"
    else:
        p["desc"] = "首次捕获：把该 URL 今日快照并入 Map 后 PUT 写回 JSONBin"
        p["title"] = "存储首次快照"

# ---------- 3) cap cleaned text size ----------
c = get_data("1900000000013")
assert c["type"] == "code"
code13 = c["code"]
assert "> 20000" in code13 and "[:20000]" in code13, "unexpected clean code"
c["code"] = code13.replace("> 20000", "> 8000").replace("[:20000]", "[:8000]")

# ---------- 4) rewire edges ----------
# 0023 -> 0014   becomes   0013 -> 0014  (GET map right after cleaning)
set_edge_attr("1900000000023-source-1900000000014-target",
              id="1900000000013-source-1900000000014-target",
              source="1900000000013")
# 0014 -> 0015   becomes   0042 -> 0015  (branch after merge)
set_edge_attr("1900000000014-source-1900000000015-target",
              id="1900000000042-source-1900000000015-target",
              source="1900000000042",
              data={"isInIteration": True, "isInLoop": False,
                    "iteration_id": "1900000000002",
                    "sourceType": "code", "targetType": "if-else"})

add_edge("1900000000014-source-1900000000041-target",
         "1900000000014", "1900000000041", "http-request", "code", "1900000000002")
add_edge("1900000000041-source-1900000000042-target",
         "1900000000041", "1900000000042", "code", "code", "1900000000002")
add_edge("1900000000023-source-1900000000042-target",
         "1900000000023", "1900000000042", "code", "code", "1900000000002")

# ---------- 5) add parse node 0041 ----------
node41 = {
    "data": {
        "code": (
            "import json\n"
            "\n"
            "def main(snapshot_map_json: str, url_md5: str) -> dict:\n"
            "    try:\n"
            "        data = json.loads(snapshot_map_json) if snapshot_map_json else {}\n"
            "    except Exception:\n"
            "        data = {}\n"
            "    if not isinstance(data, dict):\n"
            "        data = {}\n"
            "    entry = data.get(url_md5) or {}\n"
            "    if not isinstance(entry, dict):\n"
            "        entry = {}\n"
            "    return {\n"
            "        \"yesterday_content\": str(entry.get(\"content\") or \"\"),\n"
            "        \"snapshot_map_json\": json.dumps(data, ensure_ascii=False),\n"
            "    }\n"
        ),
        "code_language": "python3",
        "desc": "解析快照 Map，取出该 URL 昨日内容与完整 Map",
        "isInIteration": True,
        "isInLoop": False,
        "iteration_id": "1900000000002",
        "outputs": {
            "snapshot_map_json": {"children": None, "type": "string"},
            "yesterday_content": {"children": None, "type": "string"},
        },
        "selected": False,
        "title": "解析昨日快照",
        "type": "code",
        "variables": [
            {
                "value_selector": ["1900000000014", "body"],
                "value_type": "string",
                "variable": "snapshot_map_json",
            },
            {
                "value_selector": ["1900000000010", "url_md5"],
                "value_type": "string",
                "variable": "url_md5",
            },
        ],
    },
    "height": 79,
    "id": "1900000000041",
    "parentId": "1900000000002",
    "position": {"x": 2050, "y": 300.0},
    "positionAbsolute": {"x": 2734, "y": 300.0},
    "selected": False,
    "sourcePosition": "right",
    "targetPosition": "left",
    "type": "custom",
    "width": 242,
    "zIndex": 1001,
}

# ---------- 6) add merge node 0042 ----------
node42 = {
    "data": {
        "code": (
            "import json\n"
            "\n"
            "def main(snapshot_map_json: str, snapshot_payload: str, url_md5: str) -> dict:\n"
            "    try:\n"
            "        data = json.loads(snapshot_map_json) if snapshot_map_json else {}\n"
            "    except Exception:\n"
            "        data = {}\n"
            "    if not isinstance(data, dict):\n"
            "        data = {}\n"
            "    # 仅保留 32 位 md5 键，丢弃占位/异常键\n"
            "    data = {k: v for k, v in data.items() if isinstance(k, str) and len(k) == 32}\n"
            "    try:\n"
            "        entry = json.loads(snapshot_payload) if snapshot_payload else {}\n"
            "    except Exception:\n"
            "        entry = {}\n"
            "    if not isinstance(entry, dict):\n"
            "        entry = {}\n"
            "    data[url_md5] = entry\n"
            "    return {\"merged_map_json\": json.dumps(data, ensure_ascii=False)}\n"
        ),
        "code_language": "python3",
        "desc": "把该 URL 今日快照合并进快照 Map，供 PUT 回写",
        "isInIteration": True,
        "isInLoop": False,
        "iteration_id": "1900000000002",
        "outputs": {
            "merged_map_json": {"children": None, "type": "string"},
        },
        "selected": False,
        "title": "合并今日快照",
        "type": "code",
        "variables": [
            {
                "value_selector": ["1900000000041", "snapshot_map_json"],
                "value_type": "string",
                "variable": "snapshot_map_json",
            },
            {
                "value_selector": ["1900000000023", "snapshot_payload"],
                "value_type": "string",
                "variable": "snapshot_payload",
            },
            {
                "value_selector": ["1900000000010", "url_md5"],
                "value_type": "string",
                "variable": "url_md5",
            },
        ],
    },
    "height": 79,
    "id": "1900000000042",
    "parentId": "1900000000002",
    "position": {"x": 2350, "y": 300.0},
    "positionAbsolute": {"x": 3034, "y": 300.0},
    "selected": False,
    "sourcePosition": "right",
    "targetPosition": "left",
    "type": "custom",
    "width": 242,
    "zIndex": 1001,
}

nodes.append(node41)
nodes.append(node42)

# ---------- 7) if-else 0015 now checks yesterday_content ----------
fe = get_data("1900000000015")
assert fe["type"] == "if-else"
fe["cases"] = [
    {
        "case_id": "true",
        "conditions": [
            {
                "comparison_operator": "not empty",
                "id": "cond-yesterday-not-empty",
                "value": "",
                "varType": "string",
                "variable_selector": ["1900000000041", "yesterday_content"],
            }
        ],
        "id": "true",
        "logical_operator": "and",
    }
]
fe["desc"] = "该 URL 已有历史快照则交给 LLM 对比，否则走首次存储"
fe["title"] = "是否有昨日快照"

# ---------- 8) LLM prompt uses parsed yesterday content ----------
llm = get_data("1900000000016")
assert llm["type"] == "llm"
for tpl in llm["prompt_template"]:
    if isinstance(tpl, dict) and "text" in tpl:
        tpl["text"] = tpl["text"].replace(
            "{{#1900000000014.body#}}", "{{#1900000000041.yesterday_content#}}"
        )

with open(SRC + ".new", "w", encoding="utf-8") as f:
    yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=4096, default_flow_style=False)

print("written", SRC + ".new")

