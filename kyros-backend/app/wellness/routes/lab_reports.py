import base64
import json
import re
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import Response as FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.exceptions import (
    AppValidationError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedMediaTypeError,
)
from app.core.rate_limit import limiter
from app.core.storage import get_storage
from app.database import get_db
from app.shared.models.user import User
from app.wellness.models.lab_report import LabReport
from app.wellness.schemas.lab_report import LabReportCreate, LabReportRead, LabReportUpdate

router = APIRouter(prefix="/v1/wellness/lab-reports", tags=["Wellness"])

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_MIMES = {"image/jpeg", "image/png", "application/pdf"}
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _secure_filename(filename: str | None) -> str:
    if not filename:
        return "upload"
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "upload"


def _encode_cursor(created_at: datetime, report_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{report_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, id_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), uuid.UUID(id_str)


async def _get_report_or_404(
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> LabReport:
    result = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id,
            LabReport.user_id == user_id,
            LabReport.status != "deleted",
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Lab report not found.")
    return report


async def _to_response(report: LabReport) -> LabReportRead:
    data = LabReportRead.model_validate(report)
    if report.file_url:
        data.signed_url = await get_storage().signed_url(report.file_url)
    return data


@router.post("/", response_model=LabReportRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_lab_report(
    request: Request,
    file: UploadFile = File(...),
    metadata: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabReportRead:
    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise FileTooLargeError("File exceeds the 10 MB limit.")

    mime = file.content_type or "application/octet-stream"
    if mime not in _ALLOWED_MIMES:
        raise UnsupportedMediaTypeError(
            f"Unsupported file type '{mime}'. Accepted: {', '.join(sorted(_ALLOWED_MIMES))}."
        )

    try:
        meta = LabReportCreate.model_validate(json.loads(metadata))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AppValidationError("Invalid metadata JSON.") from exc

    safe_name = _secure_filename(file.filename)
    key = f"user-{current_user.id}/labs/{uuid.uuid4()}-{safe_name}"
    await get_storage().save(content, key, mime)

    parsed_json = [p.model_dump() for p in meta.parsed]
    report = LabReport(
        user_id=current_user.id,
        report_date=meta.report_date,
        lab_name=meta.lab_name,
        file_url=key,
        file_mime=mime,
        parsed=parsed_json,
        note=meta.note,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return await _to_response(report)


@router.get("/", response_model=list[LabReportRead])
async def list_lab_reports(
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = _DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LabReportRead]:
    stmt = (
        select(LabReport)
        .where(LabReport.user_id == current_user.id, LabReport.status != "deleted")
        .order_by(LabReport.created_at.desc(), LabReport.id.desc())
        .limit(limit)
    )

    if cursor is not None:
        cursor_time, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (LabReport.created_at < cursor_time)
            | (
                (LabReport.created_at == cursor_time)
                & (LabReport.id < cursor_id)
            )
        )

    result = await db.execute(stmt)
    reports = list(result.scalars().all())
    return [await _to_response(r) for r in reports]


@router.get("/{report_id}", response_model=LabReportRead)
async def get_lab_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabReportRead:
    report = await _get_report_or_404(report_id, current_user.id, db)
    return await _to_response(report)


@router.get("/{report_id}/file")
async def download_lab_file(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    report = await _get_report_or_404(report_id, current_user.id, db)
    if not report.file_url:
        raise NotFoundError("No file attached to this report.")
    content = await get_storage().read(report.file_url)
    filename = report.file_url.rsplit("/", 1)[-1]
    return FileResponse(
        content=content,
        media_type=report.file_mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{report_id}", response_model=LabReportRead)
async def update_lab_report(
    report_id: uuid.UUID,
    body: LabReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabReportRead:
    report = await _get_report_or_404(report_id, current_user.id, db)
    if body.report_date is not None:
        report.report_date = body.report_date
    if body.lab_name is not None:
        report.lab_name = body.lab_name
    if body.parsed is not None:
        report.parsed = [p.model_dump() for p in body.parsed]
    if body.note is not None:
        report.note = body.note
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return await _to_response(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_lab_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete: status → 'deleted'. File is kept; a cleanup job sweeps later."""
    report = await _get_report_or_404(report_id, current_user.id, db)
    report.status = "deleted"
    db.add(report)
    await db.flush()
