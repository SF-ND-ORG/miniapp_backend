from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


# 定义消息类型和状态的字面量类型
MessageType = Literal["general", "lost_and_found", "help", "announcement"]
MessageStatus = Literal["PENDING", "APPROVED", "REJECTED", "DELETED"]


class CommentMessageBase(BaseSchema):
    """评论基础Schema"""
    content: str = Field(..., min_length=1, description="消息内容")


class CommentMessageCreate(CommentMessageBase):
    """创建评论的Schema"""
    user_id: Optional[int] = Field(None, description="用户ID，由服务器自动设置")
    wall_id: Optional[int] = Field(None, description="墙ID")

class CommentMessageUpdate(BaseSchema):
    """更新评论的Schema"""
    content: Optional[str] = Field(None, min_length=1, description="消息内容")
    status: Optional[MessageStatus] = Field(None, description="消息状态")

class CommentMessageResponse(CommentMessageBase):
    """评论响应Schema"""
    id: int
    user_id: int
    status: MessageStatus
    like_count: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    content:str

class CommentStatisticsResponse(BaseSchema):
    """统计信息响应Schema"""
    total_count: int
    approved_count: int
    pending_count: int
    type_statistics: dict


class CommentMessageFilter(BaseSchema):
    """评论过滤参数Schema"""
    message_type: Optional[MessageType] = None
    status: Optional[MessageStatus] = "APPROVED"
    keyword: Optional[str] = None
    user_id: Optional[int] = None
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class MessageStatusUpdate(BaseSchema):
    """消息状态更新Schema"""
    status: MessageStatus = Field(description="新的消息状态")

class CommentMessageListResponse(BaseSchema):
    """墙消息列表响应Schema"""
    items: List[CommentMessageResponse]
    total: int