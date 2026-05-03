from app.config import load_config
from app.kiwoom.client import KiwoomClient
from app.analysis.ma import calculate_ma_set

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    client = KiwoomClient(cfg)
    code = "005930"
    bars = client.fetch_daily_bars(code, 130)
    ma = calculate_ma_set(bars)

    print("Latest 10 bars:")
    for b in bars[:10]:
        print(b.date, b.close, b.volume)

    print("\nMA:")
    for k, v in ma.items():
        print(k, round(v, 2) if v else None)
