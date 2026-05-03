from app.config import load_config
from app.kiwoom.client import KiwoomClient

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    client = KiwoomClient(cfg)
    f = client.fetch_fundamental("005930")
    print(f)
