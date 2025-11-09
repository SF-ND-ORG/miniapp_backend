import hmac

import jwt
from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.repositories.user import user_repository
from app.services.config_manager import get_admin_openids

def get_openid(authorization: str = Header(...), db: Session = Depends(get_db)) -> str:
    """
    从JWT令牌中获取openid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证信息缺失或格式错误")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # 确保这是访问令牌而不是刷新令牌
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=401, detail="无效的令牌类型")
            
        return payload["openid"]
    except jwt.ExpiredSignatureError:
        # 当令牌过期时，返回特殊的状态码，前端可以捕获并尝试刷新
        raise HTTPException(status_code=401, detail="token已过期，请刷新")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=401, detail="token无效")


def get_current_user(
    openid: str = Depends(get_openid),
    db: Session = Depends(get_db)
):
    """获取当前用户"""
    user = user_repository.get_by_openid(db, openid)
    if not user:
        raise HTTPException(status_code=400, detail="未绑定用户")
    return user


def require_admin(
    current_user = Depends(get_current_user)
):
    """要求管理员权限"""
    admin_openids = get_admin_openids()
    if not current_user.is_admin and current_user.wechat_openid not in admin_openids:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def require_admin_panel_token(x_admin_token: str = Header(...)) -> None:
    """Validate admin panel shared token header."""
    if not hmac.compare_digest(x_admin_token, settings.ADMIN_PANEL_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid admin panel token")
