from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models.refresh_token import RefreshToken
from app.db.repositories.base import BaseRepository

class RefreshTokenRepository(BaseRepository[RefreshToken, dict, dict]):# type: ignore
    """刷新令牌数据访问层"""
    
    def save_refresh_token(
        self, db: Session, openid: str, token_id: str, expires_at: datetime
    ) -> RefreshToken:
        """保存刷新令牌"""
        # 首先删除该用户的所有刷新令牌
        db.query(RefreshToken).filter(RefreshToken.openid == openid).delete()
        db.commit()
        
        # 创建新的刷新令牌
        refresh_token = RefreshToken(
            openid=openid,
            token_id=token_id,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        return refresh_token
    
    def check_refresh_token_valid(self, db: Session, openid: str, token_id: str) -> bool:
        """检查刷新令牌是否有效"""
        return db.query(RefreshToken).filter(
            RefreshToken.openid == openid,
            RefreshToken.token_id == token_id,
            RefreshToken.expires_at > datetime.now()
        ).first() is not None
    
    def invalidate_refresh_token(self, db: Session, openid: str) -> None:
        """使指定用户的所有刷新令牌失效"""
        db.query(RefreshToken).filter(RefreshToken.openid == openid).delete()
        db.commit()

# 实例化仓库
refresh_token_repository = RefreshTokenRepository(RefreshToken)