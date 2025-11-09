from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ulid import ULID

from app.core.config import settings
from app.core.security import get_openid, require_admin
from app.db.repositories.grade import grade_file_repository
from app.db.session import get_db
from app.schemas.grade import GradeFileCreate, GradeFileListResponse, GradeFileResponse

router = APIRouter()


@router.post(
	"/grade",
	summary="上传成绩excel文件",
	description="上传成绩excel文件，返回唯一标识符",
	response_model=GradeFileResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_file(
	title: str = Form(..., description="成绩文件标题"),
	file: UploadFile = File(..., description="Excel文件"),
	admin_user=Depends(require_admin),
	db: Session = Depends(get_db),
):
	upload_dir = Path(settings.EXCEL_UPLOAD_DIR)
	upload_dir.mkdir(parents=True, exist_ok=True)

	original_name = file.filename or "grade.xlsx"
	extension = Path(original_name).suffix or ".xlsx"
	if extension.lower() not in {".xls", ".xlsx"}:
		raise HTTPException(status_code=400, detail="仅支持Excel文件")
	uid = str(ULID())
	stored_name = f"{uid}{extension}"
	file_path = upload_dir / stored_name

	file_bytes = await file.read()
	if not file_bytes:
		raise HTTPException(status_code=400, detail="文件内容为空")

	with open(file_path, "wb") as destination:
		destination.write(file_bytes)

	try:
		grade_file = grade_file_repository.create(
			db,
			obj_in=GradeFileCreate(
				uid=uid,
				title=title,
				file_name=original_name,
				stored_name=stored_name,
				file_path=str(file_path),
				content_type=file.content_type,
				file_size=len(file_bytes),
				uploaded_by=getattr(admin_user, "id", None),
			),
		)
	except Exception:
		if file_path.exists():
			file_path.unlink()
		raise
	return grade_file


@router.get(
	"/grade/list",
	summary="获取成绩excel文件列表",
	description="获取已上传的成绩excel文件列表",
	response_model=GradeFileListResponse,
)
async def list_files(
	openid: str = Depends(get_openid),
	db: Session = Depends(get_db),
):
	files = grade_file_repository.list_files(db)
	return GradeFileListResponse(
		items=[GradeFileResponse.model_validate(f) for f in files],
		total=len(files),
	)


@router.get(
	"/grade/{uid}",
	summary="下载成绩excel文件",
	description="下载指定的成绩excel文件",
)
async def download_file(
	uid: str,
	openid: str = Depends(get_openid),
	db: Session = Depends(get_db),
):
	grade_file = grade_file_repository.get_by_uid(db, uid)
	if grade_file is None:
		raise HTTPException(status_code=404, detail="文件不存在")

	file_path = Path(str(grade_file.file_path))
	if not file_path.exists():
		raise HTTPException(status_code=404, detail="文件已被删除")

	media_type = (
		str(grade_file.content_type)
		if grade_file.content_type is not None
		else "application/octet-stream"
	)

	return FileResponse(
		path=file_path,
		filename=str(grade_file.file_name),
		media_type=media_type,
	)


@router.delete(
	"/grade/{uid}",
	summary="删除成绩excel文件",
	description="删除指定的成绩excel文件",
	status_code=status.HTTP_200_OK,
)
async def delete_file(
	uid: str,
	admin_user=Depends(require_admin),
	db: Session = Depends(get_db),
):
	grade_file = grade_file_repository.get_by_uid(db, uid)
	if grade_file is None:
		raise HTTPException(status_code=404, detail="文件不存在")

	file_path = Path(str(grade_file.file_path))
	if file_path.exists():
		try:
			file_path.unlink()
		except OSError:
			raise HTTPException(status_code=500, detail="删除文件失败")

	grade_file_repository.remove_by_uid(db, uid)
	return {"success": True}
    