import json
import os
import time
from datetime import datetime
import requests
from app.kiwoom.exceptions import KiwoomAuthError

class KiwoomAuth:
    def __init__(self, config: dict, logger=None):
        self.config = config
        self.logger = logger
        self.kcfg = config["kiwoom"]
        self.cache_path = self.kcfg.get("token_cache_path", ".kiwoom_token_cache.json")

    def base_url(self) -> str:
        return self.kcfg["mock_base_url"] if self.kcfg.get("mock") else self.kcfg["base_url"]

    def get_token(self) -> str:
        if self.kcfg.get("token_cache_enabled", True):
            cached = self._load_cached_token()
            if cached:
                return cached
        return self.issue_token()

    def issue_token(self) -> str:
        appkey = self.kcfg.get("appkey", "")
        secretkey = self.kcfg.get("secretkey", "")
        if not appkey or not secretkey:
            raise KiwoomAuthError("kiwoom.appkey / kiwoom.secretkey is empty.")

        url = self.base_url() + self.kcfg["endpoints"].get("token", "/oauth2/token")
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        payload = {
            "grant_type": "client_credentials",
            "appkey": appkey,
            "secretkey": secretkey,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code >= 400:
            raise KiwoomAuthError(f"Token issue failed: HTTP {resp.status_code} {resp.text[:300]}")

        data = resp.json()
        token = data.get("token") or data.get("access_token")
        if not token:
            raise KiwoomAuthError(f"Token field not found in response: {data}")

        expires_dt = data.get("expires_dt")
        expires_ts = self._parse_expires_dt(expires_dt) if expires_dt else time.time() + 60 * 60 * 20

        if self.kcfg.get("token_cache_enabled", True):
            self._save_cached_token(token, expires_ts, data)

        return token

    def _parse_expires_dt(self, expires_dt: str) -> float:
        try:
            dt = datetime.strptime(str(expires_dt), "%Y%m%d%H%M%S")
            return dt.timestamp()
        except Exception:
            return time.time() + 60 * 60 * 20

    def _load_cached_token(self):
        if not os.path.exists(self.cache_path):
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            expires_ts = float(data.get("expires_ts", 0))
            if time.time() < expires_ts - 300:
                return data.get("token")
        except Exception:
            return None
        return None

    def _save_cached_token(self, token: str, expires_ts: float, raw: dict):
        data = {"token": token, "expires_ts": expires_ts, "raw": raw}
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
