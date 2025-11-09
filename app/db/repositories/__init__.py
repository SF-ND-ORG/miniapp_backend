from app.db.repositories.user import user_repository
from app.db.repositories.song_request import song_request_repository
from app.db.repositories.refresh_token import refresh_token_repository
from app.db.repositories.grade import grade_file_repository

# 导出所有仓库
__all__ = [
    "user_repository",
    "song_request_repository",
    "refresh_token_repository",
    "grade_file_repository"
]