from app.config import load_config
from app.analysis.conditions import evaluate_conditions

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    ma = {"ma5": 120, "ma20": 100, "ma60": 80, "ma120": 90}
    print(evaluate_conditions(ma, per=4.2, pbr=0.45, cfg=cfg["analysis"]))
