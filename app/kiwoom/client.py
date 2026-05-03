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
        h = {"Content-Type": "application/json;charset=UTF-8", "authorization": f"Bearer {token}"}
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
            result.extend(self.fetch_market_symbols("KOSPI"))
        if "KOSDAQ" in markets_upper or "KRX_ALL" in markets_upper:
            result.extend(self.fetch_market_symbols("KOSDAQ"))
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
        market_key = self.kcfg.get("request_keys", {}).get("market", "mrkt_tp")
        data = self.post(endpoint, api_id, {market_key: mrkt_tp})
        symbols = parse_ka10099(data, market.upper())
        if self.logger:
            self.logger.info("%s symbols loaded: %d", market, len(symbols))
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
        return parse_daily_bars(code, data)[:count]

    def fetch_fundamental(self, code: str) -> StockFundamental:
        if self.is_mock():
            rng = random.Random(sum(ord(c) for c in code) + 1000)
            if code in ("005930", "000660"):
                return StockFundamental(code=code, per=4.2, pbr=0.45, roe=12.5, eps=6500, bps=78000, sales=300000000, operating_profit=35000000, net_income=28000000, market_cap=450000000, foreign_exhaustion_rate=52.3)
            return StockFundamental(code=code, per=round(rng.uniform(3, 25), 2), pbr=round(rng.uniform(0.2, 3.5), 2), roe=round(rng.uniform(-15, 25), 2), eps=round(rng.uniform(-2000, 15000), 2), bps=round(rng.uniform(1000, 120000), 2), sales=round(rng.uniform(100000, 50000000), 2), operating_profit=round(rng.uniform(-5000000, 10000000), 2), net_income=round(rng.uniform(-5000000, 8000000), 2), market_cap=round(rng.uniform(100000, 200000000), 2), foreign_exhaustion_rate=round(rng.uniform(0, 80), 2))
        endpoint = self.kcfg["endpoints"]["stock_info"]
        api_id = self.kcfg["api_ids"]["stock_info"]
        rk = self.kcfg.get("request_keys", {})
        data = self.post(endpoint, api_id, {rk.get("code", "stk_cd"): code})
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
    rng = random.Random(sum(ord(c) for c in code))
    price = rng.uniform(15000, 120000)
    trend = 0.004 if code in ("005930", "000660") else rng.uniform(-0.0015, 0.0035)
    generated = []
    for dt in old_to_new_dates:
        price = max(1000, price * (1.0 + trend + rng.uniform(-0.015, 0.015)))
        open_price = price * (1.0 + rng.uniform(-0.01, 0.01))
        high = max(open_price, price) * (1.0 + rng.uniform(0.000, 0.025))
        low = min(open_price, price) * (1.0 - rng.uniform(0.000, 0.025))
        volume = rng.randint(100_000, 20_000_000)
        generated.append(DailyBar(code=code, date=dt, open=round(open_price, 2), high=round(high, 2), low=round(low, 2), close=round(price, 2), volume=volume, amount=round(volume * price, 2)))
    generated.sort(key=lambda x: x.date, reverse=True)
    return generated
