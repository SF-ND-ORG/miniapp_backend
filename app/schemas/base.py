from pydantic import BaseModel

class BaseSchema(BaseModel):
    """所有Pydantic模型的基础类"""
    class Config:
        from_attributes = True  # 启用ORM模式，可直接从SQLAlchemy模型创建