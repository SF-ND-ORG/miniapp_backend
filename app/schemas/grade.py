from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.base import BaseSchema


class GradeFileCreate(BaseModel):
    uid: str
    title: str
    file_name: str
    stored_name: str
    file_path: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: Optional[int] = None


class GradeFileUpdate(BaseModel):
    title: Optional[str] = None


class GradeFileResponse(BaseSchema):
    id: int
    uid: str
    title: str
    file_name: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime


class GradeFileListResponse(BaseSchema):
    items: List[GradeFileResponse]
    total: int
