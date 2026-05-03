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
    amount: Optional[float] = None

@dataclass
class StockFundamental:
    code: str
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    sales: Optional[float] = None
    operating_profit: Optional[float] = None
    net_income: Optional[float] = None
    market_cap: Optional[float] = None
    foreign_exhaustion_rate: Optional[float] = None

@dataclass
class AnalysisResult:
    code: str
    ma5: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    ma120: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    roe: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    sales: Optional[float]
    operating_profit: Optional[float]
    net_income: Optional[float]
    market_cap: Optional[float]
    foreign_exhaustion_rate: Optional[float]
    volume_today: Optional[float]
    volume_ma20: Optional[float]
    volume_ratio: Optional[float]
    conditions: Dict[str, bool]
