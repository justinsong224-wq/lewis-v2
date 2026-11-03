"""
Agent 工具权限注册表
统一管理每个 Agent 可调用哪些 MCP server，避免越权调用
"""

AGENT_PERMISSIONS: dict[str, list[str]] = {
    "ceo":      [],
    "pm":       [],
    "dev":      ["filesystem", "git"],
    "test":     ["filesystem", "shell"],
    "devops":   ["filesystem", "shell", "git"],
    "review":   ["filesystem", "git"],
    "search":   ["search"],
    "analyst":  ["database", "filesystem"],
    "writer":   ["filesystem"],
    "customer": [],
}


def get_allowed_servers(agent_name: str) -> list[str]:
    return AGENT_PERMISSIONS.get(agent_name, [])


def check_permission(agent_name: str, server_name: str) -> bool:
    return server_name in get_allowed_servers(agent_name)
