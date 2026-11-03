#!/bin/bash
# Lewis 项目专用启动脚本
# 清除全局代理变量，避免与 Claude Code 的 litellm 代理混淆
set -e

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy

cd "$(dirname "$0")"

if [ ! -f "venv/Scripts/activate" ] && [ ! -f "venv/bin/activate" ]; then
    echo "❌ 未找到虚拟环境，请先执行：python -m venv venv"
    exit 1
fi

if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# 双重确认：pip 必须来自 venv 内部，否则立即终止
if [[ "$(which pip)" != *"venv"* ]]; then
    echo "❌ 虚拟环境未正确激活（pip 路径：$(which pip)），中止启动"
    exit 1
fi

echo "✅ 虚拟环境已激活：$(which python)"
echo "🚀 Lewis backend starting (direct connection, no proxy)..."
# 注意：不能加 --reload。Windows 上 uvicorn --reload 会用 SelectorEventLoop，
# 而 MCP 工具调用依赖 asyncio.create_subprocess_exec()，只有 ProactorEventLoop 支持，
# 两者冲突会导致 NotImplementedError（且无错误消息），表现为 Dev/Writer 等 Agent 神秘失败。
# 修改代码后需手动重启 run.sh 才能生效。
uvicorn main:app --port 8000