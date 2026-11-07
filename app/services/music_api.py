import copy
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from app.core.config import settings
from app.schemas.song import Song

COOKIE_FILE_NAME = ".netease_cookie"

# Set-Cookie 中不属于 Cookie 请求头的属性，保存前需要剔除
_COOKIE_ATTRIBUTES = {
    "max-age",
    "expires",
    "path",
    "domain",
    "httponly",
    "secure",
    "samesite",
    "priority",
    "partitioned",
}


class MusicAPIService:
    def __init__(self):
        self.base_url = settings.MUSIC_API_BASE_URL
        self.limit = settings.DEFAULT_LIMIT
        self._cookie_lock = threading.Lock()
        self._cookie_file = Path(__file__).resolve().parents[2] / COOKIE_FILE_NAME
        self._cookie = ""
        # 播放地址缓存：音频播放器会为同一个文件发起多次 Range 请求，
        # 缓存一小段时间可以避免每次都去请求网易云接口。
        self._playback_cache: Dict[tuple[str, str], tuple[float, Dict[str, Any]]] = {}
        self._playback_cache_lock = threading.Lock()
        self._playback_cache_ttl = 300
        self._load_cookie()

    # ------------------------------------------------------------------
    # 网易云 Cookie 管理
    # ------------------------------------------------------------------
    def _load_cookie(self) -> None:
        try:
            if self._cookie_file.is_file():
                self._cookie = self._cookie_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            print(f"Error loading Netease cookie: {exc}")

    def _persist_cookie_locked(self) -> None:
        try:
            if self._cookie:
                self._cookie_file.write_text(self._cookie, encoding="utf-8")
                try:
                    self._cookie_file.chmod(0o600)
                except OSError:
                    pass
            elif self._cookie_file.is_file():
                self._cookie_file.unlink()
        except OSError as exc:
            print(f"Error saving Netease cookie: {exc}")

    def get_cookie(self) -> str:
        with self._cookie_lock:
            return self._cookie

    def has_cookie(self) -> bool:
        return bool(self.get_cookie())

    @staticmethod
    def _normalize_cookie(cookie: str) -> str:
        """把 Set-Cookie 格式的字符串压缩成合法的 Cookie 请求头。

        网易云接口可能返回 ``MUSIC_U=xxx; Max-Age=...; Expires=...; Path=/;``
        这种格式，直接作为 Cookie 请求头会把属性也一起发出去，这里只保留
        ``name=value`` 部分。
        """
        pairs = []
        for chunk in (cookie or "").split(";"):
            chunk = chunk.strip()
            if not chunk or "=" not in chunk:
                continue
            name = chunk.split("=", 1)[0].strip()
            if not name or name.lower() in _COOKIE_ATTRIBUTES:
                continue
            pairs.append(chunk)
        return "; ".join(pairs)

    def set_cookie(self, cookie: str) -> None:
        value = self._normalize_cookie(cookie)
        with self._cookie_lock:
            self._cookie = value
            self._persist_cookie_locked()
        # 登录状态变化后，之前缓存的试听/播放地址可能已经不再适用
        self._clear_playback_cache()

    def clear_cookie(self) -> None:
        with self._cookie_lock:
            self._cookie = ""
            self._persist_cookie_locked()
        self._clear_playback_cache()

    def _clear_playback_cache(self) -> None:
        with self._playback_cache_lock:
            self._playback_cache.clear()

    @staticmethod
    def _store_cookie_from_response(data: Dict[str, Any]) -> str:
        cookie = data.get("cookie") if isinstance(data, dict) else None
        if not cookie and isinstance(data.get("data"), dict):
            cookie = data["data"].get("cookie")
        return str(cookie) if cookie else ""

    @staticmethod
    def _timestamp() -> int:
        return int(time.time() * 1000)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        json_body: Dict[str, Any] | None = None,
        include_cookie: bool = True,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        request_params = dict(params or {})
        if include_cookie:
            cookie = self.get_cookie()
            if cookie:
                request_params.setdefault("cookie", cookie)

        response = requests.request(
            method,
            f"{self.base_url}{path}",
            params=request_params,
            json=json_body,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # 登录相关接口
    # ------------------------------------------------------------------
    def get_login_status(self) -> Dict[str, Any]:
        if not self.has_cookie():
            return {
                "logged_in": False,
                "account": {},
                "profile": {},
                "code": 200,
                "message": "未登录",
            }

        try:
            data = self._request(
                "GET",
                "/login/status",
                params={"timestamp": self._timestamp()},
            )
        except Exception as exc:
            print(f"Error getting login status: {exc}")
            return {
                "logged_in": False,
                "account": {},
                "profile": {},
                "code": 500,
                "message": "无法获取网易云登录状态",
            }

        payload = data.get("data") if isinstance(data, dict) else None
        if not isinstance(payload, dict):
            payload = {}

        account = payload.get("account") or {}
        profile = payload.get("profile") or {}
        logged_in = bool(account or profile)
        return {
            "logged_in": logged_in,
            "account": account,
            "profile": profile,
            "code": data.get("code", 200) if isinstance(data, dict) else 500,
            "message": "已登录" if logged_in else "未登录",
        }

    def send_captcha(self, phone: str, ctcode: str = "86") -> Dict[str, Any]:
        try:
            data = self._request(
                "GET",
                "/captcha/sent",
                params={
                    "phone": phone,
                    "ctcode": ctcode,
                    "timestamp": self._timestamp(),
                },
                include_cookie=False,
            )
        except Exception as exc:
            print(f"Error sending captcha: {exc}")
            return {"success": False, "code": 500, "message": "验证码发送失败，请稍后重试"}

        code = data.get("code") if isinstance(data, dict) else None
        message = data.get("message") or data.get("msg") if isinstance(data, dict) else None
        success = code in (200, 302)
        return {
            "success": success,
            "code": code,
            "message": message or ("验证码已发送" if success else "验证码发送失败"),
        }

    def login_cellphone(
        self,
        phone: str,
        captcha: str,
        countrycode: str = "86",
    ) -> Dict[str, Any]:
        try:
            data = self._request(
                "GET",
                "/login/cellphone",
                params={
                    "phone": phone,
                    "captcha": captcha,
                    "countrycode": countrycode,
                    "timestamp": self._timestamp(),
                },
                include_cookie=False,
                timeout=20,
            )
        except Exception as exc:
            print(f"Error logging in with cellphone: {exc}")
            return {"success": False, "code": 500, "message": "登录失败，请稍后重试", "profile": {}}

        code = data.get("code") if isinstance(data, dict) else None
        success = code == 200
        payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else {}
        profile = (data.get("profile") if isinstance(data, dict) else None) or payload.get("profile") or {}
        account = (data.get("account") if isinstance(data, dict) else None) or payload.get("account") or {}
        message = data.get("message") or data.get("msg") if isinstance(data, dict) else None

        if success and isinstance(data, dict):
            cookie = self._store_cookie_from_response(data)
            if cookie:
                self.set_cookie(cookie)

        return {
            "success": success,
            "code": code,
            "message": message or ("登录成功" if success else "登录失败，请检查验证码"),
            "profile": profile,
            "account": account,
        }

    def get_qr_key(self) -> Dict[str, Any]:
        try:
            data = self._request(
                "GET",
                "/login/qr/key",
                params={"timestamp": self._timestamp()},
                include_cookie=False,
            )
        except Exception as exc:
            print(f"Error getting QR key: {exc}")
            return {"success": False, "key": "", "code": 500, "message": "获取二维码失败"}

        payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else {}
        key = payload.get("unikey") or ""
        return {
            "success": bool(key),
            "key": key,
            "code": data.get("code") if isinstance(data, dict) else None,
            "message": "" if key else "获取二维码失败",
        }

    def create_qr(self, key: str) -> Dict[str, Any]:
        try:
            data = self._request(
                "GET",
                "/login/qr/create",
                params={
                    "key": key,
                    "qrimg": "true",
                    "timestamp": self._timestamp(),
                },
                include_cookie=False,
            )
        except Exception as exc:
            print(f"Error creating QR code: {exc}")
            return {"success": False, "qrimg": "", "qrurl": "", "code": 500, "message": "生成二维码失败"}

        payload = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else {}
        qrimg = payload.get("qrimg") or ""
        qrurl = payload.get("qrurl") or ""
        return {
            "success": bool(qrimg),
            "qrimg": qrimg,
            "qrurl": qrurl,
            "code": data.get("code") if isinstance(data, dict) else None,
            "message": "" if qrimg else "生成二维码失败",
        }

    def check_qr(self, key: str) -> Dict[str, Any]:
        params = {"key": key, "timestamp": self._timestamp()}
        try:
            data = self._request(
                "GET",
                "/login/qr/check",
                params=params,
                include_cookie=False,
            )
            code = data.get("code") if isinstance(data, dict) else None

            # 部分情况下扫码后返回 502，需要带上 noCookie 重试
            if code == 502:
                params["noCookie"] = "true"
                data = self._request(
                    "GET",
                    "/login/qr/check",
                    params=params,
                    include_cookie=False,
                )
                code = data.get("code") if isinstance(data, dict) else None
        except Exception as exc:
            print(f"Error checking QR status: {exc}")
            return {"success": False, "code": 500, "message": "二维码状态检测失败"}

        if code == 803 and isinstance(data, dict):
            cookie = self._store_cookie_from_response(data)
            if cookie:
                self.set_cookie(cookie)

        messages = {
            800: "二维码已过期，请重新获取",
            801: "等待扫码",
            802: "已扫码，请在手机上确认登录",
            803: "授权登录成功",
        }
        message = None
        if isinstance(data, dict):
            message = data.get("message") or data.get("msg")
        message = message or messages.get(code, "未知状态")

        return {
            "success": code == 803,
            "code": code,
            "message": message,
        }

    def logout(self) -> Dict[str, Any]:
        try:
            if self.has_cookie():
                self._request(
                    "GET",
                    "/logout",
                    params={"timestamp": self._timestamp()},
                )
        except Exception as exc:
            print(f"Error logging out from Netease: {exc}")
        finally:
            self.clear_cookie()

        return {"success": True, "message": "已退出网易云登录"}

    # ------------------------------------------------------------------
    # 歌曲接口
    # ------------------------------------------------------------------
    def search_songs(self, query: str, source: str | None = "netease", count: int = 30, page: int = 1) -> List[Song]:
        # 去掉空格
        query = query.replace(" ", "")
        params = {
            "keywords": query,
            "limit": self.limit,
            "offset": (page - 1) * self.limit,
        }

        try:
            data = self._request("GET", "/search", params=params)
            if not data:
                return []

            result = data.get("result") or {}
            data_result_songs = result.get("songs") or []
            songs = []
            for item in data_result_songs:
                artists = item.get("artists", [])
                artists = [artist.get("name", "") for artist in artists]
                album = item.get("album") or {}

                song = Song(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    artists=artists,
                    album=album.get("name", ""),
                )
                songs.append(song)

            return songs
        except Exception as e:
            print(f"Error searching songs: {e}")
            return []

    def get_song_url(self, song_id: str, source: str | None = "netease", bitrate: str | None = None) -> Dict[str, Any]:
        """获取歌曲播放地址。

        未登录或非会员时，网易云会返回试听片段，此时 ``free_trial_info``
        会包含试听片段的开始和结束时间（单位：秒）。
        """
        cache_key = (str(song_id), str(bitrate or ""))
        now = time.time()
        with self._playback_cache_lock:
            cached = self._playback_cache.get(cache_key)
            if cached and cached[0] > now:
                return copy.deepcopy(cached[1])

        params: Dict[str, Any] = {"id": song_id}
        if bitrate:
            params["br"] = bitrate

        try:
            data = self._request("GET", "/song/url", params=params)
            items = data.get("data") if isinstance(data, dict) else None
            song_data = items[0] if items else {}

            if not isinstance(song_data, dict):
                song_data = {}

            free_trial_raw = song_data.get("freeTrialInfo")
            free_trial_info = None
            if isinstance(free_trial_raw, dict):
                free_trial_info = {
                    "start": free_trial_raw.get("start"),
                    "end": free_trial_raw.get("end"),
                }

            url = song_data.get("url") or ""
            result = {
                "code": 200 if url else 404,
                "data": {
                    "id": song_data.get("id", song_id),
                    "url": url,
                    "br": song_data.get("br", 0),
                    "size": song_data.get("size", 0),
                    "type": song_data.get("type"),
                    "level": song_data.get("level"),
                    "fee": song_data.get("fee"),
                    "payed": song_data.get("payed"),
                    "free_trial_info": free_trial_info,
                    "is_trial": free_trial_info is not None,
                },
            }

            if url:
                with self._playback_cache_lock:
                    # 顺带清理过期项，避免长时间运行后无限增长
                    if len(self._playback_cache) > 256:
                        self._playback_cache = {
                            key: value
                            for key, value in self._playback_cache.items()
                            if value[0] > now
                        }
                    self._playback_cache[cache_key] = (
                        now + self._playback_cache_ttl,
                        copy.deepcopy(result),
                    )

            return result
        except Exception as e:
            print(f"Error getting song URL: {e}")
            return {"code": 500, "data": {}}

    def get_song_detail(self, song_id: str) -> Dict[str, Any]:
        """根据歌曲ID获取歌曲详细信息"""
        try:
            data = self._request("GET", "/song/detail", params={"ids": song_id})

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
                    "cover": song_info.get("al", {}).get("picUrl", ""),
                },
            }
        except Exception as e:
            print(f"Error getting song detail: {e}")
            return {"code": 500, "data": {}}


music_api_service = MusicAPIService()
