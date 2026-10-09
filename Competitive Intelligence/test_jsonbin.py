# -*- coding: utf-8 -*-
"""Test JSONBin v3 API behavior with provided master key.
Checks: create bin (POST), read (GET), update with PUT to non-existent id (upsert?),
headers format tolerance, X-Bin-Meta behavior.
"""
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
BASE = "https://api.jsonbin.io/v3/b"


def call(method, url, body=None, headers=None):
    req = urllib.request.Request(url, method=method)
    h = {"X-Master-Key": KEY,
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
         "Accept": "application/json, text/plain, */*",
         "Origin": "https://jsonbin.io",
         "Referer": "https://jsonbin.io/"}
    if headers:
        h.update(headers)
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
        req.data = data
        h.setdefault("Content-Type", "application/json")
    req.headers.update(h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8', 'replace')
            print(method, url, '->', r.status)
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, raw[:500]
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        print(method, url, '->', e.code, raw[:500])
        return e.code, raw
    except Exception as e:
        print(method, url, '-> ERROR', repr(e))
        return None, str(e)



print('=== TEST 0: unauthenticated sanity / key validity ===')
print('KEY prefix check only (avoid echoing full key):', KEY[:6] + '...', 'len', len(KEY))

print('\n=== TEST 1: POST create a test bin ===')
test_bin_id = None
status, body = call('POST', BASE, body={"hello": "world", "tag": str(uuid.uuid4())})
if isinstance(body, dict):
    test_bin_id = (body.get('metadata') or {}).get('id')
    print('created bin id:', test_bin_id)

print('\n=== TEST 2: GET /latest normal (with metadata) ===')
if test_bin_id:
    call('GET', f'{BASE}/{test_bin_id}/latest')

print('\n=== TEST 3: GET /latest with X-Bin-Meta:false ===')
if test_bin_id:
    call('GET', f'{BASE}/{test_bin_id}/latest', headers={'X-Bin-Meta': 'false'})

print('\n=== TEST 4: PUT to NON-existent id (upsert check) ===')
fake_id = uuid.uuid4().hex[:20]
call('PUT', f'{BASE}/{fake_id}', body={"upsert": True})

print('\n=== TEST 5: GET fake bin (404 check) ===')
call('GET', f'{BASE}/{fake_id}/latest')

print('\n=== TEST 6: PUT to existing id (update) then read back ===')
if test_bin_id:
    call('PUT', f'{BASE}/{test_bin_id}', body={"hello": "updated", "n": 2})
    call('GET', f'{BASE}/{test_bin_id}/latest', headers={'X-Bin-Meta': 'false'})

print('\n=== TEST 7: headers without space after colon (Content-Type:application/json) ===')
if test_bin_id:
    call('PUT', f'{BASE}/{test_bin_id}', body={"fmt": "no-space-colon"},
         headers={'Content-Type': 'application/json'})
    call('GET', f'{BASE}/{test_bin_id}/latest', headers={'X-Bin-Meta': 'false'})

print('\n=== TEST 8: store raw string body (JSON text) ===')
if test_bin_id:
    raw_body = json.dumps({"url": "https://example.com", "content": "some text"}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}/{test_bin_id}', method='PUT', data=raw_body,
                                 headers={'X-Master-Key': KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print('PUT raw json string ->', r.status)
    except urllib.error.HTTPError as e:
        print('PUT raw json string ->', e.code, e.read().decode('utf-8', 'replace')[:300])
    call('GET', f'{BASE}/{test_bin_id}/latest', headers={'X-Bin-Meta': 'false'})

print('\n=== TEST 9: DELETE test bin (cleanup) ===')
if test_bin_id:
    call('DELETE', f'{BASE}/{test_bin_id}')

print('\nDONE')
