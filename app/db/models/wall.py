from datetime import datetime
from app.db.models.base import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean


# 消息类型常量
class MessageType:
    """消息类型常量"""
    GENERAL = "general"  # 普通消息
    LOST_AND_FOUND = "lost_and_found"  # 失物招领
    HELP = "help"  # 求助
    ANNOUNCEMENT = "announcement"  # 公告


# 消息状态常量
class MessageStatus:
    """消息状态常量"""
    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 已通过
    REJECTED = "REJECTED"  # 已拒绝
    DELETED = "DELETED"  # 已删除


class WallMessage(BaseModel):
    """校园墙消息模型"""
    __tablename__ = "wall_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, comment="用户ID")
    title = Column(String(200), nullable=True, comment="消息标题")
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(String(50), nullable=False, default=MessageType.GENERAL, comment="消息类型")
    status = Column(String(20), nullable=False, default=MessageStatus.PENDING, comment="消息状态")
    contact_info = Column(String(200), nullable=True, comment="联系方式")
    location = Column(String(200), nullable=True, comment="位置信息")
    files = Column(String(500), nullable=True, comment="图片文件，多个以逗号分隔")
    tags = Column(String(500), nullable=True, comment="标签(JSON格式)")
    view_count = Column(Integer, nullable=False, default=0, comment="浏览次数")
    like_count = Column(Integer, nullable=False, default=0, comment="点赞次数")
    timestamp = Column(DateTime, nullable=False, default=datetime.now, comment="发布时间")
    
    def __repr__(self):
        return f"<WallMessage {self.id} by User {self.user_id}: {self.title or self.content[:50]}>"