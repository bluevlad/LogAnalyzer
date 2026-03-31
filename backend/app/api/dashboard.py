"""
Dashboard API

전체 서비스 현황 요약 및 일일 리포트 조회
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import RequestLog, ErrorLog, ErrorGroup, DailyReport
from app.models.schemas import DashboardSummary, ServiceRequestSummary, DailyReportResponse

router = APIRouter()


@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
) -> DashboardSummary:
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # 서비스별 요청 통계
    service_stats = db.query(
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
    ).all()

    total_requests = sum(s.total for s in service_stats)
    total_5xx = sum(s.s5xx or 0 for s in service_stats)

    # 에러 집계
    total_errors = db.query(func.count(ErrorLog.id)).filter(
        ErrorLog.timestamp >= since
    ).scalar() or 0

    critical_errors = db.query(func.count(ErrorLog.id)).filter(
        and_(ErrorLog.timestamp >= since, ErrorLog.severity == "CRITICAL")
    ).scalar() or 0

    open_groups = db.query(func.count(ErrorGroup.id)).filter(
        ErrorGroup.status == "open"
    ).scalar() or 0

    services = [
        ServiceRequestSummary(
            service_group=s.service_group,
            total_requests=s.total,
            status_2xx=s.s2xx or 0,
            status_4xx=s.s4xx or 0,
            status_5xx=s.s5xx or 0,
            error_rate=round((s.s5xx or 0) / s.total * 100, 2) if s.total > 0 else 0.0,
            avg_response_time_ms=round(s.avg_rt, 2) if s.avg_rt else None,
        )
        for s in service_stats
    ]

    return DashboardSummary(
        total_services=len(service_stats),
        total_requests_24h=total_requests,
        total_errors_24h=total_errors,
        error_rate_24h=round(total_5xx / total_requests * 100, 2) if total_requests > 0 else 0.0,
        critical_errors=critical_errors,
        open_error_groups=open_groups,
        services=services,
    )


@router.get("/dashboard/daily-summary")
def get_daily_summary(
    date: Optional[str] = Query(None, description="YYYY-MM-DD format"),
    db: Session = Depends(get_db),
):
    """일일 요약 (StandUp 연동용)"""
    if date:
        target = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        target = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)

    report = db.query(DailyReport).filter(
        func.date(DailyReport.report_date) == target.date()
    ).first()

    if not report:
        return {"message": "No report found for this date"}

    return {
        "report_date": report.report_date.isoformat(),
        "total_requests": report.total_requests,
        "total_errors": report.total_errors,
        "new_error_groups": report.new_error_groups,
        "resolved_error_groups": report.resolved_error_groups,
        "top_errors": report.top_errors_json,
        "top_slow_endpoints": report.top_slow_endpoints_json,
        "dispatched_to_standup": report.dispatched_to_standup,
        "dispatched_to_qa": report.dispatched_to_qa,
    }


@router.get("/dashboard/reports")
def get_reports(
    limit: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
) -> list[DailyReportResponse]:
    rows = db.query(DailyReport).order_by(
        DailyReport.report_date.desc()
    ).limit(limit).all()

    return [DailyReportResponse.model_validate(r) for r in rows]
