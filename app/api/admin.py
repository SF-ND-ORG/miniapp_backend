from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_admin_panel_token
from app.db.session import get_db
from app.db.repositories.user import user_repository
from app.schemas.user import UserResponse
from app.services import config_manager

router = APIRouter()


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="搜索用户",
    description="根据关键词搜索用户（姓名、学号、OpenID或ID）"
)
async def list_users(
    _: None = Depends(require_admin_panel_token),
    db: Session = Depends(get_db),
    q: str | None = Query(None, min_length=1, max_length=64, description="搜索关键词")
):
    if not q:
        return []

    users = user_repository.search(db=db, query=q, limit=50)
    return [UserResponse.model_validate(user) for user in users]


@router.put("/users/{user_id}/admin", response_model=UserResponse, summary="更新管理员权限")
async def update_admin_status(
    user_id: int,
    is_admin: bool,
    _: None = Depends(require_admin_panel_token),
    db: Session = Depends(get_db)
):
    user = db.query(user_repository.model).filter(user_repository.model.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_admin = is_admin #type:ignore
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get(
    "/config",
    response_model=Dict[str, Any],
    summary="获取配置",
    description="获取可配置的键值"
)
async def get_config(_: None = Depends(require_admin_panel_token)):
    return config_manager.get_config_snapshot()


@router.put(
    "/config",
    response_model=Dict[str, Any],
    summary="更新配置",
    description="更新配置项，未传递的字段保持不变"
)
async def update_config(
    payload: Dict[str, Any] = Body(..., description="需要更新的配置项"),
    _: None = Depends(require_admin_panel_token)
):
    try:
        return config_manager.update_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
