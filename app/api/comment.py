from typing import Any, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.comment import CommentMessageResponse, CommentMessageListResponse, CommentMessageCreate, CommentMessageUpdate, MessageStatusUpdate
from app.db.session import get_db
from app.core.security import get_openid, require_admin
from app.db.repositories.comment import comment_repository
from app.db.repositories.user import user_repository
from sqlalchemy.orm import Session
from app.services.sanitizer import sanitize_text
MessageStatus = Literal["PENDING", "APPROVED", "REJECTED", "DELETED"]
router = APIRouter()


def _build_author_map(users) -> dict[int, Any]:
    mapping: dict[int, Any] = {}
    for user in users:
        user_id = getattr(user, "id", None)
        if isinstance(user_id, int):
            mapping[user_id] = user
    return mapping


def _resolve_author(message, author_map: dict[int, Any]):
    user_id = getattr(message, "user_id", None)
    if isinstance(user_id, int):
        return author_map.get(user_id)
    return None


def _build_comment_response(message, author=None) -> CommentMessageResponse:
    base = CommentMessageResponse.model_validate(message)
    if author is None:
        return base
    extra = {
        "author_name": getattr(author, "name", None),
        "author_nickname": getattr(author, "nickname", None),
        "author_display_name": getattr(author, "nickname", None) or getattr(author, "name", None),
        "author_avatar_url": getattr(author, "avatar_url", None),
    }
    return base.model_copy(update=extra)
@router.get("/message",
            response_model=CommentMessageListResponse,
            summary="获取评论内容",
            description="获取评论区的所有评论内容，支持分页、筛选和搜索")
def get_comment_messages(
    status: MessageStatus = Query("APPROVED", description="消息状态"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    wall_id: Optional[int] = Query(None, description="墙ID"),
    db: Session = Depends(get_db)
):
    if user_id:
        messages = comment_repository.get_messages_by_user(
            db=db,
            user_id=user_id,
        )
    elif status:
        if(wall_id is None):
            messages = comment_repository.get_messages_by_status(
                db=db,
                status=status,
            )
        else:
            messages = comment_repository.get_messages_by_status_and_wall_id(
                db=db,
                status=status,
                wall_id=wall_id,
            )
    else:
        messages = comment_repository.get_messages_by_wall_id(
            db=db,
            wall_id=wall_id,
        )
    user_ids: list[int] = []
    for msg in messages:
        uid = getattr(msg, "user_id", None)
        if isinstance(uid, int):
            user_ids.append(uid)

    authors = user_repository.get_by_ids(db, user_ids)
    author_map = _build_author_map(authors)

    response_items = [
        _build_comment_response(msg, _resolve_author(msg, author_map))
        for msg in messages
    ]

    return CommentMessageListResponse(
        items=response_items,
        total=len(messages)
    )

@router.post("/send",
             response_model=CommentMessageResponse,
             summary="发布新消息",
             description="发布新的留言")
def create_comment_message(
    message_data: CommentMessageCreate,
    db: Session = Depends(get_db),
    openid: str = Depends(get_openid)
):
    """创建新的消息"""
    # 获取用户信息
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")
    # 清洗输入内容并限制长度，防止注入和超长payload
    message_data.content = sanitize_text(message_data.content, max_length=500)  # type: ignore

    # 添加用户ID到消息数据
    message_data.user_id = user.id  # type: ignore
    message = comment_repository.create(db=db, obj_in=message_data) #type: ignore
    return _build_comment_response(message, user)

@router.delete("/delete",
             summary="删除评论",
             description="删除评论")
def delete_comment_message(
    commentid:int=0,
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """删除评论"""
    message = comment_repository.get(db=db, id=commentid)
    if not message:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    comment_repository.remove(db=db, id=commentid)
    
@router.put("/send/{message_id}",
            response_model=CommentMessageResponse,
            summary="更新消息",
            description="更新指定ID的消息")
def update_wall_message(
    message_id: int,
    message_data: CommentMessageUpdate,
    db: Session = Depends(get_db),
    openid:str = Depends(get_openid)
):
    """更新墙消息"""
    message = comment_repository.get(db=db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    if message_data.content:
        message_data.content = sanitize_text(message_data.content, max_length=500)

    updated_message = comment_repository.update(db=db, db_obj=message, obj_in=message_data) #type: ignore
    msg_user_id = getattr(updated_message, "user_id", None)
    author = user_repository.get(db, msg_user_id) if isinstance(msg_user_id, int) else None
    return _build_comment_response(updated_message, author)

@router.post("/like/{message_id}",
             response_model=CommentMessageResponse,
             summary="点赞消息",
             description="为指定消息点赞")
def like_wall_message(
    message_id: int,
    db: Session = Depends(get_db),
    openid:str = Depends(get_openid)
):
    """为消息点赞"""
    message = comment_repository.increment_like_count(db=db, message_id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    msg_user_id = getattr(message, "user_id", None)
    author = user_repository.get(db, msg_user_id) if isinstance(msg_user_id, int) else None
    return _build_comment_response(message, author)


@router.put("/status/{message_id}",
            response_model=CommentMessageResponse,
            summary="更新消息状态",
            description="更新消息的审核状态（管理员功能）")
def update_message_status(
    message_id: int,
    status_update: MessageStatusUpdate,
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """更新消息状态（管理员功能）"""
    message = comment_repository.update_status(db=db, message_id=message_id, status=status_update.status)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    msg_user_id = getattr(message, "user_id", None)
    author = user_repository.get(db, msg_user_id) if isinstance(msg_user_id, int) else None
    return _build_comment_response(message, author)
