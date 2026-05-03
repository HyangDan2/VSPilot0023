import time
import traceback
from app.rate_limiter import RateLimiter
from app.storage import Storage
from app.telegram_notifier import TelegramNotifier
from app.kiwoom.client import KiwoomClient
from app.kiwoom.exceptions import KiwoomRateLimitError, KiwoomError
from app.analysis.static_analyzer import analyze

class ScannerEngine:
    """
    GUI/CLI 공용 스캐너 엔진.
    callback dict:
      - on_status(dict)
      - on_log(str)
      - on_alert(dict)
      - should_stop() -> bool
    """
    def __init__(self, config, callbacks=None):
        self.config = config
        self.callbacks = callbacks or {}
        self.rate = RateLimiter(config["scanner"])
        self.storage = Storage(config)
        self.telegram = TelegramNotifier(config)
        self.client = KiwoomClient(config)
        self.symbols = []
        self.index = 0
        self.last_telegram = time.time()
        self.running = False

    def log(self, msg):
        cb = self.callbacks.get("on_log")
        if cb:
            cb(str(msg))
        else:
            print(msg)

    def emit_status(self, **kwargs):
        cb = self.callbacks.get("on_status")
        if cb:
            cb(kwargs)

    def emit_alert(self, **kwargs):
        cb = self.callbacks.get("on_alert")
        if cb:
            cb(kwargs)

    def should_stop(self):
        cb = self.callbacks.get("should_stop")
        return bool(cb()) if cb else False

    def initialize(self):
        if self.config["scanner"].get("symbol_refresh_on_start", True):
            self.refresh_symbols()

        self.symbols = self.storage.load_symbols()
        if not self.symbols:
            raise RuntimeError("No symbols loaded. Check Kiwoom stock list API or mock config.")

        self.index = int(self.storage.get_state("current_symbol_index", 0) or 0)
        if self.index >= len(self.symbols):
            self.index = 0

        self.log(f"Loaded symbols: {len(self.symbols)}")
        self.emit_status(total_symbols=len(self.symbols), current_index=self.index, rate=self.rate.rate)

    def refresh_symbols(self):
        markets = self.config["scanner"].get("market", ["KOSPI", "KOSDAQ"])
        symbols = self.client.fetch_symbol_list(markets)
        self.storage.replace_symbols(symbols)
        self.storage.set_state("current_symbol_index", 0)
        self.index = 0

        kospi_count = sum(1 for s in symbols if s.market.upper() == "KOSPI")
        kosdaq_count = sum(1 for s in symbols if s.market.upper() == "KOSDAQ")
        self.log(f"Symbol refresh complete: total={len(symbols)}, KOSPI={kospi_count}, KOSDAQ={kosdaq_count}")
        self.emit_status(total_symbols=len(symbols), current_index=0)

    def run_forever(self):
        self.running = True
        self.initialize()
        self.log("Scanner loop started")

        while not self.should_stop():
            self.tick()
            self.interruptible_sleep(self.rate.interval())

        self.running = False
        self.log("Scanner loop stopped")

    def interruptible_sleep(self, seconds: float):
        end = time.time() + max(0.0, seconds)
        while time.time() < end:
            if self.should_stop():
                return
            time.sleep(min(0.05, max(0.0, end - time.time())))

    def tick(self):
        if self.should_stop():
            return

        if not self.symbols:
            self.symbols = self.storage.load_symbols()
        if not self.symbols:
            return

        if self.index >= len(self.symbols):
            self.index = 0

        symbol = self.symbols[self.index]
        self.emit_status(
            current_code=symbol.code,
            current_name=symbol.name,
            current_market=symbol.market,
            current_index=self.index + 1,
            total_symbols=len(self.symbols),
            rate=self.rate.rate,
        )

        try:
            bars = self.client.fetch_daily_bars(symbol.code, self.config["scanner"].get("min_daily_bars", 130))
            if self.should_stop():
                return
            self.storage.save_daily_bars(bars)

            fundamental = self.client.fetch_fundamental(symbol.code)
            if self.should_stop():
                return
            self.storage.save_fundamental(fundamental)

            stored_bars = self.storage.load_daily_bars(symbol.code, self.config["scanner"].get("min_daily_bars", 130))
            result = analyze(symbol.code, stored_bars, fundamental, self.config["analysis"])
            self.storage.save_analysis(result)

            self.handle_alerts(symbol, result)
            self.rate.on_success()

            self.emit_status(
                last_code=symbol.code,
                last_name=symbol.name,
                ma5=result.ma5,
                ma20=result.ma20,
                ma60=result.ma60,
                ma120=result.ma120,
                per=result.per,
                pbr=result.pbr,
                condition_summary=", ".join([k for k, v in result.conditions.items() if v]) or "-",
            )

        except KiwoomRateLimitError:
            self.rate.on_429()
            self.log(f"HTTP 429 detected. Rate down: {self.rate.rate:.3f} symbols/sec")
            self.emit_status(rate=self.rate.rate, error="HTTP 429")
            return

        except KiwoomError as e:
            self.log(f"Kiwoom error for {symbol.code}: {e}")
            self.emit_status(error=str(e))
            self.index = (self.index + 1) % len(self.symbols)
            self.storage.set_state("current_symbol_index", self.index)
            return

        except Exception as e:
            self.log(f"Unexpected error for {symbol.code}: {e}\n{traceback.format_exc()}")
            self.emit_status(error=str(e))
            self.index = (self.index + 1) % len(self.symbols)
            self.storage.set_state("current_symbol_index", self.index)
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
            self.emit_alert(
                code=symbol.code,
                name=symbol.name,
                condition=condition_name,
                message=msg,
            )

    def flush_telegram_if_needed(self):
        interval = float(self.config["scanner"].get("telegram_interval_seconds", 60))
        if time.time() - self.last_telegram < interval:
            return

        alerts = self.storage.get_pending_alerts()
        if alerts:
            sent_ids = self.telegram.send_batch(alerts)
            self.storage.mark_sent(sent_ids)
            self.log(f"Telegram batch sent: {len(sent_ids)} alerts")

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
