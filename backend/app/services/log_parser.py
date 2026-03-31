"""
로그 파서 서비스

수집된 raw 로그를 분석하여 Request 로그와 Error 로그로 분류합니다.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.database_models import LogEntry, RequestLog, ErrorLog, ErrorGroup

logger = logging.getLogger(__name__)


# ===== Request 패턴 =====

# Nginx access log: "GET /api/health HTTP/1.1" 200 ... 0.003
NGINX_PATTERN = re.compile(
    r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+'
    r'(?P<path>[^\s]+)\s+HTTP/[\d.]+"'
    r'\s+(?P<status>\d{3})'
    r'(?:.*?"(?P<user_agent>[^"]*)")?'
    r'(?:.*?(?P<response_time>[\d.]+))?'
)

# Uvicorn/FastAPI: INFO: 1.2.3.4:54321 - "GET /api/foo HTTP/1.1" 200
UVICORN_PATTERN = re.compile(
    r'(?P<client_ip>[\d.]+):\d+\s+-\s+'
    r'"(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+'
    r'(?P<path>[^\s]+)\s+HTTP/[\d.]+"'
    r'\s+(?P<status>\d{3})'
)

# Spring Boot: ... GET /api/exams 200 15ms
SPRING_PATTERN = re.compile(
    r'(?P<method>GET|POST|PUT|DELETE|PATCH)\s+'
    r'(?P<path>/[^\s]+)\s+'
    r'(?P<status>\d{3})'
    r'(?:\s+(?P<response_time>\d+)ms)?'
)

# Spring Boot access log style: "GET /api/foo" 200 15
SPRING_ACCESS_PATTERN = re.compile(
    r'"(?P<method>GET|POST|PUT|DELETE|PATCH)\s+'
    r'(?P<path>[^\s"]+)"'
    r'\s+(?P<status>\d{3})'
    r'(?:\s+(?P<response_time>\d+))?'
)

REQUEST_PATTERNS = [
    ("nginx", NGINX_PATTERN),
    ("uvicorn", UVICORN_PATTERN),
    ("spring", SPRING_PATTERN),
    ("spring_access", SPRING_ACCESS_PATTERN),
]


# ===== Error 패턴 =====

ERROR_PATTERNS = {
    "500_error": re.compile(r'HTTP/[\d.]+"?\s+5\d{2}'),
    "exception": re.compile(
        r'(Traceback \(most recent call last\)|'
        r'(?:java\.lang\.\w*Exception|java\.lang\.\w*Error)|'
        r'(?:RuntimeError|ValueError|TypeError|KeyError|AttributeError|ImportError))'
    ),
    "db_error": re.compile(
        r'(sqlalchemy\.exc\.\w+|PSQLException|'
        r'org\.postgresql|connection refused.*5432|'
        r'OperationalError.*(?:could not connect|server closed))'
    ),
    "timeout": re.compile(
        r'(TimeoutError|ReadTimeout|ConnectTimeout|'
        r'java\.net\.SocketTimeoutException|'
        r'upstream timed out|504 Gateway)'
    ),
    "proxy_error": re.compile(
        r'(502 Bad Gateway|504 Gateway Timeout|'
        r'connect\(\) failed|upstream prematurely closed)'
    ),
    "static_404": re.compile(
        r'"GET /(?:static|assets|favicon|\.well-known)/[^\s]+" (?:404|403)'
    ),
    "cors_error": re.compile(
        r'(CORS|Access-Control-Allow|cross-origin)',
        re.IGNORECASE,
    ),
    "auth_failure": re.compile(
        r'(401 Unauthorized|403 Forbidden|JWT expired|'
        r'token.*(?:invalid|expired)|authentication failed)',
        re.IGNORECASE,
    ),
    "validation_error": re.compile(
        r'(422 Unprocessable|ValidationError|'
        r'RequestValidationError|MethodArgumentNotValidException)'
    ),
    "oom_error": re.compile(
        r'(OutOfMemoryError|MemoryError|Cannot allocate memory|OOM)'
    ),
}

SEVERITY_MAP = {
    "500_error": "CRITICAL",
    "exception": "CRITICAL",
    "db_error": "CRITICAL",
    "oom_error": "CRITICAL",
    "timeout": "HIGH",
    "proxy_error": "HIGH",
    "auth_failure": "MEDIUM",
    "validation_error": "MEDIUM",
    "cors_error": "MEDIUM",
    "static_404": "LOW",
}

# 무시할 로그 패턴 (health check 등)
IGNORE_PATTERNS = [
    re.compile(r'"GET /api/health HTTP'),
    re.compile(r'"GET /health HTTP'),
    re.compile(r'"GET /actuator/health HTTP'),
    re.compile(r'kube-probe'),
    re.compile(r'ELB-HealthChecker'),
]


def _should_ignore(line: str) -> bool:
    return any(p.search(line) for p in IGNORE_PATTERNS)


def _generate_fingerprint(container: str, error_type: str, message: str) -> str:
    # 숫자/타임스탬프를 제거하여 동일 오류를 그룹핑
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*', '', message)
    normalized = re.sub(r'\b\d+\b', 'N', normalized)
    normalized = re.sub(r'0x[0-9a-fA-F]+', '0xHEX', normalized)
    key = f"{container}:{error_type}:{normalized[:200]}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def parse_request_log(
    entry: LogEntry,
) -> RequestLog | None:
    """로그 라인에서 HTTP 요청 정보를 추출"""
    line = entry.raw_line

    if _should_ignore(line):
        return None

    for source_type, pattern in REQUEST_PATTERNS:
        match = pattern.search(line)
        if match:
            d = match.groupdict()
            response_time = d.get("response_time")
            if response_time:
                try:
                    rt = float(response_time)
                    # nginx는 초 단위, spring은 ms 단위
                    if source_type == "nginx" and rt < 100:
                        rt = rt * 1000
                except (ValueError, TypeError):
                    rt = None
            else:
                rt = None

            return RequestLog(
                container_name=entry.container_name,
                service_group=entry.service_group,
                timestamp=entry.timestamp,
                method=d["method"],
                path=d["path"],
                status_code=int(d["status"]),
                response_time_ms=rt,
                client_ip=d.get("client_ip"),
                user_agent=d.get("user_agent"),
                source_type=source_type,
            )

    return None


def parse_error_log(
    entry: LogEntry,
) -> ErrorLog | None:
    """로그 라인에서 오류 정보를 추출"""
    line = entry.raw_line

    if _should_ignore(line):
        return None

    # ERROR/WARN 레벨이거나, stderr 스트림인 경우에만 오류 분석
    is_error_candidate = (
        entry.log_level in ("ERROR", "FATAL", "SEVERE", "WARN")
        or entry.stream == "stderr"
    )

    if not is_error_candidate:
        # status 5xx도 오류로 분류
        if not ERROR_PATTERNS["500_error"].search(line):
            return None

    for error_type, pattern in ERROR_PATTERNS.items():
        if pattern.search(line):
            fingerprint = _generate_fingerprint(
                entry.container_name, error_type, line
            )
            return ErrorLog(
                container_name=entry.container_name,
                service_group=entry.service_group,
                timestamp=entry.timestamp,
                error_type=error_type,
                severity=SEVERITY_MAP.get(error_type, "MEDIUM"),
                message=line[:2000],
                fingerprint=fingerprint,
            )

    # 패턴에 매칭되지 않더라도 ERROR 레벨이면 기록
    if entry.log_level in ("ERROR", "FATAL", "SEVERE"):
        fingerprint = _generate_fingerprint(
            entry.container_name, "unclassified", line
        )
        return ErrorLog(
            container_name=entry.container_name,
            service_group=entry.service_group,
            timestamp=entry.timestamp,
            error_type="unclassified",
            severity="MEDIUM",
            message=line[:2000],
            fingerprint=fingerprint,
        )

    return None


def _update_error_group(db: Session, error: ErrorLog) -> None:
    """오류 그룹 업데이트 또는 생성"""
    group = db.query(ErrorGroup).filter(
        ErrorGroup.fingerprint == error.fingerprint
    ).first()

    if group:
        group.last_seen = error.timestamp
        group.occurrence_count += 1
        if SEVERITY_MAP.get(error.error_type, "MEDIUM") == "CRITICAL":
            group.severity = "CRITICAL"
        error.group_id = group.id
    else:
        group = ErrorGroup(
            fingerprint=error.fingerprint,
            container_name=error.container_name,
            service_group=error.service_group,
            error_type=error.error_type,
            severity=error.severity,
            sample_message=error.message[:500],
            first_seen=error.timestamp,
            last_seen=error.timestamp,
            occurrence_count=1,
        )
        db.add(group)
        db.flush()
        error.group_id = group.id


def parse_collected_logs(db: Session) -> dict:
    """미파싱 로그를 분석하여 Request/Error 로그로 분류"""
    unparsed = db.query(LogEntry).filter(
        LogEntry.parsed == False  # noqa: E712
    ).order_by(LogEntry.timestamp).limit(10000).all()

    if not unparsed:
        return {"requests": 0, "errors": 0, "total": 0}

    request_count = 0
    error_count = 0

    for entry in unparsed:
        # Request 파싱 시도
        request_log = parse_request_log(entry)
        if request_log:
            db.add(request_log)
            request_count += 1

        # Error 파싱 시도 (request와 독립적)
        error_log = parse_error_log(entry)
        if error_log:
            _update_error_group(db, error_log)
            db.add(error_log)
            error_count += 1

        entry.parsed = True

    db.commit()

    logger.info(
        "Parsed %d logs: %d requests, %d errors",
        len(unparsed), request_count, error_count,
    )

    return {
        "requests": request_count,
        "errors": error_count,
        "total": len(unparsed),
    }
