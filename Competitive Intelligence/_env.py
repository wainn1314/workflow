# -*- coding: utf-8 -*-
"""极简 .env 加载器（仅标准库，无第三方依赖）。

背景：Competitive Intelligence/ 下的调试/测试脚本为了不在代码里硬编码密钥，
统一改为从环境变量读取 `JSONBIN_API_KEY`。本模块让这些脚本也能像正式项目
一样直接读取同目录的 `.env` 文件，无需额外安装 python-dotenv。

用法（在读取环境变量之前调用一次）：

    from _env import load_env
    load_env()                                   # 读取同目录 .env
    KEY = os.environ.get("JSONBIN_API_KEY", "")

优先级：已存在的系统环境变量（不会被 .env 覆盖） > `.env` 文件 > 脚本内默认值。
"""
import os

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_env(path=None):
    """把 .env 中的键值对写入 os.environ（不覆盖已存在的变量），返回成功加载的键名列表。"""
    env_path = path or _ENV_PATH
    if not os.path.isfile(env_path):
        return []
    loaded = []
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if not key or key in os.environ:
                continue
            os.environ[key] = val
            loaded.append(key)
    return loaded


if __name__ == "__main__":
    names = load_env()
    if names:
        print("[_env] 已从 %s 加载: %s" % (_ENV_PATH, ", ".join(names)))
    else:
        print("[_env] 未加载任何变量。请确认 %s 存在（可复制 .env.example 为 .env）" % _ENV_PATH)
