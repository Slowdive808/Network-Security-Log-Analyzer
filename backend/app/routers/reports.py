from __future__ import annotations

"""
Report routes.

POST   /api/reports/{file_id}          — generate a report
GET    /api/reports/{file_id}          — list reports for a file
GET    /api/reports/{file_id}/{rep_id}/download — download report
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import LogFile, Report
from app.reporter import generate_report
from app.schemas import ReportRead

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_file_or_404(file_id: int, db: Session) -> LogFile:
    f = db.get(LogFile, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if f.status != "done":
        raise HTTPException(status_code=409, detail="File analysis not yet complete")
    return f


@router.post("/{file_id}", response_model=ReportRead, status_code=201)
def create_report(
    file_id: int,
    report_type: str = "summary",
    fmt: str = "pdf",
    db: Session = Depends(get_db),
):
    f = _get_file_or_404(file_id, db)
    out_path = generate_report(f, db, report_type=report_type, fmt=fmt)
    rep = Report(
        file_id=file_id,
        report_type=report_type,
        format=fmt,
        file_path=str(out_path),
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


@router.get("/{file_id}", response_model=List[ReportRead])
def list_reports(file_id: int, db: Session = Depends(get_db)):
    if not db.get(LogFile, file_id):
        raise HTTPException(status_code=404, detail="File not found")
    return db.query(Report).filter(Report.file_id == file_id).order_by(Report.created_at.desc()).all()


@router.get("/{file_id}/{report_id}/download")
def download_report(file_id: int, report_id: int, db: Session = Depends(get_db)):
    rep = db.get(Report, report_id)
    if not rep or rep.file_id != file_id:
        raise HTTPException(status_code=404, detail="Report not found")
    path = settings.reports_dir / rep.file_path if not rep.file_path.startswith("/") else rep.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing on disk")
    media = "application/pdf" if rep.format == "pdf" else "image/png"
    return FileResponse(path, media_type=media, filename=path.name)
