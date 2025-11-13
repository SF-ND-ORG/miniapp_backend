from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.schemas.auth import LoginRequest, BindRequest, RefreshTokenRequest, TokenResponse
from app.schemas.song import SongRequest
from app.schemas.user import UserProfileUpdate, UserResponse
from app.services.auth import create_token_pair, verify_wechat_code, verify_refresh_token
from app.db.repositories import user_repository, song_request_repository
from app.core.security import get_openid
from app.db.session import get_db
from app.services.sanitizer import sanitize_text

router = APIRouter()


def _build_user_response(user) -> UserResponse:
    base = UserResponse.model_validate(user)
    display_name = getattr(user, "nickname", None) or getattr(user, "name", None)
    return base.model_copy(update={"display_name": display_name})


@router.post("/login", response_model=TokenResponse,
             summary="微信小程序登录",
             response_description="包含访问令牌和刷新令牌的对象",
             description="使用微信小程序的code进行登录，成功后返回访问令牌和刷新令牌",
             responses={
                    400: {
                        "description": "登录失败，可能是code无效或其他错误",
                        "content": {
                            "application/json": {
                                "example": {"detail": "无效的code或其他错误"}
                            }
                        }
                    }
                }
             )
def login_wechat(data: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    result = verify_wechat_code(data.code)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["msg"])

    openid = result["openid"]
    # 使用新的token对生成函数
    tokens = create_token_pair(openid, db)

    return tokens


@router.post("/bind",
             response_model=Dict[str, Any],
             summary="绑定微信账号",
             description="将微信账号与学生ID和姓名进行绑定",
                responses={
                    400: {
                        "description": "绑定失败，可能是学号或姓名不正确，或已被其他微信绑定",
                        "content": {
                            "application/json": {
                                "examples": {
                                    "学号或姓名不正确": {"value": {"detail": "学号或姓名不正确"}},
                                    "已被其他微信绑定": {"value": {"detail": "该学号已被其他微信绑定"}},
                                    "曾经已绑定过": {"value": {"detail": "曾经已绑定过"}}
                                }
                            }
                        }
                    },
                    200: {
                        "description": "绑定成功或曾经已绑定过",
                        "content": {
                            "application/json": {
                                "examples":{
                                    "绑定成功": {"value": {"success": True, "msg": "绑定成功"}},
                                    "曾经已绑定过": {"value": {"success": True, "msg": "曾经已绑定过"}}
                                }
                            }
                        }
                    }
                }
             )
def wechat_bind(
        data: BindRequest,
        db: Session = Depends(get_db),
        openid: str = Depends(get_openid)
) -> Dict[str, Any]:
    if not data.agree_privacy:
        raise HTTPException(status_code=400, detail="请先阅读并同意隐私声明")
    # 检查学生ID和姓名是否存在并匹配
    user = user_repository.get_by_student_id_and_name(db, data.student_id, data.name)

    if not user:
        raise HTTPException(status_code=400, detail="学号或姓名不正确")

    # 检查是否已经绑定到其他微信
    if user.wechat_openid and user.wechat_openid != openid:#type: ignore
        raise HTTPException(status_code=400, detail="该学号已被其他微信绑定")

    # 如果已经绑定到这个微信
    if user.wechat_openid == openid:#type: ignore
        return {"success": True, "msg": "曾经已绑定过"}

    # 绑定openid
    user_repository.bind_user(db, user.id, openid)  #type: ignore

    return {"success": True, "msg": "绑定成功"}


@router.post("/refresh", response_model=TokenResponse,
             description="使用刷新令牌刷新访问令牌",
             summary="刷新访问令牌"
             )
def refresh_token(
        data: RefreshTokenRequest,
        db: Session = Depends(get_db)
) -> Dict[str, Any]:
    result = verify_refresh_token(data.refresh_token, db)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["msg"])

    return result["tokens"]


@router.get("/isbound",
            description="检查用户是否已绑定学生账号",
            summary="检查用户绑定状态",
            )
def is_bound(
        db: Session = Depends(get_db),
        openid: str = Depends(get_openid)
) -> Dict[str, bool]:
    user = user_repository.get_by_openid(db, openid)
    return {"is_bound": user is not None}


@router.post("/song/request",
             summary="发起点歌请求",
             responses={
                 200: {"description": "点歌成功",
                            "content": {
                                "application/json": {
                                    "example": {"success": True, "msg": "点歌成功，等待审核"}
                                }
                            }
                    },
                 400: {
                     "description": "点歌失败",
                     "content": {
                         "application/json": {
                             "examples": {
                                 "未绑定": {"value": {"detail": "未绑定用户"}},
                                 "频率限制": {"value": {"detail": "30分钟内只能点一次歌，请稍后再试"}},
                                 "重复点歌": {"value": {"detail": "你或别人已经点过这首歌了"}},
                                 "数量限制": {"value": {"detail": "你最多只能有3首未审核通过或未播放的歌曲"}}
                             }
                         }
                     }
                 }
             }
             )
def song_request(
        data: SongRequest,
        db: Session = Depends(get_db),
        openid: str = Depends(get_openid)
) -> Dict[str, Any]:
    """
    用户提交点歌请求，系统会进行一系列检查，包括用户绑定状态、点歌频率、重复点歌检查等。

    ### 限制条件:
    - 用户必须已绑定学生账号
    - 普通用户30分钟内只能点一首歌
    - 不能重复点已经在队列中的歌曲
    - 普通用户最多只能有3首未审核或未播放的歌曲
    - 管理员不受上述限制

    ### 参数:
    - **song_id**: 网易云音乐歌曲ID

    ### 返回:
    - **success**: 是否成功
    - **msg**: 结果消息
    """
    # 获取用户
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")

    user_id = user.id
    is_admin = user.is_admin or openid in settings.ADMIN_OPENIDS

    # 检查用户在最近30分钟内是否已经请求过歌曲
    if not is_admin and song_request_repository.check_recent_song_requests(db, user_id) > 0:  # type: ignore
        raise HTTPException(status_code=400, detail="30分钟内只能点一次歌，请稍后再试")

    # 检查用户是否已经请求过这首歌
    if song_request_repository.check_song_already_requested(db, user_id, data.song_id):  # type: ignore
        raise HTTPException(status_code=400, detail="你或别人已经点过这首歌了")

    # 检查用户是否有太多未审核/已批准的歌曲
    if not is_admin and song_request_repository.count_pending_approved_songs(db, user_id) >= 3:  # type: ignore
        raise HTTPException(status_code=400, detail="你最多只能有3首未审核通过或未播放的歌曲")

    # 创建歌曲请求
    song_request_repository.create_song_request(db, user_id, data.song_id, data.song_name)  # type: ignore

    return {"success": True, "msg": "点歌成功，等待审核"}

@router.get("/song/getrequests",
           summary="获取用户所有点歌请求",
           response_model=Dict[str, Any],
           description="获取当前用户的所有点歌请求，包括已审核和未审核的歌曲请求"
           )
def get_all_song_requests_of_user(
        db: Session = Depends(get_db),
        openid: str = Depends(get_openid)
) -> Dict[str, Any]:
    """
    获取用户的所有点歌请求
    """
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")

    requests = song_request_repository.get_requests_by_user_id(db, user.id,status=["pending", "approved", "rejected"])  # type: ignore

    return {"requests": requests}


@router.get(
    "/userinfo",
    summary="获取用户信息",
    response_model=UserResponse,
    description="获取当前用户的详细信息"
)
def get_user_info(
        db: Session = Depends(get_db),
        openid: str = Depends(get_openid)
) -> UserResponse:
    """
    获取用户信息
    """
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")

    return _build_user_response(user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="更新个人信息",
    description="更新当前绑定用户的头像与昵称"
)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    openid: str = Depends(get_openid)
) -> UserResponse:
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")

    has_change = False

    if payload.nickname is not None:
        nickname = sanitize_text(payload.nickname, max_length=50)
        if not nickname:
            raise HTTPException(status_code=400, detail="昵称不能为空")
        user.nickname = nickname  # type: ignore
        has_change = True

    if payload.avatar_url is not None:
        avatar_url = payload.avatar_url.strip()
        if len(avatar_url) > 255:
            raise HTTPException(status_code=400, detail="头像链接过长")
        user.avatar_url = avatar_url or None  # type: ignore
        has_change = True

    if not has_change:
        raise HTTPException(status_code=400, detail="未提供需要更新的字段")

    db.commit()
    db.refresh(user)

    return _build_user_response(user)