from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.schemas.song import (
    Song, 
    SongStatisticsResponse, 
    SongHistoryResponse, 
    SongReviewRequest,
    PendingSongListResponse,
    SongRequestResponse
)
from app.services.music_api import music_api_service
from app.db.repositories import song_request_repository
from app.db.session import get_db
from app.core.security import require_admin

router = APIRouter()

@router.get("/search",
            response_model=Dict[str, List[Song]],
            summary="歌曲搜索",
            description="进行歌曲搜索",
            responses={
                200: {
                    "description": "成功返回歌曲列表",
                    "content": {
                        "application/json": {
                            "example": {
                                "songs": [
                                    {
                                        "id": "123456",
                                        "name": "Example Song",
                                        "artists": ["Artist Name"],
                                        "album": "Example Album",
                                        "duration": 240,
                                        "cover": "http://example.com/cover.jpg",
                                        "source": "netease"
                                    }
                                ]
                            }
                        }
                    }
                },
                400: {
                    "description": "查询参数错误",
                    "content": {
                        "application/json": {
                            "example": {"detail": "查询参数错误"}
                        }
                    }
                }
            }
            )

def search_songs(query: str = Query(..., min_length=1), 
                 source: str|None = None, 
                 count: int = 30, 
                 page: int = 1) -> Dict[str, List[Song]]:
    songs = music_api_service.search_songs(query, source, count, page)
    return {"songs": songs}

@router.get("/geturl",summary="获取歌曲URL",description="获取歌曲的播放URL",
            responses={
                200: {
                    "description": "成功返回歌曲URL",
                    "content": {
                        "application/json": {
                            "example": {
                                "url": "http://example.com/song.mp3",
                                "source": "netease",
                                "br": "320k"
                            }
                        }
                    }
                },
                400: {
                    "description": "查询参数错误",
                    "content": {
                        "application/json": {
                            "example": {"detail": "查询参数错误"}
                        }
                    }
                }
            })
def get_song_url(id: str = Query(..., description="Song ID"), 
                 source: str|None = None,
                 br: str|None = None) -> Dict[str, Any]:
    return music_api_service.get_song_url(id, source, br)


@router.get("/songs/admin/statistics",
            response_model=SongStatisticsResponse,
            summary="获取歌曲统计信息",
            description="获取歌曲管理统计信息（管理员功能）")
def get_song_statistics(
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
) -> SongStatisticsResponse:
    """获取歌曲统计信息（管理员功能）"""
    stats = song_request_repository.get_song_statistics(db)
    return SongStatisticsResponse(**stats)


@router.get("/songs/admin/history",
            response_model=SongHistoryResponse,
            summary="获取歌曲历史记录",
            description="获取歌曲点播历史记录（管理员功能）")
def get_song_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    date: Optional[str] = Query(None, description="日期筛选 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
) -> SongHistoryResponse:
    """获取歌曲历史记录（管理员功能）"""
    history_data = song_request_repository.get_song_history(
        db=db,
        page=page,
        page_size=page_size,
        date=date
    )
    return SongHistoryResponse(**history_data)


@router.get("/songs/admin/pending",
            response_model=PendingSongListResponse,
            summary="获取待审核歌曲列表",
            description="获取待审核的歌曲列表（管理员功能）")
def get_pending_songs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: pending, approved, rejected"),
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
) -> PendingSongListResponse:
    """获取待审核歌曲列表（管理员功能）"""
    status_filter = [status] if status else None
    pending_data = song_request_repository.get_pending_songs_for_review(
        db=db,
        page=page,
        page_size=page_size,
        status_filter=status_filter
    )
    return PendingSongListResponse(**pending_data)


@router.put("/songs/admin/review/{request_id}",
            response_model=SongRequestResponse,
            summary="审核歌曲请求",
            description="审核歌曲请求：通过或拒绝（管理员功能）")
def review_song_request(
    request_id: int,
    review_data: SongReviewRequest,
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
) -> SongRequestResponse:
    """审核歌曲请求（管理员功能）"""
    # 检查请求是否存在
    current_status = song_request_repository.get_song_request_status(db, request_id)
    if not current_status:
        raise HTTPException(status_code=404, detail="歌曲请求不存在")
    
    # 检查是否已经审核过
    if current_status != "pending":
        raise HTTPException(status_code=400, detail=f"歌曲请求已经是{current_status}状态，无法重复审核")
    
    # 执行审核
    updated_request = song_request_repository.update_song_request_status(
        db=db,
        request_id=request_id,
        status=review_data.status,
        reason=review_data.reason or "",
        reviewer_id=admin_user.id
    )
    
    if not updated_request:
        raise HTTPException(status_code=500, detail="审核失败")
    
    response_data = {
        "id": updated_request.id,
        "song_id": updated_request.song_id,
        "song_name": updated_request.song_name,
        "status": updated_request.status,
        "request_time": updated_request.request_time,
        "review_time": updated_request.review_time,
        "review_reason": updated_request.review_reason,
        "user_id": updated_request.user_id,
        "user_name": updated_request.user.name if updated_request.user else None,
        "user_student_id": updated_request.user.student_id if updated_request.user else None
    }
    return SongRequestResponse(**response_data)
