from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    llm_api_key: str = Field(default="", repr=False)
    serper_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    redis_retry_seconds: float = Field(default=30, ge=1, le=300)
    database_url: str = "sqlite:///./lewis.db"

    # 通用模型配置，由根目录 .env 或环境变量提供。
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=90, gt=0)
    agent_timeout_seconds: float = Field(default=240, gt=0)
    llm_json_mode: Literal["auto", "json_object", "prompt"] = "auto"

    @field_validator("llm_base_url")
    @classmethod
    def normalize_base_url(cls, value):
        from urllib.parse import urlsplit
        value = value.strip().rstrip("/")
        if not value:
            return value
        if value.endswith("/chat/completions"):
            value = value[:-len("/chat/completions")]
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("模型 URL 必须是无凭据、查询参数的 HTTP/HTTPS 基础地址")
        return value

    class Config:
        env_file = ROOT / ".env"
        populate_by_name = True
        extra = "ignore"  # MCP 的 LEWIS_WORKSPACE 由工具层读取

settings = Settings()
