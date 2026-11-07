from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema

# API请求模式
class SongRequest(BaseModel):
    song_id: str
    song_name: str

class PlayerPlayedRequest(BaseModel):
    request_id: int

# API响应模式
class Song(BaseModel):
    id: str
    name: str
    artists: List[str]
    album: str
    duration: Optional[int] = None
    cover: Optional[str] = None

class SearchResponse(BaseModel):
    songs: List[Song]

class SongRequestResponse(BaseSchema):
    id: int
    song_id: str
    song_name: str
    status: str
    request_time: datetime
    review_time: Optional[datetime] = None
    review_reason: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    user_student_id: Optional[str] = None


# 播放器相关Schema
class CurrentSongResponse(BaseSchema):
    """当前播放歌曲响应"""
    current_song: Optional[SongRequestResponse] = None
    is_playing: bool = False
    queue_position: Optional[int] = None


# 歌曲管理统计Schema
class SongStatisticsResponse(BaseSchema):
    """歌曲统计信息响应"""
    total_requests: int
    today_requests: int
    pending_count: int
    approved_count: int
    rejected_count: int
    played_count: int


# 歌曲历史列表Schema
class SongHistoryResponse(BaseSchema):
    """歌曲历史记录响应"""
    items: List[SongRequestResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# 歌曲审核相关Schema
class SongReviewRequest(BaseSchema):
    """歌曲审核请求"""
    status: str = Field(..., pattern="^(approved|rejected)$", description="审核状态：approved或rejected")
    reason: Optional[str] = Field(None, max_length=500, description="审核理由")


class PendingSongListResponse(BaseSchema):
    """待审核歌曲列表响应"""
    items: List[SongRequestResponse]
    total: int
    page: int
    page_size: int
    has_next: bool