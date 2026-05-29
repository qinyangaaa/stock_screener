"""筛选引擎 — 两级过滤 + 综合评分"""

import logging
import time
import uuid
from datetime import datetime, date
from typing import Optional

from config import strategy_config as cfg, app_config
from fetcher import AkshareFetcher, DFCFetcher, SinaFetcher, BaseFetcher
from strategy.rules import (
    rule1_change_pct, rule2_volume_ratio, rule3_turnover, rule4_market_cap,
    rule5_step_volume, rule6_ma_trend_and_chip, rule7_intraday_strength,
    rule8_late_session_signal,
)
from strategy.scorer import compute_scores
from models.database import (
    save_screening_run, update_screening_run, save_recommendations,
    save_screening_details,
)

logger = logging.getLogger("STOCK_SCREENER")


class ScreeningEngine:
    """选股筛选引擎"""

    def __init__(self):
        self.task_id: Optional[str] = None
        self.run_id: Optional[int] = None
        self._progress: dict = {"stage": "idle", "msg": "", "percent": 0}
        self._cancelled = False

    @property
    def progress(self) -> dict:
        return dict(self._progress)

    def cancel(self):
        self._cancelled = True

    def _get_fetcher(self) -> BaseFetcher:
        if app_config.data_source == "dfcf":
            return DFCFetcher()
        elif app_config.data_source == "sina":
            return SinaFetcher()
        return AkshareFetcher()

    def run(self) -> dict:
        """执行完整筛选流程，返回结果摘要"""
        self.task_id = uuid.uuid4().hex[:12]
        self._cancelled = False
        self.run_id = save_screening_run(self.task_id, "running")
        fetcher = self._get_fetcher()

        result = {
            "task_id": self.task_id,
            "date": date.today().isoformat(),
            "total_stocks": 0,
            "stage1_passed": 0,
            "stage2_passed": 0,
            "recommendations": [],
        }

        try:
            # ========== 第一级过滤 ==========
            self._progress = {"stage": "stage1", "msg": "获取全A股实时行情...", "percent": 5}
            quotes = fetcher.fetch_spot_all()
            if not quotes:
                raise RuntimeError("获取实时行情失败，请检查网络或数据源")

            result["total_stocks"] = len(quotes)
            self._progress["msg"] = f"获取 {len(quotes)} 只股票实时行情"
            self._progress["percent"] = 10

            # 判断极端行情
            up_count = sum(1 for q in quotes if q.change_pct > 0)
            down_count = sum(1 for q in quotes if q.change_pct < 0)
            total = len(quotes)
            up_ratio = up_count / total if total > 0 else 0
            down_ratio = down_count / total if total > 0 else 0
            is_extreme = up_ratio > cfg.extreme_market_ratio or down_ratio > cfg.extreme_market_ratio

            # 规则 1-4 批量过滤（记录每只股票各规则的通过/失败详情）
            stage1_candidates = []
            s1_rule_fails = {"rule1_change_pct": 0, "rule2_volume_ratio": 0,
                             "rule3_turnover": 0, "rule4_market_cap": 0}
            s1_failed_samples = {"rule1_change_pct": [], "rule2_volume_ratio": [],
                                 "rule3_turnover": [], "rule4_market_cap": []}
            max_samples_per_rule = 30

            for q in quotes:
                if self._cancelled:
                    return result
                ok1, d1 = rule1_change_pct(q, is_extreme)
                ok2, d2 = rule2_volume_ratio(q)
                ok3, d3 = rule3_turnover(q)
                ok4, d4 = rule4_market_cap(q)

                if not ok1:
                    s1_rule_fails["rule1_change_pct"] += 1
                    if len(s1_failed_samples["rule1_change_pct"]) < max_samples_per_rule:
                        s1_failed_samples["rule1_change_pct"].append({
                            "code": q.code, "name": q.name,
                            "change_pct": q.change_pct, "detail": d1,
                        })
                if not ok2:
                    s1_rule_fails["rule2_volume_ratio"] += 1
                    if len(s1_failed_samples["rule2_volume_ratio"]) < max_samples_per_rule:
                        s1_failed_samples["rule2_volume_ratio"].append({
                            "code": q.code, "name": q.name,
                            "volume_ratio": q.volume_ratio, "detail": d2,
                        })
                if not ok3:
                    s1_rule_fails["rule3_turnover"] += 1
                    if len(s1_failed_samples["rule3_turnover"]) < max_samples_per_rule:
                        s1_failed_samples["rule3_turnover"].append({
                            "code": q.code, "name": q.name,
                            "turnover": q.turnover, "detail": d3,
                        })
                if not ok4:
                    s1_rule_fails["rule4_market_cap"] += 1
                    if len(s1_failed_samples["rule4_market_cap"]) < max_samples_per_rule:
                        s1_failed_samples["rule4_market_cap"].append({
                            "code": q.code, "name": q.name,
                            "market_cap": q.market_cap, "detail": d4,
                        })

                if all([ok1, ok2, ok3, ok4]):
                    stage1_candidates.append(q)

            # 按量比降序排列
            stage1_candidates.sort(key=lambda q: q.volume_ratio, reverse=True)
            result["stage1_passed"] = len(stage1_candidates)
            update_screening_run(self.run_id, passed_stage1=len(stage1_candidates))
            self._progress["percent"] = 20

            # ========== 第二级过滤 ==========
            if not stage1_candidates:
                details = {
                    "total_stocks": result["total_stocks"],
                    "stage1": {
                        "passed": 0,
                        "passed_stocks": [],
                        "rule_fails": s1_rule_fails,
                        "failed_samples": s1_failed_samples,
                        "is_extreme": is_extreme,
                    },
                    "stage2": {"passed": 0, "rule_fails": {}, "candidates": [], "failed": []},
                }
                save_screening_details(self.run_id, details)
                self._finish_run("completed", result, 0)
                return result

            # 预取指数分时数据
            self._progress["msg"] = "获取大盘分时数据..."
            index_bars = fetcher.fetch_index_minute_bars()

            stage2_candidates = []
            stage2_failed = []  # 记录进入二级但未全部通过的个股详情
            total_s1 = len(stage1_candidates)
            fail_stats = {"no_data": 0, "rule5": 0, "rule6": 0, "rule7": 0, "rule8": 0}
            for idx, quote in enumerate(stage1_candidates):
                if self._cancelled:
                    break

                pct = 20 + int((idx / total_s1) * 60)
                self._progress = {
                    "stage": "stage2",
                    "msg": f"分析候选股 {idx+1}/{total_s1}: {quote.name}({quote.code})",
                    "percent": pct,
                }

                rule_results = {}

                # 获取分钟K线
                minute_bars = fetcher.fetch_minute_bars(quote.code)
                if len(minute_bars) < 6:
                    fail_stats["no_data"] += 1
                    stage2_failed.append({
                        "code": quote.code, "name": quote.name,
                        "change_pct": quote.change_pct,
                        "volume_ratio": quote.volume_ratio,
                        "turnover": quote.turnover,
                        "market_cap": quote.market_cap,
                        "failed_rule": "no_data",
                        "rule_results": {"rule5": {"passed": False, "detail": "分钟K线数据不足"}},
                    })
                    continue
                time.sleep(0.05)

                # 规则 5: 成交量台阶式上升
                ok5, d5 = rule5_step_volume(minute_bars)
                rule_results["rule5"] = {"passed": ok5, "detail": d5}
                if not ok5:
                    fail_stats["rule5"] += 1
                    stage2_failed.append({
                        "code": quote.code, "name": quote.name,
                        "change_pct": quote.change_pct,
                        "volume_ratio": quote.volume_ratio,
                        "turnover": quote.turnover,
                        "market_cap": quote.market_cap,
                        "failed_rule": "rule5_step_volume",
                        "rule_results": {k: {"passed": v["passed"], "detail": v["detail"]}
                                         for k, v in rule_results.items()},
                    })
                    continue

                # 获取日K线
                daily_bars = fetcher.fetch_daily_bars(quote.code, 60)

                # 获取筹码分布
                chip = fetcher.fetch_chip_distribution(quote.code)

                # 规则 6: 多头排列 + 套牢盘
                ok6, d6 = rule6_ma_trend_and_chip(daily_bars, chip, quote.latest_price)
                rule_results["rule6"] = {"passed": ok6, "detail": d6}
                if not ok6:
                    fail_stats["rule6"] += 1
                    stage2_failed.append({
                        "code": quote.code, "name": quote.name,
                        "change_pct": quote.change_pct,
                        "volume_ratio": quote.volume_ratio,
                        "turnover": quote.turnover,
                        "market_cap": quote.market_cap,
                        "failed_rule": "rule6_ma_chip",
                        "rule_results": {k: {"passed": v["passed"], "detail": v["detail"]}
                                         for k, v in rule_results.items()},
                    })
                    continue

                # 规则 7: 分时强度
                ok7, d7 = rule7_intraday_strength(minute_bars, index_bars, quote.change_pct)
                rule_results["rule7"] = {"passed": ok7, "detail": d7}
                if not ok7:
                    fail_stats["rule7"] += 1
                    stage2_failed.append({
                        "code": quote.code, "name": quote.name,
                        "change_pct": quote.change_pct,
                        "volume_ratio": quote.volume_ratio,
                        "turnover": quote.turnover,
                        "market_cap": quote.market_cap,
                        "failed_rule": "rule7_intraday",
                        "rule_results": {k: {"passed": v["passed"], "detail": v["detail"]}
                                         for k, v in rule_results.items()},
                    })
                    continue

                # 规则 8: 尾盘信号
                ok8, d8 = rule8_late_session_signal(minute_bars)
                rule_results["rule8"] = {"passed": ok8, "detail": d8}
                if not ok8:
                    fail_stats["rule8"] += 1
                    stage2_failed.append({
                        "code": quote.code, "name": quote.name,
                        "change_pct": quote.change_pct,
                        "volume_ratio": quote.volume_ratio,
                        "turnover": quote.turnover,
                        "market_cap": quote.market_cap,
                        "failed_rule": "rule8_late_signal",
                        "rule_results": {k: {"passed": v["passed"], "detail": v["detail"]}
                                         for k, v in rule_results.items()},
                    })
                    continue

                # 全部通过
                above_count = sum(1 for b in minute_bars if b.close > b.avg_price and b.avg_price > 0)
                intraday_ratio = above_count / len(minute_bars) if minute_bars else 0.7

                ma_conditions_met = 0
                if daily_bars and len(daily_bars) >= 60:
                    import numpy as np
                    closes = np.array([b.close for b in daily_bars])
                    mas = {p: closes[-p:].mean() for p in cfg.ma_periods}
                    pairs = list(cfg.ma_periods)
                    for i in range(len(pairs) - 1):
                        if mas[pairs[i]] > mas[pairs[i + 1]]:
                            ma_conditions_met += 1
                else:
                    ma_conditions_met = 3

                late_signal_strength = 1.0 if ok8 else 0.5

                stage2_candidates.append({
                    "quote": quote,
                    "rule_results": rule_results,
                    "intraday_ratio": intraday_ratio,
                    "ma_conditions_met": ma_conditions_met,
                    "late_signal_strength": late_signal_strength,
                })

                time.sleep(0.1)

            logger.info(f"二级过滤失败分布: {fail_stats}")

            # 汇总筛选明细
            stage1_passed_stocks = [
                {
                    "code": q.code, "name": q.name,
                    "change_pct": q.change_pct,
                    "volume_ratio": q.volume_ratio,
                    "turnover": q.turnover,
                    "market_cap": q.market_cap,
                }
                for q in stage1_candidates
            ]
            details = {
                "total_stocks": result["total_stocks"],
                "stage1": {
                    "passed": len(stage1_candidates),
                    "passed_stocks": stage1_passed_stocks,
                    "rule_fails": s1_rule_fails,
                    "failed_samples": s1_failed_samples,
                    "is_extreme": is_extreme,
                },
                "stage2": {
                    "passed": len(stage2_candidates),
                    "rule_fails": fail_stats,
                    "candidates": [
                        {
                            "code": q.code, "name": q.name,
                            "change_pct": q.change_pct,
                            "volume_ratio": q.volume_ratio,
                            "turnover": q.turnover,
                            "market_cap": q.market_cap,
                            "rule_results": {k: {"passed": v["passed"], "detail": v["detail"]}
                                             for k, v in item["rule_results"].items()},
                        }
                        for item in stage2_candidates
                    ],
                    "failed": stage2_failed,
                },
            }
            save_screening_details(self.run_id, details)

            result["stage2_passed"] = len(stage2_candidates)
            result["fail_stats"] = fail_stats
            self._progress["percent"] = 85
            self._progress["msg"] = f"第二级过滤完成，{len(stage2_candidates)} 只候选股进入评分"

            # ========== 综合评分 ==========
            if not stage2_candidates:
                self._finish_run("completed", result, 0)
                return result

            ranked = compute_scores(stage2_candidates)

            # 组装输出
            recommendations = []
            for c in ranked:
                q = c["quote"]
                rule_details = {"stage1": "passed"}
                for rk, rv in c.get("rule_results", {}).items():
                    rule_details[rk] = rv

                recommendations.append({
                    "rank": c["rank"],
                    "code": q.code,
                    "name": q.name,
                    "score": c["score"],
                    "signal": c["signal"],
                    "change_pct": q.change_pct,
                    "volume_ratio": q.volume_ratio,
                    "turnover": q.turnover,
                    "market_cap": q.market_cap,
                    "rule_details": rule_details,
                })

            self._progress["msg"] = "保存结果..."
            save_recommendations(self.run_id, recommendations, result["date"])
            result["recommendations"] = recommendations
            self._finish_run("completed", result, len(recommendations))
            self._progress = {"stage": "done", "msg": f"筛选完成，推荐 {len(recommendations)} 只股票", "percent": 100}

            return result

        except Exception as e:
            logger.exception(f"Screening failed: {e}")
            self._finish_run("failed", result, 0, error=str(e))
            self._progress = {"stage": "error", "msg": str(e), "percent": 0}
            result["error"] = str(e)
            return result

    def _finish_run(self, status: str, result: dict, passed_all: int, error: str = None):
        update_kwargs = {
            "status": status,
            "finished_at": datetime.now().isoformat(),
            "total_stocks": result["total_stocks"],
            "passed_stage1": result["stage1_passed"],
            "passed_all": passed_all,
        }
        if error:
            update_kwargs["error"] = error
        update_screening_run(self.run_id, **update_kwargs)
