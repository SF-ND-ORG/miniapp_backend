from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


# 定义消息类型和状态的字面量类型
MessageType = Literal["general", "lost_and_found", "help", "announcement"]
MessageStatus = Literal["PENDING", "APPROVED", "REJECTED", "DELETED"]


class WallMessageBase(BaseSchema):
    """墙消息基础Schema"""
    title: Optional[str] = Field(None, max_length=200, description="消息标题")
    content: str = Field(..., min_length=1, description="消息内容")
    message_type: MessageType = Field("general", description="消息类型")
    contact_info: Optional[str] = Field(None, max_length=200, description="联系方式")
    location: Optional[str] = Field(None, max_length=200, description="位置信息")  
    tags: Optional[str] = Field(None, max_length=500, description="标签")
    files: Optional[str] = Field(None, max_length=500, description="图片文件，多个以逗号分隔")

class WallMessageCreate(WallMessageBase):
    """创建墙消息的Schema"""
    user_id: Optional[int] = Field(None, description="用户ID，由服务器自动设置")


class WallMessageUpdate(BaseSchema):
    """更新墙消息的Schema"""
    title: Optional[str] = Field(None, max_length=200, description="消息标题")
    content: Optional[str] = Field(None, min_length=1, description="消息内容")
    message_type: Optional[MessageType] = Field(None, description="消息类型")
    status: Optional[MessageStatus] = Field(None, description="消息状态")
    contact_info: Optional[str] = Field(None, max_length=200, description="联系方式")
    location: Optional[str] = Field(None, max_length=200, description="位置信息")
    tags: Optional[str] = Field(None, max_length=500, description="标签")
    files: Optional[str] = Field(None, max_length=500, description="图片文件，多个以逗号分隔")


class WallMessageResponse(WallMessageBase):
    """墙消息响应Schema"""
    id: int
    user_id: int
    status: MessageStatus
    view_count: int
    like_count: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = None
    author_nickname: Optional[str] = None
    author_display_name: Optional[str] = None
    author_avatar_url: Optional[str] = None


class WallMessageListResponse(BaseSchema):
    """墙消息列表响应Schema"""
    items: List[WallMessageResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class WallStatisticsResponse(BaseSchema):
    """墙统计信息响应Schema"""
    total_count: int
    approved_count: int
    pending_count: int
    type_statistics: dict


class WallMessageFilter(BaseSchema):
    """墙消息过滤参数Schema"""
    message_type: Optional[MessageType] = None
    status: Optional[MessageStatus] = "APPROVED"
    keyword: Optional[str] = None
    user_id: Optional[int] = None
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class MessageStatusUpdate(BaseSchema):
    """消息状态更新Schema"""
    status: MessageStatus = Field(description="新的消息状态")
