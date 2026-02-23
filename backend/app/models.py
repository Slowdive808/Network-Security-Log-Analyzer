from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float
)
from sqlalchemy.orm import relationship
from app.database import Base


class LogFile(Base):
    __tablename__ = "log_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)          # stored filename (uuid)
    original_name = Column(String, nullable=False)    # user-uploaded filename
    file_format = Column(String)                       # csv | json | syslog | auto
    file_size = Column(Integer)                        # bytes
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")         # pending|processing|done|error
    error_message = Column(Text)
    event_count = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)

    events = relationship("LogEvent", back_populates="log_file", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="log_file", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="log_file", cascade="all, delete-orphan")


class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("log_files.id"), nullable=False)
    timestamp = Column(DateTime, index=True)
    source_ip = Column(String, index=True)
    dest_ip = Column(String)
    username = Column(String, index=True)
    event_type = Column(String)   # auth | network | system
    action = Column(String)       # login | logout | connect | disconnect | scan
    status = Column(String)       # success | failed | error
    port = Column(Integer)
    protocol = Column(String)
    bytes_sent = Column(Integer)
    bytes_received = Column(Integer)
    raw_line = Column(Text)
    severity = Column(String, default="info")  # info | low | medium | high | critical

    log_file = relationship("LogFile", back_populates="events")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("log_files.id"), nullable=False)
    detection_time = Column(DateTime, default=datetime.utcnow)
    anomaly_type = Column(String, index=True)  # brute_force|port_scan|traffic_spike|off_hours
    severity = Column(String, index=True)       # low | medium | high | critical
    source_ip = Column(String, index=True)
    username = Column(String)
    description = Column(Text)
    event_count = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    false_positive = Column(Boolean, default=False)
    notes = Column(Text)
    score = Column(Float)  # confidence / risk score 0–100

    log_file = relationship("LogFile", back_populates="anomalies")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("log_files.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    report_type = Column(String, default="summary")  # summary | detailed
    file_path = Column(String)
    format = Column(String, default="pdf")  # pdf | png

    log_file = relationship("LogFile", back_populates="reports")
