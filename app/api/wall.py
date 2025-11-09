from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.repositories.wall import wall_repository
from app.db.repositories.user import user_repository
from app.schemas.wall import (
    WallMessageCreate,
    WallMessageUpdate,
    WallMessageResponse,
    WallMessageListResponse,
    WallStatisticsResponse,
    MessageStatusUpdate
)
from app.core.security import get_openid, require_admin
from app.services.sanitizer import sanitize_text


# 定义类型
MessageType = Literal["general", "lost_and_found", "help", "announcement"]
MessageStatus = Literal["PENDING", "APPROVED", "REJECTED", "DELETED"]

router = APIRouter()

@router.get("/messages",
            response_model=WallMessageListResponse,
            summary="获取留言墙内容",
            description="获取留言墙的所有留言内容，支持分页、筛选和搜索")
def get_wall_messages(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    message_type: Optional[MessageType] = Query(None, description="消息类型"),
    status: MessageStatus = Query("APPROVED", description="消息状态"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    db: Session = Depends(get_db)
):
    """获取墙消息列表"""
    skip = (page - 1) * page_size
    keyword = sanitize_text(keyword, max_length=100) if keyword else None
    
    if keyword:
        messages = wall_repository.search_messages(
            db=db,
            keyword=keyword,
            message_type=message_type,
            status=status,
            skip=skip,
            limit=page_size
        )
    elif user_id:
        messages = wall_repository.get_messages_by_user(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=page_size
        )
    elif message_type:
        messages = wall_repository.get_messages_by_type(
            db=db,
            message_type=message_type,
            status=status,
            skip=skip,
            limit=page_size
        )
    else:
        messages = wall_repository.get_messages_by_status(
            db=db,
            status=status,
            skip=skip,
            limit=page_size
        )
    
    total = wall_repository.count_messages(
        db=db,
        message_type=message_type,
        status=status,
        keyword=keyword,
        user_id=user_id
    )
    has_next = len(messages) == page_size
    
    return WallMessageListResponse(
        items=[WallMessageResponse.model_validate(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next
    )


@router.get("/messages/popular",
            response_model=List[WallMessageResponse],
            summary="获取热门消息",
            description="获取热门留言（按点赞数排序）")
def get_popular_messages(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取热门消息"""
    skip = (page - 1) * page_size
    messages = wall_repository.get_popular_messages(
        db=db,
        skip=skip,
        limit=page_size
    )
    return [WallMessageResponse.model_validate(msg) for msg in messages]


@router.get("/messages/{message_id}",
            response_model=WallMessageResponse,
            summary="获取单条消息",
            description="获取指定ID的消息详情")
def get_wall_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    """获取单条消息并增加浏览次数"""
    message = wall_repository.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    # 增加浏览次数
    wall_repository.increment_view_count(db=db, message_id=message_id)
    
    return WallMessageResponse.model_validate(message)


@router.post("/messages",
             response_model=WallMessageResponse,
             summary="发布新消息",
             description="发布新的留言到墙上")
def create_wall_message(
    message_data: WallMessageCreate,
    db: Session = Depends(get_db),
    openid: str = Depends(get_openid)
):
    """创建新的墙消息"""
    # 获取用户信息
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")
    
    # 添加用户ID到消息数据
    message_data.user_id = user.id  # type: ignore

    # 清洗文本字段，避免注入及敏感字符
    message_data.title = sanitize_text(message_data.title, max_length=200) if message_data.title else None
    message_data.content = sanitize_text(message_data.content, max_length=2000)  # type: ignore
    message_data.contact_info = sanitize_text(message_data.contact_info, max_length=200) if message_data.contact_info else None
    message_data.location = sanitize_text(message_data.location, max_length=200) if message_data.location else None
    message_data.tags = sanitize_text(message_data.tags, max_length=500) if message_data.tags else None

    message = wall_repository.create(db=db, obj_in=message_data)
    return WallMessageResponse.model_validate(message)


@router.put("/messages/{message_id}",
            response_model=WallMessageResponse,
            summary="更新消息",
            description="更新指定ID的消息")
def update_wall_message(
    message_id: int,
    message_data: WallMessageUpdate,
    db: Session = Depends(get_db)
):
    """更新墙消息"""
    message = wall_repository.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    if message_data.title:
        message_data.title = sanitize_text(message_data.title, max_length=200)
    if message_data.content:
        message_data.content = sanitize_text(message_data.content, max_length=2000)
    if message_data.contact_info:
        message_data.contact_info = sanitize_text(message_data.contact_info, max_length=200)
    if message_data.location:
        message_data.location = sanitize_text(message_data.location, max_length=200)
    if message_data.tags:
        message_data.tags = sanitize_text(message_data.tags, max_length=500)

    updated_message = wall_repository.update(db=db, db_obj=message, obj_in=message_data)
    return WallMessageResponse.model_validate(updated_message)


@router.delete("/messages/{message_id}",
               summary="删除消息",
               description="删除指定ID的消息")
def delete_wall_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    """删除墙消息"""
    message = wall_repository.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    wall_repository.remove(db=db, id=message_id)
    return {"message": "消息已删除"}


@router.post("/messages/{message_id}/like",
             response_model=WallMessageResponse,
             summary="点赞消息",
             description="为指定消息点赞")
def like_wall_message(
    message_id: int,
    db: Session = Depends(get_db)
):
    """为消息点赞"""
    message = wall_repository.increment_like_count(db=db, message_id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    return WallMessageResponse.model_validate(message)


@router.put("/messages/{message_id}/status",
            response_model=WallMessageResponse,
            summary="更新消息状态",
            description="更新消息的审核状态（管理员功能）")
def update_message_status(
    message_id: int,
    status_update: MessageStatusUpdate,
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """更新消息状态（管理员功能）"""
    message = wall_repository.update_status(db=db, message_id=message_id, status=status_update.status)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    return WallMessageResponse.model_validate(message)


@router.get("/statistics",
            response_model=WallStatisticsResponse,
            summary="获取统计信息",
            description="获取墙的统计信息")
def get_wall_statistics(db: Session = Depends(get_db)):
    """获取墙统计信息"""
    stats = wall_repository.get_statistics(db=db)
    return WallStatisticsResponse(**stats)


@router.get("/admin/messages",
            response_model=WallMessageListResponse,
            summary="管理员获取所有消息",
            description="管理员获取所有状态的消息（包括待审核）")
def get_admin_messages(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[MessageStatus] = Query(None, description="消息状态筛选"),
    message_type: Optional[MessageType] = Query(None, description="消息类型筛选"),
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """管理员获取消息列表"""
    skip = (page - 1) * page_size
    
    if status:
        messages = wall_repository.get_messages_by_status(
            db=db,
            status=status,
            skip=skip,
            limit=page_size
        )
    elif message_type:
        messages = wall_repository.get_messages_by_type(
            db=db,
            message_type=message_type,
            status="PENDING",
            skip=skip,
            limit=page_size
        )
    else:
        # 默认显示待审核的消息
        messages = wall_repository.get_messages_by_status(
            db=db,
            status="PENDING",
            skip=skip,
            limit=page_size
        )
    
    total = len(messages) + skip if len(messages) == page_size else skip + len(messages)
    has_next = len(messages) == page_size
    
    return WallMessageListResponse(
        items=[WallMessageResponse.model_validate(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next
    )