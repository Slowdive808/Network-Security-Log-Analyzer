from __future__ import annotations

"""
Anomaly routes.

GET    /api/anomalies          — list all anomalies (with filters)
GET    /api/anomalies/{id}     — get single anomaly
PATCH  /api/anomalies/{id}     — update (mark false-positive / add notes)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Anomaly
from app.schemas import AnomalyRead, AnomalyUpdate

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("", response_model=List[AnomalyRead])
def list_anomalies(
    severity: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    false_positive: Optional[bool] = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    q = db.query(Anomaly)
    if severity:
        q = q.filter(Anomaly.severity == severity)
    if anomaly_type:
        q = q.filter(Anomaly.anomaly_type == anomaly_type)
    if source_ip:
        q = q.filter(Anomaly.source_ip.contains(source_ip))
    if false_positive is not None:
        q = q.filter(Anomaly.false_positive == false_positive)
    return (
        q.order_by(Anomaly.detection_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{anomaly_id}", response_model=AnomalyRead)
def get_anomaly(anomaly_id: int, db: Session = Depends(get_db)):
    a = db.get(Anomaly, anomaly_id)
    if not a:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return a


@router.patch("/{anomaly_id}", response_model=AnomalyRead)
def update_anomaly(
    anomaly_id: int, payload: AnomalyUpdate, db: Session = Depends(get_db)
):
    a = db.get(Anomaly, anomaly_id)
    if not a:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    if payload.false_positive is not None:
        a.false_positive = payload.false_positive
    if payload.notes is not None:
        a.notes = payload.notes
    db.commit()
    db.refresh(a)
    return a
