from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Symbol:
    code: str
    name: str
    market: str
    enabled: bool = True

@dataclass
class DailyBar:
    code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class StockFundamental:
    code: str
    per: Optional[float] = None
    pbr: Optional[float] = None

@dataclass
class AnalysisResult:
    code: str
    ma5: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    ma120: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    conditions: Dict[str, bool]
