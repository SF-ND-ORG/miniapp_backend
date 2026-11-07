import jwt
import datetime
import requests
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories import refresh_token_repository

def create_access_token(openid: str, expiry_hours: int|None = None) -> str:
    """
    创建短期访问令牌
    """
    if expiry_hours is None:
        expiry_hours = settings.ACCESS_TOKEN_EXPIRE_HOURS
        
    payload = {
        "openid": openid,
        "exp": datetime.datetime.now() + datetime.timedelta(hours=expiry_hours),
        "type": "access"
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

def create_refresh_token(openid: str, db: Session, expiry_days: int|None = None) -> str:
    """
    创建长期刷新令牌
    """
    if expiry_days is None:
        expiry_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        
    # 为刷新令牌添加唯一ID，用于标识和撤销
    refresh_token_id = str(uuid.uuid4())
    expires_at = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    
    payload = {
        "openid": openid,
        "exp": expires_at,
        "jti": refresh_token_id,  # JWT ID
        "type": "refresh"
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    # 将刷新令牌保存到数据库
    refresh_token_repository.save_refresh_token(db, openid, refresh_token_id, expires_at)
    
    return token

def create_token_pair(openid: str, db: Session) -> Dict[str, str]:
    """
    创建访问令牌和刷新令牌对
    """
    access_token = create_access_token(openid)
    refresh_token = create_refresh_token(openid, db)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def verify_refresh_token(token: str, db: Session) -> Dict[str, Any]:
    """
    验证刷新令牌并返回新的令牌对
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # 确认这是刷新令牌
        if payload.get("type") != "refresh":
            return {"success": False, "msg": "无效的刷新令牌类型"}
        
        openid = payload.get("openid")
        jti = payload.get("jti")
        
        # 检查令牌是否在数据库中有效
        if not refresh_token_repository.check_refresh_token_valid(db, openid, jti):
            return {"success": False, "msg": "刷新令牌已失效"}
        
        # 创建新的令牌对
        tokens = create_token_pair(openid, db)
        return {"success": True, "tokens": tokens, "openid": openid}
        
    except jwt.ExpiredSignatureError:
        return {"success": False, "msg": "刷新令牌已过期"}
    except (jwt.InvalidTokenError, Exception) as e:
        return {"success": False, "msg": f"无效的刷新令牌: {str(e)}"}

def verify_wechat_code(code: str) -> Dict[str, Any]:
    """
    验证微信登录码并获取openid
    """
    wx_url = (
        "https://api.weixin.qq.com/sns/jscode2session?"
        f"appid={settings.WECHAT_APPID}&secret={settings.WECHAT_SECRET}"
        f"&js_code={code}&grant_type=authorization_code"
    )
    
    try:
        resp = requests.get(wx_url)
        wx_data = resp.json()
        
        if "errcode" in wx_data and wx_data["errcode"] != 0:
            return {"success": False, "msg": f"微信登录失败: {wx_data.get('errmsg')}"}
        
        return {"success": True, "openid": wx_data["openid"]}
    except Exception as e:
        return {"success": False, "msg": f"微信登录请求失败: {str(e)}"}
