# -*- coding: utf-8 -*-
"""Second round: check bin id format constraints & response body shapes."""
import json
import os
import sys
import urllib.request
import urllib.error
import hashlib

from _env import load_env  # 同目录极简 .env 加载器（仅标准库）

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_env()  # 从同目录 .env 读取 JSONBIN_API_KEY（无 .env 时回退到系统环境变量）
KEY = os.environ.get("JSONBIN_API_KEY", "")
BASE = "https://api.jsonbin.io/v3/b"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Origin": "https://jsonbin.io", "Referer": "https://jsonbin.io/"}


def call(method, url, body=None, headers=None, show=True):
    req = urllib.request.Request(url, method=method)
    h = dict(UA, **{"X-Master-Key": KEY})
    if headers:
        h.update(headers)
    if body is not None:
        req.data = json.dumps(body).encode('utf-8') if not isinstance(body, bytes) else body
        h.setdefault("Content-Type", "application/json")
    req.headers.update(h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8', 'replace')
            if show:
                print(method, url.split('/b/')[-1], '->', r.status, '|', raw[:400])
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        if show:
            print(method, url.split('/b/')[-1], '->', e.code, '|', raw[:400])
        return e.code, raw
    except Exception as e:
        if show:
            print(method, url, '-> ERROR', repr(e))
        return None, str(e)


print('=== A: PUT/GET with 32-hex id (like md5 hexdigest) ===')
md5id = hashlib.md5(b'https://example.com/page').hexdigest()
print('md5 of url =', md5id, 'len', len(md5id))
st, body = call('PUT', f'{BASE}/{md5id}', body={"url": "x", "content": "hello"})
st, body = call('GET', f'{BASE}/{md5id}/latest')
print('GET body type:', type(body))

print('\n=== B: create a real bin, PUT md5-format id body, inspect GET shapes ===')
st, body = call('POST', f'{BASE}', body={"probe": True})
bid = body['metadata']['id']
print('created bin:', bid)
st, body = call('PUT', f'{BASE}/{bid}', body={"url": "https://a.com", "content": "text-v1"})
st, body = call('GET', f'{BASE}/{bid}/latest')
print('GET default keys:', list(body.keys()) if isinstance(body, dict) else body)
rec = body.get('record')
print('record:', rec)
st, body2 = call('GET', f'{BASE}/{bid}/latest', headers={'X-Bin-Meta': 'false'})
print('GET X-Bin-Meta:false ->', body2)

print('\n=== C: store object with nested text (as the workflow does) ===')
# simulate workflow: body is JSON of {"url":..., "content": cleaned html}
payload = json.dumps({"url": "https://a.com", "content": "今日的 cleaned text"}, ensure_ascii=False)
st, body = call('PUT', f'{BASE}/{bid}', body=payload.encode('utf-8'))
st, body = call('GET', f'{BASE}/{bid}/latest', headers={'X-Bin-Meta': 'false'})
print('GET X-Bin-Meta:false after storing json-dumped string ->', repr(body)[:300])

print('\n=== D: what does X-Bin-Meta false return for GET /latest on collection? skip ===')
print('\n=== E: DELETE bin ===')
call('DELETE', f'{BASE}/{bid}', show=False)
print('cleaned up')
