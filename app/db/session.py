from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# 创建数据库引擎，配置连接池
engine = create_engine(
    settings.DATABASE_URI,
    poolclass=QueuePool,  # 使用队列池
    pool_size=10,         # 连接池大小
    max_overflow=20,      # 超出连接池大小后可创建的最大连接数
    pool_timeout=30,      # 获取连接的超时时间（秒）
    pool_recycle=1800,    # 回收连接的时间（秒）
    pool_pre_ping=True,   # 连接前ping一下，确保连接可用
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 数据库依赖项函数，用于FastAPI的依赖注入
def get_db():
    """
    获取数据库会话的依赖函数
    在每个API请求中使用此函数获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()