from __future__ import annotations

"""
Dashboard statistics.

GET /api/stats — aggregated counts and chart data
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Anomaly, LogEvent, LogFile
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    total_files = db.query(func.count(LogFile.id)).scalar() or 0
    total_events = db.query(func.count(LogEvent.id)).scalar() or 0
    total_anomalies = db.query(func.count(Anomaly.id)).scalar() or 0
    high_sev = (
        db.query(func.count(Anomaly.id))
        .filter(Anomaly.severity.in_(["high", "critical"]))
        .scalar()
        or 0
    )

    # Anomalies by type
    type_counts = db.query(Anomaly.anomaly_type, func.count(Anomaly.id)).group_by(Anomaly.anomaly_type).all()
    anomalies_by_type = {t: c for t, c in type_counts}

    # Anomalies by severity
    sev_counts = db.query(Anomaly.severity, func.count(Anomaly.id)).group_by(Anomaly.severity).all()
    anomalies_by_severity = {s: c for s, c in sev_counts}

    # Events by hour (0-23)
    hour_counts: Counter = Counter()
    for (ts,) in db.query(LogEvent.timestamp).filter(LogEvent.timestamp.isnot(None)).all():
        hour_counts[ts.hour] += 1
    events_by_hour = [{"hour": h, "count": hour_counts.get(h, 0)} for h in range(24)]

    # Events over time (last 30 days, grouped by day)
    from collections import defaultdict
    day_counts: dict = defaultdict(int)
    for (ts,) in db.query(LogEvent.timestamp).filter(LogEvent.timestamp.isnot(None)).all():
        day_counts[ts.strftime("%Y-%m-%d")] += 1
    events_over_time = sorted(
        [{"date": d, "count": c} for d, c in day_counts.items()],
        key=lambda x: x["date"],
    )[-30:]

    # Top source IPs by event count
    ip_counts = (
        db.query(LogEvent.source_ip, func.count(LogEvent.id))
        .filter(LogEvent.source_ip.isnot(None))
        .group_by(LogEvent.source_ip)
        .order_by(func.count(LogEvent.id).desc())
        .limit(10)
        .all()
    )
    top_source_ips = [{"ip": ip, "count": c} for ip, c in ip_counts]

    return DashboardStats(
        total_files=total_files,
        total_events=total_events,
        total_anomalies=total_anomalies,
        high_severity_anomalies=high_sev,
        anomalies_by_type=anomalies_by_type,
        anomalies_by_severity=anomalies_by_severity,
        events_by_hour=events_by_hour,
        events_over_time=events_over_time,
        top_source_ips=top_source_ips,
    )
