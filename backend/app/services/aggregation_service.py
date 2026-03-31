"""
집계 서비스

시간별/일별 통계를 생성하고 데이터 보존 정책을 적용합니다.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, and_, case, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.database_models import (
    RequestLog, ErrorLog, ErrorGroup, HourlyStats, DailyReport, LogEntry,
)

logger = logging.getLogger(__name__)


def aggregate_hourly_stats(db: Session) -> int:
    """최근 2시간의 시간별 통계를 생성/갱신"""
    now = datetime.now(timezone.utc)
    two_hours_ago = now - timedelta(hours=2)

    # 서비스 그룹 목록 조회
    services = db.query(RequestLog.service_group).filter(
        RequestLog.timestamp >= two_hours_ago
    ).distinct().all()

    count = 0
    for (service_group,) in services:
        for hour_offset in range(2):
            hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hour_offset)
            hour_end = hour_start + timedelta(hours=1)

            # Request 집계
            req_stats = db.query(
                func.count(RequestLog.id).label("total"),
                func.sum(case((RequestLog.status_code.between(200, 299), 1), else_=0)).label("s2xx"),
                func.sum(case((RequestLog.status_code.between(300, 399), 1), else_=0)).label("s3xx"),
                func.sum(case((RequestLog.status_code.between(400, 499), 1), else_=0)).label("s4xx"),
                func.sum(case((RequestLog.status_code.between(500, 599), 1), else_=0)).label("s5xx"),
                func.avg(RequestLog.response_time_ms).label("avg_rt"),
                func.max(RequestLog.response_time_ms).label("max_rt"),
            ).filter(
                and_(
                    RequestLog.service_group == service_group,
                    RequestLog.timestamp >= hour_start,
                    RequestLog.timestamp < hour_end,
                )
            ).first()

            # P95 response time (근사치)
            p95_rt = None
            if req_stats.total and req_stats.total > 0:
                p95_row = db.query(RequestLog.response_time_ms).filter(
                    and_(
                        RequestLog.service_group == service_group,
                        RequestLog.timestamp >= hour_start,
                        RequestLog.timestamp < hour_end,
                        RequestLog.response_time_ms.isnot(None),
                    )
                ).order_by(
                    RequestLog.response_time_ms.desc()
                ).offset(
                    max(0, int(req_stats.total * 0.05))
                ).first()
                if p95_row:
                    p95_rt = p95_row[0]

            # Error 집계
            err_stats = db.query(
                func.count(ErrorLog.id).label("total"),
                func.count(func.distinct(ErrorLog.fingerprint)).label("unique"),
            ).filter(
                and_(
                    ErrorLog.service_group == service_group,
                    ErrorLog.timestamp >= hour_start,
                    ErrorLog.timestamp < hour_end,
                )
            ).first()

            # Upsert
            existing = db.query(HourlyStats).filter(
                and_(
                    HourlyStats.service_group == service_group,
                    HourlyStats.hour == hour_start,
                )
            ).first()

            if existing:
                existing.total_requests = req_stats.total or 0
                existing.status_2xx = req_stats.s2xx or 0
                existing.status_3xx = req_stats.s3xx or 0
                existing.status_4xx = req_stats.s4xx or 0
                existing.status_5xx = req_stats.s5xx or 0
                existing.avg_response_time_ms = req_stats.avg_rt
                existing.max_response_time_ms = req_stats.max_rt
                existing.p95_response_time_ms = p95_rt
                existing.error_count = err_stats.total or 0
                existing.unique_errors = err_stats.unique or 0
            else:
                hourly = HourlyStats(
                    service_group=service_group,
                    hour=hour_start,
                    total_requests=req_stats.total or 0,
                    status_2xx=req_stats.s2xx or 0,
                    status_3xx=req_stats.s3xx or 0,
                    status_4xx=req_stats.s4xx or 0,
                    status_5xx=req_stats.s5xx or 0,
                    avg_response_time_ms=req_stats.avg_rt,
                    max_response_time_ms=req_stats.max_rt,
                    p95_response_time_ms=p95_rt,
                    error_count=err_stats.total or 0,
                    unique_errors=err_stats.unique or 0,
                )
                db.add(hourly)
            count += 1

    db.commit()
    logger.info("Aggregated hourly stats: %d entries", count)
    return count


def generate_daily_report(db: Session, report_date: datetime | None = None) -> DailyReport:
    """일일 리포트 생성"""
    if report_date is None:
        report_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)

    day_start = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    # 전체 요청 수
    total_requests = db.query(func.count(RequestLog.id)).filter(
        and_(RequestLog.timestamp >= day_start, RequestLog.timestamp < day_end)
    ).scalar() or 0

    # 전체 오류 수
    total_errors = db.query(func.count(ErrorLog.id)).filter(
        and_(ErrorLog.timestamp >= day_start, ErrorLog.timestamp < day_end)
    ).scalar() or 0

    # 신규 오류 그룹
    new_groups = db.query(func.count(ErrorGroup.id)).filter(
        and_(ErrorGroup.first_seen >= day_start, ErrorGroup.first_seen < day_end)
    ).scalar() or 0

    # 해결된 오류 그룹
    resolved_groups = db.query(func.count(ErrorGroup.id)).filter(
        and_(
            ErrorGroup.status == "resolved",
            ErrorGroup.last_seen >= day_start,
            ErrorGroup.last_seen < day_end,
        )
    ).scalar() or 0

    # Top 오류
    top_errors = db.query(
        ErrorGroup.service_group,
        ErrorGroup.error_type,
        ErrorGroup.severity,
        ErrorGroup.sample_message,
        ErrorGroup.occurrence_count,
    ).filter(
        ErrorGroup.last_seen >= day_start,
        ErrorGroup.status == "open",
    ).order_by(
        ErrorGroup.occurrence_count.desc()
    ).limit(10).all()

    top_errors_json = json.dumps([
        {
            "service": e.service_group,
            "type": e.error_type,
            "severity": e.severity,
            "message": e.sample_message[:200],
            "count": e.occurrence_count,
        }
        for e in top_errors
    ])

    # 느린 엔드포인트 Top 10
    slow_endpoints = db.query(
        RequestLog.service_group,
        RequestLog.method,
        RequestLog.path,
        func.avg(RequestLog.response_time_ms).label("avg_rt"),
        func.max(RequestLog.response_time_ms).label("max_rt"),
        func.count(RequestLog.id).label("count"),
    ).filter(
        and_(
            RequestLog.timestamp >= day_start,
            RequestLog.timestamp < day_end,
            RequestLog.response_time_ms.isnot(None),
        )
    ).group_by(
        RequestLog.service_group, RequestLog.method, RequestLog.path,
    ).order_by(
        text("avg_rt DESC")
    ).limit(10).all()

    top_slow_json = json.dumps([
        {
            "service": e.service_group,
            "method": e.method,
            "path": e.path,
            "avg_ms": round(e.avg_rt, 1),
            "max_ms": round(e.max_rt, 1) if e.max_rt else None,
            "count": e.count,
        }
        for e in slow_endpoints
    ])

    report = DailyReport(
        report_date=day_start,
        total_requests=total_requests,
        total_errors=total_errors,
        new_error_groups=new_groups,
        resolved_error_groups=resolved_groups,
        top_errors_json=top_errors_json,
        top_slow_endpoints_json=top_slow_json,
    )
    db.add(report)
    db.commit()

    logger.info(
        "Daily report for %s: %d requests, %d errors, %d new groups",
        day_start.date(), total_requests, total_errors, new_groups,
    )
    return report


def cleanup_old_data(db: Session) -> dict:
    """보존 기간이 지난 데이터 삭제"""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    raw_cutoff = now - timedelta(days=settings.LOG_RETENTION_DAYS)
    agg_cutoff = now - timedelta(days=settings.AGGREGATE_RETENTION_DAYS)

    raw_deleted = db.query(LogEntry).filter(
        LogEntry.timestamp < raw_cutoff
    ).delete()

    req_deleted = db.query(RequestLog).filter(
        RequestLog.timestamp < raw_cutoff
    ).delete()

    err_deleted = db.query(ErrorLog).filter(
        ErrorLog.timestamp < raw_cutoff
    ).delete()

    hourly_deleted = db.query(HourlyStats).filter(
        HourlyStats.hour < agg_cutoff
    ).delete()

    db.commit()

    result = {
        "raw_logs": raw_deleted,
        "request_logs": req_deleted,
        "error_logs": err_deleted,
        "hourly_stats": hourly_deleted,
    }
    logger.info("Cleanup: %s", result)
    return result
