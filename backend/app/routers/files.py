from __future__ import annotations

"""
File management routes.

POST   /api/files/upload        — upload + analyse a log file
GET    /api/files               — list all files
GET    /api/files/{id}          — get a single file's metadata
DELETE /api/files/{id}          — delete file + its data
GET    /api/files/{id}/events   — paginated events for a file
GET    /api/files/{id}/anomalies— anomalies for a file
"""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.detector import AnomalyEngine
from app.models import Anomaly, LogEvent, LogFile
from app.parser import parse_log_file
from app.schemas import AnomalyRead, LogEventRead, LogFileRead

router = APIRouter(prefix="/api/files", tags=["files"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_file_or_404(file_id: int, db: Session) -> LogFile:
    f = db.get(LogFile, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return f


def _analyse(file_id: int, stored_path: Path) -> None:
    """Parse log file, store events + anomalies, update status."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        log_file = db.get(LogFile, file_id)
        if not log_file:
            return

        log_file.status = "processing"
        db.commit()

        try:
            df, fmt = parse_log_file(stored_path)
        except Exception as exc:
            log_file.status = "error"
            log_file.error_message = str(exc)
            db.commit()
            return

        log_file.file_format = fmt

        # Bulk-insert events
        BATCH = 1000
        events_data = df.to_dict(orient="records")
        for i in range(0, len(events_data), BATCH):
            batch = events_data[i : i + BATCH]
            db.bulk_insert_mappings(
                LogEvent,
                [
                    {
                        "file_id": file_id,
                        "timestamp": r.get("timestamp") if not str(r.get("timestamp")) == "NaT" else None,
                        "source_ip": r.get("source_ip"),
                        "dest_ip": r.get("dest_ip"),
                        "username": r.get("username"),
                        "event_type": r.get("event_type"),
                        "action": r.get("action"),
                        "status": r.get("status"),
                        "port": int(r["port"]) if r.get("port") is not None and str(r.get("port")) not in ("", "<NA>", "nan") else None,
                        "protocol": r.get("protocol"),
                        "bytes_sent": int(r["bytes_sent"]) if r.get("bytes_sent") is not None and str(r.get("bytes_sent")) not in ("", "<NA>", "nan") else None,
                        "bytes_received": int(r["bytes_received"]) if r.get("bytes_received") is not None and str(r.get("bytes_received")) not in ("", "<NA>", "nan") else None,
                        "raw_line": r.get("raw_line", ""),
                        "severity": "info",
                    }
                    for r in batch
                ],
            )
            db.commit()

        # Run detectors
        engine = AnomalyEngine()
        raw_anomalies = engine.run(df)

        for a in raw_anomalies:
            db.add(
                Anomaly(
                    file_id=file_id,
                    detection_time=a.get("detection_time"),
                    anomaly_type=a["anomaly_type"],
                    severity=a["severity"],
                    source_ip=a.get("source_ip"),
                    username=a.get("username"),
                    description=a["description"],
                    event_count=a.get("event_count"),
                    start_time=a.get("start_time"),
                    end_time=a.get("end_time"),
                    false_positive=False,
                    score=a.get("score"),
                )
            )

        db.commit()

        log_file.event_count = len(events_data)
        log_file.anomaly_count = len(raw_anomalies)
        log_file.status = "done"
        db.commit()

    except Exception as exc:
        db.rollback()
        log_file = db.get(LogFile, file_id)
        if log_file:
            log_file.status = "error"
            log_file.error_message = str(exc)
            db.commit()
    finally:
        db.close()


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=LogFileRead, status_code=201)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    ext = Path(file.filename or "log.log").suffix or ".log"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = settings.upload_dir / stored_name
    stored_path.write_bytes(content)

    log_file = LogFile(
        filename=stored_name,
        original_name=file.filename or stored_name,
        file_size=len(content),
        status="pending",
    )
    db.add(log_file)
    db.commit()
    db.refresh(log_file)

    background_tasks.add_task(_analyse, log_file.id, stored_path)
    return log_file


@router.get("", response_model=List[LogFileRead])
def list_files(db: Session = Depends(get_db)):
    return db.query(LogFile).order_by(LogFile.upload_time.desc()).all()


@router.get("/{file_id}", response_model=LogFileRead)
def get_file(file_id: int, db: Session = Depends(get_db)):
    return _get_file_or_404(file_id, db)


@router.delete("/{file_id}", status_code=204)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    f = _get_file_or_404(file_id, db)
    stored = settings.upload_dir / f.filename
    if stored.exists():
        stored.unlink()
    db.delete(f)
    db.commit()


@router.get("/{file_id}/events", response_model=List[LogEventRead])
def get_events(
    file_id: int,
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _get_file_or_404(file_id, db)
    q = db.query(LogEvent).filter(LogEvent.file_id == file_id)
    if status:
        q = q.filter(LogEvent.status == status)
    if event_type:
        q = q.filter(LogEvent.event_type == event_type)
    if source_ip:
        q = q.filter(LogEvent.source_ip.contains(source_ip))
    if username:
        q = q.filter(LogEvent.username.contains(username))
    return q.order_by(LogEvent.timestamp).offset(skip).limit(limit).all()


@router.get("/{file_id}/anomalies", response_model=List[AnomalyRead])
def get_file_anomalies(file_id: int, db: Session = Depends(get_db)):
    _get_file_or_404(file_id, db)
    return (
        db.query(Anomaly)
        .filter(Anomaly.file_id == file_id)
        .order_by(Anomaly.severity.desc(), Anomaly.detection_time.desc())
        .all()
    )
