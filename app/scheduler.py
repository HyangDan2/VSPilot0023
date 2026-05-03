import time
from app.rate_limiter import RateLimiter
from app.storage import Storage
from app.telegram_notifier import TelegramNotifier
from app.kiwoom.client import KiwoomClient
from app.kiwoom.exceptions import KiwoomRateLimitError, KiwoomError
from app.analysis.static_analyzer import analyze

class ScannerScheduler:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.rate = RateLimiter(config["scanner"])
        self.storage = Storage(config)
        self.telegram = TelegramNotifier(config, logger=logger)
        self.client = KiwoomClient(config, logger=logger)

        if config["scanner"].get("symbol_refresh_on_start", True):
            self.refresh_symbols()

        self.symbols = self.storage.load_symbols()
        if not self.symbols:
            raise RuntimeError("No symbols loaded. Check Kiwoom stock list API or mock config.")

        self.index = int(self.storage.get_state("current_symbol_index", 0) or 0)
        self.last_telegram = time.time()

    def refresh_symbols(self):
        markets = self.config["scanner"].get("market", ["KOSPI", "KOSDAQ"])
        symbols = self.client.fetch_symbol_list(markets)
        self.storage.upsert_symbols(symbols)
        if self.logger:
            self.logger.info("Symbol refresh complete: %d symbols", len(symbols))

    def tick(self):
        if self.index >= len(self.symbols):
            self.index = 0

        symbol = self.symbols[self.index]

        try:
            bars = self.client.fetch_daily_bars(symbol.code, self.config["scanner"].get("min_daily_bars", 130))
            self.storage.save_daily_bars(bars)

            fundamental = self.client.fetch_fundamental(symbol.code)
            self.storage.save_fundamental(fundamental)

            stored_bars = self.storage.load_daily_bars(symbol.code, self.config["scanner"].get("min_daily_bars", 130))
            result = analyze(symbol.code, stored_bars, fundamental, self.config["analysis"])
            self.storage.save_analysis(result)

            self.handle_alerts(symbol, result)
            self.rate.on_success()

        except KiwoomRateLimitError:
            self.rate.on_429()
            if self.logger:
                self.logger.warning("429 detected. New rate: %.3f symbols/sec", self.rate.rate)
            return

        except KiwoomError as e:
            if self.logger:
                self.logger.error("Kiwoom error for %s: %s", symbol.code, e)
            return

        except Exception as e:
            if self.logger:
                self.logger.exception("Unexpected error for %s: %s", symbol.code, e)
            return

        self.index = (self.index + 1) % len(self.symbols)
        self.storage.set_state("current_symbol_index", self.index)

        self.rate.maybe_recover()
        self.flush_telegram_if_needed()

    def handle_alerts(self, symbol, result):
        cooldown = int(self.config.get("alert", {}).get("cooldown_minutes", 30))
        include = set(self.config.get("alert", {}).get("include_conditions", []))

        for condition_name, matched in result.conditions.items():
            if include and condition_name not in include:
                continue
            if not matched:
                continue
            if not self.storage.should_alert(symbol.code, condition_name, cooldown):
                continue

            msg = (
                f"MA5={fmt(result.ma5)}, MA20={fmt(result.ma20)}, "
                f"MA60={fmt(result.ma60)}, MA120={fmt(result.ma120)}, "
                f"PER={fmt(result.per)}, PBR={fmt(result.pbr)}"
            )
            self.storage.enqueue_alert(symbol.code, condition_name, msg)

    def flush_telegram_if_needed(self):
        interval = float(self.config["scanner"].get("telegram_interval_seconds", 60))
        if time.time() - self.last_telegram < interval:
            return

        alerts = self.storage.get_pending_alerts()
        if alerts:
            sent_ids = self.telegram.send_batch(alerts)
            self.storage.mark_sent(sent_ids)

        self.last_telegram = time.time()

    def get_sleep_interval(self):
        return self.rate.interval()

def fmt(v):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)
