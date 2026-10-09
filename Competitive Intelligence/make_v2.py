# -*- coding: utf-8 -*-
"""Produce 竞品动态自动监控_v2.yml with scheme-error hardening.

Changes vs v1 (竞品动态自动监控.yml):
  1) Node 0010 (计算URL MD5) now also outputs fetch_url / url_valid and
     guarantees fetch_url ALWAYS starts with http(s):// so the legacy
     http-request node can never receive an empty or scheme-less value.
  2) Node 0011 (抓取页面内容) url now reads {{#1900000000010.fetch_url#}}
     instead of {{#1900000000002.item#}}.
  3) Node 0031 webhook guard upgraded from "not empty" to "start with http"
     so placeholder/whitespace webhook values can never reach node 0032.
"""
import shutil
import sys
import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "竞品动态自动监控.yml"
DST = "竞品动态自动监控_v2.yml"
BAK = "竞品动态自动监控.yml.bak2"

CODE_0010 = (
    "import hashlib\n"
    "\n"
    "def main(url: str) -> dict:\n"
    "    raw = str(url or \"\").strip()\n"
    "    url_md5 = hashlib.md5(raw.encode(\"utf-8\")).hexdigest()\n"
    "    low = raw.lower()\n"
    "    if low.startswith((\"http://\", \"https://\")):\n"
    "        fetch_url = raw\n"
    "        url_valid = \"yes\"\n"
    "    elif raw:\n"
    "        # 缺少协议头时补全 https://，保证 HTTP 节点不会收到不带协议的串\n"
    "        fetch_url = \"https://\" + raw\n"
    "        url_valid = \"no-scheme\"\n"
    "    else:\n"
    "        # 空 item 时使用可访问的占位页（httpstat.us/204 稳定返回 204），\n"
    "        # 使流程走 0012=false -> 0021 异常处理，而不是让 HTTP 节点抛 scheme 错误\n"
    "        fetch_url = \"https://httpstat.us/204\"\n"
    "        url_valid = \"empty\"\n"
    "    return {\"url_md5\": url_md5, \"url\": raw, \"fetch_url\": fetch_url, \"url_valid\": url_valid}\n"
)

shutil.copyfile(SRC, BAK)
with open(SRC, encoding="utf-8") as f:
    doc = yaml.safe_load(f)

nodes = doc["workflow"]["graph"]["nodes"]
by_id = {str(n["id"]): n for n in nodes}


def get_data(nid):
    return by_id[str(nid)]["data"]


# ---------- 1) node 0010 code + outputs ----------
n10 = get_data("1900000000010")
assert n10["type"] == "code" and n10["title"] == "计算URL MD5", n10["title"]
n10["code"] = CODE_0010
n10["outputs"] = {
    "url": {"children": None, "type": "string"},
    "url_md5": {"children": None, "type": "string"},
    "fetch_url": {"children": None, "type": "string"},
    "url_valid": {"children": None, "type": "string"},
}

# ---------- 2) node 0011 url source ----------
n11 = get_data("1900000000011")
assert n11["type"] == "http-request" and n11["title"] == "抓取页面内容", n11["title"]
assert n11["url"] == "{{#1900000000002.item#}}", n11["url"]
n11["url"] = "{{#1900000000010.fetch_url#}}"

# ---------- 3) node 0031 webhook guard ----------
n31 = get_data("1900000000031")
assert n31["type"] == "if-else"
conds = n31["cases"][0]["conditions"]
assert conds[1]["variable_selector"] == ["1900000000001", "webhook_url"], conds[1]
conds[1]["comparison_operator"] = "start with"
conds[1]["value"] = "http"
conds[1]["id"] = "cond-webhook-starts-http"
conds[1]["varType"] = "string"

with open(DST, "w", encoding="utf-8") as f:
    yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=4096,
                   default_flow_style=False)

print("written", DST)
