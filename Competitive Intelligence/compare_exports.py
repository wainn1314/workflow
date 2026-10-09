# -*- coding: utf-8 -*-
"""Full-tree field-level diff between DSL yaml files (layout-only keys ignored)."""
import io
import sys
import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = {"v1": "竞品动态自动监控.yml", "v2": "竞品动态自动监控_v2.yml"}
IGNORE_KEYS = {"position", "positionAbsolute", "width", "height", "selected", "zIndex",
               "viewport", "sourcePosition", "targetPosition", "draggable", "parentId"}

def deep_diff(a, b, path="", out=None):
    if out is None:
        out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE_KEYS:
                continue
            p = f"{path}.{k}" if path else k
            if k not in a:
                out.append(f"{p}:  <only in right> {repr(b[k])[:200]}")
            elif k not in b:
                out.append(f"{p}:  <only in left> {repr(a[k])[:200]}")
            else:
                deep_diff(a[k], b[k], p, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list len {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            deep_diff(x, y, f"{path}[{i}]", out)
    else:
        if a != b:
            out.append(f"{path}: {repr(a)[:200]}  !=  {repr(b)[:200]}")
    return out

docs = {k: yaml.safe_load(io.open(v, encoding="utf-8")) for k, v in FILES.items()}

for pair in (("v1", "v2"),):
    a, b = pair
    diffs = deep_diff(docs[a], docs[b])
    print(f"===== {a}  vs  {b} : {len(diffs)} field differences =====")
    for d in diffs[:80]:
        print("  ", d)
    print()
