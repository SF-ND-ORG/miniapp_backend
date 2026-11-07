from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_admin_panel_token
from app.db.session import get_db
from app.db.repositories import song_request_repository
from app.db.repositories.user import user_repository
from app.schemas.song import PlayerPlayedRequest
from app.schemas.netease import NeteaseCaptchaRequest, NeteaseCellphoneLoginRequest
from app.schemas.user import UserResponse
from app.services import config_manager
from app.services.music_api import music_api_service

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


@router.get(
    "/player/queue",
    response_model=Dict[str, Any],
    summary="获取点歌台队列",
    description="获取已审核通过、等待播放的歌曲队列（管理面板功能）"
)
async def get_player_queue(
    _: None = Depends(require_admin_panel_token),
    db: Session = Depends(get_db)
):
    queue = song_request_repository.get_approved_song_queue(db)
    return {"queue": queue, "total": len(queue)}


@router.get(
    "/player/song/{song_id}",
    response_model=Dict[str, Any],
    summary="获取点歌台歌曲播放信息",
    description="根据歌曲 ID 获取歌曲详情与播放地址（管理面板功能）"
)
async def get_player_song(
    song_id: str,
    br: str | None = Query(None, max_length=20, description="码率，例如 320000"),
    _: None = Depends(require_admin_panel_token)
):
    detail = music_api_service.get_song_detail(song_id)
    playback = music_api_service.get_song_url(song_id, bitrate=br)
    return {
        "song": detail.get("data", {}),
        "playback": playback.get("data", {}),
        "code": playback.get("code", 500),
    }


@router.post(
    "/player/played",
    response_model=Dict[str, Any],
    summary="标记点歌台歌曲已播放",
    description="将队列中的歌曲标记为已播放（管理面板功能）"
)
async def mark_player_song_played(
    data: PlayerPlayedRequest,
    _: None = Depends(require_admin_panel_token),
    db: Session = Depends(get_db)
):
    status = song_request_repository.get_song_request_status(db, data.request_id)
    if status is None:
        raise HTTPException(status_code=404, detail="歌曲请求不存在")
    if status == "rejected":
        raise HTTPException(status_code=400, detail="已拒绝的歌曲请求无法标记为已播放")

    song_request_repository.update_song_request_status(db, data.request_id, "played")
    return {"success": True, "request_id": data.request_id}


@router.get(
    "/music/login/status",
    response_model=Dict[str, Any],
    summary="获取网易云登录状态",
    description="查询当前后端保存的网易云登录状态（管理面板功能）"
)
async def get_netease_login_status(_: None = Depends(require_admin_panel_token)):
    return music_api_service.get_login_status()


@router.post(
    "/music/captcha/sent",
    response_model=Dict[str, Any],
    summary="发送网易云短信验证码",
    description="向指定手机号发送网易云登录验证码（管理面板功能）"
)
async def send_netease_captcha(
    payload: NeteaseCaptchaRequest,
    _: None = Depends(require_admin_panel_token)
):
    return music_api_service.send_captcha(payload.phone, payload.ctcode)


@router.post(
    "/music/login/cellphone",
    response_model=Dict[str, Any],
    summary="网易云手机验证码登录",
    description="使用手机号和短信验证码登录网易云（管理面板功能）"
)
async def login_netease_cellphone(
    payload: NeteaseCellphoneLoginRequest,
    _: None = Depends(require_admin_panel_token)
):
    return music_api_service.login_cellphone(
        payload.phone,
        payload.captcha,
        payload.countrycode,
    )


@router.get(
    "/music/login/qr/key",
    response_model=Dict[str, Any],
    summary="获取网易云二维码登录 key",
    description="生成网易云二维码登录所需的 key（管理面板功能）"
)
async def get_netease_qr_key(_: None = Depends(require_admin_panel_token)):
    return music_api_service.get_qr_key()


@router.get(
    "/music/login/qr/create",
    response_model=Dict[str, Any],
    summary="生成网易云登录二维码",
    description="根据 key 生成网易云登录二维码图片（管理面板功能）"
)
async def create_netease_qr(
    key: str = Query(..., min_length=1, max_length=128, description="二维码登录 key"),
    _: None = Depends(require_admin_panel_token)
):
    return music_api_service.create_qr(key)


@router.get(
    "/music/login/qr/check",
    response_model=Dict[str, Any],
    summary="查询网易云二维码扫码状态",
    description="轮询查询二维码扫码状态（管理面板功能）"
)
async def check_netease_qr(
    key: str = Query(..., min_length=1, max_length=128, description="二维码登录 key"),
    _: None = Depends(require_admin_panel_token)
):
    return music_api_service.check_qr(key)


@router.post(
    "/music/logout",
    response_model=Dict[str, Any],
    summary="退出网易云登录",
    description="清理后端保存的网易云登录状态（管理面板功能）"
)
async def logout_netease(_: None = Depends(require_admin_panel_token)):
    return music_api_service.logout()
