"""交易日历工具 — 判断某日是否为 A 股交易日"""

import logging
from datetime import date, datetime, timedelta
from functools import lru_cache

logger = logging.getLogger("TRADING_CALENDAR")

_cache_date = None
_cache_result = None


def is_trading_day(check_date: date = None) -> bool:
    """判断是否为 A 股交易日，带内存缓存"""
    global _cache_date, _cache_result
    if check_date is None:
        check_date = date.today()

    if _cache_date == check_date:
        return _cache_result

    trading = _check_trading_day(check_date)
    _cache_date = check_date
    _cache_result = trading
    return trading


def _check_trading_day(check_date: date) -> bool:
    """实际判断逻辑：先基本判断，再查交易日历"""
    # 周末一定不是交易日
    if check_date.weekday() >= 5:
        return False

    try:
        import akshare as ak
        df = ak.tool_trade_date_hist_sina()
        trade_dates = set(df["trade_date"].astype(str).values)
        date_str = check_date.isoformat().replace("-", "")
        if date_str in trade_dates:
            return True
        # 日期不在日历中（可能是未来日期），回退到周一到周五判断
        logger.info(f"{check_date} 不在交易日历中，使用周一到周五作为默认")
        return check_date.weekday() < 5
    except Exception as e:
        logger.warning(f"交易日历查询失败 ({e})，使用周一到周五作为默认")
        return check_date.weekday() < 5


def next_trading_day(after: date = None) -> date:
    """获取下一个交易日"""
    if after is None:
        after = date.today()
    d = after + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def prev_trading_day(before: date = None) -> date:
    """获取上一个交易日"""
    if before is None:
        before = date.today()
    d = before - timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d
