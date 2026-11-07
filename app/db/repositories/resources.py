import os
import re
import time
import base64
from ulid import ULID
from app.core.config import settings

# 允许存储的图片扩展名白名单
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}


def encrypt_str(data: str) -> str:
    # 使用 URL-safe base64：标准 base64 中的 '+' 与 '/' 会导致
    # 1) 文件路径出现嵌套目录（open 失败）
    # 2) 放入 URL 查询串时 '+' 被解析为空格、'/' 破坏结构
    # urlsafe 变体仅使用 '-' 与 '_'，对路径与 URL 均安全
    return base64.urlsafe_b64encode(data.encode("utf-8")).decode()


def decrypt_str(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode()
    except Exception:
        # 兼容极少数可能残留的旧版标准 base64 uid
        return base64.b64decode(data.encode("utf-8")).decode()


def sanitize_extension(extension: str) -> str:
    """清洗扩展名，仅保留白名单内的小写字母数字，防止路径穿越与非法文件名。"""
    ext = str(extension).lower().strip()
    ext = re.sub(r"[^a-z0-9]", "", ext)
    return ext if ext in ALLOWED_EXTENSIONS else "png"


class ResourcesManager():
    def __init__(self):
        self.upload_dir = settings.PICTURE_UPLOAD_DIR
        # 上传目录必须在实例创建时确保存在，否则首次写入会因父目录缺失而 500
        os.makedirs(self.upload_dir, exist_ok=True)

    def register_picture(self, extension: str):
        timestamp_ulid = ULID.from_timestamp(time.time())
        return encrypt_str(str(timestamp_ulid) + f".{sanitize_extension(extension)}")

    def get_extension(self, uid: str):
        decrypted_str = decrypt_str(uid)
        return decrypted_str.split(".")[-1]

    def get_picture_path(self, uid: str, extension: str):
        file_name = f"{uid}.{sanitize_extension(extension)}"
        return os.path.join(self.upload_dir, file_name)

    def delete_picture(self, uid: str) -> bool:
        """删除指定 uid 的图片文件；文件不存在或解析失败时忽略。返回是否实际删除。"""
        if not uid:
            return False
        try:
            extension = self.get_extension(uid)
        except Exception:
            return False
        file_path = self.get_picture_path(uid, extension)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError:
                return False
        return False


resourcesManager = ResourcesManager()
