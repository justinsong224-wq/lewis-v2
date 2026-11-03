"""保存验证日志并透传 Python 退出码，避免 PowerShell 重定向误判。"""
from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys


def run_logged(command, stderr_path):
    stderr_path = Path(stderr_path)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    with stderr_path.open('wb') as error_log:
        return subprocess.call(command, stderr=error_log, env=environment)


def main():
    backend = Path(__file__).resolve().parent
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    log = backend / 'workspace/validation' / (stamp + '-run.stderr.log')
    print('stderr log: ' + str(log), flush=True)
    return run_logged([sys.executable, '-B', str(backend / 'run_demo.py'), *sys.argv[1:]], log)


if __name__ == '__main__':
    sys.exit(main())
