"""
Search MCP Service
提供网络搜索工具，接入 Serper.dev，供 Search Agent 专用
"""
import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lewis-search")

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"


@mcp.tool()
async def web_search(query: str, num_results: int = 5) -> str:
    """使用 Serper.dev 搜索网络信息。query: 搜索关键词，num_results: 返回结果数量（1-10）"""
    if not SERPER_API_KEY:
        return "ERROR: 未配置 SERPER_API_KEY"

    num_results = max(1, min(10, num_results))

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    if kg := data.get("knowledgeGraph"):
        results.append(f"【知识图谱】{kg.get('title', '')}：{kg.get('description', '')}")

    for i, item in enumerate(data.get("organic", []), 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        results.append(f"{i}. {title}\n   {snippet}\n   链接：{link}")

    return "\n\n".join(results) if results else "未找到相关结果"


@mcp.tool()
async def news_search(query: str, num_results: int = 5) -> str:
    """搜索最新新闻。query: 搜索关键词"""
    if not SERPER_API_KEY:
        return "ERROR: 未配置 SERPER_API_KEY"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for i, item in enumerate(data.get("news", []), 1):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        date = item.get("date", "")
        link = item.get("link", "")
        results.append(f"{i}. [{date}] {title}\n   {snippet}\n   链接：{link}")

    return "\n\n".join(results) if results else "未找到相关新闻"


if __name__ == "__main__":
    mcp.run(transport="stdio")