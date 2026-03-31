"""
스케줄러

APScheduler를 사용하여 로그 수집, 파싱, 집계, 정리 작업을 주기적으로 실행합니다.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.log_collector import collect_all_logs
from app.services.log_parser import parse_collected_logs
from app.services.aggregation_service import (
    aggregate_hourly_stats,
    generate_daily_report,
    cleanup_old_data,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _get_db_session():
    return SessionLocal()


async def collect_and_parse_job():
    """로그 수집 + 파싱 (5분마다)"""
    db = _get_db_session()
    try:
        collected = collect_all_logs(db)
        if collected > 0:
            parsed = parse_collected_logs(db)
            logger.info(
                "Collect & parse: %d collected, %d requests, %d errors",
                collected, parsed["requests"], parsed["errors"],
            )
    except Exception as e:
        logger.error("Collect & parse failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def aggregation_job():
    """시간별 집계 (매 시간)"""
    db = _get_db_session()
    try:
        aggregate_hourly_stats(db)
    except Exception as e:
        logger.error("Hourly aggregation failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def daily_report_job():
    """일일 리포트 생성 + 외부 연동 디스패치 (매일 06:00)"""
    db = _get_db_session()
    try:
        from app.services.integration_service import dispatch_daily_report
        report = generate_daily_report(db)
        dispatch_daily_report(db, report)
    except Exception as e:
        logger.error("Daily report failed: %s", e)
        db.rollback()
    finally:
        db.close()


async def cleanup_job():
    """오래된 데이터 삭제 (매일 03:00)"""
    db = _get_db_session()
    try:
        cleanup_old_data(db)
    except Exception as e:
        logger.error("Cleanup failed: %s", e)
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    settings = get_settings()

    # 로그 수집 + 파싱 (5분마다)
    scheduler.add_job(
        collect_and_parse_job,
        "interval",
        minutes=settings.LOG_COLLECT_INTERVAL_MINUTES,
        id="collect_and_parse",
        max_instances=1,
    )

    # 시간별 집계 (매 시간 :05)
    scheduler.add_job(
        aggregation_job,
        "cron",
        minute=5,
        id="hourly_aggregation",
        max_instances=1,
    )

    # 일일 리포트 (매일 06:00)
    scheduler.add_job(
        daily_report_job,
        "cron",
        hour=settings.DAILY_REPORT_HOUR,
        minute=0,
        id="daily_report",
        max_instances=1,
    )

    # 데이터 정리 (매일 03:00)
    scheduler.add_job(
        cleanup_job,
        "cron",
        hour=3,
        minute=0,
        id="cleanup",
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        "Scheduler started: collect every %d min, report at %02d:00",
        settings.LOG_COLLECT_INTERVAL_MINUTES,
        settings.DAILY_REPORT_HOUR,
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
