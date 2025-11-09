from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models.song_request import SongRequest
from app.db.models.user import User
from app.schemas.song import SongRequest as SongRequestSchema, SongRequestResponse
from app.db.repositories.base import BaseRepository
from app.services.music_api import music_api_service

class SongRequestRepository(BaseRepository[SongRequest, SongRequestSchema, SongRequestSchema]):
    """歌曲请求数据访问层"""
    
    def check_recent_song_requests(self, db: Session, user_id: int, minutes: int = 30) -> int:
        """检查用户最近的点歌请求"""
        thirty_min_ago = datetime.now() - timedelta(minutes=minutes)
        return db.query(SongRequest).filter(
            SongRequest.user_id == user_id,
            SongRequest.request_time > thirty_min_ago,
            SongRequest.status.in_(["pending", "approved", "played"])
        ).count()
    
    def check_song_already_requested(self, db: Session, user_id: int, song_id: str) -> bool:
        """检查用户是否已经请求过该歌曲"""
        return db.query(SongRequest).filter(
            SongRequest.song_id == song_id,
            SongRequest.status.in_(["pending", "approved"])
        ).count() > 0
    
    def count_pending_approved_songs(self, db: Session, user_id: int) -> int:
        """计算用户待审核和已批准的歌曲数量"""
        return db.query(SongRequest).filter(
            SongRequest.user_id == user_id,
            SongRequest.status.in_(["pending", "approved"])
        ).count()
    
    def create_song_request(self, db: Session, user_id: int, song_id: str,song_name:str) -> SongRequest:
        """创建歌曲请求"""
        song_request = SongRequest(
            user_id=user_id,
            song_id=song_id,
            song_name=song_name,
            status="pending",
            request_time=datetime.now()
        )
        db.add(song_request)
        db.commit()
        db.refresh(song_request)
        return song_request
    
    def get_song_requests_by_status(self, db: Session, status: str) -> List[Dict[str, Any]]:
        """获取指定状态的歌曲请求列表"""
        query = db.query(
            SongRequest.id,
            SongRequest.song_id,
            SongRequest.song_name,
            SongRequest.status,
            SongRequest.request_time,
            SongRequest.review_time,
            SongRequest.review_reason,
            User.student_id,
            User.name,
            User.wechat_openid
        ).join(
            User, SongRequest.user_id == User.id
        ).filter(
            SongRequest.status == status
        ).order_by(
            SongRequest.request_time.asc()
        )
        
        result = []
        for row in query.all():
            # 转换查询结果为字典
            result.append({
                "id": row.id,
                "song_id": row.song_id,
                "song_name": row.song_name,
                "status": row.status,
                "request_time": row.request_time,
                "review_time": row.review_time,
                "review_reason": row.review_reason,
                "student_id": row.student_id,
                "name": row.name,
                "wechat_openid": row.wechat_openid
            })
        
        return result
    
    def get_song_request_status(self, db: Session, request_id: int) -> Optional[str]:
        """获取歌曲请求的状态"""
        request = db.query(SongRequest).filter(SongRequest.id == request_id).first()
        return request.status if request else None# type: ignore
    
    def update_song_request_status(
        self, db: Session, request_id: int, status: str, reason: str = "", reviewer_id: int|None = None
    ) -> SongRequest:
        """更新歌曲请求的状态"""
        request = db.query(SongRequest).filter(SongRequest.id == request_id).first()
        if request:
            request.status = status# type: ignore
            request.review_time = datetime.now()# type: ignore
            request.review_reason = reason# type: ignore
            request.reviewer_id = reviewer_id# type: ignore
            db.commit()
            db.refresh(request)
        return request
    
    def get_approved_song_queue(self, db: Session) -> List[Dict[str, Any]]:
        """获取已批准的歌曲队列"""
        query = db.query(
            SongRequest.id,
            SongRequest.song_id,
            SongRequest.song_name,
            SongRequest.request_time,
            User.name,
            User.student_id
        ).join(
            User, SongRequest.user_id == User.id
        ).filter(
            SongRequest.status == "approved"
        ).order_by(
            SongRequest.request_time.asc()
        )
        
        result = []
        for row in query.all():
            # 暂时从歌曲名称中尝试提取艺术家信息，或者设为默认值
            title = str(row.song_name)
            artist = "未知艺术家"
            
            # 如果歌曲名称包含" - "，尝试分离艺术家和歌曲名
            if " - " in title:
                parts = title.split(" - ", 1)
                if len(parts) == 2:
                    artist = parts[0].strip()
                    title = parts[1].strip()
            
            result.append({
                "id": row.id,
                "request_id": row.id,
                "song_id": row.song_id,
                "title": title,
                "artist": artist,
                "requester_name": row.name,
                "created_at": row.request_time.isoformat() if row.request_time else None
            })
        
        return result

    def get_requests_by_user_id(self, db: Session, user_id: int, status: List[str]) -> List[SongRequest]:
        """根据ID获取歌曲请求"""
        fetchall = db.query(SongRequest).filter(SongRequest.user_id == user_id, SongRequest.status.in_(status)).all()
        result = []
        for row in fetchall:
            result.append(SongRequestResponse.model_validate(row))
        return result

    def get_current_playing_song(self, db: Session) -> Optional[Dict[str, Any]]:
        """获取当前播放的歌曲"""
        # 查找状态为 "playing" 的歌曲，如果没有则返回队列中第一首
        current = db.query(SongRequest).join(User, SongRequest.user_id == User.id).filter(
            SongRequest.status == "playing"
        ).first()
        
        if not current:
            # 如果没有正在播放的歌曲，返回队列中第一首已批准的歌曲
            current = db.query(SongRequest).join(User, SongRequest.user_id == User.id).filter(
                SongRequest.status == "approved"
            ).order_by(SongRequest.request_time.asc()).first()
        
        if current:
            # 暂时从歌曲名称中尝试提取艺术家信息，或者设为默认值
            title = str(current.song_name)
            artist = "未知艺术家"
            
            # 如果歌曲名称包含" - "，尝试分离艺术家和歌曲名
            if " - " in title:
                parts = title.split(" - ", 1)
                if len(parts) == 2:
                    artist = parts[0].strip()
                    title = parts[1].strip()
            
            return {
                "id": current.id,
                "song_id": current.song_id,
                "title": title,
                "artist": artist,
                "requester_name": current.user.name if current.user else "未知用户",
                "created_at": current.request_time.isoformat() if current.request_time is not None else None,
                "status": current.status
            }
        return None

    def get_song_statistics(self, db: Session) -> Dict[str, int]:
        """获取歌曲统计信息"""
        # 总请求数
        total_requests = db.query(SongRequest).count()
        
        # 今日请求数
        today = datetime.now().date()
        today_requests = db.query(SongRequest).filter(
            func.date(SongRequest.request_time) == today
        ).count()
        
        # 各状态统计
        pending_count = db.query(SongRequest).filter(SongRequest.status == "pending").count()
        approved_count = db.query(SongRequest).filter(SongRequest.status == "approved").count()
        rejected_count = db.query(SongRequest).filter(SongRequest.status == "rejected").count()
        played_count = db.query(SongRequest).filter(SongRequest.status == "played").count()
        
        return {
            "total_requests": total_requests,
            "today_requests": today_requests,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "played_count": played_count
        }

    def get_song_history(
        self, 
        db: Session, 
        page: int = 1, 
        page_size: int = 20,
        date: Optional[str] = None,
        status_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """获取歌曲历史记录（分页）"""
        query = db.query(SongRequest).join(User, SongRequest.user_id == User.id)
        
        # 日期筛选
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(func.date(SongRequest.request_time) == target_date)
        
        # 状态筛选
        if status_filter:
            query = query.filter(SongRequest.status.in_(status_filter))
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * page_size
        items = query.order_by(SongRequest.request_time.desc()).offset(offset).limit(page_size).all()
        
        # 转换为响应格式
        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "song_id": item.song_id,
                "song_name": item.song_name,
                "status": item.status,
                "request_time": item.request_time,
                "review_time": item.review_time,
                "review_reason": item.review_reason,
                "user_id": item.user_id,
                "user_name": item.user.name if item.user else None,
                "user_student_id": item.user.student_id if item.user else None
            })
        
        has_next = (page * page_size) < total
        
        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next
        }

    def get_pending_songs_for_review(
        self, 
        db: Session, 
        page: int = 1, 
        page_size: int = 20,
        status_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """获取待审核的歌曲列表（分页）"""
        query = db.query(SongRequest).join(User, SongRequest.user_id == User.id)
        
        # 状态筛选 - 默认只显示待审核的
        if status_filter:
            query = query.filter(SongRequest.status.in_(status_filter))
        else:
            query = query.filter(SongRequest.status == "pending")
        
        # 计算总数
        total = query.count()
        
        # 分页查询 - 按请求时间排序，最新的在前
        offset = (page - 1) * page_size
        items = query.order_by(SongRequest.request_time.asc()).offset(offset).limit(page_size).all()
        
        # 转换为响应格式
        result_items = []
        for item in items:
            result_items.append({
                "id": item.id,
                "song_id": item.song_id,
                "song_name": item.song_name,
                "status": item.status,
                "request_time": item.request_time,
                "review_time": item.review_time,
                "review_reason": item.review_reason,
                "user_id": item.user_id,
                "user_name": item.user.name if item.user else None,
                "user_student_id": item.user.student_id if item.user else None
            })
        
        has_next = (page * page_size) < total
        
        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next
        }

song_request_repository = SongRequestRepository(SongRequest)