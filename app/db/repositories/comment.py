from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.db.repositories.base import BaseRepository
from app.db.models.comment import CommentMessage,MessageStatus
from app.schemas.comment import CommentMessageCreate,CommentMessageUpdate


class CommentRepository(BaseRepository[CommentMessage, CommentMessageUpdate, CommentMessageCreate]):
    """校园墙消息仓储类"""
    
    def __init__(self):
        super().__init__(CommentMessage)
    
    def get_messages_by_status_and_wall_id(
        self,
        db: Session,
        status: str,
        skip: int = 0,
        limit: int = 100,
        wall_id: int = 0
    ) -> List[CommentMessage]:
        """根据状态获取消息列表"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
            .filter(self.model.wall_id == wall_id)
            .order_by(desc(self.model.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_messages_by_status(
        self,
        db: Session,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[CommentMessage]:
        """根据状态获取消息列表"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
            .order_by(desc(self.model.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_messages_by_wall_id(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        wall_id: int = 0
    ) -> List[CommentMessage]:
        """根据墙获取消息列表"""
        return (
            db.query(self.model)
            .filter(self.model.wall_id == wall_id)
            .order_by(desc(self.model.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_messages_by_user(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[CommentMessage]:
        """获取用户发布的消息"""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_popular_messages(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: str = "APPROVED",
        wall_id: int = 0
    ) -> List[CommentMessage]:
        """获取热门消息（按点赞数排序）"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
            .filter(self.model.wall_id == wall_id)
            .order_by(desc(self.model.like_count))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def increment_like_count(self, db: Session, message_id: int) -> Optional[CommentMessage]:
        """增加点赞次数"""
        message = self.get(db, message_id)
        if message:
            # 直接更新数据库中的值
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.like_count: self.model.like_count + 1}
            )
            db.commit()
            db.refresh(message)
        return message
    
    def update_status(
        self,
        db: Session,
        message_id: int,
        status: str
    ) -> Optional[CommentMessage]:
        """更新消息状态"""
        message = self.get(db, message_id)
        if message:
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.status: status}
            )
            db.commit()
            db.refresh(message)
        return message

    def delete_by_wall_id(self, db: Session, wall_id: int) -> int:
        """删除指定墙下的所有评论，避免外键残留"""
        deleted = (
            db.query(self.model)
            .filter(self.model.wall_id == wall_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
    
    def count_messages(
        self,
        db: Session,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> int:
        """计算符合条件的消息总数"""
        query = db.query(self.model)
        
        if status:
            query = query.filter(self.model.status == status)
        
        if keyword:
            search_filter = or_(
                self.model.content.contains(keyword),
            )
            query = query.filter(search_filter)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return query.count()


comment_repository = CommentRepository()
