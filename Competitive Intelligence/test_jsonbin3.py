# -*- coding: utf-8 -*-
"""Round 3: check account/bin size limits & 24-hex non-existing bin behavior."""
import json
import os
import sys
import urllib.request
import urllib.error
import uuid

from _env import load_env  # 同目录极简 .env 加载器（仅标准库）

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_env()  # 从同目录 .env 读取 JSONBIN_API_KEY（无 .env 时回退到系统环境变量）
KEY = os.environ.get("JSONBIN_API_KEY", "")
BASE = "https://api.jsonbin.io/v3"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Origin": "https://jsonbin.io", "Referer": "https://jsonbin.io/"}


def call(method, url, body=None, headers=None, label=''):
    req = urllib.request.Request(url, method=method)
    h = dict(UA, **{"X-Master-Key": KEY})
    if headers:
        h.update(headers)
    if body is not None:
        req.data = json.dumps(body).encode('utf-8') if not isinstance(body, bytes) else body
        h.setdefault("Content-Type", "application/json")
    req.headers.update(h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode('utf-8', 'replace')
            print(label, '->', r.status, '|', raw[:300])
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        print(label, '->', e.code, '|', raw[:300])
        return e.code, raw
    except Exception as e:
        print(label, '-> ERROR', repr(e))
        return None, str(e)


print('=== 1: account info ===')
call('GET', f'{BASE}/account')

print('\n=== 2: 24-hex non-existent bin PUT/GET ===')
fake24 = uuid.uuid4().hex[:24]
print('fake24 id:', fake24)
call('PUT', f'{BASE}/b/{fake24}', body={"x": 1}, label='PUT fake24')
call('GET', f'{BASE}/b/{fake24}/latest', label='GET fake24')

print('\n=== 3: 15KB bin upload (size limit check) ===')
big = {"url": "https://example.com/big", "content": "X" * 15000}
st, body = call('POST', f'{BASE}/b', body=big, label='POST 15KB bin')
bid = (body.get('metadata') or {}).get('id') if isinstance(body, dict) else None
if bid:
    call('DELETE', f'{BASE}/b/{bid}', label='cleanup 15KB bin')

print('\n=== 4: 100KB upload check ===')
big2 = {"url": "https://example.com/big2", "content": "Y" * 100000}
st, body = call('POST', f'{BASE}/b', body=big2, label='POST 100KB bin')
bid2 = (body.get('metadata') or {}).get('id') if isinstance(body, dict) else None
if bid2:
    call('DELETE', f'{BASE}/b/{bid2}', label='cleanup 100KB bin')
