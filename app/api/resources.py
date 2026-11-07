from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.security import get_openid
from app.db.repositories.resources import resourcesManager
import os

router = APIRouter()

# 图片文件头（magic bytes）白名单，用于服务端二次校验上传内容确为图片
IMAGE_MAGICS = [
    b"\x89PNG",                 # PNG
    b"\xff\xd8\xff",            # JPEG
    b"GIF87a",                  # GIF
    b"GIF89a",                  # GIF
    b"BM",                      # BMP
    b"RIFF",                    # WEBP (实际为 RIFF....WEBP)
]


def _is_image_bytes(data: bytes) -> bool:
    if not data:
        return False
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return any(data.startswith(magic) for magic in IMAGE_MAGICS)


@router.post("/image", summary="上传图片", description="上传图片，返回图片的唯一标识符")
async def create_file(file: UploadFile = File(...), extension: str = "png", openid: str = Depends(get_openid)):
    # 分块读取并在超过上限时立即拒绝，避免把超大文件整体读入内存造成 DoS
    # 使用 file.read() 循环以兼容各版本 Starlette（部分版本无 .stream()）
    data = b""
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        data += chunk
        if len(data) > settings.MAX_IMAGE_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="图片大小超过限制")
    if not _is_image_bytes(data):
        raise HTTPException(status_code=400, detail="仅支持上传图片文件")
    uid = resourcesManager.register_picture(extension)
    file_path = resourcesManager.get_picture_path(uid, extension)
    with open(file_path, "wb") as f:
        f.write(data)
    return {"uid": uid}


@router.delete("/image", summary="删除图片", description="删除指定的图片文件")
async def delete_file(uid: str, openid: str = Depends(get_openid)):
    extension = resourcesManager.get_extension(uid)
    file_path = resourcesManager.get_picture_path(uid, extension)
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"success": True}


@router.get("/image", summary="下载图片", description="下载指定的图片文件")
async def download_file(uid: str):
    extension = resourcesManager.get_extension(uid)
    file_path = resourcesManager.get_picture_path(uid, extension)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(
        path=file_path,
        filename=f"{uid}.{extension}",
        headers={"X-Content-Type-Options": "nosniff"},
    )
