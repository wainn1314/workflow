# -*- coding: utf-8 -*-
"""Structural validation for the fixed DSL."""
import json
import re
import sys
import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F = sys.argv[1] if len(sys.argv) > 1 else "竞品动态自动监控.yml"
with open(F, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh)

g = doc["workflow"]["graph"]
nodes = g["nodes"]
edges = g["edges"]
ids = [str(n["id"]) for n in nodes]
edge_ids = [str(e["id"]) for e in edges]
by_id = {i: n for i, n in zip(ids, nodes)}

errors = []
# 1) duplicate ids
assert len(ids) == len(set(ids)), "duplicate node ids"
assert len(edge_ids) == len(set(edge_ids)), "duplicate edge ids"

# 2) every edge endpoint exists
for e in edges:
    for key in ("source", "target"):
        ref = str(e[key])
        if ref not in by_id:
            errors.append("edge %s references missing node %s" % (e["id"], ref))

# 3) every node has exactly one parent walk (skip: template nodes parentId empty)
# check referenced variable_selector ids exist
sel_nodes = set()
for n in nodes:
    d = n.get("data") or {}
    if not d.get("isInIteration") and not d.get("isInLoop"):
        pass
    # scan data for selector references
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "value_selector" and isinstance(v, list) and v:
                    sel_nodes.add(str(v[0]))
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(d)
missing = sel_nodes - set(ids)
if missing:
    errors.append("selectors referencing missing nodes: %s" % missing)

# 4) workflow-level known refs (start/end/features, answer)
for n in nodes:
    d = n.get("data") or {}
    for key in ("start_node_id", "end_node_id"):
        if key in d and str(d[key]) not in by_id and str(d[key]) != "":
            errors.append("node %s %s=%s missing" % (n["id"], key, d[key]))
    for sel in ("iterator_selector", "output_selector"):
        if sel in d and isinstance(d[sel], list) and d[sel]:
            sel_nodes.add(str(d[sel][0]))
        if sel in d and isinstance(d[sel], str) and d[sel]:
            sel_nodes.add(d[sel])

# 5) iteration children sanity: nodes flagged isInIteration must have parentId iteration and idempotent iteration_id
it_ids = [str(n["id"]) for n in nodes if (n.get("data") or {}).get("type") == "iteration"]
for n in nodes:
    d = n.get("data") or {}
    if d.get("isInIteration"):
        if n.get("parentId") not in it_ids:
            errors.append("node %s isInIteration but parentId=%s" % (n["id"], n.get("parentId")))
        if str(n["id"]).startswith("1900000000") and d.get("iteration_id") and str(d["iteration_id"]) not in it_ids:
            errors.append("node %s iteration_id=%s missing" % (n["id"], d["iteration_id"]))

# 6) targeted assertions about the fix
def data(nid):
    return by_id[str(nid)]["data"]

it = data("1900000000002")
assert it["parallel_nums"] == 1, it["parallel_nums"]

g14 = data("1900000000014")
assert g14["url"] == "https://api.jsonbin.io/v3/b/6a9bb95ef5f4af5e296cdd93/latest", g14["url"]
assert "User-Agent: Mozilla/5.0" in g14["headers"]
assert "X-Bin-Meta: false" in g14["headers"]
assert ": " in g14["headers"].split("\n")[0]

p17, p20 = data("1900000000017"), data("1900000000020")
for p in (p17, p20):
    assert p["url"] == "https://api.jsonbin.io/v3/b/6a9bb95ef5f4af5e296cdd93", p["url"]
    assert p["body"]["data"][0]["value"] == "{{#1900000000042.merged_map_json#}}"
    assert "User-Agent: Mozilla/5.0" in p["headers"]

c13 = data("1900000000013")["code"]
assert "> 8000" in c13 and "[:8000]" in c13 and "20000" not in c13, "cap not applied"

# edge rewiring checks
def edge(source, target):
    out = []
    for e in edges:
        if str(e["source"]) == source and str(e["target"]) == target:
            out.append(e)
    return out

assert len(edge("1900000000013", "1900000000014")) == 1, "0013->0014"
assert len(edge("1900000000014", "1900000000041")) == 1, "0014->0041"
assert len(edge("1900000000041", "1900000000042")) == 1, "0041->0042"
assert len(edge("1900000000023", "1900000000042")) == 1, "0023->0042"
assert len(edge("1900000000042", "1900000000015")) == 1, "0042->0015"
assert len(edge("1900000000014", "1900000000015")) == 0, "old direct edge must be gone"
assert len(edge("1900000000023", "1900000000014")) == 0, "old 0023->0014 must be gone"
assert len(edge("1900000000013", "1900000000023")) == 1, "0013->0023 preserved"

fe = data("1900000000015")
conds = fe["cases"][0]["conditions"]
assert conds[0]["comparison_operator"] == "not empty"
assert conds[0]["variable_selector"] == ["1900000000041", "yesterday_content"]

llm_prompt = json.dumps(data("1900000000016")["prompt_template"], ensure_ascii=False)
assert "{{#1900000000014.body#}}" not in llm_prompt, "old body ref remains in LLM prompt"
assert "{{#1900000000041.yesterday_content#}}" in llm_prompt

# code nodes compile-ish: simple py syntax sanity by compile()
for nid in ("1900000000041", "1900000000042", "1900000000013", "1900000000023", "1900000000010"):
    code = data(nid)["code"]
    try:
        compile(code, "<node:%s>" % nid, "exec")
    except SyntaxError as exc:
        errors.append("node %s code syntax error: %s" % (nid, exc))

# 7) v2 hardening assertions (active only when file carries the v2 changes)
n10 = data("1900000000010")
if "fetch_url" in (n10.get("outputs") or {}):
    assert "fetch_url" in n10["code"] and "url_valid" in n10["code"]
    assert "httpstat.us/204" in n10["code"], "empty-item fallback URL missing"
    assert 'startswith(("http://", "https://"))' in n10["code"].replace("low.", ""), \
        "scheme prefix branch missing"
    n11 = data("1900000000011")
    assert n11["url"] == "{{#1900000000010.fetch_url#}}", n11["url"]
    n31 = data("1900000000031")
    web_cond = [c for c in n31["cases"][0]["conditions"]
                if c["variable_selector"] == ["1900000000001", "webhook_url"]]
    assert web_cond and web_cond[0]["comparison_operator"] == "start with", \
        "webhook guard must be 'start with http'"
    assert web_cond[0]["value"] == "http", web_cond[0]["value"]

# 8) no leftover raw item binding in the only dynamic GET http node (v2 only)
if "fetch_url" in (data("1900000000010").get("outputs") or {}):
    n11 = data("1900000000011")
    assert "item#}}" not in n11["url"], n11["url"]

# 9) v3: published Web-App friendly start input (paragraph string) stays paired
svars = {v["variable"]: v for v in data("1900000000001")["variables"]}
s_type = svars["competitor_urls"]["type"]
p40 = data("1900000000040")["variables"][0]
assert p40["variable"] == "data" and p40["value_selector"] == ["1900000000001", "competitor_urls"]
if s_type == "paragraph":
    assert p40["value_type"] == "string", "paragraph input must feed code node as string"
elif s_type == "json_object":
    assert p40["value_type"] == "object", "json_object input feeds code node as object"
else:
    errors.append("unexpected start type for competitor_urls: %s" % s_type)

print("nodes:", len(ids), "edges:", len(edges), "iteration nodes ok:", len([1 for n in nodes if (n.get('data') or {}).get('isInIteration')]))
if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("ALL STRUCTURAL CHECKS PASSED")
