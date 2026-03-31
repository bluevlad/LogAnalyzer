"""
Request 분석 API

HTTP 요청 로그 조회, 서비스별 요약, 엔드포인트 통계, 시간별 추이
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import RequestLog, HourlyStats
from app.models.schemas import (
    RequestStats, EndpointStats, ServiceRequestSummary,
    HourlyStatsResponse, PaginatedResponse,
)

router = APIRouter()


@router.get("/requests/summary")
def get_request_summary(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
) -> RequestStats:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = db.query(
        func.count(RequestLog.id).label("total"),
        func.sum(case((RequestLog.status_code.between(200, 299), 1), else_=0)).label("s2xx"),
        func.sum(case((RequestLog.status_code.between(300, 399), 1), else_=0)).label("s3xx"),
        func.sum(case((RequestLog.status_code.between(400, 499), 1), else_=0)).label("s4xx"),
        func.sum(case((RequestLog.status_code.between(500, 599), 1), else_=0)).label("s5xx"),
        func.avg(RequestLog.response_time_ms).label("avg_rt"),
    ).filter(RequestLog.timestamp >= since)

    if service:
        q = q.filter(RequestLog.service_group == service)

    r = q.first()
    total = r.total or 0
    s5xx = r.s5xx or 0

    return RequestStats(
        total_requests=total,
        status_2xx=r.s2xx or 0,
        status_3xx=r.s3xx or 0,
        status_4xx=r.s4xx or 0,
        status_5xx=s5xx,
        avg_response_time_ms=round(r.avg_rt, 2) if r.avg_rt else None,
        error_rate=round(s5xx / total * 100, 2) if total > 0 else 0.0,
    )


@router.get("/requests/by-service")
def get_requests_by_service(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
) -> list[ServiceRequestSummary]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    rows = db.query(
        RequestLog.service_group,
        func.count(RequestLog.id).label("total"),
        func.sum(case((RequestLog.status_code.between(200, 299), 1), else_=0)).label("s2xx"),
        func.sum(case((RequestLog.status_code.between(400, 499), 1), else_=0)).label("s4xx"),
        func.sum(case((RequestLog.status_code.between(500, 599), 1), else_=0)).label("s5xx"),
        func.avg(RequestLog.response_time_ms).label("avg_rt"),
    ).filter(
        RequestLog.timestamp >= since
    ).group_by(
        RequestLog.service_group
    ).order_by(
        func.count(RequestLog.id).desc()
    ).all()

    return [
        ServiceRequestSummary(
            service_group=r.service_group,
            total_requests=r.total,
            status_2xx=r.s2xx or 0,
            status_4xx=r.s4xx or 0,
            status_5xx=r.s5xx or 0,
            error_rate=round((r.s5xx or 0) / r.total * 100, 2) if r.total > 0 else 0.0,
            avg_response_time_ms=round(r.avg_rt, 2) if r.avg_rt else None,
        )
        for r in rows
    ]


@router.get("/requests/top-endpoints")
def get_top_endpoints(
    hours: int = Query(24, ge=1, le=720),
    sort_by: str = Query("count", regex="^(count|error_rate|avg_rt)$"),
    limit: int = Query(20, ge=1, le=100),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[EndpointStats]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(
        RequestLog.path,
        RequestLog.method,
        RequestLog.service_group,
        func.count(RequestLog.id).label("total"),
        func.sum(case((RequestLog.status_code >= 500, 1), else_=0)).label("errors"),
        func.avg(RequestLog.response_time_ms).label("avg_rt"),
        func.max(RequestLog.response_time_ms).label("max_rt"),
    ).filter(
        RequestLog.timestamp >= since
    )

    if service:
        q = q.filter(RequestLog.service_group == service)

    q = q.group_by(
        RequestLog.path, RequestLog.method, RequestLog.service_group
    )

    order_map = {
        "count": func.count(RequestLog.id).desc(),
        "error_rate": (func.sum(case((RequestLog.status_code >= 500, 1), else_=0)) * 100.0 / func.count(RequestLog.id)).desc(),
        "avg_rt": func.avg(RequestLog.response_time_ms).desc(),
    }
    q = q.order_by(order_map[sort_by])

    rows = q.limit(limit).all()

    return [
        EndpointStats(
            path=r.path,
            method=r.method,
            service_group=r.service_group,
            total_requests=r.total,
            error_count=r.errors or 0,
            error_rate=round((r.errors or 0) / r.total * 100, 2) if r.total > 0 else 0.0,
            avg_response_time_ms=round(r.avg_rt, 2) if r.avg_rt else None,
            max_response_time_ms=round(r.max_rt, 2) if r.max_rt else None,
        )
        for r in rows
    ]


@router.get("/requests/timeline")
def get_request_timeline(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[HourlyStatsResponse]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(HourlyStats).filter(HourlyStats.hour >= since)
    if service:
        q = q.filter(HourlyStats.service_group == service)

    rows = q.order_by(HourlyStats.hour).all()

    return [
        HourlyStatsResponse(
            service_group=r.service_group,
            hour=r.hour,
            total_requests=r.total_requests,
            status_2xx=r.status_2xx,
            status_3xx=r.status_3xx,
            status_4xx=r.status_4xx,
            status_5xx=r.status_5xx,
            avg_response_time_ms=r.avg_response_time_ms,
            error_count=r.error_count,
        )
        for r in rows
    ]


@router.get("/requests/slow")
def get_slow_requests(
    hours: int = Query(24, ge=1, le=720),
    threshold_ms: float = Query(1000, ge=100),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    rows = db.query(RequestLog).filter(
        and_(
            RequestLog.timestamp >= since,
            RequestLog.response_time_ms >= threshold_ms,
        )
    ).order_by(
        RequestLog.response_time_ms.desc()
    ).limit(limit).all()

    return [
        {
            "id": r.id,
            "service_group": r.service_group,
            "container_name": r.container_name,
            "timestamp": r.timestamp.isoformat(),
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "response_time_ms": r.response_time_ms,
        }
        for r in rows
    ]
