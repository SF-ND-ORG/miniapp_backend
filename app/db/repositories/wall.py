from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.db.models.wall import WallMessage
from app.db.repositories.base import BaseRepository
from app.db.repositories.resources import resourcesManager
from app.schemas.wall import WallMessageCreate, WallMessageUpdate


class WallRepository(BaseRepository[WallMessage, WallMessageCreate, WallMessageUpdate]):
    """校园墙消息仓储类"""
    
    def __init__(self):
        super().__init__(WallMessage)
    
    def get_messages_by_type(
        self,
        db: Session,
        message_type: str,
        status: str = "APPROVED",
        skip: int = 0,
        limit: int = 20
    ) -> List[WallMessage]:
        """根据消息类型获取消息列表"""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.message_type == message_type,
                    self.model.status == status
                )
            )
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
        limit: int = 20
    ) -> List[WallMessage]:
        """根据状态获取消息列表"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
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
        limit: int = 20
    ) -> List[WallMessage]:
        """获取用户发布的消息"""
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search_messages(
        self,
        db: Session,
        keyword: str,
        message_type: Optional[str] = None,
        status: str = "APPROVED",
        skip: int = 0,
        limit: int = 20
    ) -> List[WallMessage]:
        """搜索消息"""
        query = db.query(self.model).filter(self.model.status == status)
        
        # 添加关键词搜索
        if keyword:
            search_filter = or_(
                self.model.title.contains(keyword),
                self.model.content.contains(keyword),
                self.model.tags.contains(keyword)
            )
            query = query.filter(search_filter)
        
        # 添加类型过滤
        if message_type:
            query = query.filter(self.model.message_type == message_type)
        
        return query.order_by(desc(self.model.timestamp)).offset(skip).limit(limit).all()
    
    def get_popular_messages(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status: str = "APPROVED"
    ) -> List[WallMessage]:
        """获取热门消息（按点赞数排序）"""
        return (
            db.query(self.model)
            .filter(self.model.status == status)
            .order_by(desc(self.model.like_count), desc(self.model.view_count))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def increment_view_count(self, db: Session, message_id: int) -> Optional[WallMessage]:
        """增加浏览次数"""
        message = self.get(db, message_id)
        if message:
            # 直接更新数据库中的值
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.view_count: self.model.view_count + 1}
            )
            db.commit()
            db.refresh(message)
        return message
    
    def change_like_count(self, db: Session, message_id: int,count: int,user_id: int )-> Optional[WallMessage]:
        """改变点赞次数"""
        message = self.get(db, message_id)
        #print("#")
        #print(message.like_users)
        if user_id in message.like_users:
            message.like_users.remove(user_id)
            count= -1
            #print(message.like_users)
        else:
            message.like_users.append(user_id)
            count= 1
        if message:
            # 直接更新数据库中的值
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.like_count: self.model.like_count + count}
            )
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.like_users: message.like_users}
            )
            db.commit()
            db.refresh(message)
        return message
    
    def update_status(
        self,
        db: Session,
        message_id: int,
        status: str
    ) -> Optional[WallMessage]:
        """更新消息状态。

        驳回/撤回只改变状态，不删除图片：审核操作是可逆的，
        管理员之后可以通过“恢复”把状态改回 APPROVED，此时仍需读取原图片。
        图片只在消息被彻底删除时才清理。
        """
        message = self.get(db, message_id)
        if message:
            db.query(self.model).filter(self.model.id == message_id).update(
                {self.model.status: status}
            )
            db.commit()
            db.refresh(message)
        return message

    def remove(self, db: Session, *, id: int) -> Optional[WallMessage]:
        """彻底删除消息，并清理不再被任何消息引用的图片文件。"""
        message = self.get(db, id)
        if not message:
            return None
        files = message.files
        db.delete(message)
        db.commit()
        # 数据库记录删除成功后再清理磁盘，避免删除失败却丢失图片
        self._delete_unreferenced_pictures(db, files)
        return message

    def _delete_unreferenced_pictures(self, db: Session, files: Optional[str]) -> None:
        """删除不再被任何消息引用的图片（尽力而为，失败不影响主流程）。

        同一个 uid 可能被多条消息引用，因此先检查其余消息，
        只清理确实没有任何引用的文件，避免误删其他消息仍在使用的图片。
        """
        if not files:
            return
        uids = {uid.strip() for uid in files.split(",") if uid.strip()}
        if not uids:
            return

        referenced = set()
        rows = db.query(self.model.files).filter(self.model.files.isnot(None)).all()
        for (row_files,) in rows:
            for uid in (row_files or "").split(","):
                uid = uid.strip()
                if uid in uids:
                    referenced.add(uid)

        for uid in uids - referenced:
            try:
                resourcesManager.delete_picture(uid)
            except Exception:
                # 图片清理失败不应阻断删除流程
                pass
    
    def get_statistics(self, db: Session) -> dict:
        """获取墙消息统计信息"""
        total_count = db.query(self.model).count()
        approved_count = db.query(self.model).filter(self.model.status == "APPROVED").count()
        pending_count = db.query(self.model).filter(self.model.status == "PENDING").count()
        
        # 按类型统计
        type_stats = {}
        message_types = ["general", "lost_and_found", "help", "announcement"]
        for msg_type in message_types:
            count = db.query(self.model).filter(
                and_(
                    self.model.message_type == msg_type,
                    self.model.status == "APPROVED"
                )
            ).count()
            type_stats[msg_type] = count
        
        return {
            "total_count": total_count,
            "approved_count": approved_count,
            "pending_count": pending_count,
            "type_statistics": type_stats
        }
    def count_messages(
        self,
        db: Session,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> int:
        """计算符合条件的消息总数"""
        query = db.query(self.model)
        
        if status:
            query = query.filter(self.model.status == status)
        
        if message_type:
            query = query.filter(self.model.message_type == message_type)
        
        if keyword:
            search_filter = or_(
                self.model.title.contains(keyword),
                self.model.content.contains(keyword),
                self.model.tags.contains(keyword)
            )
            query = query.filter(search_filter)
        
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        
        return query.count()


wall_repository = WallRepository()
