#!/usr/bin/env python3
"""一键启动股票推荐小工具的前后端服务"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def start_backend():
    print("[backend] 启动 Flask 后端...")
    return subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(BACKEND),
    )


def start_frontend():
    print("[frontend] 安装依赖...")
    subprocess.run(["yarn", "install"], cwd=str(FRONTEND), check=False)
    print("[frontend] 启动 Vite 开发服务器...")
    return subprocess.Popen(
        ["yarn", "dev"],
        cwd=str(FRONTEND),
    )


def main():
    parser = argparse.ArgumentParser(description="股票推荐小工具")
    parser.add_argument("--backend-only", action="store_true", help="仅启动后端")
    parser.add_argument("--frontend-only", action="store_true", help="仅启动前端")
    args = parser.parse_args()

    processes = []

    try:
        if not args.frontend_only:
            processes.append(("backend", start_backend()))
            time.sleep(2)  # 等待后端就绪

        if not args.backend_only:
            processes.append(("frontend", start_frontend()))

        print("\n服务已启动:")
        if not args.frontend_only:
            print("  后端: http://localhost:8038")
        if not args.backend_only:
            print("  前端: http://localhost:5174")
        print("\n按 Ctrl+C 停止所有服务\n")

        for name, proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\n正在停止...")
        for name, proc in processes:
            proc.terminate()
            proc.wait()
        print("已停止")


if __name__ == "__main__":
    main()
