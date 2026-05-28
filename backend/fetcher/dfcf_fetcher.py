"""东方财富 API 数据获取 — HTTP 直连，不依赖 akshare"""

import requests
from typing import Optional

from .base import BaseFetcher, SpotQuote, MinuteBar, DailyBar, ChipDistribution


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _get(url: str, timeout: int = 30, retries: int = 2) -> Optional[requests.Response]:
    import time
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=_HEADERS)
            if resp.status_code == 200 and len(resp.text) > 0:
                return resp
            if attempt < retries:
                time.sleep(3)
        except Exception:
            if attempt < retries:
                time.sleep(3)
    return None


class DFCFetcher(BaseFetcher):
    """东方财富数据获取实现 — HTTP 协议"""

    _SPOT_URL = (
        "http://push2.eastmoney.com/api/qt/clist/get"
        "?pn={pn}&pz=100&po=1&np=1&fltt=2&invt=2"
        "&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        "&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21"
    )

    _KLINE_URL = (
        "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        "?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
        "&fields2=f51,f52,f53,f54,f55,f56,f57"
        "&klt={klt}&fqt={fqt}&end=20500101&lmt={lmt}"
    )

    _CYQ_URL = (
        "http://push2his.eastmoney.com/api/qt/stock/cyq/get"
        "?secid={secid}&days=1"
    )

    @staticmethod
    def _secid(code: str) -> str:
        market = 1 if code.startswith("6") else 0
        return f"{market}.{code}"

    # ── Spot ──────────────────────────────────────────────

    def fetch_spot_all(self) -> list[SpotQuote]:
        import time as _time
        results = []
        for pn in range(1, 100):
            url = self._SPOT_URL.format(pn=pn)
            resp = _get(url, timeout=30)
            if resp is None:
                break
            try:
                data = resp.json()
                items = data.get("data", {}).get("diff", [])
            except Exception:
                break
            if not items:
                break
            for row in items:
                results.append(SpotQuote(
                    code=row.get("f12", ""),
                    name=row.get("f14", ""),
                    change_pct=_safe_float(row.get("f3")),
                    volume_ratio=_safe_float(row.get("f10")),
                    turnover=_safe_float(row.get("f8")),
                    market_cap=_safe_float(row.get("f20")) / 1e8,
                    latest_price=_safe_float(row.get("f2")),
                    high=_safe_float(row.get("f15")),
                    low=_safe_float(row.get("f16")),
                    open=_safe_float(row.get("f17")),
                ))
            _time.sleep(0.3)  # 页间延迟，避免被 ban
        return results

    # ── Minute K-lines ────────────────────────────────────

    def fetch_minute_bars(self, code: str, period: str = "5") -> list[MinuteBar]:
        url = self._KLINE_URL.format(
            secid=self._secid(code), klt=period, fqt=0, lmt=240,
        )
        return self._parse_minute(url)

    def fetch_index_minute_bars(self, index_code: str = "sh000001", period: str = "5") -> list[MinuteBar]:
        if index_code == "sh000001":
            secid = "1.000001"
        else:
            secid = f"1.{index_code[2:]}"
        url = self._KLINE_URL.format(secid=secid, klt=period, fqt=0, lmt=240)
        return self._parse_minute(url)

    def _parse_minute(self, url: str) -> list[MinuteBar]:
        resp = _get(url, timeout=15)
        if resp is None:
            return []
        try:
            klines = resp.json().get("data", {}).get("klines", [])
        except Exception:
            return []

        cum_amt = 0.0
        cum_vol = 0.0
        results = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 7:
                continue
            dt_str, open_s, close_s, high_s, low_s, vol_s, amt_s = parts[:7]
            vol = _safe_float(vol_s)
            amt = _safe_float(amt_s)
            cum_vol += vol
            cum_amt += amt
            avg_price = cum_amt / cum_vol if cum_vol > 0 else 0
            time_str = dt_str.split(" ")[-1][:5] if " " in dt_str else dt_str[-5:]
            results.append(MinuteBar(
                time=time_str,
                open=_safe_float(open_s),
                close=_safe_float(close_s),
                high=_safe_float(high_s),
                low=_safe_float(low_s),
                volume=vol,
                avg_price=avg_price,
            ))
        return results

    # ── Daily K-lines ─────────────────────────────────────

    def fetch_daily_bars(self, code: str, days: int = 60) -> list[DailyBar]:
        url = self._KLINE_URL.format(
            secid=self._secid(code), klt=101, fqt=1, lmt=days,
        )
        resp = _get(url, timeout=15)
        if resp is None:
            return []
        try:
            klines = resp.json().get("data", {}).get("klines", [])
        except Exception:
            return []

        results = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 7:
                continue
            dt_str, open_s, close_s, high_s, low_s, vol_s, _ = parts[:7]
            results.append(DailyBar(
                date=dt_str[:10] if dt_str else "",
                open=_safe_float(open_s),
                close=_safe_float(close_s),
                high=_safe_float(high_s),
                low=_safe_float(low_s),
                volume=_safe_float(vol_s),
            ))
        return results

    # ── Chip Distribution ────────────────────────────────

    def fetch_chip_distribution(self, code: str) -> Optional[ChipDistribution]:
        url = self._CYQ_URL.format(secid=self._secid(code))
        resp = _get(url, timeout=10)
        if resp is None:
            return None
        try:
            data = resp.json().get("data", {})
        except Exception:
            return None
        if not data:
            return None

        avg_cost = _safe_float(data.get("avgCost"))
        profit_ratio = _safe_float(data.get("winRate")) / 100.0
        return ChipDistribution(
            avg_cost=avg_cost,
            trapped_ratio=1.0 - profit_ratio,
            profit_ratio=profit_ratio,
        )
