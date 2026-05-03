from app.config import load_config
from app.storage import Storage

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    Storage(cfg)
    print("DB initialized.")
