from sqlalchemy import BigInteger, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.models.base import BaseModel


class GradeFile(BaseModel):
    """存储成绩文件的元数据"""
    __tablename__ = "grade_files"

    uid = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    file_name = Column(String, nullable=False)  # 原始文件名
    stored_name = Column(String, nullable=False)  # 存储在服务器上的文件名
    file_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    uploader = relationship("User", foreign_keys=[uploaded_by])