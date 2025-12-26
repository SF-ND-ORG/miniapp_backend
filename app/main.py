from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import wechat, songs, player, wall, comment, resources, grade, admin
from app.core.config import settings
from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware, SQLInjectionMiddleware

# 创建FastAPI应用实例
app = FastAPI(title="校园点歌系统API",
    description="实现了微信小程序端的登录、绑定、搜索、点歌、管理员审核、歌曲播放等全流程",
    version="1.0.0")

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SQLInjectionMiddleware)


# 注册路由
app.include_router(wechat.router, prefix=f"{settings.API_V1_STR}/wechat", tags=["微信小程序"])
app.include_router(songs.router, prefix=settings.API_V1_STR, tags=["歌曲搜索"])
app.include_router(player.router, prefix=f"{settings.API_V1_STR}/player", tags=["播放器"])
app.include_router(wall.router, prefix=f"{settings.API_V1_STR}/wall", tags=["校园墙"])
app.include_router(comment.router, prefix=f"{settings.API_V1_STR}/comment", tags=["评论"])
app.include_router(resources.router, prefix=f"{settings.API_V1_STR}/resources", tags=["资源管理"])
app.include_router(grade.router, prefix=settings.API_V1_STR, tags=["成绩管理"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["管理面板"])

@app.get("/",description="API根路径", summary="API根路径",
         responses={
                200: {
                    "description": "欢迎信息",
                    "content": {
                        "application/json": {
                            "example": {"message": "Welcome to Song Request System API"}
                        }
                    }
                }
         })
def read_root():
    return {"message": "Welcome to Song Request System API"}


admin_static_dir = Path(__file__).resolve().parent / "static_admin"
if admin_static_dir.exists():
    app.mount("/admin", StaticFiles(directory=str(admin_static_dir), html=True), name="admin")
