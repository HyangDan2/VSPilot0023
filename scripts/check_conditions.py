from app.config import load_config
from app.analysis.conditions import evaluate_conditions

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    metrics = {
        "ma": {"ma5": 120, "ma20": 100, "ma60": 80, "ma120": 90},
        "per": 4.2,
        "pbr": 0.45,
        "roe": 12.5,
        "eps": 6500,
        "bps": 78000,
        "sales": 300000000,
        "operating_profit": 35000000,
        "net_income": 28000000,
        "market_cap": 450000000,
        "foreign_exhaustion_rate": 52.3,
        "volume_ratio": 2.5,
    }
    print(evaluate_conditions(metrics, cfg["analysis"]))
