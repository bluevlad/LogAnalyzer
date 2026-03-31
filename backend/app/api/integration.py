"""
Integration API

수동 트리거: GitHub Issue 생성, QA Dashboard 전송, StandUp 보고
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.database_models import ErrorGroup
from app.services.integration_service import (
    create_github_issue_for_error,
    push_to_qa_dashboard,
    report_fixes_to_standup,
)

router = APIRouter()


@router.post("/integration/github-issue/{group_id}")
def create_issue_for_group(
    group_id: int,
    db: Session = Depends(get_db),
):
    """특정 오류 그룹에 대해 GitHub Issue 수동 생성"""
    group = db.query(ErrorGroup).filter(ErrorGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Error group not found")

    if group.github_issue_number:
        return {
            "status": "already_exists",
            "issue_number": group.github_issue_number,
            "issue_url": group.github_issue_url,
        }

    result = create_github_issue_for_error(group)
    if result:
        group.github_issue_number = result["number"]
        group.github_issue_url = result["url"]
        db.commit()
        return {"status": "created", **result}

    raise HTTPException(status_code=500, detail="Failed to create GitHub issue")


@router.post("/integration/qa-dashboard")
def push_errors_to_qa(
    status: str = Query("open", regex="^(open|acknowledged)$"),
    severity: str = Query(None),
    db: Session = Depends(get_db),
):
    """오류 그룹을 QA Dashboard에 수동 전송"""
    q = db.query(ErrorGroup).filter(ErrorGroup.status == status)
    if severity:
        q = q.filter(ErrorGroup.severity == severity.upper())

    groups = q.all()
    if not groups:
        return {"status": "no_data", "message": "No matching error groups"}

    success = push_to_qa_dashboard(db, groups)
    return {
        "status": "sent" if success else "failed",
        "groups_count": len(groups),
    }


@router.post("/integration/standup")
def report_to_standup(
    db: Session = Depends(get_db),
):
    """해결된 오류 그룹을 StandUp에 수동 보고"""
    resolved = db.query(ErrorGroup).filter(
        ErrorGroup.status == "resolved"
    ).all()

    if not resolved:
        return {"status": "no_data", "message": "No resolved error groups"}

    success = report_fixes_to_standup(db, resolved)
    return {
        "status": "sent" if success else "failed",
        "groups_count": len(resolved),
    }
