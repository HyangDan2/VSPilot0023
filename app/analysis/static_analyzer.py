from typing import List
from app.models import DailyBar, StockFundamental, AnalysisResult
from app.analysis.ma import calculate_ma_set
from app.analysis.volume import volume_ma, volume_ratio
from app.analysis.conditions import evaluate_conditions

def analyze(code: str, bars: List[DailyBar], fundamental: StockFundamental, cfg: dict) -> AnalysisResult:
    ma = calculate_ma_set(bars)
    v_ma20 = volume_ma(bars, 20)
    v_ratio = volume_ratio(bars, 20)
    volume_today = float(bars[0].volume) if bars else None

    metrics = {
        "ma": ma,
        "per": fundamental.per,
        "pbr": fundamental.pbr,
        "roe": fundamental.roe,
        "eps": fundamental.eps,
        "bps": fundamental.bps,
        "sales": fundamental.sales,
        "operating_profit": fundamental.operating_profit,
        "net_income": fundamental.net_income,
        "market_cap": fundamental.market_cap,
        "foreign_exhaustion_rate": fundamental.foreign_exhaustion_rate,
        "volume_today": volume_today,
        "volume_ma20": v_ma20,
        "volume_ratio": v_ratio,
    }

    conditions = evaluate_conditions(metrics, cfg)

    return AnalysisResult(
        code=code,
        ma5=ma["ma5"],
        ma20=ma["ma20"],
        ma60=ma["ma60"],
        ma120=ma["ma120"],
        per=fundamental.per,
        pbr=fundamental.pbr,
        roe=fundamental.roe,
        eps=fundamental.eps,
        bps=fundamental.bps,
        sales=fundamental.sales,
        operating_profit=fundamental.operating_profit,
        net_income=fundamental.net_income,
        market_cap=fundamental.market_cap,
        foreign_exhaustion_rate=fundamental.foreign_exhaustion_rate,
        volume_today=volume_today,
        volume_ma20=v_ma20,
        volume_ratio=v_ratio,
        conditions=conditions,
    )
