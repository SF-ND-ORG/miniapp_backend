from urllib.parse import quote, urlparse

import requests
from fastapi import APIRouter, Query, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
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

# 只允许代理网易云音乐 CDN 的地址，避免该接口被当作任意 URL 代理使用
_ALLOWED_AUDIO_HOST_SUFFIXES = (".music.126.net", ".126.net")
_AUDIO_PROXY_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
_AUDIO_RESPONSE_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "ETag",
    "Last-Modified",
)
_AUDIO_EXTENSIONS = (".mp3", ".flac", ".m4a", ".aac", ".wav", ".ogg")
_AUDIO_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Range, Content-Type",
    "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges, Content-Type",
}


def _parse_song_id(value: str) -> str:
    """兼容 /song/stream/123 和 /song/stream/123.mp3 两种写法。"""
    song_id = value
    lower = song_id.lower()
    for ext in _AUDIO_EXTENSIONS:
        if lower.endswith(ext):
            song_id = song_id[: -len(ext)]
            break
    if not song_id.isdigit():
        raise HTTPException(status_code=400, detail="歌曲 ID 不合法")
    return song_id


def _is_allowed_audio_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return bool(host) and host.endswith(_ALLOWED_AUDIO_HOST_SUFFIXES)


def _audio_extension(audio_type: str | None) -> str:
    value = (audio_type or "").lower().lstrip(".")
    return value if f".{value}" in _AUDIO_EXTENSIONS else "mp3"


@router.get("/geturl",summary="获取歌曲URL",description="获取歌曲的播放URL（包含试听片段信息与代理播放地址）",
            responses={
                200: {
                    "description": "成功返回歌曲URL",
                    "content": {
                        "application/json": {
                            "example": {
                                "code": 200,
                                "data": {
                                    "id": "33894312",
                                    "url": "http://example.com/song.mp3",
                                    "stream_url": "/api/song/stream/33894312.mp3?br=320000",
                                    "free_trial_info": None,
                                    "is_trial": False
                                }
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
    result = music_api_service.get_song_url(id, source, br)
    data = dict(result.get("data") or {})

    # 小程序无法给 InnerAudioContext 设置请求头，也无法直接播放 http 音频；
    # 这里额外返回一个同源的代理地址，由后端转发网易云音频流（包含 Range 支持）。
    if data.get("url"):
        ext = _audio_extension(data.get("type"))
        stream_path = (
            f"{settings.API_V1_STR}/song/stream/"
            f"{quote(str(data.get('id') or id), safe='')}.{ext}"
        )
        if br:
            stream_path += f"?br={quote(str(br), safe='')}"
        data["stream_url"] = stream_path

    return {"code": result.get("code", 500), "data": data}


@router.get(
    "/song/stream/{song_id}",
    summary="代理播放歌曲音频",
    description="将网易云音频流代理给小程序的 InnerAudioContext，支持 Range 请求",
)
def stream_song_audio(
    song_id: str,
    request: Request,
    br: str | None = Query(None, max_length=20, description="码率，例如 320000"),
):
    song_id = _parse_song_id(song_id)

    playback = music_api_service.get_song_url(song_id, bitrate=br)
    data = playback.get("data") or {}
    audio_url = data.get("url") or ""
    if not audio_url:
        raise HTTPException(status_code=404, detail="无法获取该歌曲的音频地址")
    if not _is_allowed_audio_url(audio_url):
        raise HTTPException(status_code=502, detail="音频地址不受信任")

    upstream_headers = {
        "User-Agent": _AUDIO_PROXY_USER_AGENT,
        "Accept": "*/*",
        # 不发送 Referer：网易云 CDN 在带 Referer 时可能返回 403
    }
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    try:
        upstream = requests.get(
            audio_url,
            headers=upstream_headers,
            stream=True,
            timeout=(10, 60),
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="音频源连接失败") from exc

    if upstream.status_code not in (200, 206):
        upstream.close()
        raise HTTPException(
            status_code=502,
            detail=f"音频源返回异常状态: {upstream.status_code}",
        )

    if not _is_allowed_audio_url(upstream.url or audio_url):
        upstream.close()
        raise HTTPException(status_code=502, detail="音频地址重定向不受信任")

    response_headers = {
        name: upstream.headers[name]
        for name in _AUDIO_RESPONSE_HEADERS
        if upstream.headers.get(name)
    }
    response_headers.setdefault("Content-Type", "audio/mpeg")
    response_headers.setdefault("Accept-Ranges", "bytes")
    response_headers["Cache-Control"] = "private, max-age=300"
    response_headers["Content-Disposition"] = "inline"
    response_headers.update(_AUDIO_CORS_HEADERS)

    def iterator():
        try:
            for chunk in upstream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return StreamingResponse(
        iterator(),
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=None,
    )


@router.head(
    "/song/stream/{song_id}",
    include_in_schema=False,
)
def head_song_audio(
    song_id: str,
    br: str | None = Query(None, max_length=20),
):
    """部分播放器会先发 HEAD 请求探测音频大小和类型。"""
    song_id = _parse_song_id(song_id)

    playback = music_api_service.get_song_url(song_id, bitrate=br)
    data = playback.get("data") or {}
    audio_url = data.get("url") or ""
    if not audio_url:
        raise HTTPException(status_code=404, detail="无法获取该歌曲的音频地址")
    if not _is_allowed_audio_url(audio_url):
        raise HTTPException(status_code=502, detail="音频地址不受信任")

    try:
        upstream = requests.head(
            audio_url,
            headers={
                "User-Agent": _AUDIO_PROXY_USER_AGENT,
                "Accept": "*/*",
                # 不发送 Referer，避免网易云 CDN 返回 403
            },
            timeout=(10, 20),
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="音频源连接失败") from exc

    if upstream.status_code not in (200, 206):
        upstream.close()
        raise HTTPException(
            status_code=502,
            detail=f"音频源返回异常状态: {upstream.status_code}",
        )

    if not _is_allowed_audio_url(upstream.url or audio_url):
        upstream.close()
        raise HTTPException(status_code=502, detail="音频地址重定向不受信任")

    headers = {
        name: upstream.headers[name]
        for name in _AUDIO_RESPONSE_HEADERS
        if upstream.headers.get(name)
    }
    headers.setdefault("Content-Type", "audio/mpeg")
    headers.setdefault("Accept-Ranges", "bytes")
    headers["Cache-Control"] = "private, max-age=300"
    headers["Content-Disposition"] = "inline"
    headers.update(_AUDIO_CORS_HEADERS)
    upstream.close()

    return Response(status_code=200, headers=headers)


@router.options(
    "/song/stream/{song_id}",
    include_in_schema=False,
)
def options_song_audio(song_id: str):
    _parse_song_id(song_id)
    return Response(status_code=204, headers=_AUDIO_CORS_HEADERS)


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
