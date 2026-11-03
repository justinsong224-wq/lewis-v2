"""将模型逐行输出规范化为现有文件写入契约，禁止猜测或修补代码。"""
import re
from pathlib import PurePosixPath

FILE_PROTOCOL = """
文件输出协议优先于前面的 JSON 示例：不要返回 JSON，不要使用 Markdown 围栏。
每个文件严格使用下面的独立行标记，正文直接输出原始文件内容，不做 JSON 转义：
<<<LEWIS_FILE:app.py>>>
from fastapi import FastAPI
app = FastAPI()
<<<LEWIS_END_FILE>>>
可连续输出多个文件，每个文件都必须有开始和结束标记。只输出文件块。
路径相对任务根目录，不输出绝对路径或父目录。返回完整可运行文件，不使用省略号代替代码。
"""


def parse_file_blocks(text):
    files, seen = [], set()
    path, lines = None, []
    for line in text.splitlines(keepends=True):
        marker = line.rstrip("\r\n")
        start = re.fullmatch(r"<<<LEWIS_FILE:([^<>]+)>>>", marker)
        if start:
            if path is not None:
                raise ValueError("文件块未结束")
            path = start.group(1)
            clean = PurePosixPath(path)
            canonical = clean.as_posix()
            protected = {'.git', '.lewis', '.env', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules'}
            if ("\\" in path or ":" in path or clean.is_absolute() or ".." in clean.parts
                    or not clean.name or canonical != path
                    or any(part.casefold() in protected for part in clean.parts)
                    or canonical.casefold() in seen):
                raise ValueError("文件路径无效或重复")
            lines = []
        elif marker == "<<<LEWIS_END_FILE>>>":
            if path is None:
                raise ValueError("文件结束标记缺少开始标记")
            files.append({"path": path, "content": "".join(lines)})
            seen.add(PurePosixPath(path).as_posix().casefold())
            path, lines = None, []
        elif path is not None:
            lines.append(line)
        elif marker.strip():
            raise ValueError("文件块之外含有额外内容")
    if path is not None or not files:
        raise ValueError("文件输出为空或被截断")
    return {"files": files, "summary": f"模型生成 {len(files)} 个文件，执行结果由工具验证"}


async def generate_files(system_prompt, user_prompt, *, tests_only=False, documents_only=False):
    from agents.base import llm_text
    protocol = FILE_PROTOCOL
    if tests_only:
        protocol = protocol.replace("app.py", "test_app.py").replace("from fastapi import FastAPI\napp = FastAPI()", "def test_example():\n    assert True")
        protocol += "\n本角色只输出任务根目录 test_*.py 测试文件，禁止返回应用、README、依赖文件或子目录。"
    if documents_only:
        protocol = protocol.replace("app.py", "README.md").replace("from fastapi import FastAPI\napp = FastAPI()", "# 使用说明\n运行与验证步骤")
        protocol += "\n本角色仅输出 Markdown 说明文件，不输出 Python 或其他源代码文件。"
    return parse_file_blocks(await llm_text(system_prompt + protocol, user_prompt))


def normalize_files(result):
    files = result.get("files", [])
    if not isinstance(files, list):
        raise ValueError("files 必须为列表")
    normalized = []
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("文件必须包含 path")
        item = dict(item)
        if "lines" in item:
            lines = item.pop("lines")
            if not isinstance(lines, list) or any(not isinstance(line, str) or "\n" in line or "\r" in line for line in lines):
                raise ValueError("lines 必须是逐行字符串数组")
            content = "\n".join(lines)
            if "content" in item and item["content"] != content:
                raise ValueError("content 与 lines 内容冲突")
            item["content"] = content
        if not isinstance(item.get("content"), str):
            raise ValueError("文件缺少有效 content 或 lines")
        normalized.append(item)
    return {**result, "files": normalized}
