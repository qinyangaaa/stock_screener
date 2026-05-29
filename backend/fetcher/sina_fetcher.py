"""Sina + Tencent 混合数据获取 — 高效的批量行情 + 个股详情"""

import re
import time
import requests
from typing import Optional

import akshare as ak

from .base import BaseFetcher, SpotQuote, MinuteBar, DailyBar, ChipDistribution


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn",
}

# 绕过系统代理（127.0.0.1:7897 会拦截 EastMoney API）
_NO_PROXY = {"http": None, "https": None}

# Cache for stock codes
_CODE_CACHE: Optional[list[tuple[str, str]]] = None


def _get_stock_codes() -> list[tuple[str, str]]:
    """获取全 A 股代码和名称，带缓存，排除指定板块"""
    global _CODE_CACHE
    if _CODE_CACHE is not None:
        return _CODE_CACHE
    try:
        df = ak.stock_info_a_code_name()
        codes = [(row["code"], row["name"]) for _, row in df.iterrows()]
        _CODE_CACHE = codes
        return codes
    except Exception:
        return []


def _filter_codes(codes: list[tuple[str, str]], exclude_prefixes: list[str]) -> list[tuple[str, str]]:
    """过滤掉指定板块的股票"""
    if not exclude_prefixes:
        return codes
    return [(c, n) for c, n in codes if not any(c.startswith(p) for p in exclude_prefixes)]


def _sina_code(em_code: str) -> str:
    """东方财富代码转 Sina 代码"""
    if em_code.startswith("6"):
        return f"sh{em_code}"
    return f"sz{em_code}"


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if val and val != "-" else default
    except (ValueError, TypeError):
        return default


def _parse_sina_quote(line: str) -> Optional[SpotQuote]:
    """解析单行 Sina 行情数据"""
    if "=" not in line or '"' not in line:
        return None
    code_part = line.split("=")[0]
    market_code = code_part.split("_")[-1]  # sh600000
    em_code = market_code[2:]  # 600000
    data = line.split('"')[1] if '"' in line else ""
    fields = data.split(",")
    if len(fields) < 10:
        return None

    name = fields[0]
    open_p = _safe_float(fields[1])
    yest_close = _safe_float(fields[2])
    price = _safe_float(fields[3])
    high = _safe_float(fields[4])
    low = _safe_float(fields[5])
    volume = _safe_float(fields[8])       # 成交量（股）
    amount = _safe_float(fields[9])       # 成交额（元）

    # 计算涨跌幅
    change_pct = ((price - yest_close) / yest_close * 100) if yest_close > 0 else 0

    # 量比、换手率、流通市值 需要从腾讯补充
    return SpotQuote(
        code=em_code,
        name=name,
        change_pct=round(change_pct, 2),
        volume_ratio=0,   # 后续腾讯补充
        turnover=0,        # 后续腾讯补充
        market_cap=0,      # 后续腾讯补充
        latest_price=price,
        high=high,
        low=low,
        open=open_p,
    )


def _fetch_tencent_details(codes: list[str]) -> dict[str, dict]:
    """批量获取腾讯行情详情（量比、换手率、流通市值）"""
    if not codes:
        return {}

    result = {}
    batch_size = 50

    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        qt_codes = ",".join(_sina_code(c) for c in batch)
        url = f"http://qt.gtimg.cn/q={qt_codes}"

        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://gu.qq.com",
            }, proxies=_NO_PROXY)
            resp.encoding = "gbk"
        except Exception:
            continue

        for line in resp.text.strip().split("\n"):
            if "=" not in line or '"' not in line:
                continue
            var_name = line.split("=")[0]
            market_code = var_name.split("_")[-1]
            em_code = market_code[2:]
            data = line.split('"')[1]
            fields = data.split("~")
            if len(fields) < 50:
                continue

            # 腾讯字段索引：
            # 38: 换手率, 45: 量比, 47: 流通市值（亿）
            result[em_code] = {
                "turnover": _safe_float(fields[38]),
                "volume_ratio": _safe_float(fields[45]),
                "market_cap": _safe_float(fields[47]),  # 单位亿
            }

        time.sleep(0.2)  # batch 间延迟

    return result


class SinaFetcher(BaseFetcher):
    """Sina + Tencent 混合数据获取器"""

    # ── Spot ──────────────────────────────────────────────

    def fetch_spot_all(self) -> list[SpotQuote]:
        codes = _get_stock_codes()
        if not codes:
            return []

        # 过滤掉创业板(300)和科创板(688)等指定板块
        from config import strategy_config
        exclude_str = getattr(strategy_config, "exclude_boards", "")
        if exclude_str:
            exclude_prefixes = [p.strip() for p in exclude_str.split(",") if p.strip()]
            codes = _filter_codes(codes, exclude_prefixes)

        all_quotes = []
        batch_size = 800
        sina_codes = [_sina_code(c) for c, _ in codes]

        for i in range(0, len(sina_codes), batch_size):
            batch = sina_codes[i:i + batch_size]
            url = "http://hq.sinajs.cn/list=" + ",".join(batch)
            try:
                resp = requests.get(url, timeout=30, headers=_HEADERS, proxies=_NO_PROXY)
                resp.encoding = "gbk"
            except Exception:
                continue

            for line in resp.text.strip().split("\n"):
                q = _parse_sina_quote(line)
                if q and q.latest_price > 0:
                    all_quotes.append(q)
            time.sleep(0.3)

        # 批量补充腾讯数据
        valid_codes = [q.code for q in all_quotes if 2 <= abs(q.change_pct) <= 8]
        tx_data = _fetch_tencent_details(valid_codes)
        for q in all_quotes:
            if q.code in tx_data:
                d = tx_data[q.code]
                q.volume_ratio = d["volume_ratio"]
                q.turnover = d["turnover"]
                q.market_cap = d["market_cap"]

        return all_quotes

    # ── Minute K-lines (Sina API) ─────────────────────────

    def fetch_minute_bars(self, code: str, period: str = "5") -> list[MinuteBar]:
        sc = _sina_code(code)
        url = (
            f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={sc}&scale={period}&datalen=240"
        )
        return self._parse_minute_sina(url)

    def fetch_index_minute_bars(self, index_code: str = "sh000001", period: str = "5") -> list[MinuteBar]:
        url = (
            f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={index_code}&scale={period}&datalen=240"
        )
        return self._parse_minute_sina(url)

    @staticmethod
    def _parse_minute_sina(url: str) -> list[MinuteBar]:
        import json as _json
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            }, proxies={"http": None, "https": None})
            if resp.status_code != 200:
                return []
            raw = resp.text
            # Sina returns JS-like: callback({...}) — extract JSON
            if "(" in raw and raw.endswith(")"):
                raw = raw[raw.index("(") + 1:-1]
            bars = _json.loads(raw)
        except Exception:
            return []

        # 用 (high+low+close)/3 * volume 累计近似 VWAP
        cum_vol = 0.0
        cum_wx_price = 0.0
        results = []
        for bar in bars:
            open_p = _safe_float(bar.get("open"))
            close_p = _safe_float(bar.get("close"))
            high_p = _safe_float(bar.get("high"))
            low_p = _safe_float(bar.get("low"))
            vol = _safe_float(bar.get("volume"))
            tp = (high_p + low_p + close_p) / 3
            cum_wx_price += tp * vol
            cum_vol += vol
            avg_price = cum_wx_price / cum_vol if cum_vol > 0 else 0

            day_str = bar.get("day", "")
            time_str = day_str.split(" ")[-1][:5] if " " in day_str else day_str[-5:]

            results.append(MinuteBar(
                time=time_str,
                open=open_p,
                close=close_p,
                high=high_p,
                low=low_p,
                volume=vol,
                avg_price=avg_price,
            ))
        return results

    # ── Daily K-lines (Sina API) ──────────────────────────

    def fetch_daily_bars(self, code: str, days: int = 60) -> list[DailyBar]:
        import json as _json
        sc = _sina_code(code)
        url = (
            f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"CN_MarketData.getKLineData?symbol={sc}&scale=240&datalen={days}"
        )
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            }, proxies={"http": None, "https": None})
            raw = resp.text
            if "(" in raw and raw.endswith(")"):
                raw = raw[raw.index("(") + 1:-1]
            bars = _json.loads(raw)
        except Exception:
            return []

        results = []
        for bar in bars:
            results.append(DailyBar(
                date=bar.get("day", "")[:10],
                open=_safe_float(bar.get("open")),
                close=_safe_float(bar.get("close")),
                high=_safe_float(bar.get("high")),
                low=_safe_float(bar.get("low")),
                volume=_safe_float(bar.get("volume")),
            ))
        return results

    # ── Chip Distribution ────────────────────────────────

    def fetch_chip_distribution(self, code: str) -> Optional[ChipDistribution]:
        # Sina 无筹码分布接口，返回 None，引擎会跳过此规则
        return None
