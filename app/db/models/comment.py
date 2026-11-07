from datetime import datetime
from app.db.models.base import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
# 消息状态常量
class MessageStatus:
    """消息状态常量"""
    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 已通过
    REJECTED = "REJECTED"  # 已拒绝
    DELETED = "DELETED"  # 已删除


class CommentMessage(BaseModel):
    """消息模型"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, comment="用户ID")
    content = Column(Text, nullable=False, comment="消息内容")
    status = Column(String(20), nullable=False, default=MessageStatus.PENDING, comment="消息状态")
    like_count = Column(Integer, nullable=False, default=0, comment="点赞次数")
    timestamp = Column(DateTime, nullable=False, default=datetime.now, comment="发布时间")
    wall_id = Column(Integer, nullable=True, comment="墙ID")

    def __repr__(self):
        return f"<CommentMessage {self.id} by User {self.user_id}: {self.content[:50]}>"