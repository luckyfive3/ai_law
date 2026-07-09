"""
AI法律助手 v1.0 — 配置管理
支持 YAML 配置文件 + 环境变量覆盖
"""
import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，支持环境变量覆盖"""

    # ── 服务配置 ──
    server_port: int = 8080
    server_host: str = "0.0.0.0"
    read_timeout: int = 30
    write_timeout: int = 60

    # ── MongoDB ──
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "ai_law"
    mongo_max_pool_size: int = 50
    mongo_min_pool_size: int = 10

    # ── JWT ──
    jwt_secret: str = "dev-jwt-secret-change-in-production-32chars"
    jwt_access_ttl: int = 86400        # 24 小时（秒）
    jwt_refresh_ttl: int = 604800      # 7 天（秒）

    # ── LLM (LangChain + DeepSeek) ──
    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout: int = 30
    llm_max_retries: int = 3

    # ── RAGFlow ──
    ragflow_base_url: str = "http://ragflow:9380"
    ragflow_api_key: str = ""
    ragflow_dataset_id: str = ""
    ragflow_top_k: int = 5
    ragflow_similarity_threshold: float = 0.5
    ragflow_timeout: int = 10

    # ── 内容安全 ──
    safety_enable: bool = True
    safety_keywords_file: str = "blocked_keywords.txt"

    # ── 限流 ──
    rate_limit_messages_per_user_per_minute: int = 10
    rate_limit_requests_per_ip_per_minute: int = 30
    rate_limit_burst: int = 5

    # ── 域名 ──
    domain: str = "localhost"

    class Config:
        env_file = str(Path(__file__).parent / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"


def load_config(config_path: Optional[str] = None) -> Settings:
    """加载配置：先读 YAML，再叠加环境变量"""
    settings = Settings()

    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", str(Path(__file__).parent / "config.yaml"))

    yaml_path = Path(config_path)
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

        # 服务配置
        if "server" in yaml_config:
            s = yaml_config["server"]
            if "port" in s:
                settings.server_port = s["port"]

        # MongoDB 配置
        if "mongodb" in yaml_config:
            m = yaml_config["mongodb"]
            if "uri" in m:
                settings.mongo_uri = m["uri"]
            if "database" in m:
                settings.mongo_db_name = m["database"]
            if "max_pool_size" in m:
                settings.mongo_max_pool_size = m["max_pool_size"]

        # JWT 配置
        if "jwt" in yaml_config:
            j = yaml_config["jwt"]
            if "secret" in j:
                settings.jwt_secret = j["secret"]
            if "access_ttl" in j:
                settings.jwt_access_ttl = parse_duration(j["access_ttl"])
            if "refresh_ttl" in j:
                settings.jwt_refresh_ttl = parse_duration(j["refresh_ttl"])

        # LLM 配置
        if "llm" in yaml_config:
            l = yaml_config["llm"]
            for key in ("provider", "base_url", "api_key", "model"):
                if key in l:
                    setattr(settings, f"llm_{key}", l[key])
            if "temperature" in l:
                settings.llm_temperature = l["temperature"]
            if "max_tokens" in l:
                settings.llm_max_tokens = l["max_tokens"]
            if "timeout" in l:
                settings.llm_timeout = parse_duration_seconds(l["timeout"])

        # RAGFlow 配置
        if "ragflow" in yaml_config:
            r = yaml_config["ragflow"]
            for key in ("base_url", "api_key", "dataset_id"):
                if key in r:
                    setattr(settings, f"ragflow_{key}", r[key])
            if "top_k" in r:
                settings.ragflow_top_k = r["top_k"]
            if "similarity_threshold" in r:
                settings.ragflow_similarity_threshold = r["similarity_threshold"]
            if "timeout" in r:
                settings.ragflow_timeout = parse_duration_seconds(r["timeout"])

        # 安全配置
        if "safety" in yaml_config:
            if "enable" in yaml_config["safety"]:
                settings.safety_enable = yaml_config["safety"]["enable"]

        # 限流配置
        if "rate_limit" in yaml_config:
            rl = yaml_config["rate_limit"]
            if "messages_per_user_per_minute" in rl:
                settings.rate_limit_messages_per_user_per_minute = rl["messages_per_user_per_minute"]
            if "requests_per_ip_per_minute" in rl:
                settings.rate_limit_requests_per_ip_per_minute = rl["requests_per_ip_per_minute"]

    # 环境变量覆盖（DB_*, REDIS_* 等旧变量兼容）
    _env_overrides = {
        "MONGO_URI": "mongo_uri",
        "MONGODB_URI": "mongo_uri",
        "JWT_SECRET": "jwt_secret",
        "DEEPSEEK_API_KEY": "llm_api_key",
        "DEEPSEEK_BASE_URL": "llm_base_url",
        "RAGFLOW_API_KEY": "ragflow_api_key",
        "RAGFLOW_BASE_URL": "ragflow_base_url",
        "RAGFLOW_DATASET_ID": "ragflow_dataset_id",
        "DOMAIN": "domain",
    }
    for env_key, attr in _env_overrides.items():
        val = os.getenv(env_key)
        if val:
            setattr(settings, attr, val)

    return settings


def parse_duration(dur_str: str) -> int:
    """解析 '24h' / '168h' / '30m' 为秒"""
    dur_str = dur_str.strip().lower()
    if dur_str.endswith("h"):
        return int(float(dur_str[:-1]) * 3600)
    elif dur_str.endswith("m"):
        return int(float(dur_str[:-1]) * 60)
    elif dur_str.endswith("s"):
        return int(float(dur_str[:-1]))
    else:
        return int(dur_str)


def parse_duration_seconds(dur_str: str) -> int:
    """解析 '30s' / '5s' 为秒"""
    return parse_duration(dur_str)
