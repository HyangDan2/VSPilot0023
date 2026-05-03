from typing import List, Optional
from app.models import Symbol, DailyBar, StockFundamental

def to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "+"):
            return None
        return abs(float(s))
    except Exception:
        return None

def to_int(value) -> int:
    try:
        s = str(value).strip().replace(",", "")
        if s in ("", "-", "+"):
            return 0
        return abs(int(float(s)))
    except Exception:
        return 0

def get_first_list(data: dict):
    preferred = (
        "stk_list",
        "list",
        "items",
        "output",
        "data",
        "kospi_list",
        "kosdaq_list",
        "mrkt_list",
    )
    for key in preferred:
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
    code = str(value).replace("A", "").strip()
    code = code.replace(" ", "")
    return code

def is_valid_stock_code(code: str) -> bool:
    # 한국 종목코드는 6자리 숫자. 00010 같은 시장구분/분류값 오인식을 방지.
    return isinstance(code, str) and len(code) == 6 and code.isdigit()

def normalize_name(value, fallback=""):
    if value is None:
        return fallback
    return str(value).strip()

def parse_market_symbols(data: dict, market: str) -> List[Symbol]:
    list_key, rows = get_first_list(data)
    symbols = []

    for r in rows:
        if not isinstance(r, dict):
            continue

        # 실제 Kiwoom/라이브러리별 필드명을 폭넓게 지원하되, 6자리 숫자만 통과.
        code = (
            r.get("stk_cd")
            or r.get("code")
            or r.get("jongmok_cd")
            or r.get("isu_cd")
            or r.get("short_code")
            or r.get("종목코드")
            or r.get("단축코드")
        )
        name = (
            r.get("stk_nm")
            or r.get("name")
            or r.get("jongmok_nm")
            or r.get("isu_nm")
            or r.get("kor_name")
            or r.get("종목명")
            or r.get("한글종목명")
        )

        code = normalize_code(code)
        if not is_valid_stock_code(code):
            continue

        name = normalize_name(name, code)
        symbols.append(Symbol(code=code, name=name, market=market))

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
            # 일부 래퍼는 output 안에 ka10081OutBlock1을 둠
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

        date = (
            r.get("dt")
            or r.get("date")
            or r.get("일자")
            or r.get("trde_dt")
            or r.get("stk_dt")
        )
        close = (
            r.get("cur_prc")
            or r.get("close")
            or r.get("현재가")
            or r.get("close_pric")
            or r.get("stk_clpr")
        )
        open_ = r.get("open_pric") or r.get("open") or r.get("시가") or r.get("stk_oprc")
        high = r.get("high_pric") or r.get("high") or r.get("고가") or r.get("stk_hgpr")
        low = r.get("low_pric") or r.get("low") or r.get("저가") or r.get("stk_lwpr")
        volume = r.get("trde_qty") or r.get("volume") or r.get("거래량") or r.get("acc_trdvol")

        if date and close is not None:
            bars.append(DailyBar(
                code=code,
                date=str(date)[:8],
                open=to_float(open_) or to_float(close) or 0.0,
                high=to_float(high) or to_float(close) or 0.0,
                low=to_float(low) or to_float(close) or 0.0,
                close=to_float(close) or 0.0,
                volume=to_int(volume),
            ))

    bars.sort(key=lambda x: x.date, reverse=True)
    return bars

def parse_fundamental(code: str, data: dict) -> StockFundamental:
    rows = []
    for key in ("output", "data", "list", "items"):
        if isinstance(data.get(key), list) and data[key]:
            rows = data[key]
            break

    source = rows[0] if rows else data

    per = source.get("per") or source.get("PER") or source.get("per_rt") or source.get("PER배율")
    pbr = source.get("pbr") or source.get("PBR") or source.get("pbr_rt") or source.get("PBR배율")

    return StockFundamental(code=code, per=to_float(per), pbr=to_float(pbr))
