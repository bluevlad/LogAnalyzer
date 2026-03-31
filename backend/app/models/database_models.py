from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean,
    Index, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class LogEntry(Base):
    """원본 로그 라인 (파싱 전 raw)"""
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_name = Column(String(128), nullable=False, index=True)
    service_group = Column(String(64), nullable=False, index=True)
    stream = Column(String(10), nullable=False)  # stdout / stderr
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    raw_line = Column(Text, nullable=False)
    log_level = Column(String(16))  # DEBUG, INFO, WARN, ERROR, FATAL
    parsed = Column(Boolean, default=False)
    collected_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_log_entries_container_ts", "container_name", "timestamp"),
        Index("ix_log_entries_level_ts", "log_level", "timestamp"),
    )


class RequestLog(Base):
    """HTTP 요청 파싱 결과"""
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_name = Column(String(128), nullable=False, index=True)
    service_group = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float)  # nullable - not all logs include this
    client_ip = Column(String(45))
    user_agent = Column(String(512))
    source_type = Column(String(32), nullable=False)  # nginx, uvicorn, spring

    __table_args__ = (
        Index("ix_request_logs_service_ts", "service_group", "timestamp"),
        Index("ix_request_logs_status_ts", "status_code", "timestamp"),
        Index("ix_request_logs_path", "path"),
    )


class ErrorLog(Base):
    """오류 로그 파싱 결과"""
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_name = Column(String(128), nullable=False, index=True)
    service_group = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    error_type = Column(String(64), nullable=False)  # 500_error, exception, db_error, etc.
    severity = Column(String(16), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    fingerprint = Column(String(64), nullable=False, index=True)  # 중복 그룹핑용 해시
    group_id = Column(Integer, ForeignKey("error_groups.id"), nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))

    group = relationship("ErrorGroup", back_populates="errors")

    __table_args__ = (
        Index("ix_error_logs_service_ts", "service_group", "timestamp"),
        Index("ix_error_logs_type_severity", "error_type", "severity"),
    )


class ErrorGroup(Base):
    """동일 오류 그룹 (fingerprint 기반)"""
    __tablename__ = "error_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fingerprint = Column(String(64), unique=True, nullable=False)
    container_name = Column(String(128), nullable=False)
    service_group = Column(String(64), nullable=False)
    error_type = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)
    sample_message = Column(Text, nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    occurrence_count = Column(Integer, default=1)
    status = Column(String(16), default="open")  # open, acknowledged, resolved, ignored
    github_issue_number = Column(Integer)
    github_issue_url = Column(String(256))

    errors = relationship("ErrorLog", back_populates="group")

    __table_args__ = (
        Index("ix_error_groups_status", "status"),
        Index("ix_error_groups_service", "service_group"),
    )


class HourlyStats(Base):
    """시간별 집계"""
    __tablename__ = "hourly_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_group = Column(String(64), nullable=False)
    hour = Column(DateTime(timezone=True), nullable=False)
    total_requests = Column(Integer, default=0)
    status_2xx = Column(Integer, default=0)
    status_3xx = Column(Integer, default=0)
    status_4xx = Column(Integer, default=0)
    status_5xx = Column(Integer, default=0)
    avg_response_time_ms = Column(Float)
    max_response_time_ms = Column(Float)
    p95_response_time_ms = Column(Float)
    error_count = Column(Integer, default=0)
    unique_errors = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_hourly_stats_service_hour", "service_group", "hour", unique=True),
    )


class DailyReport(Base):
    """일일 리포트"""
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(DateTime(timezone=True), nullable=False, unique=True)
    total_requests = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    new_error_groups = Column(Integer, default=0)
    resolved_error_groups = Column(Integer, default=0)
    top_errors_json = Column(Text)  # JSON array of top error summaries
    top_slow_endpoints_json = Column(Text)  # JSON array of slowest endpoints
    dispatched_to_standup = Column(Boolean, default=False)
    dispatched_to_qa = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
