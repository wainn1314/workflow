# -*- coding: utf-8 -*-
"""Probe Dify marketplace backend endpoints for deepseek/tongyi plugin manifests."""
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

candidates = [
    "https://marketplace.dify.ai/api/v1/plugins?keyword=deepseek",
    "https://marketplace.dify.ai/api/plugin/search?keyword=deepseek",
    "https://marketplace.dify.ai/v1/plugin/search?keyword=deepseek",
    "https://api.marketplace.dify.ai/v1/plugins?keyword=deepseek",
]


def hit(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json",
        "Origin": "https://marketplace.dify.ai", "Referer": "https://marketplace.dify.ai/",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", errors="replace")
            print("OK ", r.status, url, "len=", len(raw))
            print(raw[:800].replace("\n", " "))
            print("---")
            return True
    except urllib.error.HTTPError as e:
        print("ERR", e.code, url)
        return False
    except Exception as e:
        print("ERR", type(e).__name__, url)
        return False


any_ok = False
for c in candidates:
    if hit(c):
        any_ok = True
        break
print("found endpoint:", any_ok)
