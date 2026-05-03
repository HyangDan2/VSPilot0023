import sqlite3
import datetime
from typing import List
from app.models import Symbol, DailyBar, StockFundamental, AnalysisResult

class Storage:
    def __init__(self, config):
        self.config = config
        self.path = config["storage"]["sqlite_path"]
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            updated_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_daily (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (code, date)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            code TEXT PRIMARY KEY,
            per REAL,
            pbr REAL,
            fetched_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            ma5 REAL,
            ma20 REAL,
            ma60 REAL,
            ma120 REAL,
            per REAL,
            pbr REAL,
            bullish_value INTEGER,
            ma5_above_ma120 INTEGER,
            analyzed_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            condition_name TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            sent_at TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS scanner_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        self.conn.commit()


    def replace_symbols(self, symbols: List[Symbol]):
        """전체 종목 리스트를 새로 받은 결과로 교체한다. mock 잔존 종목 방지용."""
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute("DELETE FROM symbols")
        cur.executemany("""
        INSERT INTO symbols (code, name, market, enabled, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """, [(s.code, s.name, s.market, int(s.enabled), now) for s in symbols])
        self.conn.commit()

    def upsert_symbols(self, symbols: List[Symbol]):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.executemany("""
        INSERT INTO symbols (code, name, market, enabled, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            name=excluded.name,
            market=excluded.market,
            enabled=excluded.enabled,
            updated_at=excluded.updated_at
        """, [(s.code, s.name, s.market, int(s.enabled), now) for s in symbols])
        self.conn.commit()

    def load_symbols(self) -> List[Symbol]:
        cur = self.conn.cursor()
        rows = cur.execute("""
        SELECT code, name, market, enabled
        FROM symbols
        WHERE enabled=1
        ORDER BY market, code
        """).fetchall()
        return [Symbol(r["code"], r["name"], r["market"], bool(r["enabled"])) for r in rows]

    def symbol_name(self, code: str) -> str:
        cur = self.conn.cursor()
        row = cur.execute("SELECT name FROM symbols WHERE code=?", (code,)).fetchone()
        return row["name"] if row else code

    def save_daily_bars(self, bars: List[DailyBar]):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.executemany("""
        INSERT INTO ohlcv_daily (code, date, open, high, low, close, volume, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code, date) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume,
            fetched_at=excluded.fetched_at
        """, [(b.code, b.date, b.open, b.high, b.low, b.close, b.volume, now) for b in bars])
        self.conn.commit()

    def load_daily_bars(self, code: str, limit: int = 130) -> List[DailyBar]:
        cur = self.conn.cursor()
        rows = cur.execute("""
        SELECT code, date, open, high, low, close, volume
        FROM ohlcv_daily
        WHERE code=?
        ORDER BY date DESC
        LIMIT ?
        """, (code, limit)).fetchall()
        return [DailyBar(r["code"], r["date"], r["open"], r["high"], r["low"], r["close"], r["volume"]) for r in rows]

    def save_fundamental(self, f: StockFundamental):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO fundamentals (code, per, pbr, fetched_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            per=excluded.per,
            pbr=excluded.pbr,
            fetched_at=excluded.fetched_at
        """, (f.code, f.per, f.pbr, now))
        self.conn.commit()

    def save_analysis(self, result: AnalysisResult):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        c = result.conditions
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO analysis_results
        (code, ma5, ma20, ma60, ma120, per, pbr, bullish_value, ma5_above_ma120, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.code,
            result.ma5,
            result.ma20,
            result.ma60,
            result.ma120,
            result.per,
            result.pbr,
            int(c.get("bullish_value", False)),
            int(c.get("ma5_above_ma120", False)),
            now,
        ))
        self.conn.commit()

    def should_alert(self, code: str, condition_name: str, cooldown_minutes: int) -> bool:
        cur = self.conn.cursor()
        row = cur.execute("""
        SELECT created_at
        FROM alert_events
        WHERE code=? AND condition_name=?
        ORDER BY created_at DESC
        LIMIT 1
        """, (code, condition_name)).fetchone()

        if not row:
            return True

        try:
            last = datetime.datetime.fromisoformat(row["created_at"])
            return datetime.datetime.now() - last > datetime.timedelta(minutes=cooldown_minutes)
        except Exception:
            return True

    def enqueue_alert(self, code: str, condition_name: str, message: str):
        name = self.symbol_name(code)
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO alert_events (code, name, condition_name, message, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """, (code, name, condition_name, message, now))
        self.conn.commit()

    def get_pending_alerts(self):
        cur = self.conn.cursor()
        return cur.execute("""
        SELECT id, code, name, condition_name, message, created_at
        FROM alert_events
        WHERE status='pending'
        ORDER BY created_at ASC
        """).fetchall()

    def mark_sent(self, ids):
        if not ids:
            return
        now = datetime.datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        q = ",".join(["?"] * len(ids))
        cur.execute(f"UPDATE alert_events SET status='sent', sent_at=? WHERE id IN ({q})", [now, *ids])
        self.conn.commit()

    def get_state(self, key: str, default=None):
        cur = self.conn.cursor()
        row = cur.execute("SELECT value FROM scanner_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_state(self, key: str, value):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO scanner_state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))
        self.conn.commit()
