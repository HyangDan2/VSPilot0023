import time
from app.config import load_config
from app.logger import setup_logger
from app.scheduler import ScannerScheduler

def main():
    config = load_config("config.yaml")
    logger = setup_logger()
    scheduler = ScannerScheduler(config, logger=logger)

    logger.info("Scanner started")

    while True:
        scheduler.tick()
        time.sleep(scheduler.get_sleep_interval())

if __name__ == "__main__":
    main()
