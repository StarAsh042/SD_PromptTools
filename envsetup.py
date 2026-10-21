# -*- coding: utf-8 -*-
"""启动前的环境修正。

两件事，都必须发生在 `import gradio` 之前：

1. **本地回环绕过代理**：机器上装了系统代理时（Windows 注册表里那一份，
   不是环境变量），httpx 会把 `http://127.0.0.1:8080` 的探活请求也发给代理，
   代理再往外绕一圈，结果是 `httpx.ReadTimeout`，`launch()` 直接抛异常退出。
2. **关闭遥测**：Gradio 启动时会在后台线程请求外网上报，网络不通就抛
   `ConnectTimeout`，堆栈刷屏，看起来像程序崩了，其实只是遥测失败。
"""
import os

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def merge_no_proxy(current: str, hosts=LOOPBACK_HOSTS) -> str:
    """把回环地址并进已有的 NO_PROXY，保留用户原来配置的条目。"""
    items = [part.strip() for part in current.split(",") if part.strip()]
    existing = {part.lower() for part in items}
    for host in hosts:
        if host.lower() not in existing:
            items.append(host)
    return ",".join(items)


def prepare(environ=None) -> dict:
    """就地修正环境变量，返回同一个 dict 方便测试。"""
    env = os.environ if environ is None else environ
    for key in ("NO_PROXY", "no_proxy"):
        env[key] = merge_no_proxy(env.get(key, ""))
    env.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    return env
