"""
Docker 컨테이너 로그 수집 서비스

Docker SDK를 사용하여 각 컨테이너의 stdout/stderr 로그를 수집하고
raw 로그 라인을 DB에 저장합니다.
"""

import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import docker
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.database_models import LogEntry

logger = logging.getLogger(__name__)

# 서비스 그룹 매핑 (컨테이너명 prefix → 그룹)
SERVICE_GROUP_MAP = {
    "academy-": "Academy",
    "teacherhub-": "TeacherHub",
    "academyinsight-": "AcademyInsight",
    "allergyinsight-": "AllergyInsight",
    "healthpulse-": "HealthPulse",
    "newsletterplatform-": "NewsLetterPlatform",
    "hopenvision-": "HopenVision",
    "standup-": "StandUp",
    "companyanalyzer-": "CompanyAnalyzer",
    "edufit-": "EduFit",
    "infrawatcher-": "InfraWatcher",
    "qa-dashboard-": "QA Dashboard",
    "unmong-": "Gateway",
    "postgresql": "Database",
    "mongodb": "Database",
    "pgadmin": "Database",
    "mongo-express": "Database",
    "wiki-hub": "Wiki Hub",
}

# 수집 제외 컨테이너
EXCLUDE_CONTAINERS = {"loganalyzer-backend", "loganalyzer-frontend"}

# 마지막 수집 시점 추적
_last_collected: dict[str, datetime] = {}


def get_service_group(container_name: str) -> str:
    name_lower = container_name.lower()
    for prefix, group in SERVICE_GROUP_MAP.items():
        if name_lower.startswith(prefix):
            return group
    return "Unknown"


def _collect_container_logs(
    container, since: datetime, until: datetime
) -> list[dict]:
    """단일 컨테이너의 로그를 수집 (Thread에서 실행)"""
    container_name = container.name
    results = []

    try:
        for stream_type in ("stdout", "stderr"):
            is_stdout = stream_type == "stdout"
            logs = container.logs(
                since=since,
                until=until,
                timestamps=True,
                stdout=is_stdout,
                stderr=not is_stdout,
            )

            if not logs:
                continue

            lines = logs.decode("utf-8", errors="replace").strip().split("\n")
            for line in lines:
                if not line.strip():
                    continue

                # Docker timestamp format: 2026-03-31T10:00:00.123456789Z
                ts_str, _, log_text = line.partition(" ")
                try:
                    ts = datetime.fromisoformat(
                        ts_str.replace("Z", "+00:00")[:32]
                    )
                except (ValueError, IndexError):
                    ts = until
                    log_text = line

                results.append({
                    "container_name": container_name,
                    "service_group": get_service_group(container_name),
                    "stream": stream_type,
                    "timestamp": ts,
                    "raw_line": log_text.strip(),
                    "log_level": _extract_log_level(log_text),
                })

    except Exception as e:
        logger.warning("Failed to collect logs from %s: %s", container_name, e)

    return results


def _extract_log_level(line: str) -> str | None:
    line_upper = line[:200].upper()
    for level in ("FATAL", "ERROR", "SEVERE", "WARN", "WARNING", "INFO", "DEBUG", "TRACE"):
        if level in line_upper:
            if level in ("WARN", "WARNING"):
                return "WARN"
            if level == "SEVERE":
                return "ERROR"
            return level
    return None


def collect_all_logs(db: Session) -> int:
    """모든 Docker 컨테이너에서 로그 수집"""
    settings = get_settings()

    try:
        client = docker.DockerClient(base_url=f"unix://{settings.DOCKER_SOCKET}")
    except Exception as e:
        logger.error("Failed to connect to Docker: %s", e)
        return 0

    now = datetime.now(timezone.utc)
    default_since = now - timedelta(minutes=settings.LOG_COLLECT_INTERVAL_MINUTES + 1)

    containers = [
        c for c in client.containers.list()
        if c.name not in EXCLUDE_CONTAINERS and c.status == "running"
    ]

    total_lines = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for container in containers:
            since = _last_collected.get(container.name, default_since)
            futures[executor.submit(
                _collect_container_logs, container, since, now
            )] = container.name

        for future in futures:
            container_name = futures[future]
            try:
                log_entries = future.result(timeout=30)
                if log_entries:
                    for entry_data in log_entries:
                        db.add(LogEntry(**entry_data))
                    total_lines += len(log_entries)
                _last_collected[container_name] = now
            except Exception as e:
                logger.error("Error processing logs for %s: %s", container_name, e)

    if total_lines > 0:
        db.commit()
        logger.info("Collected %d log lines from %d containers", total_lines, len(containers))

    return total_lines
