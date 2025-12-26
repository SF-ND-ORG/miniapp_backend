import os
from dotenv import load_dotenv
from typing import List

# 加载环境变量
load_dotenv()

class Settings:
    # 项目基础配置
    PROJECT_NAME: str = "校园点歌系统"
    API_V1_STR: str = "/api"
    DEVELOP_MODE: bool = os.getenv("DEVELOP_MODE", "true").lower() in ("true", "1", "yes")
    
    # 数据库配置
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    
    # 数据库连接URI
    DATABASE_URI: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # JWT令牌相关
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-key")
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # 请求体大小限制（字节）
    MAX_JSON_BODY_BYTES: int = int(os.getenv("MAX_JSON_BODY_BYTES", "131072"))
    MAX_UPLOAD_BODY_BYTES: int = int(os.getenv("MAX_UPLOAD_BODY_BYTES", str(50 * 1024 * 1024)))
    
    # WeChat配置
    WECHAT_APPID: str = os.getenv("WECHAT_APPID","ber")
    WECHAT_SECRET: str = os.getenv("WECHAT_SECRET","ber")
    
    # 音乐API配置
    MUSIC_API_BASE_URL: str = "http://127.0.0.1:3000"
    DEFAULT_LIMIT:int = 30
    
    # 管理员openids
    ADMIN_OPENIDS: List[str] = [
        'ojeMl5_7XpeJv0m3M5vE1EU51Gok',
        'ojeMl53DDXEqKVLxEb8WJnaN9Fck', 
        'ojeMl5xiY5Rpc31-cl2EzzYeP2BY',
        'ojeMl57IoAIFZXH-cKgB-_rYkx1s',
        'ojeMl5wp-gpIUw2TJiXZUUfZWPI8'
    ]

    # Admin panel shared secret
    ADMIN_PANEL_TOKEN: str = os.getenv("ADMIN_PANEL_TOKEN", "change-me")

    # Config override file path
    CONFIG_FILE_PATH: str = os.getenv("CONFIG_FILE_PATH", "app_config.json")

    # Player API shared secret
    PLAYER_ACCESS_TOKEN: str = os.getenv("PLAYER_ACCESS_TOKEN", "change-player-token")

    PICTURE_UPLOAD_DIR: str = "static/pictures"
    EXCEL_UPLOAD_DIR: str = "static/excels"

settings = Settings()