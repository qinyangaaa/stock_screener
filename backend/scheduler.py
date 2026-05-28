"""定时任务管理 — 交易日 14:30 触发筛选"""

import logging
import threading
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from trading_calendar import is_trading_day
from strategy.engine import ScreeningEngine

logger = logging.getLogger("SCHEDULER")

_scheduler: BackgroundScheduler = None
_engine: ScreeningEngine = None
_running_task: threading.Thread = None


def get_engine() -> ScreeningEngine:
    global _engine
    if _engine is None:
        _engine = ScreeningEngine()
    return _engine


def _screening_job():
    """定时任务回调"""
    if not is_trading_day():
        logger.info("今日非交易日，跳过定时筛选")
        return

    global _running_task
    engine = get_engine()

    if _running_task and _running_task.is_alive():
        logger.warning("上一次筛选仍在运行，跳过本次定时触发")
        return

    logger.info(f"定时筛选开始 {datetime.now()}")
    _running_task = threading.Thread(target=engine.run, daemon=True)
    _running_task.start()


def start_scheduler():
    """启动后台调度器"""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    # 周一至周五 14:30 触发
    _scheduler.add_job(
        _screening_job,
        CronTrigger(day_of_week="mon-fri", hour=14, minute=30),
        id="daily_screening",
        name="每日股票筛选",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("定时调度器已启动 (周一至周五 14:30)")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("定时调度器已停止")
