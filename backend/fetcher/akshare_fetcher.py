"""akshare 数据获取实现"""

import akshare as ak
import pandas as pd
from typing import Optional
from datetime import datetime

from .base import BaseFetcher, SpotQuote, MinuteBar, DailyBar, ChipDistribution


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if pd.notna(val) else default
    except (ValueError, TypeError):
        return default


class AkshareFetcher(BaseFetcher):

    def fetch_spot_all(self) -> list[SpotQuote]:
        df = ak.stock_zh_a_spot_em()
        results = []
        for _, row in df.iterrows():
            results.append(SpotQuote(
                code=row["代码"],
                name=row["名称"],
                change_pct=_safe_float(row.get("涨跌幅", 0)),
                volume_ratio=_safe_float(row.get("量比", 0)),
                turnover=_safe_float(row.get("换手率", 0)),
                market_cap=_safe_float(row.get("流通市值", 0)) / 1e8,  # 元→亿
                latest_price=_safe_float(row.get("最新价", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                open=_safe_float(row.get("今开", 0)),
            ))
        return results

    def fetch_minute_bars(self, code: str, period: str = "5") -> list[MinuteBar]:
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=code, period=period, adjust="")
        except Exception:
            return []
        if df is None or df.empty:
            return []

        # 计算分时均线（累计成交额/累计成交量）
        cumulative_amount = 0.0
        cumulative_volume = 0.0

        results = []
        for _, row in df.iterrows():
            vol = _safe_float(row.get("成交量", 0))
            amt = _safe_float(row.get("成交额", 0))
            cumulative_volume += vol
            cumulative_amount += amt
            avg_price = cumulative_amount / cumulative_volume if cumulative_volume > 0 else 0

            time_str = str(row.get("时间", ""))
            if len(time_str) >= 5:
                time_str = time_str[-5:]  # 取 HH:MM 部分

            results.append(MinuteBar(
                time=time_str,
                open=_safe_float(row.get("开盘", 0)),
                close=_safe_float(row.get("收盘", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                volume=vol,
                avg_price=avg_price,
            ))
        return results

    def fetch_daily_bars(self, code: str, days: int = 60) -> list[DailyBar]:
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        except Exception:
            return []
        if df is None or df.empty:
            return []

        df = df.tail(days)
        results = []
        for _, row in df.iterrows():
            results.append(DailyBar(
                date=str(row["日期"])[:10],
                open=_safe_float(row["开盘"]),
                close=_safe_float(row["收盘"]),
                high=_safe_float(row["最高"]),
                low=_safe_float(row["最低"]),
                volume=_safe_float(row["成交量"]),
            ))
        return results

    def fetch_chip_distribution(self, code: str) -> Optional[ChipDistribution]:
        """通过 akshare 获取筹码分布"""
        try:
            df = ak.stock_cyq_em(symbol=code, adjust="")
        except Exception:
            return None
        if df is None or df.empty:
            return None

        latest = df.iloc[-1]
        avg_cost = _safe_float(latest.get("平均成本", 0))
        profit_ratio = _safe_float(latest.get("获利比例", 0)) / 100.0
        trapped_ratio = 1.0 - profit_ratio
        return ChipDistribution(
            avg_cost=avg_cost,
            trapped_ratio=trapped_ratio,
            profit_ratio=profit_ratio,
        )

    def fetch_index_minute_bars(self, index_code: str = "sh000001", period: str = "5") -> list[MinuteBar]:
        """获取上证指数分钟K线"""
        try:
            df = ak.stock_zh_index_hist_min_em(symbol=index_code, period=period)
        except Exception:
            return []
        if df is None or df.empty:
            return []

        cumulative_amount = 0.0
        cumulative_volume = 0.0
        results = []
        for _, row in df.iterrows():
            vol = _safe_float(row.get("成交量", 0))
            amt = _safe_float(row.get("成交额", 0))
            cumulative_volume += vol
            cumulative_amount += amt
            avg_price = cumulative_amount / cumulative_volume if cumulative_volume > 0 else 0

            time_str = str(row.get("时间", ""))
            if len(time_str) >= 5:
                time_str = time_str[-5:]

            results.append(MinuteBar(
                time=time_str,
                open=_safe_float(row.get("开盘", 0)),
                close=_safe_float(row.get("收盘", 0)),
                high=_safe_float(row.get("最高", 0)),
                low=_safe_float(row.get("最低", 0)),
                volume=vol,
                avg_price=avg_price,
            ))
        return results
