"""综合评分模块 — 加权打分 + 排名"""

from typing import Optional

from config import strategy_config as cfg
from fetcher.base import SpotQuote, MinuteBar


def compute_scores(candidates: list[dict]) -> list[dict]:
    """
    对通过全部规则的候选股综合打分。
    candidates: list of dict，每项包含 quote、bars 等原始数据和 rule_results。
    返回按 score 降序排列的列表，附加 rank 和 signal。
    """
    if not candidates:
        return []

    n = len(candidates)

    # 提取各因子原始值
    volume_ratios = [c["quote"].volume_ratio for c in candidates]
    change_pcts = [c["quote"].change_pct for c in candidates]
    turnovers = [c["quote"].turnover for c in candidates]
    intraday_ratios = [c.get("intraday_ratio", 0.7) for c in candidates]
    ma_conditions = [c.get("ma_conditions_met", 3) for c in candidates]
    late_signals = [c.get("late_signal_strength", 0.5) for c in candidates]

    for i, c in enumerate(candidates):
        score = 0.0

        # 1. 量比排名分 (25%)
        score += cfg.score_volume_ratio_weight * _normalize_rank(
            volume_ratios[i], volume_ratios, higher_better=True
        )

        # 2. 涨幅合理性 (20%) — 越接近 4% 越好
        score += cfg.score_change_pct_weight * _proximity_score(
            change_pcts[i], target=4.0, floor=cfg.change_pct_min, ceil=cfg.change_pct_max
        )

        # 3. 换手率适中 (15%) — 越接近 12% 越好
        score += cfg.score_turnover_weight * _proximity_score(
            turnovers[i], target=12.0, floor=cfg.turnover_min, ceil=cfg.turnover_max
        )

        # 4. 均线多头强度 (15%) — 3/4 = 0.75, 4/4 = 1.0
        ma_score = ma_conditions[i] / len(cfg.ma_periods)
        score += cfg.score_ma_strength_weight * ma_score

        # 5. 分时强度 (15%)
        score += cfg.score_intraday_weight * _normalize_rank(
            intraday_ratios[i], intraday_ratios, higher_better=True
        )

        # 6. 尾盘信号 (10%)
        score += cfg.score_late_signal_weight * late_signals[i]

        c["score"] = round(score * 100, 1)

    # 按分数降序排列
    candidates.sort(key=lambda x: x["score"], reverse=True)

    for rank, c in enumerate(candidates, 1):
        c["rank"] = rank
        if rank <= cfg.top_n_strong:
            c["signal"] = "strong_buy"
        elif c["score"] >= 60:
            c["signal"] = "buy"
        else:
            c["signal"] = "watch"

    return candidates


def _normalize_rank(value: float, all_values: list[float], higher_better: bool = True) -> float:
    """Min-Max 归一化到 [0, 1]"""
    if not all_values or max(all_values) == min(all_values):
        return 0.5
    mn, mx = min(all_values), max(all_values)
    if higher_better:
        return (value - mn) / (mx - mn)
    else:
        return (mx - value) / (mx - mn)


def _proximity_score(value: float, target: float, floor: float, ceil: float) -> float:
    """距离目标值越近分数越高，线性衰减到边界为0"""
    max_dist = max(target - floor, ceil - target)
    if max_dist <= 0:
        return 0.5
    dist = abs(value - target)
    return max(0.0, 1.0 - dist / max_dist)
