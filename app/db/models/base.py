from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from app.db.session import Base

class BaseModel(Base):
    """所有模型的基础模型类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)