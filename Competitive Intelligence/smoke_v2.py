# -*- coding: utf-8 -*-
"""Smoke-test hardened node 0010 + node 0040 semantics in v2/v3 DSL files.

Usage: python smoke_v2.py [file.yml]   (default: 竞品动态自动监控_v3.yml)
"""
import io
import json
import sys
import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F = sys.argv[1] if len(sys.argv) > 1 else "竞品动态自动监控_v3.yml"
doc = yaml.safe_load(io.open(F, encoding="utf-8"))
nodes = doc["workflow"]["graph"]["nodes"]
by_id = {str(n["id"]): n["data"] for n in nodes}
print("file:", F, "| nodes:", len(nodes))

def run(nid, **kw):
    code = by_id[nid]["code"]
    ns = {}
    exec(compile(code, "<%s>" % nid, "exec"), ns)
    return ns["main"](**kw)

print("== node 0010 fetch_url normalization ==")
cases = [
    ("https://example.com/pricing", {}),
    ("http://example.com/x", {}),
    ("example.com/no-scheme", {"url_valid": "no-scheme"}),
    ("", {"url_valid": "empty", "fetch_url": "https://httpstat.us/204"}),
    ("   ", {"url_valid": "empty"}),
    ("https://github.com/trending", {}),
]
ok = True
for raw, expect in cases:
    out = run("1900000000010", url=raw)
    fu = out["fetch_url"]
    good = fu.startswith(("http://", "https://"))
    print(f"  in={raw!r:35} url_md5={out['url_md5']} valid={out['url_valid']} fetch_url={fu}")
    if not good:
        ok = False
    for k, v in expect.items():
        if out.get(k) != v:
            ok = False
            print(f"    !! expected {k}={v!r} got {out.get(k)!r}")
assert ok

print("\n== node 0040 url extraction robustness ==")
p40 = [
    ('{"urls":["https://a.com/","https://b.com/x"]}', ["https://a.com/", "https://b.com/x"]),
    ('["https://a.com/","https://b.com/x"]', ["https://a.com/", "https://b.com/x"]),
    ("https://a.com/", ["https://a.com/"]),
    ('{"competitor_urls":{"urls":["https://c.io"]}}', ["https://c.io"]),
    ('{"urls":["https://ok.com","",null,"  "]}', ["https://ok.com"]),
    ('{"urls":[]}', []),
]
for inp, expect in p40:
    out = run("1900000000040", data=inp)
    assert out["url_list"] == expect, (inp, out)
    print(f"  ok  {inp!r:.60} -> {out['url_list']}")

print("\n== node 0031 webhook guard semantics (v2) ==")
import copy
n31 = by_id["1900000000031"]["cases"][0]
conds = {c["id"]: c for c in n31["conditions"]}
assert conds["cond-webhook-starts-http"]["comparison_operator"] == "start with"
assert conds["cond-webhook-starts-http"]["value"] == "http"
print("  operator=start with value=http ; condition ids:", list(conds))

# emulate Dify start-with + report-contains
def should_push(report, webhook):
    return ("变化类型" in report) and str(webhook).startswith("http")

rows = [
    ("变化类型：有变化\n详情...", "https://open.feishu.cn/xxx", True),
    ("变化类型：有变化", "你的机器人webhook", False),
    ("变化类型：有变化", "   ", False),
    ("变化类型：有变化", "", False),
    ("本次监控无结果", "https://oapi.dingtalk.com/x", False),
]
for r, w, exp in rows:
    got = should_push(r, w)
    print(f"  report含变化类型={'变化类型' in r!s:<5} webhook={w!r:.32} -> push={got}")
    assert got == exp, (r, w, exp)

print("\n== start input form typing (v2 json_object / v3 paragraph) ==")
start_vars = {v["variable"]: v for v in by_id["1900000000001"]["variables"]}
cvar = start_vars["competitor_urls"]
p40 = by_id["1900000000040"]["variables"][0]
print(f"  competitor_urls.type={cvar['type']}  required={cvar['required']}")
print(f"  0040 data value_type={p40['value_type']}  selector={p40['value_selector']}")
pairs = {("json_object", "object"), ("paragraph", "string")}
assert (cvar["type"], p40["value_type"]) in pairs, "start type and 0040 value_type must stay paired"
# str-mode must still parse the documented JSON text for a paragraph input
assert p40["variable"] == "data"
print("  type pair consistent: json/paragraph input is parsed downstream by 0040 str branch")
print("\nALL SMOKE TESTS PASSED")
