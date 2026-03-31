from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Request Log Schemas ---

class RequestLogResponse(BaseModel):
    id: int
    container_name: str
    service_group: str
    timestamp: datetime
    method: str
    path: str
    status_code: int
    response_time_ms: Optional[float] = None
    source_type: str

    model_config = {"from_attributes": True}


class RequestStats(BaseModel):
    total_requests: int
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    avg_response_time_ms: Optional[float] = None
    error_rate: float  # percentage


class EndpointStats(BaseModel):
    path: str
    method: str
    service_group: str
    total_requests: int
    error_count: int
    error_rate: float
    avg_response_time_ms: Optional[float] = None
    max_response_time_ms: Optional[float] = None


class ServiceRequestSummary(BaseModel):
    service_group: str
    total_requests: int
    status_2xx: int
    status_4xx: int
    status_5xx: int
    error_rate: float
    avg_response_time_ms: Optional[float] = None


# --- Error Log Schemas ---

class ErrorLogResponse(BaseModel):
    id: int
    container_name: str
    service_group: str
    timestamp: datetime
    error_type: str
    severity: str
    message: str
    stack_trace: Optional[str] = None
    fingerprint: str
    resolved: bool

    model_config = {"from_attributes": True}


class ErrorGroupResponse(BaseModel):
    id: int
    fingerprint: str
    container_name: str
    service_group: str
    error_type: str
    severity: str
    sample_message: str
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    status: str
    github_issue_number: Optional[int] = None
    github_issue_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ErrorSummary(BaseModel):
    total_errors: int
    critical: int
    high: int
    medium: int
    low: int
    open_groups: int
    resolved_groups: int


# --- Hourly Stats Schemas ---

class HourlyStatsResponse(BaseModel):
    service_group: str
    hour: datetime
    total_requests: int
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int
    avg_response_time_ms: Optional[float] = None
    error_count: int

    model_config = {"from_attributes": True}


# --- Dashboard ---

class DashboardSummary(BaseModel):
    total_services: int
    total_requests_24h: int
    total_errors_24h: int
    error_rate_24h: float
    critical_errors: int
    open_error_groups: int
    services: list[ServiceRequestSummary]


# --- Daily Report ---

class DailyReportResponse(BaseModel):
    id: int
    report_date: datetime
    total_requests: int
    total_errors: int
    new_error_groups: int
    resolved_error_groups: int
    dispatched_to_standup: bool
    dispatched_to_qa: bool

    model_config = {"from_attributes": True}


# --- Pagination ---

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
