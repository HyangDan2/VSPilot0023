import random
import requests
from datetime import date, timedelta
from typing import List
from app.models import Symbol, DailyBar, StockFundamental
from app.kiwoom.auth import KiwoomAuth
from app.kiwoom.exceptions import KiwoomRateLimitError, KiwoomError
from app.kiwoom.response_parser import parse_ka10099, parse_daily_bars, parse_fundamental

class KiwoomClient:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.kcfg = config["kiwoom"]
        self.auth = KiwoomAuth(config, logger=logger)

    def is_mock(self) -> bool:
        return bool(self.kcfg.get("mock", True)) or not bool(self.kcfg.get("enabled", False))

    def base_url(self) -> str:
        return self.kcfg["mock_base_url"] if self.kcfg.get("mock") else self.kcfg["base_url"]

    def headers(self, api_id: str = None) -> dict:
        token = self.auth.get_token()
        h = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
        }
        if api_id:
            h["api-id"] = api_id
        return h

    def post(self, endpoint: str, api_id: str, payload: dict) -> dict:
        if self.is_mock():
            raise KiwoomError("post() called in mock mode.")

        url = self.base_url() + endpoint
        resp = requests.post(url, headers=self.headers(api_id), json=payload, timeout=20)

        if resp.status_code == 401:
            self.auth.issue_token()
            resp = requests.post(url, headers=self.headers(api_id), json=payload, timeout=20)

        if resp.status_code == 429:
            raise KiwoomRateLimitError("HTTP 429 Too Many Requests")
        if resp.status_code >= 400:
            raise KiwoomError(f"HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        return_code = data.get("return_code")
        if return_code not in (None, 0, "0"):
            raise KiwoomError(f"Kiwoom API failed api-id={api_id}: return_code={return_code}, return_msg={data.get('return_msg')}")
        return data

    def fetch_symbol_list(self, markets: List[str]) -> List[Symbol]:
        if self.is_mock():
            return [
                Symbol("005930", "삼성전자", "KOSPI"),
                Symbol("000660", "SK하이닉스", "KOSPI"),
                Symbol("035420", "NAVER", "KOSPI"),
                Symbol("035720", "카카오", "KOSPI"),
                Symbol("091990", "셀트리온헬스케어", "KOSDAQ"),
            ]

        result = []
        markets_upper = [m.upper() for m in markets]

        if "KOSPI" in markets_upper or "KRX_ALL" in markets_upper:
            kospi = self.fetch_market_symbols("KOSPI")
            result.extend(kospi)
            if self.logger:
                self.logger.info("KOSPI symbols loaded: %d", len(kospi))

        if "KOSDAQ" in markets_upper or "KRX_ALL" in markets_upper:
            kosdaq = self.fetch_market_symbols("KOSDAQ")
            result.extend(kosdaq)
            if self.logger:
                self.logger.info("KOSDAQ symbols loaded: %d", len(kosdaq))

        dedup = {}
        for s in result:
            if s.code:
                dedup[s.code] = s
        return list(dedup.values())

    def fetch_market_symbols(self, market: str) -> List[Symbol]:
        endpoint = self.kcfg["endpoints"]["stock_list"]
        api_id = self.kcfg["api_ids"].get("stock_list_kospi", "ka10099")
        market_params = self.kcfg.get("market_params", {})
        mrkt_tp = market_params.get("kosdaq", "10") if market.upper() == "KOSDAQ" else market_params.get("kospi", "0")
        rk = self.kcfg.get("request_keys", {})
        market_key = rk.get("market", "mrkt_tp")

        data = self.post(endpoint, api_id, {market_key: mrkt_tp})
        symbols = parse_ka10099(data, market.upper())
        if not symbols and self.logger:
            self.logger.warning("%s parser returned 0. Top-level keys=%s", market, list(data.keys()))
        return symbols

    def fetch_kospi_symbols(self) -> List[Symbol]:
        return self.fetch_market_symbols("KOSPI")

    def fetch_kosdaq_symbols(self) -> List[Symbol]:
        return self.fetch_market_symbols("KOSDAQ")

    def fetch_daily_bars(self, code: str, count: int = 130) -> List[DailyBar]:
        if self.is_mock():
            return make_mock_daily_bars(code, count)

        endpoint = self.kcfg["endpoints"]["daily_chart"]
        api_id = self.kcfg["api_ids"]["daily_chart"]
        rk = self.kcfg.get("request_keys", {})
        chart_cfg = self.kcfg.get("chart", {})

        payload = {
            rk.get("code", "stk_cd"): code,
            rk.get("base_date", "base_dt"): chart_cfg.get("base_dt", "00000000"),
            rk.get("adjusted_price", "upd_stkpc_tp"): str(chart_cfg.get("upd_stkpc_tp", "1")),
        }

        data = self.post(endpoint, api_id, payload)
        bars = parse_daily_bars(code, data)[:count]
        if not bars and self.logger:
            self.logger.warning("No daily bars parsed for %s. Top-level keys=%s", code, list(data.keys()))
        return bars

    def fetch_fundamental(self, code: str) -> StockFundamental:
        if self.is_mock():
            if code in ("005930", "000660"):
                return StockFundamental(code=code, per=4.2, pbr=0.45)
            return StockFundamental(code=code, per=round(random.uniform(5, 18), 2), pbr=round(random.uniform(0.6, 2.5), 2))

        endpoint = self.kcfg["endpoints"]["stock_info"]
        api_id = self.kcfg["api_ids"]["stock_info"]
        rk = self.kcfg.get("request_keys", {})
        payload = {
            rk.get("code", "stk_cd"): code,
        }
        data = self.post(endpoint, api_id, payload)
        return parse_fundamental(code, data)

def recent_trading_dates(count: int) -> List[str]:
    d = date.today()
    dates = []
    while len(dates) < count:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

def make_mock_daily_bars(code: str, count: int) -> List[DailyBar]:
    dates = recent_trading_dates(count)
    old_to_new_dates = list(reversed(dates))
    seed = sum(ord(c) for c in code)
    rng = random.Random(seed)

    base_price = rng.uniform(15000, 120000)
    trend = rng.uniform(-0.0015, 0.0035)

    if code in ("005930", "000660"):
        trend = 0.004

    price = base_price
    generated = []

    for dt in old_to_new_dates:
        noise = rng.uniform(-0.015, 0.015)
        price = max(1000, price * (1.0 + trend + noise))

        open_price = price * (1.0 + rng.uniform(-0.01, 0.01))
        high = max(open_price, price) * (1.0 + rng.uniform(0.000, 0.025))
        low = min(open_price, price) * (1.0 - rng.uniform(0.000, 0.025))
        volume = rng.randint(100_000, 20_000_000)

        generated.append(DailyBar(
            code=code,
            date=dt,
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(price, 2),
            volume=volume,
        ))

    generated.sort(key=lambda x: x.date, reverse=True)
    return generated
