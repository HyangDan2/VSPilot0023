from app.config import load_config
from app.kiwoom.client import KiwoomClient
from app.analysis.ma import calculate_ma_set

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    client = KiwoomClient(cfg)
    code = "005930"
    bars = client.fetch_daily_bars(code, 130)
    print("bars:", len(bars))
    for b in bars[:5]:
        print(b.date, b.open, b.high, b.low, b.close, b.volume)
    print(calculate_ma_set(bars))
