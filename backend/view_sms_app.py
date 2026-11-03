"""启动 Lewis 已生成的短信应用；不调用开发模型。"""
import argparse
import json
import os
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=("base", "batch"), default="base")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    case = json.loads((ROOT / "demo/sms-classifier/case.json").read_text(encoding="utf-8"))
    task_id = case[args.version + "_task"]
    if not task_id:
        raise SystemExit("此版本尚未验收完成，暂不提供展示入口")
    workspace = ROOT / "backend/workspace/tasks" / task_id
    if not (workspace / "app.py").is_file():
        raise SystemExit("生成应用缺失：" + str(workspace))
    os.environ.setdefault("SMS_ASSET_DIR", str(ROOT / "backend/workspace/assets/sms"))
    import sys
    sys.path.insert(0, str(workspace))
    from app import app
    import app as generated
    from chinese_sms import LanguagePredictor, DIRECTORY
    if (DIRECTORY / 'transformer.pt').is_file():
        from functools import lru_cache
        original = generated.get_predictor
        @lru_cache(maxsize=1)
        def get_predictor():
            return LanguagePredictor(original())
        generated.get_predictor = get_predictor
    from sms_presentation import install
    install(app, workspace)
    port = args.port or (8001 if args.version == "base" else 8002)
    print("Lewis 任务：" + task_id, flush=True)
    print("应用地址：http://127.0.0.1:" + str(port), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, workers=1)


if __name__ == "__main__":
    main()
