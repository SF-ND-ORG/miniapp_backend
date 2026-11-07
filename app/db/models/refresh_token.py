from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint

from app.db.session import Base
from app.db.models.base import BaseModel

class RefreshToken(BaseModel):
    """刷新令牌模型"""
    __tablename__ = "refresh_tokens"
    
    # 关联的微信openid
    openid = Column(String, nullable=False, index=True)
    # 令牌ID
    token_id = Column(String, nullable=False, index=True)
    # 过期时间
    expires_at = Column(DateTime, nullable=False)
    
    # 唯一约束，确保每个openid和token_id组合只有一个
    __table_args__ = (
        UniqueConstraint('openid', 'token_id', name='uix_refresh_token_openid_token_id'),
    )
    
    def __repr__(self):
        return f"<RefreshToken {self.token_id} (openid={self.openid})>"