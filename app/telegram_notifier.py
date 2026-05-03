import requests

class TelegramNotifier:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.enabled = bool(config.get("telegram", {}).get("enabled", False))
        self.token = str(config["telegram"]["bot_token"]).strip()
        self.chat_id = str(config["telegram"]["chat_id"]).strip()

    def send_batch(self, alerts):
        if not alerts:
            return []

        ids = [a["id"] for a in alerts]
        lines = ["📈 조건 감지 종목", ""]
        for a in alerts:
            lines.append(f"- {a['name']}({a['code']}) | {a['condition_name']}")

        messages = split_lines(lines, max_chars=3900)

        if not self.enabled:
            for msg in messages:
                if self.logger:
                    self.logger.info("[Telegram disabled] %s", msg)
                else:
                    print(msg)
            return ids

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for msg in messages:
            resp = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": msg, "disable_web_page_preview": True},
                timeout=15,
            )
            if resp.status_code >= 400 and self.logger:
                self.logger.error("Telegram error %s: %s", resp.status_code, resp.text[:1000])
            resp.raise_for_status()
        return ids

def split_lines(lines, max_chars=3900):
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        add_len = len(line) + 1
        if current and current_len + add_len > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += add_len
    if current:
        chunks.append("\n".join(current))
    return chunks
