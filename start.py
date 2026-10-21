# -*- coding: utf-8 -*-
"""一键启动：检查环境 → 缺什么补什么 → 启动界面。

设计原则：只在缺东西时动手，已经装好就直接启动，不重复安装。
"""
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)
CORE_MODULE = "sdprompt_core"
REQUIRED = [("gradio", "gradio"), ("PIL", "Pillow"), ("numpy", "numpy")]


def log(message: str = "") -> None:
    """带 flush 的输出：管道里也能保证"先提示、再装包"的顺序。"""
    sys.stdout.write(str(message) + chr(10))
    sys.stdout.flush()


def python_ok() -> bool:
    return sys.version_info[:2] >= MIN_PYTHON


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def missing_requirements() -> list:
    return [package for module, package in REQUIRED if not has_module(module)]


def newest_wheel() -> Path | None:
    wheels = sorted(
        (ROOT / "target" / "wheels").glob("*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return wheels[0] if wheels else None


def pip_install(*args: str) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args])


def ensure_requirements() -> str:
    missing = missing_requirements()
    if not missing:
        return "依赖已就绪"
    log(f"[安装] 缺少 {', '.join(missing)}，开始安装运行依赖...")
    pip_install("-r", str(ROOT / "requirements.txt"))
    return "已安装运行依赖"


def ensure_core() -> str:
    if has_module(CORE_MODULE):
        return "Rust 核心已就绪"

    wheel = newest_wheel()
    if wheel is not None:
        log(f"[安装] 使用预编译轮子 {wheel.name}")
        pip_install("--no-deps", "--force-reinstall", str(wheel))
        return "已从预编译轮子安装 Rust 核心"

    if (ROOT / "Cargo.toml").exists():
        log("[安装] 没找到预编译轮子，尝试本地编译（需要 Rust 工具链）...")
        try:
            pip_install(".")
            return "已本地编译并安装 Rust 核心"
        except subprocess.CalledProcessError:
            pass

    raise SystemExit(
        "Rust 核心缺失，且无法自动安装。\n"
        "  方案一：安装 Rust 工具链（https://rustup.rs）后重新运行本脚本\n"
        "  方案二：从仓库 Releases 下载对应平台的 .whl，放到 target\\wheels\\ 后重试"
    )


def report() -> bool:
    log(f"Python      : {sys.version.split()[0]}")
    log(f"解释器      : {sys.executable}")
    log(f"运行依赖    : {'就绪' if not missing_requirements() else '缺少 ' + ', '.join(missing_requirements())}")
    log(f"Rust 核心   : {'就绪' if has_module(CORE_MODULE) else '未安装'}")
    if not python_ok():
        log(f"[错误] 需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 及以上")
    return python_ok() and not missing_requirements() and has_module(CORE_MODULE)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="SD 提示词工具集启动器")
    parser.add_argument("--check", action="store_true", help="只检查环境，不安装、不启动")
    parser.add_argument("--no-launch", action="store_true", help="补齐环境后退出，不启动界面")
    args = parser.parse_args(argv)

    if not python_ok():
        log(f"[错误] 需要 Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 及以上，当前 {sys.version.split()[0]}")
        return 1

    if args.check:
        return 0 if report() else 1

    log("=" * 46)
    log(" SD 提示词工具集")
    log("=" * 46)
    log(ensure_requirements())
    log(ensure_core())

    if not has_module(CORE_MODULE):
        log("[错误] Rust 核心仍不可用，请查看上面的提示")
        return 1

    if args.no_launch:
        log("环境就绪（未启动界面）")
        return 0

    log("[启动] 正在打开界面，稍后浏览器会自动弹出；关闭本窗口即停止服务")
    return subprocess.call([sys.executable, str(ROOT / "main.py")], cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
