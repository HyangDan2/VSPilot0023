from datetime import datetime
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QGridLayout, QCheckBox
)
from app.config import load_config, save_config
from app.gui.scanner_worker import ScannerWorker
from app.gui.condition_dialog import ConditionDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiwoom Static Scanner - PySide6 GUI")

        self.config_path = "config.yaml"
        self.config = None
        self.thread = None
        self.worker = None
        self._stopping = False

        self._build_ui()
        self._build_menu()
        self.load_config_file(self.config_path, silent=True)

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        act_load = file_menu.addAction("Load config.yaml")
        act_save = file_menu.addAction("Save config.yaml")
        act_exit = file_menu.addAction("Exit")

        cond_menu = menu.addMenu("Conditions")
        act_cond = cond_menu.addAction("Edit Alert Conditions")
        act_preset = cond_menu.addAction("Reset Default Conditions")

        act_load.triggered.connect(self.on_load_clicked)
        act_save.triggered.connect(self.save_current_config)
        act_exit.triggered.connect(self.close)
        act_cond.triggered.connect(self.open_condition_dialog)
        act_preset.triggered.connect(self.reset_default_conditions)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        self.btn_load = QPushButton("Load config.yaml")
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)

        self.lbl_config = QLabel("config: -")
        self.lbl_config.setTextInteractionFlags(Qt.TextSelectableByMouse)

        top.addWidget(self.btn_load)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        top.addWidget(self.lbl_config, 1)
        layout.addLayout(top)

        status_box = QGroupBox("Scanner Status")
        grid = QGridLayout(status_box)

        self.lbl_running = QLabel("Stopped")
        self.lbl_current = QLabel("-")
        self.lbl_progress = QLabel("-")
        self.lbl_rate = QLabel("-")
        self.lbl_last = QLabel("-")
        self.lbl_ma = QLabel("-")
        self.lbl_value = QLabel("-")
        self.lbl_conditions = QLabel("-")
        self.lbl_active_conditions = QLabel("-")
        self.chk_auto_scroll = QCheckBox("Auto-scroll log")
        self.chk_auto_scroll.setChecked(True)

        grid.addWidget(QLabel("State"), 0, 0)
        grid.addWidget(self.lbl_running, 0, 1)
        grid.addWidget(QLabel("Current"), 0, 2)
        grid.addWidget(self.lbl_current, 0, 3)
        grid.addWidget(QLabel("Progress"), 1, 0)
        grid.addWidget(self.lbl_progress, 1, 1)
        grid.addWidget(QLabel("Rate"), 1, 2)
        grid.addWidget(self.lbl_rate, 1, 3)
        grid.addWidget(QLabel("Last"), 2, 0)
        grid.addWidget(self.lbl_last, 2, 1)
        grid.addWidget(QLabel("MA"), 2, 2)
        grid.addWidget(self.lbl_ma, 2, 3)
        grid.addWidget(QLabel("PER/PBR"), 3, 0)
        grid.addWidget(self.lbl_value, 3, 1)
        grid.addWidget(QLabel("Matched"), 3, 2)
        grid.addWidget(self.lbl_conditions, 3, 3)
        grid.addWidget(QLabel("Active Conditions"), 4, 0)
        grid.addWidget(self.lbl_active_conditions, 4, 1, 1, 3)
        grid.addWidget(self.chk_auto_scroll, 5, 0)

        layout.addWidget(status_box)

        self.alert_table = QTableWidget(0, 5)
        self.alert_table.setHorizontalHeaderLabels(["Time", "Code", "Name", "Condition", "Message"])
        self.alert_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(QLabel("Detected Alerts"))
        layout.addWidget(self.alert_table, 2)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_view, 2)

        self.btn_load.clicked.connect(self.on_load_clicked)
        self.btn_start.clicked.connect(self.on_start_clicked)
        self.btn_stop.clicked.connect(self.on_stop_clicked)

    def load_config_file(self, path, silent=False):
        try:
            self.config = load_config(path)
            self.config_path = path
            self.lbl_config.setText(f"config: {path}")
            self.update_active_conditions_label()
            self.append_log(f"Config loaded: {path}")
        except Exception as e:
            self.config = None
            self.lbl_config.setText(f"config load failed: {path}")
            if not silent:
                QMessageBox.critical(self, "Config error", str(e))
            else:
                self.append_log(f"Config not loaded: {e}")

    def update_active_conditions_label(self):
        if not self.config:
            self.lbl_active_conditions.setText("-")
            return
        custom = self.config.get("analysis", {}).get("custom_conditions", [])
        if custom:
            names = [c.get("name", "") for c in custom if c.get("enabled", True)]
        else:
            names = self.config.get("alert", {}).get("include_conditions", [])
        self.lbl_active_conditions.setText(", ".join(names) if names else "-")

    def on_load_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open config YAML", "", "YAML Files (*.yaml *.yml);;All Files (*)")
        if path:
            self.load_config_file(path)

    def save_current_config(self):
        if not self.config:
            QMessageBox.warning(self, "No config", "Load config.yaml first.")
            return
        try:
            save_config(self.config_path, self.config)
            self.append_log(f"Config saved: {self.config_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def open_condition_dialog(self):
        if not self.config:
            QMessageBox.warning(self, "No config", "Load config.yaml first.")
            return
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Scanner running", "Stop scanner before editing conditions.")
            return

        dlg = ConditionDialog(self.config, self)
        if dlg.exec():
            self.update_active_conditions_label()
            self.save_current_config()
            self.append_log("Alert conditions updated.")

    def reset_default_conditions(self):
        if not self.config:
            QMessageBox.warning(self, "No config", "Load config.yaml first.")
            return
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Scanner running", "Stop scanner before editing conditions.")
            return

        self.config.setdefault("analysis", {})
        self.config["analysis"]["custom_conditions"] = [
            {
                "name": "bullish_value",
                "enabled": True,
                "ma_order": [5, 20, 60],
                "ma_above": [],
                "metrics": [
                    {"metric": "per", "op": "<", "value": 5.0},
                    {"metric": "pbr", "op": "<", "value": 0.5},
                ],
            },
            {
                "name": "ma5_above_ma120",
                "enabled": True,
                "ma_order": [],
                "ma_above": [[5, 120]],
                "metrics": [],
            },
        ]
        self.config.setdefault("alert", {})
        self.config["alert"]["include_conditions"] = ["bullish_value", "ma5_above_ma120"]
        self.update_active_conditions_label()
        self.save_current_config()
        self.append_log("Default alert conditions restored.")

    def on_start_clicked(self):
        if not self.config:
            QMessageBox.warning(self, "No config", "Load config.yaml first.")
            return

        if self.thread and self.thread.isRunning():
            return

        self._stopping = False
        self.thread = QThread(self)
        self.worker = ScannerWorker(self.config)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.on_status)
        self.worker.log.connect(self.append_log)
        self.worker.alert.connect(self.on_alert)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_load.setEnabled(False)
        self.lbl_running.setText("Running")
        self.append_log("GUI scanner starting...")

        self.thread.start()

    def on_stop_clicked(self):
        self.stop_thread_blocking(timeout_ms=5000)

    def stop_thread_blocking(self, timeout_ms=5000):
        if self._stopping:
            return
        self._stopping = True

        if self.worker:
            self.append_log("Stop requested...")
            self.worker.stop()

        if self.thread and self.thread.isRunning():
            if not self.thread.wait(timeout_ms):
                self.append_log("Thread did not stop in time. Terminating as fallback...")
                self.thread.terminate()
                self.thread.wait(2000)

        self.btn_stop.setEnabled(False)

    def on_finished(self):
        self.append_log("Worker finished.")
        self.lbl_running.setText("Stopped")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_load.setEnabled(True)
        self.thread = None
        self.worker = None
        self._stopping = False

    def on_error(self, msg):
        self.append_log(f"ERROR: {msg}")
        QMessageBox.critical(self, "Scanner error", msg)

    def on_status(self, s):
        if "current_code" in s:
            self.lbl_current.setText(f"{s.get('current_name', '')}({s.get('current_code', '')}) / {s.get('current_market', '')}")
        if "current_index" in s and "total_symbols" in s:
            self.lbl_progress.setText(f"{s['current_index']} / {s['total_symbols']}")
        if "rate" in s:
            self.lbl_rate.setText(f"{float(s['rate']):.3f} symbols/sec")
        if "last_code" in s:
            self.lbl_last.setText(f"{s.get('last_name', '')}({s.get('last_code', '')})")
        if any(k in s for k in ("ma5", "ma20", "ma60", "ma120")):
            self.lbl_ma.setText(
                f"MA5={fmt(s.get('ma5'))}, MA20={fmt(s.get('ma20'))}, "
                f"MA60={fmt(s.get('ma60'))}, MA120={fmt(s.get('ma120'))}"
            )
        if "per" in s or "pbr" in s:
            self.lbl_value.setText(f"PER={fmt(s.get('per'))}, PBR={fmt(s.get('pbr'))}")
        if "condition_summary" in s:
            self.lbl_conditions.setText(str(s["condition_summary"]))
        if "error" in s:
            self.append_log(f"Status error: {s['error']}")

    def on_alert(self, a):
        row = self.alert_table.rowCount()
        self.alert_table.insertRow(row)

        values = [
            datetime.now().strftime("%H:%M:%S"),
            a.get("code", ""),
            a.get("name", ""),
            a.get("condition", ""),
            a.get("message", ""),
        ]
        for col, val in enumerate(values):
            self.alert_table.setItem(row, col, QTableWidgetItem(str(val)))

        self.alert_table.scrollToBottom()

    def append_log(self, msg):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{now}] {msg}")
        if self.chk_auto_scroll.isChecked():
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.stop_thread_blocking(timeout_ms=5000)
        event.accept()

def fmt(v):
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)
