from PySide6.QtCore import QObject, Signal, Slot
from app.scanner_engine import ScannerEngine

class ScannerWorker(QObject):
    status = Signal(dict)
    log = Signal(str)
    alert = Signal(dict)
    finished = Signal()
    error = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._stop = False
        self.engine = None

    @Slot()
    def run(self):
        try:
            self._stop = False
            self.engine = ScannerEngine(
                self.config,
                callbacks={
                    "on_status": self.status.emit,
                    "on_log": self.log.emit,
                    "on_alert": self.alert.emit,
                    "should_stop": lambda: self._stop,
                },
            )
            self.engine.run_forever()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @Slot()
    def stop(self):
        self._stop = True
