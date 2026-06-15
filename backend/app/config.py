"""应用配置管理：从环境变量和 .env 文件加载配置。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置，自动从 .env 和环境变量加载。"""

    # App
    app_name: str = "AI Chat Assistant"
    app_debug: bool = True

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "ai_chat"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 小时

    # AI API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def database_url(self) -> str:
        """数据库连接 URL：有 MySQL 配置时用 MySQL，否则用 SQLite。"""
        if self.mysql_password:
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        return "sqlite:///./ai_chat.db"

    @property
    def mysql_url(self) -> str:
        """构建 MySQL 连接 URL。"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL。"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"


settings = Settings()
