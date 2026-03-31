"""
Error 분석 API

오류 로그 조회, 오류 그룹 관리, 심각도별 집계, 오류 타임라인
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import ErrorLog, ErrorGroup
from app.models.schemas import (
    ErrorLogResponse, ErrorGroupResponse, ErrorSummary, PaginatedResponse,
)

router = APIRouter()


@router.get("/errors/summary")
def get_error_summary(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ErrorSummary:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(ErrorLog).filter(ErrorLog.timestamp >= since)
    if service:
        q = q.filter(ErrorLog.service_group == service)

    total = q.count()
    critical = q.filter(ErrorLog.severity == "CRITICAL").count()
    high = q.filter(ErrorLog.severity == "HIGH").count()
    medium = q.filter(ErrorLog.severity == "MEDIUM").count()
    low = q.filter(ErrorLog.severity == "LOW").count()

    gq = db.query(ErrorGroup)
    if service:
        gq = gq.filter(ErrorGroup.service_group == service)
    open_groups = gq.filter(ErrorGroup.status == "open").count()
    resolved_groups = gq.filter(ErrorGroup.status == "resolved").count()

    return ErrorSummary(
        total_errors=total,
        critical=critical,
        high=high,
        medium=medium,
        low=low,
        open_groups=open_groups,
        resolved_groups=resolved_groups,
    )


@router.get("/errors/list")
def get_error_list(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    severity: Optional[str] = None,
    error_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(ErrorLog).filter(ErrorLog.timestamp >= since)
    if service:
        q = q.filter(ErrorLog.service_group == service)
    if severity:
        q = q.filter(ErrorLog.severity == severity.upper())
    if error_type:
        q = q.filter(ErrorLog.error_type == error_type)

    total = q.count()
    items = q.order_by(
        ErrorLog.timestamp.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return PaginatedResponse(
        items=[ErrorLogResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/errors/groups")
def get_error_groups(
    status: Optional[str] = Query(None, regex="^(open|acknowledged|resolved|ignored)$"),
    service: Optional[str] = None,
    severity: Optional[str] = None,
    sort_by: str = Query("last_seen", regex="^(last_seen|occurrence_count|first_seen)$"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ErrorGroupResponse]:
    q = db.query(ErrorGroup)

    if status:
        q = q.filter(ErrorGroup.status == status)
    if service:
        q = q.filter(ErrorGroup.service_group == service)
    if severity:
        q = q.filter(ErrorGroup.severity == severity.upper())

    order_map = {
        "last_seen": ErrorGroup.last_seen.desc(),
        "occurrence_count": ErrorGroup.occurrence_count.desc(),
        "first_seen": ErrorGroup.first_seen.desc(),
    }
    q = q.order_by(order_map[sort_by])

    rows = q.limit(limit).all()
    return [ErrorGroupResponse.model_validate(r) for r in rows]


@router.put("/errors/groups/{group_id}/status")
def update_error_group_status(
    group_id: int = Path(...),
    new_status: str = Query(..., regex="^(open|acknowledged|resolved|ignored)$"),
    db: Session = Depends(get_db),
):
    group = db.query(ErrorGroup).filter(ErrorGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Error group not found")

    group.status = new_status
    if new_status == "resolved":
        # 해당 그룹의 모든 에러 resolved 처리
        db.query(ErrorLog).filter(
            ErrorLog.group_id == group_id,
            ErrorLog.resolved == False,  # noqa: E712
        ).update({"resolved": True, "resolved_at": datetime.now(timezone.utc)})

    db.commit()
    return {"status": "updated", "group_id": group_id, "new_status": new_status}


@router.get("/errors/timeline")
def get_error_timeline(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """시간별 오류 발생 히트맵 데이터"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(
        ErrorLog.service_group,
        func.date_trunc("hour", ErrorLog.timestamp).label("hour"),
        ErrorLog.severity,
        func.count(ErrorLog.id).label("count"),
    ).filter(
        ErrorLog.timestamp >= since
    )

    if service:
        q = q.filter(ErrorLog.service_group == service)

    rows = q.group_by(
        ErrorLog.service_group,
        func.date_trunc("hour", ErrorLog.timestamp),
        ErrorLog.severity,
    ).order_by("hour").all()

    return [
        {
            "service_group": r.service_group,
            "hour": r.hour.isoformat() if r.hour else None,
            "severity": r.severity,
            "count": r.count,
        }
        for r in rows
    ]


@router.get("/errors/types")
def get_error_type_stats(
    hours: int = Query(24, ge=1, le=720),
    service: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """오류 유형별 집계"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    q = db.query(
        ErrorLog.error_type,
        ErrorLog.severity,
        func.count(ErrorLog.id).label("count"),
    ).filter(
        ErrorLog.timestamp >= since,
    )

    if service:
        q = q.filter(ErrorLog.service_group == service)

    rows = q.group_by(
        ErrorLog.error_type, ErrorLog.severity,
    ).order_by(
        func.count(ErrorLog.id).desc()
    ).all()

    return [
        {
            "error_type": r.error_type,
            "severity": r.severity,
            "count": r.count,
        }
        for r in rows
    ]
