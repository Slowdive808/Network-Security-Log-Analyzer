from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── LogFile ──────────────────────────────────────────────────────────────────

class LogFileBase(BaseModel):
    original_name: str
    file_format: Optional[str] = None


class LogFileCreate(LogFileBase):
    filename: str
    file_size: int


class LogFileRead(LogFileBase):
    id: int
    filename: str
    file_size: int
    upload_time: datetime
    status: str
    error_message: Optional[str] = None
    event_count: int
    anomaly_count: int

    model_config = {"from_attributes": True}


# ── LogEvent ─────────────────────────────────────────────────────────────────

class LogEventRead(BaseModel):
    id: int
    file_id: int
    timestamp: Optional[datetime]
    source_ip: Optional[str]
    dest_ip: Optional[str]
    username: Optional[str]
    event_type: Optional[str]
    action: Optional[str]
    status: Optional[str]
    port: Optional[int]
    protocol: Optional[str]
    bytes_sent: Optional[int]
    bytes_received: Optional[int]
    severity: str

    model_config = {"from_attributes": True}


# ── Anomaly ───────────────────────────────────────────────────────────────────

class AnomalyRead(BaseModel):
    id: int
    file_id: int
    detection_time: datetime
    anomaly_type: str
    severity: str
    source_ip: Optional[str]
    username: Optional[str]
    description: str
    event_count: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    false_positive: bool
    notes: Optional[str]
    score: Optional[float]

    model_config = {"from_attributes": True}


class AnomalyUpdate(BaseModel):
    false_positive: Optional[bool] = None
    notes: Optional[str] = None


# ── Report ────────────────────────────────────────────────────────────────────

class ReportRead(BaseModel):
    id: int
    file_id: int
    created_at: datetime
    report_type: str
    format: str

    model_config = {"from_attributes": True}


# ── Stats ─────────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_files: int
    total_events: int
    total_anomalies: int
    high_severity_anomalies: int
    anomalies_by_type: Dict[str, int]
    anomalies_by_severity: Dict[str, int]
    events_by_hour: List[Dict[str, Any]]    # [{hour: 0, count: 42}, ...]
    events_over_time: List[Dict[str, Any]]  # [{date: "2024-01-01", count: 120}, ...]
    top_source_ips: List[Dict[str, Any]]    # [{ip: "...", count: N}, ...]
