"""数据获取抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SpotQuote:
    """实时行情快照"""
    code: str
    name: str
    change_pct: float      # 涨跌幅 %
    volume_ratio: float    # 量比
    turnover: float        # 换手率 %
    market_cap: float      # 流通市值（亿）
    latest_price: float    # 最新价
    high: float            # 今日最高
    low: float             # 今日最低
    open: float            # 开盘价


@dataclass
class MinuteBar:
    """5分钟K线"""
    time: str              # HH:MM
    open: float
    close: float
    high: float
    low: float
    volume: float
    avg_price: float       # 分时均线（黄线）= 累计成交额/累计成交量


@dataclass
class DailyBar:
    """日K线"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float


@dataclass
class ChipDistribution:
    """筹码分布"""
    avg_cost: float        # 平均成本
    trapped_ratio: float   # 上方套牢盘比例（成本 > 现价）
    profit_ratio: float    # 获利盘比例（成本 < 现价）


class BaseFetcher(ABC):
    """数据获取抽象基类"""

    @abstractmethod
    def fetch_spot_all(self) -> list[SpotQuote]:
        """获取全 A 股实时行情"""
        ...

    @abstractmethod
    def fetch_minute_bars(self, code: str, period: str = "5") -> list[MinuteBar]:
        """获取单只股票当日分钟K线"""
        ...

    @abstractmethod
    def fetch_daily_bars(self, code: str, days: int = 60) -> list[DailyBar]:
        """获取单只股票日K线"""
        ...

    @abstractmethod
    def fetch_chip_distribution(self, code: str) -> Optional[ChipDistribution]:
        """获取筹码分布"""
        ...

    @abstractmethod
    def fetch_index_minute_bars(self, index_code: str = "sh000001", period: str = "5") -> list[MinuteBar]:
        """获取指数分钟K线（默认上证指数）"""
        ...
