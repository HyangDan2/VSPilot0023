from typing import List
from app.models import DailyBar, StockFundamental, AnalysisResult
from app.analysis.ma import calculate_ma_set
from app.analysis.conditions import evaluate_conditions

def analyze(code: str, bars: List[DailyBar], fundamental: StockFundamental, cfg: dict) -> AnalysisResult:
    ma = calculate_ma_set(bars)
    conditions = evaluate_conditions(ma, fundamental.per, fundamental.pbr, cfg)
    return AnalysisResult(
        code=code,
        ma5=ma["ma5"],
        ma20=ma["ma20"],
        ma60=ma["ma60"],
        ma120=ma["ma120"],
        per=fundamental.per,
        pbr=fundamental.pbr,
        conditions=conditions,
    )
