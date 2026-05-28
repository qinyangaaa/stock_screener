"""策略参数配置和全局设置"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class StrategyConfig:
    """选股策略参数，集中管理所有可调阈值"""

    # 涨幅区间 (常规行情)
    change_pct_min: float = 3.0
    change_pct_max: float = 5.0
    # 极端行情放宽区间（全市场涨跌家数比 > 阈值时启用）
    extreme_market_ratio: float = 0.7  # 上涨/下跌占比 > 70% 视为极端
    extreme_change_pct_min: float = 2.0
    extreme_change_pct_max: float = 7.0

    # 量比
    volume_ratio_min: float = 1.0

    # 换手率
    turnover_min: float = 5.0
    turnover_max: float = 20.0

    # 流通市值（亿）
    market_cap_min: float = 100
    market_cap_max: float = 500

    # 成交量台阶式上升
    step_volume_window: int = 6       # 最后N根5分钟K线
    step_volume_recent: int = 3       # 最近N根要求高于前一半均值
    step_volume_min_recent_pass: int = 2  # 最近N根中至少M根达标

    # K线多头排列
    ma_periods: Tuple[int, int, int, int] = (5, 10, 20, 60)
    ma_conditions_min: int = 3        # 至少满足几组 MA 大小关系

    # 套牢盘
    trapped_chip_ratio: float = 0.6   # 上方筹码 > 60% 意味着上方抛压大 → 避开
    # 实际含义更正：上方套牢盘多 = 压力大，应该避开。所以如果 > 60% 则剔除
    trapped_chip_max: float = 0.6     # 上方套牢盘比例上限，超过则剔除

    # 分时强度
    intraday_above_avg_ratio: float = 0.7  # 站上黄线的K线占比下限
    index_outperform: bool = True          # 必须强于大盘

    # 尾盘信号 (14:30后)
    late_session_start: str = "14:30"
    pullback_to_avg_threshold: float = 0.005  # 回踩距黄线 ≤ 0.5%
    new_high_lookback: str = "14:30"         # 从此时开始看新高

    # 评分权重
    score_volume_ratio_weight: float = 0.25
    score_change_pct_weight: float = 0.20
    score_turnover_weight: float = 0.15
    score_ma_strength_weight: float = 0.15
    score_intraday_weight: float = 0.15
    score_late_signal_weight: float = 0.10

    # 推荐
    top_n_strong: int = 5  # 强烈推荐前 N 只


@dataclass
class AppConfig:
    """应用全局配置"""
    port: int = 8038
    host: str = "0.0.0.0"
    database_path: str = "stock_screener.db"
    data_source: str = "sina"  # "sina" | "akshare" | "dfcf"
    debug: bool = True


strategy_config = StrategyConfig()
app_config = AppConfig()
