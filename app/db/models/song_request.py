from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.base import BaseModel

class SongRequest(BaseModel):
    """歌曲请求模型"""
    __tablename__ = "song_requests"
    
    # 外键，关联到用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # 歌曲ID
    song_id = Column(String, nullable=False)
    # 歌曲名称，存储歌曲的名称
    song_name = Column(String, nullable=False)
    # 状态：pending（待审核），approved（通过），rejected（驳回），played（已播放）
    status = Column(String, nullable=False, default="pending")
    # 请求时间
    request_time = Column(DateTime, nullable=False)
    # 审核时间
    review_time = Column(DateTime, nullable=True)
    # 审核理由
    review_reason = Column(Text, nullable=True)
    # 审核人ID，外键，关联到管理员（用户表）
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # 关系
    user = relationship("User", back_populates="song_requests", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<SongRequest {self.id} (song_id={self.song_id}, status={self.status})>"