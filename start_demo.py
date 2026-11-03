"""一个终端启动答辩所需服务；Ctrl+C 统一停止本次启动的进程。"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def main():
    python = ROOT / "backend/venv-sms/Scripts/python.exe"
    node = shutil.which("node")
    vite = ROOT / "frontend/node_modules/vite/bin/vite.js"
    if not python.is_file() or not node or not vite.is_file():
        raise SystemExit("缺少现有 Python/Node 依赖，请先准备项目环境。")
    services = [
        ("lewis", 8000, [str(python), "-B", "backend/view_demo.py"], ROOT, "/api/health"),
        ("base", 8001, [str(python), "-B", "backend/view_sms_app.py"], ROOT, "/"),
        ("batch", 8002, [str(python), "-B", "backend/view_sms_app.py", "--version", "batch"], ROOT, "/"),
        ("frontend", 5173, [node, str(vite), "--host", "127.0.0.1", "--port", "5173", "--strictPort"], ROOT / "frontend", "/"),
    ]
    for name, port, *_ in services:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit(f"端口 {port} 已被使用，请先停止原服务再启动；不会关闭已有进程。")
    directory = ROOT / "backend/workspace/validation/launcher"
    directory.mkdir(parents=True, exist_ok=True)
    running, logs = [], []
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        for name, port, command, cwd, endpoint in services:
            log = (directory / (name + ".log")).open("wb")
            logs.append(log)
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=log, stderr=log,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            running.append(process)
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"{name} 启动失败，查看 {directory / (name + chr(46) + 'log')}")
                try:
                    with urlopen(f"http://127.0.0.1:{port}{endpoint}", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if time.monotonic() > deadline:
                    raise RuntimeError(f"{name} 启动超时，查看启动日志")
                time.sleep(.25)
        print("全部启动完成。在 Cursor 打开 docs/答辩演示流程.md，按总文档演示。", flush=True)
        print("保持这一个终端运行；演示结束按 Ctrl+C，统一停止服务。", flush=True)
        while True:
            if any(process.poll() is not None for process in running):
                raise RuntimeError("有服务退出，详情见 backend/workspace/validation/launcher")
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止本次启动的服务……", flush=True)
    finally:
        for process in reversed(running):
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.terminate()
                process.wait(timeout=10)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()

