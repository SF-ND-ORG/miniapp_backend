import requests
from typing import List, Dict, Any
from app.core.config import settings
from app.schemas.song import Song

class MusicAPIService:
    def __init__(self):
        self.base_url = settings.MUSIC_API_BASE_URL
        self.limit = settings.DEFAULT_LIMIT
    
    def search_songs(self, query: str, source: str|None = "netease", count: int = 30, page: int = 1) -> List[Song]:
        # 去掉空格
        query = query.replace(" ", "")
        params = {
            "keywords": query,
            "limit": self.limit,
            "offset": (page-1)*self.limit
        }
        
        try:
            response = requests.get(self.base_url+"/search", params=params)
            data = response.json()
            
            if not data:
                return []
            data_result_songs = data.get("result").get("songs")
            songs = []
            for item in data_result_songs:
                artists = item.get("artists", [])
                artists = [artist.get("name", "") for artist in artists]
                
                song = Song(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artists=artists,
                    album=item.get("album").get("name", ""),
                )
                songs.append(song)
            
            return songs
        except Exception as e:
            print(f"Error searching songs: {e}")
            return []
    
    def get_song_url(self, song_id: str, source: str|None = "netease", bitrate: str|None = None) -> Dict[str, Any]:
        params = {
            "id": song_id,
            "br": bitrate
        }
        
        try:
            response = requests.get(self.base_url+"/song/url", params=params)
            data = response.json()
            data_data = data.get("data")[0] if data and "data" in data else {}
            return {
                "code": 200 if data and "url" in data else 404,
                "data": {
                    "url": data_data.get("url", ""),
                    "br": data_data.get("br", 0),
                    "size": data_data.get("size", 0)
                }
            }
        except Exception as e:
            print(f"Error getting song URL: {e}")
            return {"code": 500, "data": {}}
    
    def get_song_detail(self, song_id: str) -> Dict[str, Any]:
        """根据歌曲ID获取歌曲详细信息"""
        try:
            response = requests.get(f"{self.base_url}/song/detail", params={"ids": song_id})
            data = response.json()
            
            if not data or "songs" not in data or not data["songs"]:
                return {"code": 404, "data": {}}
            
            song_info = data["songs"][0]
            artists = song_info.get("ar", [])
            artist_names = [artist.get("name", "") for artist in artists]
            
            return {
                "code": 200,
                "data": {
                    "id": str(song_info.get("id", "")),
                    "name": song_info.get("name", ""),
                    "artists": artist_names,
                    "album": song_info.get("al", {}).get("name", ""),
                    "duration": song_info.get("dt", 0),
                    "cover": song_info.get("al", {}).get("picUrl", "")
                }
            }
        except Exception as e:
            print(f"Error getting song detail: {e}")
            return {"code": 500, "data": {}}

music_api_service = MusicAPIService()