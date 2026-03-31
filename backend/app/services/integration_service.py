"""
외부 시스템 연동 서비스

- GitHub Issue 생성 (QA Agent 파이프라인 연결)
- QA Dashboard 직접 연동
- StandUp dev-plan 항목 등록
"""

import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.database_models import ErrorGroup, DailyReport

logger = logging.getLogger(__name__)

SEVERITY_TO_PRIORITY = {
    "CRITICAL": "P0",
    "HIGH": "P1",
    "MEDIUM": "P2",
    "LOW": "P3",
}

# 서비스 그룹 → GitHub 리포 매핑
SERVICE_TO_REPO = {
    "Academy": "bluevlad/Academy-MSA",
    "AllergyInsight": "bluevlad/AllergyInsight",
    "HopenVision": "bluevlad/HopenVision",
    "EduFit": "bluevlad/EduFit",
    "CompanyAnalyzer": "bluevlad/CompanyAnalyzer",
    "StandUp": "bluevlad/StandUp",
    "InfraWatcher": "bluevlad/InfraWatcher",
    "NewsLetterPlatform": "bluevlad/NewsLetterPlatform",
}


# ===== GitHub Issue (Phase 3) =====

def create_github_issue_for_error(error_group: ErrorGroup) -> dict | None:
    """오류 그룹에 대한 GitHub Issue 생성 (QA-AGENT-META 포함)"""
    settings = get_settings()
    if not settings.GITHUB_TOKEN:
        logger.warning("GitHub token not configured, skipping issue creation")
        return None

    repo = SERVICE_TO_REPO.get(error_group.service_group)
    if not repo:
        logger.info("No repo mapping for %s, skipping", error_group.service_group)
        return None

    priority = SEVERITY_TO_PRIORITY.get(error_group.severity, "P2")

    # QA-AGENT-META 블록 생성 (Auto-Tobe-Agent가 파싱)
    qa_meta = {
        "source": "log-analyzer",
        "runId": f"loganalyzer-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "project": error_group.service_group.lower().replace(" ", ""),
        "priority": priority,
        "error_type": error_group.error_type,
        "fingerprint": error_group.fingerprint,
        "occurrence_count": error_group.occurrence_count,
        "fix_hint": _generate_fix_hint(error_group),
        "verification": _generate_verification(error_group),
        "auto_fixable": error_group.error_type in (
            "static_404", "cors_error", "validation_error",
        ),
    }

    title = f"[LogAnalyzer] {error_group.service_group}: {error_group.error_type} ({priority})"
    body = f"""## 로그 기반 오류 감지

- **서비스**: {error_group.service_group}
- **오류 유형**: {error_group.error_type}
- **심각도**: {error_group.severity} ({priority})
- **발생 횟수**: {error_group.occurrence_count}회
- **최초 감지**: {error_group.first_seen.isoformat()}
- **최종 감지**: {error_group.last_seen.isoformat()}

### 샘플 로그
```
{error_group.sample_message[:1000]}
```

### 수정 제안
{_generate_fix_hint(error_group)}

---
*이 이슈는 LogAnalyzer에 의해 자동 생성되었습니다.*

<!-- QA-AGENT-META
{json.dumps(qa_meta, indent=2)}
-->
"""

    labels = ["log-analyzer", f"severity:{error_group.severity.lower()}", error_group.error_type]

    try:
        from github import Github
        gh = Github(settings.GITHUB_TOKEN)
        repo_obj = gh.get_repo(repo)
        issue = repo_obj.create_issue(
            title=title,
            body=body,
            labels=[l for l in labels if l in [lbl.name for lbl in repo_obj.get_labels()]],
        )

        logger.info("Created GitHub issue #%d for %s", issue.number, error_group.fingerprint)
        return {"number": issue.number, "url": issue.html_url}

    except Exception as e:
        logger.error("Failed to create GitHub issue: %s", e)
        return None


def _generate_fix_hint(error_group: ErrorGroup) -> str:
    hints = {
        "500_error": "500 Internal Server Error 발생. 서버 로그에서 상세 스택트레이스를 확인하세요.",
        "exception": "미처리 예외 발생. 해당 코드 경로에 적절한 에러 핸들링을 추가하세요.",
        "db_error": "데이터베이스 연결/쿼리 오류. 커넥션 풀 설정과 쿼리를 점검하세요.",
        "timeout": "요청 타임아웃 발생. 성능 병목 지점을 프로파일링하세요.",
        "proxy_error": "리버스 프록시 오류. 대상 서비스의 상태와 Nginx 설정을 확인하세요.",
        "cors_error": "CORS 정책 위반. 백엔드 CORS 설정에 해당 origin을 추가하세요.",
        "auth_failure": "인증/인가 실패. 토큰 만료 정책과 갱신 로직을 확인하세요.",
        "validation_error": "요청 유효성 검증 실패. 클라이언트 측 입력 검증을 강화하세요.",
        "static_404": "정적 파일 404. 빌드 결과물 경로와 Nginx 설정을 확인하세요.",
        "oom_error": "메모리 부족. 컨테이너 메모리 제한과 메모리 누수를 점검하세요.",
    }
    return hints.get(error_group.error_type, "오류 로그를 분석하여 원인을 파악하세요.")


def _generate_verification(error_group: ErrorGroup) -> str:
    return f"서비스 '{error_group.service_group}'의 로그에서 fingerprint '{error_group.fingerprint}' 오류가 재발하지 않는지 확인"


# ===== QA Dashboard (Phase 3) =====

def push_to_qa_dashboard(db: Session, error_groups: list[ErrorGroup]) -> bool:
    """QA Dashboard에 점검 항목 직접 등록"""
    settings = get_settings()
    if not settings.QA_DASHBOARD_API_KEY:
        logger.warning("QA Dashboard API key not configured")
        return False

    health_results = []
    for group in error_groups:
        health_results.append({
            "projectName": group.service_group.lower().replace(" ", ""),
            "healthy": False,
            "endpoints": [{
                "url": f"[log-analyzer] {group.error_type}",
                "label": f"{group.error_type} ({group.severity})",
                "healthy": False,
                "statusCode": 500 if group.severity == "CRITICAL" else 400,
                "responseTimeMs": 0,
            }],
        })

    payload = {
        "runId": f"loganalyzer-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "durationMs": 0,
        "source": "log-analyzer",
        "healthResults": health_results,
        "testResults": [],
        "summary": {
            "totalProjects": len(set(g.service_group for g in error_groups)),
            "healthyProjects": 0,
            "testedProjects": 0,
            "totalTests": 0,
            "totalPassed": 0,
            "totalFailed": len(error_groups),
            "totalSkipped": 0,
        },
    }

    try:
        resp = httpx.post(
            f"{settings.QA_DASHBOARD_API_URL}/api/ingest",
            headers={"Authorization": f"Bearer {settings.QA_DASHBOARD_API_KEY}"},
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Pushed %d error groups to QA Dashboard", len(error_groups))
        return True
    except Exception as e:
        logger.error("Failed to push to QA Dashboard: %s", e)
        return False


# ===== StandUp (Phase 4) =====

def report_fixes_to_standup(
    db: Session,
    resolved_groups: list[ErrorGroup],
) -> bool:
    """해결된 오류 그룹을 StandUp에 진행사항으로 등록"""
    settings = get_settings()
    if not settings.STANDUP_API_KEY:
        logger.warning("StandUp API key not configured")
        return False

    for group in resolved_groups:
        payload = {
            "title": f"[LogFix] {group.service_group}: {group.error_type} 수정 완료",
            "repository": SERVICE_TO_REPO.get(group.service_group, ""),
            "status": "closed",
            "category": "bug-fix",
            "priority": SEVERITY_TO_PRIORITY.get(group.severity, "P2"),
        }

        try:
            resp = httpx.post(
                f"{settings.STANDUP_API_URL}/api/v1/work-items",
                headers={"Authorization": f"Bearer {settings.STANDUP_API_KEY}"},
                json=payload,
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info("Reported fix to StandUp: %s", group.fingerprint)
            else:
                logger.warning(
                    "StandUp response %d: %s", resp.status_code, resp.text[:200]
                )
        except Exception as e:
            logger.error("Failed to report to StandUp: %s", e)

    return True


# ===== Daily Report Dispatch =====

def dispatch_daily_report(db: Session, report: DailyReport) -> None:
    """일일 리포트 기반으로 GitHub Issue + QA + StandUp 연동"""

    # 1. CRITICAL/HIGH 미해결 오류 → GitHub Issue 생성
    critical_groups = db.query(ErrorGroup).filter(
        ErrorGroup.status == "open",
        ErrorGroup.severity.in_(["CRITICAL", "HIGH"]),
        ErrorGroup.github_issue_number.is_(None),
        ErrorGroup.occurrence_count >= 3,
    ).all()

    for group in critical_groups:
        result = create_github_issue_for_error(group)
        if result:
            group.github_issue_number = result["number"]
            group.github_issue_url = result["url"]

    # 2. 모든 open 오류 → QA Dashboard
    open_groups = db.query(ErrorGroup).filter(
        ErrorGroup.status == "open",
    ).all()

    if open_groups:
        qa_result = push_to_qa_dashboard(db, open_groups)
        report.dispatched_to_qa = qa_result

    # 3. 해결된 오류 → StandUp
    resolved_groups = db.query(ErrorGroup).filter(
        ErrorGroup.status == "resolved",
    ).all()

    if resolved_groups:
        standup_result = report_fixes_to_standup(db, resolved_groups)
        report.dispatched_to_standup = standup_result

    db.commit()
    logger.info(
        "Dispatched daily report: %d GH issues, %d QA groups, %d StandUp items",
        len(critical_groups), len(open_groups), len(resolved_groups),
    )
