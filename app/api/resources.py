from fastapi import APIRouter, Depends,File
from fastapi.responses import FileResponse
from app.core.security import get_openid
from app.db.repositories.resources import resourcesManager 
import os

router = APIRouter()
@router.post("/image",summary="上传图片",description="上传图片，返回图片的唯一标识符")  
async def create_file(file: bytes = File(),extension: str = "png",openid: str = Depends(get_openid)):
    uid = resourcesManager.register_picture(extension)
    file_path = resourcesManager.get_picture_path(uid, extension)
    with open(file_path, "wb") as f:
        f.write(file)
    return {"uid": uid}

@router.delete("/image",summary="删除图片",description="删除指定的图片文件")  
async def delete_file(uid:str,openid: str = Depends(get_openid)):
    extension = resourcesManager.get_extension(uid)
    file_path = resourcesManager.get_picture_path(uid, extension)
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"success": True}

@router.get("/image",summary="下载图片",description="下载指定的图片文件")  
async def download_file(uid:str):
    extension = resourcesManager.get_extension(uid)
    file_path = resourcesManager.get_picture_path(uid, extension)
    return FileResponse(path = file_path,filename=f"{uid}.{extension}")
    