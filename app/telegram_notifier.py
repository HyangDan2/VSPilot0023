import requests

class TelegramNotifier:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.enabled = bool(config.get("telegram", {}).get("enabled", False))
        self.token = config["telegram"]["bot_token"]
        self.chat_id = config["telegram"]["chat_id"]

    def send_batch(self, alerts):
        if not alerts:
            return []

        ids = [a["id"] for a in alerts]
        lines = ["📈 Kiwoom Static Scanner 조건 감지", ""]
        for a in alerts:
            lines.append(f"- {a['name']}({a['code']}) | {a['condition_name']}")
            lines.append(f"  {a['message']}")

        msg = "\n".join(lines)

        if not self.enabled:
            if self.logger:
                self.logger.info("[Telegram disabled] %s", msg)
            else:
                print(msg)
            return ids

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        resp = requests.post(url, json={"chat_id": self.chat_id, "text": msg}, timeout=15)
        resp.raise_for_status()
        return ids
