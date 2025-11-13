from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.base import BaseModel

class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    # 微信openid，可以为空（未绑定时）
    wechat_openid = Column(String, unique=True, index=True, nullable=True)
    # 学号
    student_id = Column(String, unique=True, index=True, nullable=False)
    # 姓名
    name = Column(String, nullable=False)
    # 昵称
    nickname = Column(String, nullable=True)
    # 头像地址
    avatar_url = Column(String, nullable=True)
    # 绑定时间
    bind_time = Column(DateTime, nullable=True)
    # 是否为管理员
    is_admin = Column(Boolean, nullable=False, default=False)
    
    # 关系
    song_requests = relationship(
        "SongRequest",
        back_populates="user",
        foreign_keys="SongRequest.user_id"
    )
    
    def __repr__(self):
        return f"<User {self.name} ({self.student_id})>"