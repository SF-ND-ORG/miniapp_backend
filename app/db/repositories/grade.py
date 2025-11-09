from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.grade import GradeFile
from app.db.repositories.base import BaseRepository
from app.schemas.grade import GradeFileCreate, GradeFileUpdate


class GradeFileRepository(BaseRepository[GradeFile, GradeFileCreate, GradeFileUpdate]):
    """成绩文件仓储"""

    def __init__(self) -> None:
        super().__init__(GradeFile)

    def get_by_uid(self, db: Session, uid: str) -> Optional[GradeFile]:
        return db.query(self.model).filter(self.model.uid == uid).first()

    def remove_by_uid(self, db: Session, uid: str) -> Optional[GradeFile]:
        obj = self.get_by_uid(db, uid)
        if obj is None:
            return None
        db.delete(obj)
        db.commit()
        return obj

    def list_files(self, db: Session, *, limit: int = 100) -> List[GradeFile]:
        return (
            db.query(self.model)
            .order_by(desc(self.model.created_at))
            .limit(limit)
            .all()
        )


grade_file_repository = GradeFileRepository()
