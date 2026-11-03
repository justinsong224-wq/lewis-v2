"""复用已保存需求与调研，单独诊断角色输出；不写应用、不伪造成功任务。"""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
from unittest.mock import patch

from agents import base
from agents.ceo_agent import ceo_agent_run
from agents.dev_agent import DEV_SYSTEM
from agents.file_output import normalize_files
from agents.file_output import generate_files
from config.settings import settings
from graph.contracts import ordered_subtasks

ROOT = Path(__file__).resolve().parent


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("ceo", "dev"), required=True)
    parser.add_argument("--source", default="e56eb673-219a-4863-9c60-51f06249183f")
    parser.add_argument("--json-mode", choices=("auto", "json_object", "prompt"))
    parser.add_argument("--file-blocks", action="store_true")
    args = parser.parse_args()
    # 只接受 UUID，输入与输出固定在独立验证目录。
    from uuid import UUID
    UUID(args.source)
    directory = ROOT / "workspace" / "validation"
    source = json.loads((directory / (args.source + ".json")).read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output = directory / ("diagnosis-" + args.role + "-" + stamp)
    output.mkdir()
    if args.json_mode:
        settings.llm_json_mode = args.json_mode
    original_parse = base.parse_json_object
    attempts = []

    def capture(content):
        number = len(attempts) + 1
        text = content if isinstance(content, str) else ""
        for secret in (settings.llm_api_key, settings.serper_api_key):
            if secret:
                text = text.replace(secret, "[REDACTED]")
        (output / f"response-{number}.txt").write_text(text, encoding="utf-8")
        attempt = {"attempt": number, "characters": len(text)}
        attempts.append(attempt)
        try:
            value = original_parse(content)
            attempt["parsed"] = True
            return value
        except ValueError as exc:
            attempt.update(parsed=False, error=str(exc))
            if isinstance(exc, json.JSONDecodeError):
                attempt["near_error"] = repr(text[max(0, exc.pos - 90):exc.pos + 90])
            print(json.dumps(attempt, ensure_ascii=False), flush=True)
            raise

    started = datetime.now()
    report = {"role": args.role, "source_task": args.source, "model": settings.llm_model,
              "json_mode": settings.llm_json_mode, "attempts": attempts}
    try:
        with patch.object(base, "parse_json_object", capture):
            results = source["snapshot"]["agent_results"]
            if args.role == "ceo":
                value = await asyncio.wait_for(ceo_agent_run(source["user_input"], args.source,
                    context={k: results[k] for k in ("pm", "search") if k in results}), settings.agent_timeout_seconds)
                ordered_subtasks(value)
            else:
                plan = source["snapshot"]["plan"]
                task = next(t for t in ordered_subtasks(plan) if t["agent"] == "dev")
                context = {"user_input": source["user_input"], "plan": plan,
                           **{k: results[k] for k in ("pm", "search") if k in results}}
                prompt = "背景：" + json.dumps(context, ensure_ascii=False) + "\n开发任务：" + task["task"]
                if args.file_blocks:
                    from agents import file_output
                    original = file_output.parse_file_blocks
                    def capture_files(text):
                        (output / "response-files.txt").write_text(text, encoding="utf-8")
                        return original(text)
                    with patch.object(file_output, "parse_file_blocks", capture_files):
                        value = await asyncio.wait_for(generate_files(DEV_SYSTEM, prompt), settings.agent_timeout_seconds)
                else:
                    value = await asyncio.wait_for(base.llm_json(DEV_SYSTEM, prompt), settings.agent_timeout_seconds)
                    value = normalize_files(value)
        (output / "parsed.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        report["status"] = "parsed"
    except Exception as exc:
        report.update(status="failed", error_type=type(exc).__name__)
    report["seconds"] = round((datetime.now() - started).total_seconds(), 2)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**report, "directory": str(output)}, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "parsed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
