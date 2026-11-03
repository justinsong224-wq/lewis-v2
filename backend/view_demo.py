"""使用现有工作台查看短信案例库，不覆盖原历史库。"""
from pathlib import Path
import argparse
import os
import uvicorn
from memory import sqlite_history as history

ROOT = Path(__file__).resolve().parents[1]

def select_database(case='sms'):
    if case != 'sms':
        raise ValueError('仅保留短信演示案例')
    database = ROOT / 'backend/workspace/validation/sms-history.db'
    if not database.is_file():
        raise FileNotFoundError('短信案例库不存在')
    return database

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--case', choices=('sms',), default='sms')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    history.DB_PATH = str(select_database(args.case))
    os.environ.setdefault('SMS_ASSET_DIR', str(ROOT / 'backend/workspace/assets/sms'))
    print('使用短信案例库：' + history.DB_PATH, flush=True)
    if not args.prepare_only:
        uvicorn.run('main:app', host='127.0.0.1', port=args.port, workers=1)

if __name__ == '__main__':
    main()
