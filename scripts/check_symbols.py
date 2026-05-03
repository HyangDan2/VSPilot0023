from app.config import load_config
from app.kiwoom.client import KiwoomClient

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    client = KiwoomClient(cfg)
    symbols = client.fetch_symbol_list(cfg["scanner"].get("market", ["KOSPI", "KOSDAQ"]))

    kospi = [s for s in symbols if s.market.upper() == "KOSPI"]
    kosdaq = [s for s in symbols if s.market.upper() == "KOSDAQ"]

    print("TOTAL:", len(symbols))
    print("KOSPI:", len(kospi))
    print("KOSDAQ:", len(kosdaq))
    print("SAMPLE:")
    for s in symbols[:20]:
        print(s.market, s.code, s.name)
