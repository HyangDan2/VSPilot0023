from typing import List, Optional
from app.models import Symbol, DailyBar, StockFundamental

def to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "+", "--"):
            return None
        return float(s)
    except Exception:
        return None

def to_abs_float(value) -> Optional[float]:
    v = to_float(value)
    return abs(v) if v is not None else None

def to_int(value) -> int:
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "+", "--"):
            return 0
        return int(abs(float(s)))
    except Exception:
        return 0

def pick(source: dict, keys):
    for k in keys:
        if k in source and source.get(k) not in (None, ""):
            return source.get(k)
    return None

def get_first_list(data: dict):
    for key in ("stk_list", "list", "items", "output", "data", "kospi_list", "kosdaq_list", "mrkt_list"):
        value = data.get(key)
        if isinstance(value, list):
            return key, value
    for key, value in data.items():
        if isinstance(value, list):
            return key, value
    return None, []

def normalize_code(value):
    if value is None:
        return ""
    return str(value).replace("A", "").replace(" ", "").strip()

def is_valid_stock_code(code: str) -> bool:
    return isinstance(code, str) and len(code) == 6 and code.isdigit()

def normalize_name(value, fallback=""):
    return fallback if value is None else str(value).strip()

def parse_market_symbols(data: dict, market: str) -> List[Symbol]:
    _, rows = get_first_list(data)
    symbols = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        code = pick(r, ["stk_cd", "code", "jongmok_cd", "isu_cd", "short_code", "종목코드", "단축코드"])
        name = pick(r, ["stk_nm", "name", "jongmok_nm", "isu_nm", "kor_name", "종목명", "한글종목명"])
        code = normalize_code(code)
        if not is_valid_stock_code(code):
            continue
        symbols.append(Symbol(code=code, name=normalize_name(name, code), market=market))
    return symbols

def parse_ka10099(data: dict, market: str = "KOSPI") -> List[Symbol]:
    return parse_market_symbols(data, market)

def parse_symbol_list(data: dict, market: str) -> List[Symbol]:
    return parse_market_symbols(data, market)

def parse_daily_bars(code: str, data: dict) -> List[DailyBar]:
    candidates = [
        data.get("stk_dt_pole_chart_qry"),
        data.get("ka10081OutBlock1"),
        data.get("output"),
        data.get("list"),
        data.get("daily"),
        data.get("data"),
    ]

    rows = []
    for c in candidates:
        if isinstance(c, list):
            rows = c
            break
        if isinstance(c, dict):
            for nested_key in ("ka10081OutBlock1", "stk_dt_pole_chart_qry", "list", "data"):
                if isinstance(c.get(nested_key), list):
                    rows = c[nested_key]
                    break
        if rows:
            break

    if not rows:
        _, rows = get_first_list(data)

    bars = []
    for r in rows:
        if not isinstance(r, dict):
            continue

        date = pick(r, ["dt", "date", "일자", "trde_dt", "stk_dt"])
        close = pick(r, ["cur_prc", "close", "현재가", "close_pric", "stk_clpr"])
        open_ = pick(r, ["open_pric", "open", "시가", "stk_oprc"])
        high = pick(r, ["high_pric", "high", "고가", "stk_hgpr"])
        low = pick(r, ["low_pric", "low", "저가", "stk_lwpr"])
        volume = pick(r, ["trde_qty", "volume", "거래량", "acc_trdvol"])
        amount = pick(r, ["trde_prica", "trd_amt", "거래대금", "acc_trdval"])

        if date and close is not None:
            bars.append(DailyBar(
                code=code,
                date=str(date)[:8],
                open=to_abs_float(open_) or to_abs_float(close) or 0.0,
                high=to_abs_float(high) or to_abs_float(close) or 0.0,
                low=to_abs_float(low) or to_abs_float(close) or 0.0,
                close=to_abs_float(close) or 0.0,
                volume=to_int(volume),
                amount=to_abs_float(amount),
            ))

    bars.sort(key=lambda x: x.date, reverse=True)
    return bars

def first_dict_payload(data: dict) -> dict:
    for key in ("output", "data", "list", "items"):
        value = data.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0]
        if isinstance(value, dict):
            return value
    return data

def parse_fundamental(code: str, data: dict) -> StockFundamental:
    source = first_dict_payload(data)

    per = pick(source, ["per", "PER", "per_rt", "PER배율"])
    pbr = pick(source, ["pbr", "PBR", "pbr_rt", "PBR배율"])
    roe = pick(source, ["roe", "ROE", "roe_rt", "ROE율"])
    eps = pick(source, ["eps", "EPS", "EPS원"])
    bps = pick(source, ["bps", "BPS", "BPS원"])
    sales = pick(source, ["sales", "sale_amt", "revenue", "매출액"])
    operating_profit = pick(source, ["operating_profit", "oper_prft", "bus_pro", "영업이익"])
    net_income = pick(source, ["net_income", "net_prft", "순이익", "당기순이익"])
    market_cap = pick(source, ["market_cap", "mkt_cap", "시가총액", "market_capitalization"])
    foreign_exhaustion_rate = pick(source, ["foreign_exhaustion_rate", "frgn_exh_rt", "외인소진률", "외국인소진률", "for_exh_rt"])

    return StockFundamental(
        code=code,
        per=to_float(per),
        pbr=to_float(pbr),
        roe=to_float(roe),
        eps=to_float(eps),
        bps=to_float(bps),
        sales=to_float(sales),
        operating_profit=to_float(operating_profit),
        net_income=to_float(net_income),
        market_cap=to_float(market_cap),
        foreign_exhaustion_rate=to_float(foreign_exhaustion_rate),
    )
