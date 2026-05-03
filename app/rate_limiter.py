import time

class RateLimiter:
    def __init__(self, cfg):
        self.rate = float(cfg["initial_symbols_per_second"])
        self.min_rate = float(cfg["min_symbols_per_second"])
        self.max_rate = float(cfg["max_symbols_per_second"])
        self.down_factor = float(cfg["rate_downscale_factor"])
        self.recovery_step = float(cfg["rate_recovery_step"])
        self.recovery_after = float(cfg.get("recovery_after_success_seconds", 60))
        self.last_429 = None
        self.last_recovery = time.time()
        self.last_success = None

    def on_429(self):
        self.rate = max(self.min_rate, self.rate * self.down_factor)
        self.last_429 = time.time()
        self.last_recovery = time.time()

    def on_success(self):
        self.last_success = time.time()

    def maybe_recover(self):
        now = time.time()
        if self.last_429 and now - self.last_429 < self.recovery_after:
            return
        if now - self.last_recovery >= self.recovery_after:
            self.rate = min(self.max_rate, self.rate + self.recovery_step)
            self.last_recovery = now

    def interval(self):
        return max(0.001, 1.0 / max(self.min_rate, self.rate))
