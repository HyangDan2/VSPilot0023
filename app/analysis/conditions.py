def safe_lt(value, threshold) -> bool:
    return value is not None and threshold is not None and value < threshold

def safe_lte(value, threshold) -> bool:
    return value is not None and threshold is not None and value <= threshold

def safe_gt(a, b) -> bool:
    return a is not None and b is not None and a > b

def safe_gte(a, b) -> bool:
    return a is not None and b is not None and a >= b

def get_ma(ma: dict, window: int):
    return ma.get(f"ma{int(window)}")

def eval_ma_order(ma: dict, order) -> bool:
    if not order or len(order) < 2:
        return True
    values = [get_ma(ma, int(w)) for w in order]
    return all(safe_gt(values[i], values[i + 1]) for i in range(len(values) - 1))

def compare_metric(metric_name: str, op: str, threshold, ma: dict, per, pbr) -> bool:
    if metric_name.startswith("ma"):
        value = ma.get(metric_name)
    elif metric_name == "per":
        value = per
    elif metric_name == "pbr":
        value = pbr
    else:
        return False

    if threshold is None:
        return True

    if op == "<":
        return safe_lt(value, threshold)
    if op == "<=":
        return safe_lte(value, threshold)
    if op == ">":
        return safe_gt(value, threshold)
    if op == ">=":
        return safe_gte(value, threshold)
    if op == "==":
        return value is not None and float(value) == float(threshold)
    return False

def evaluate_legacy_conditions(ma: dict, per, pbr, cfg: dict) -> dict:
    conditions_cfg = cfg.get("conditions", {})

    ma5 = ma.get("ma5")
    ma20 = ma.get("ma20")
    ma60 = ma.get("ma60")
    ma120 = ma.get("ma120")

    bullish_value_enabled = conditions_cfg.get("bullish_value", {}).get("enabled", True)
    ma5_above_ma120_enabled = conditions_cfg.get("ma5_above_ma120", {}).get("enabled", True)

    bullish_value = False
    if bullish_value_enabled:
        per_lt = conditions_cfg.get("bullish_value", {}).get("per_lt", 5.0)
        pbr_lt = conditions_cfg.get("bullish_value", {}).get("pbr_lt", 0.5)
        bullish_value = (
            safe_gt(ma5, ma20)
            and safe_gt(ma20, ma60)
            and safe_lt(per, per_lt)
            and safe_lt(pbr, pbr_lt)
        )

    ma5_above_ma120 = False
    if ma5_above_ma120_enabled:
        ma5_above_ma120 = safe_gt(ma5, ma120)

    return {
        "bullish_value": bullish_value,
        "ma5_above_ma120": ma5_above_ma120,
    }

def evaluate_custom_conditions(ma: dict, per, pbr, cfg: dict) -> dict:
    results = {}
    custom_conditions = cfg.get("custom_conditions", [])

    for item in custom_conditions:
        name = str(item.get("name", "")).strip()
        if not name:
            continue

        enabled = bool(item.get("enabled", True))
        if not enabled:
            results[name] = False
            continue

        ok = True

        ma_order = item.get("ma_order", [])
        if ma_order:
            ok = ok and eval_ma_order(ma, ma_order)

        ma_above = item.get("ma_above", [])
        for pair in ma_above:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                ok = False
                continue
            ok = ok and safe_gt(get_ma(ma, int(pair[0])), get_ma(ma, int(pair[1])))

        metric_rules = item.get("metrics", [])
        for rule in metric_rules:
            if not isinstance(rule, dict):
                ok = False
                continue
            metric = rule.get("metric")
            op = rule.get("op", "<")
            threshold = rule.get("value")
            try:
                threshold = float(threshold) if threshold is not None and threshold != "" else None
            except Exception:
                threshold = None
            ok = ok and compare_metric(metric, op, threshold, ma, per, pbr)

        results[name] = bool(ok)

    return results

def evaluate_conditions(ma: dict, per, pbr, cfg: dict) -> dict:
    # custom_conditions가 있으면 custom 우선, 없으면 기존 하드코딩 조건 사용
    if cfg.get("custom_conditions"):
        return evaluate_custom_conditions(ma, per, pbr, cfg)
    return evaluate_legacy_conditions(ma, per, pbr, cfg)
