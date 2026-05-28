"""选股策略 8 条规则的独立实现"""

import numpy as np
from typing import Tuple, Optional

from config import strategy_config as cfg
from fetcher.base import SpotQuote, MinuteBar, DailyBar, ChipDistribution


def rule1_change_pct(quote: SpotQuote, is_extreme: bool = False) -> Tuple[bool, str]:
    """涨幅 3%-5%，极端行情放宽到 2%-7%"""
    mn = cfg.extreme_change_pct_min if is_extreme else cfg.change_pct_min
    mx = cfg.extreme_change_pct_max if is_extreme else cfg.change_pct_max
    ok = mn <= quote.change_pct <= mx
    detail = f"涨幅 {quote.change_pct:.2f}% [需 {mn}%-{mx}%]"
    return ok, detail


def rule2_volume_ratio(quote: SpotQuote) -> Tuple[bool, str]:
    """量比 >= 1"""
    ok = quote.volume_ratio >= cfg.volume_ratio_min
    detail = f"量比 {quote.volume_ratio:.2f} [需 >= {cfg.volume_ratio_min}]"
    return ok, detail


def rule3_turnover(quote: SpotQuote) -> Tuple[bool, str]:
    """换手率 5%-20%"""
    ok = cfg.turnover_min <= quote.turnover <= cfg.turnover_max
    detail = f"换手率 {quote.turnover:.2f}% [需 {cfg.turnover_min}%-{cfg.turnover_max}%]"
    return ok, detail


def rule4_market_cap(quote: SpotQuote) -> Tuple[bool, str]:
    """流通市值 100亿-500亿"""
    ok = cfg.market_cap_min <= quote.market_cap <= cfg.market_cap_max
    detail = f"流通市值 {quote.market_cap:.1f}亿 [需 {cfg.market_cap_min}-{cfg.market_cap_max}亿]"
    return ok, detail


def rule5_step_volume(bars: list[MinuteBar]) -> Tuple[bool, str]:
    """最后 6 根 5 分钟 K 线成交量台阶式上升"""
    n = cfg.step_volume_window
    if len(bars) < n:
        return False, f"5分钟K线不足 {len(bars)} 根 (需 >= {n})"

    recent_bars = bars[-n:]
    volumes = np.array([b.volume for b in recent_bars])

    # 线性回归斜率必须为正
    x = np.arange(n)
    slope = np.polyfit(x, volumes, 1)[0]
    if slope <= 0:
        return False, f"成交量斜率 {slope:.4f} <= 0 (需 > 0)"

    # 最近 cfg.step_volume_recent 根中至少 cfg.step_volume_min_recent_pass 根 > 前一半均值
    first_half_mean = volumes[:n//2].mean()
    recent_count = sum(1 for v in volumes[-cfg.step_volume_recent:] if v > first_half_mean)
    ok = recent_count >= cfg.step_volume_min_recent_pass
    detail = (
        f"成交量斜率 {slope:.4f}, 前一半均值 {first_half_mean:.1f}, "
        f"后{cfg.step_volume_recent}根中{recent_count}根超过均值 [需 >= {cfg.step_volume_min_recent_pass}]"
    )
    return ok, detail


def rule6_ma_trend_and_chip(
    daily_bars: list[DailyBar],
    chip: Optional[ChipDistribution],
    current_price: float,
) -> Tuple[bool, str]:
    """K线多头排列 + 上方套牢盘检查"""
    if len(daily_bars) < max(cfg.ma_periods):
        return False, f"日K线不足 {len(daily_bars)} 根 (需 >= {max(cfg.ma_periods)})"

    closes = np.array([b.close for b in daily_bars])

    # 计算均线
    mas = {}
    for p in cfg.ma_periods:
        mas[p] = closes[-p:].mean()

    # 检查 MA5 > MA10 > MA20 > MA60
    conditions_met = 0
    ma_details = []
    pairs = list(cfg.ma_periods)
    for i in range(len(pairs) - 1):
        short_p, long_p = pairs[i], pairs[i + 1]
        if mas[short_p] > mas[long_p]:
            conditions_met += 1
            ma_details.append(f"MA{short_p}({mas[short_p]:.2f}) > MA{long_p}({mas[long_p]:.2f}) ✓")
        else:
            ma_details.append(f"MA{short_p}({mas[short_p]:.2f}) > MA{long_p}({mas[long_p]:.2f}) ✗")

    ma_ok = conditions_met >= cfg.ma_conditions_min

    # 上方套牢盘检查：上方套牢盘比例 > 阈值意味着上方抛压大 → 剔除
    if chip is not None:
        chip_ok = chip.trapped_ratio <= cfg.trapped_chip_max
        chip_detail = f"上方套牢盘 {chip.trapped_ratio:.1%} [需 <= {cfg.trapped_chip_max:.0%}]"
    else:
        chip_ok = True  # 无数据时不剔除
        chip_detail = "无筹码数据，跳过"

    ok = ma_ok and chip_ok
    detail = f"多头条件 {conditions_met}/{len(pairs)} [需 >= {cfg.ma_conditions_min}]; {chip_detail}"
    return ok, detail


def rule7_intraday_strength(
    bars: list[MinuteBar],
    index_bars: list[MinuteBar],
    stock_change: float,
) -> Tuple[bool, str]:
    """分时图：股价全天站黄线上 + 强于大盘"""
    if len(bars) < 3:
        return False, f"分时数据不足 ({len(bars)} 根)"

    # 站上黄线（收盘价 > 分时均线）的占比
    above_count = sum(1 for b in bars if b.close > b.avg_price and b.avg_price > 0)
    above_ratio = above_count / len(bars)

    # 个股 vs 大盘涨幅
    if index_bars and len(index_bars) >= 2:
        index_open = index_bars[0].open
        index_close = index_bars[-1].close
        index_change = (index_close - index_open) / index_open * 100 if index_open > 0 else 0
    else:
        index_change = 0
        above_ratio = above_count / len(bars)

    intraday_ok = above_ratio >= cfg.intraday_above_avg_ratio
    outperform_ok = stock_change >= index_change if cfg.index_outperform else True

    detail = (
        f"站上黄线占比 {above_ratio:.1%} [需 >= {cfg.intraday_above_avg_ratio:.0%}]; "
        f"个股涨幅 {stock_change:.2f}% vs 大盘 {index_change:.2f}%"
    )
    return intraday_ok and outperform_ok, detail


def rule8_late_session_signal(bars: list[MinuteBar]) -> Tuple[bool, str]:
    """尾盘（14:30后）创新高 + 回踩黄线不破"""
    # 筛选 14:30 之后的 K 线
    late_bars = [b for b in bars if b.time >= cfg.late_session_start]
    if len(late_bars) < 3:
        return False, f"14:30后K线不足 ({len(late_bars)} 根)"

    # 所有K线中找日内最高价
    all_highs = [b.high for b in bars]
    day_high = max(all_highs) if all_highs else 0

    # 14:30 后是否出现日内新高
    late_highs = [b.high for b in late_bars]
    if max(late_highs) < day_high * 0.998:  # 允许微小误差
        return False, "14:30后未见日内新高"

    # 找到新高后，检查是否有回踩黄线不破
    high_idx = None
    for i, b in enumerate(late_bars):
        if b.high >= day_high * 0.998:
            high_idx = i
            break

    if high_idx is None:
        return False, "未定位到新高位置"

    # 新高之后检查回踩
    after_high = late_bars[high_idx:]
    pullback_found = False
    for b in after_high:
        if b.avg_price > 0 and b.low <= b.avg_price * (1 + cfg.pullback_to_avg_threshold):
            pullback_found = True
            # 关键：回踩不能跌破黄线
            if b.low < b.avg_price:
                return False, f"回踩时跌破黄线 (low={b.low:.2f} < avg={b.avg_price:.2f})"
            break

    if pullback_found:
        return True, "14:30后创新高且回踩黄线不破 ✓"
    else:
        return False, "14:30后未出现回踩黄线信号"
