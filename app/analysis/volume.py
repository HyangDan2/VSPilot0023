from typing import List, Optional
from app.models import DailyBar

def volume_ma(bars: List[DailyBar], window: int = 20) -> Optional[float]:
    if len(bars) < window:
        return None
    volumes = [float(b.volume or 0) for b in bars[:window]]
    return sum(volumes) / window

def volume_ratio(bars: List[DailyBar], window: int = 20) -> Optional[float]:
    if not bars:
        return None
    ma = volume_ma(bars, window)
    if not ma:
        return None
    return float(bars[0].volume or 0) / ma
