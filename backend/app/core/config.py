from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "LogAnalyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 9092

    # Database
    DATABASE_URL: str = "postgresql://loganalyzer_svc:changeme@localhost:5432/loganalyzer"

    # CORS
    CORS_ORIGINS: str = "https://loganalyzer.unmong.com,http://localhost:4092"

    # Docker
    DOCKER_SOCKET: str = "/var/run/docker.sock"
    DOCKER_HOST_ALIAS: str = "host.docker.internal"

    # Log collection
    LOG_COLLECT_INTERVAL_MINUTES: int = 5
    LOG_RETENTION_DAYS: int = 30
    AGGREGATE_RETENTION_DAYS: int = 90
    # 관리 대상 서비스 그룹 (콤마 구분) — 해당 그룹의 컨테이너만 수집. 빈 값이면 전체 수집
    MANAGED_SERVICES: str = "AllergyInsight,SkillRadar,NewsLetterPlatform"

    def managed_service_list(self) -> list[str]:
        return [s.strip() for s in self.MANAGED_SERVICES.split(",") if s.strip()]

    # Integration - StandUp
    STANDUP_API_URL: str = "http://host.docker.internal:9060"
    STANDUP_API_KEY: str = ""

    # Integration - QA Dashboard
    QA_DASHBOARD_API_URL: str = "http://host.docker.internal:9095"
    QA_DASHBOARD_API_KEY: str = ""

    # Integration - GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_REPOS: str = ""  # comma-separated "owner/repo" list

    # Report
    DAILY_REPORT_HOUR: int = 6
    ERROR_THRESHOLD_CRITICAL: int = 10  # per hour
    ERROR_THRESHOLD_HIGH: int = 5

    model_config = {
        "env_file": ".env",
        "env_prefix": "LA_",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
