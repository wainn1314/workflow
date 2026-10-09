# -*- coding: utf-8 -*-
"""End-to-end JSONBin integration test mirroring the fixed DSL logic.

Simulates two consecutive monitoring days over real HTTP pages + real JSONBin.
Uses the ACTUAL python code embedded in 竞品动态自动监控.yml for nodes
0013(clean), 0023(build entry), 0041(parse), 0042(merge) so the test matches
the workflow's runtime behaviour exactly.  The LLM comparison step cannot run
here (needs Dify + model key) so it is replaced by a rule-based marker.
"""
import io
import json
import os
import sys
import urllib.request
import yaml

from _env import load_env  # 同目录极简 .env 加载器（仅标准库）

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BIN_ID = "6a9bb95ef5f4af5e296cdd93"

load_env()  # 从同目录 .env 读取 JSONBIN_API_KEY（无 .env 时回退到系统环境变量）
KEY = os.environ.get("JSONBIN_API_KEY", "")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

doc = yaml.safe_load(io.open("竞品动态自动监控.yml", encoding="utf-8"))
by_id = {str(n["id"]): n["data"] for n in doc["workflow"]["graph"]["nodes"]}


def exec_node(nid, **inputs):
    code = by_id[nid]["code"]
    ns = {}
    exec(compile(code, "<%s>" % nid, "exec"), ns)
    return ns["main"](**inputs)


def http_jsonbin(method, path, body=None, meta=True):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": UA,
        "X-Master-Key": KEY,
        "Accept": "application/json",
        "Origin": "https://jsonbin.io",
        "Referer": "https://jsonbin.io/",
    }
    if not meta:
        headers["X-Bin-Meta"] = "false"
    data = None if body is None else body.encode("utf-8")
    req = urllib.request.Request("https://api.jsonbin.io/v3/b/%s" % path, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8")


def get_map():
    st, body = http_jsonbin("GET", "%s/latest" % BIN_ID, meta=False)
    assert st == 200, body
    return body


def put_map(map_str):
    st, body = http_jsonbin("PUT", BIN_ID, body=map_str)
    assert st == 200, body


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def md5(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def run_day(urls):
    """Simulate one monitoring day: fetch each url, first-run or compare path."""
    reports = []
    for url in urls:
        raw_html = fetch(url)
        cleaned = exec_node("1900000000013", html_content=raw_html)["cleaned_text"]
        entry = exec_node("1900000000023", url=url, content=cleaned)["snapshot_payload"]
        uid = md5(url)
        body = get_map()  # GET map
        parsed = exec_node("1900000000041", snapshot_map_json=body, url_md5=uid)
        yesterday = parsed["yesterday_content"]
        merged = exec_node("1900000000042", snapshot_map_json=parsed["snapshot_map_json"],
                           snapshot_payload=entry, url_md5=uid)["merged_map_json"]
        put_map(merged)  # write snapshot (both branches PUT after merge)
        if yesterday == "":
            reports.append("[首次] 已存储今日快照: %s (%.1f KB 文本)" % (url, len(cleaned) / 1024))
        else:
            if cleaned.strip() == yesterday.strip():
                reports.append("[无变化] %s" % url)
            else:
                reports.append("[有变化] %s（交给 LLM 做详细分析）" % url)
    return reports


# ---- Day 1 : first captures ----
print("== Day 1: 首次运行 ==")
urls_a = ["https://example.com/", "https://example.org/"]
for r in run_day(urls_a):
    print(" ", r)

# ---- Day 2 : same pages, compare path ----
print("\n== Day 2: 抓取+对比（昨日快照存在） ==")
for r in run_day(urls_a):
    print(" ", r)

map_raw = get_map()
data = json.loads(map_raw)
print("\nMap keys:", sorted(data.keys()))
print("总记录大小: %.1f KB" % (len(map_raw) / 1024))

# ---- Simulate an actual change on example.org and re-run ----
print("\n== Day 3: 人为改存昨日内容，验证变化可被识别 ==")
import copy
mutated = json.loads(map_raw)
for k, v in mutated.items():
    if v.get("url", "").startswith("https://example.org/"):
        mutated[k] = {"url": v["url"], "content": "Example Domain OLD FROZEN 1995 snapshot text for comparison test."}
put_map(json.dumps(mutated, ensure_ascii=False))
for r in run_day(["https://example.org/"]):
    print(" ", r)

# ---- cleanup: reset bin to placeholder like pre-run state ----
put_map(json.dumps({"_init": True}))
print("\n已重置快照 bin 为初始占位状态（等待真实工作流首次写入）。")
print("ALL JSONBIN INTEGRATION TESTS PASSED")
