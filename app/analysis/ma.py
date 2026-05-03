from typing import List, Optional
from app.models import DailyBar

def moving_average(bars: List[DailyBar], window: int) -> Optional[float]:
    if len(bars) < window:
        return None
    closes = [float(b.close) for b in bars[:window]]
    return sum(closes) / window

def calculate_ma_set(bars: List[DailyBar]) -> dict:
    # bars는 최신일자가 앞에 오는 리스트 기준
    return {
        "ma5": moving_average(bars, 5),
        "ma20": moving_average(bars, 20),
        "ma60": moving_average(bars, 60),
        "ma120": moving_average(bars, 120),
    }
