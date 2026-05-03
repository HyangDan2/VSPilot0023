import os
import yaml

def load_config(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Copy config.example.yaml to config.yaml first.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_config(path: str, config: dict):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
