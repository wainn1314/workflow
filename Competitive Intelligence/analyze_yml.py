# -*- coding: utf-8 -*-
import yaml, json, sys
from collections import Counter
from difflib import unified_diff

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def pretty(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1).splitlines()


# ---------------- node-by-node diff ----------------
a = load('竞品动态自动监控.yml')
b = load('competitor_monitor.yml')

wa = a['workflow']
wb = b['workflow']

ka, kb = set(wa.keys()), set(wb.keys())
print('workflow keys diff A-B:', sorted(ka - kb))
print('workflow keys diff B-A:', sorted(kb - ka))
print('A workflow keys:', sorted(ka))
print('B workflow keys:', sorted(kb))

env = wa.get('environment_variables') or []
print('A env vars:')
for e in env:
    print('   ', e.get('name'), '| len(value)=', len(e.get('value') or ''))
print('B env vars:')
for e in wb.get('environment_variables') or []:
    print('   ', e.get('name'), '| len(value)=', len(e.get('value') or ''))

ga, gb = wa['graph'], wb['graph']
na = {str(n['id']): n for n in ga['nodes']}
nb = {str(n['id']): n for n in gb['nodes']}
print('A node ids:', sorted(na.keys()))
print('B node ids:', sorted(nb.keys()))
print('nodes only in A:', sorted(set(na) - set(nb)))
print('nodes only in B:', sorted(set(nb) - set(na)))

for nid in sorted(set(na) & set(nb)):
    da, db = na[nid].get('data') or {}, nb[nid].get('data') or {}
    if da == db:
        continue
    print('### NODE', nid, 'differs. title:', repr(da.get('title')), 'vs', repr(db.get('title')))
    lines = list(unified_diff(pretty(db), pretty(da), fromfile='competitor_monitor.yml', tofile='竞品动态自动监控.yml', lineterm=''))
    print('\n'.join(lines))
    print('-' * 80)
