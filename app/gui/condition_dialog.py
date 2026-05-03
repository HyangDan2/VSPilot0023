from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QCheckBox, QHeaderView, QLabel, QMessageBox,
    QComboBox, QDoubleSpinBox, QWidget
)
from PySide6.QtCore import Qt

COLUMNS = [
    "Enabled",
    "Name",
    "MA Order",
    "MA Above",
    "PER <",
    "PBR <",
]

class ConditionDialog(QDialog):
    """
    조건식 편집 MVP.
    지원:
      - MA 정배열: 예) 5>20>60
      - MA 비교: 예) 5>120
      - PER < x
      - PBR < x

    config 저장 포맷:
    analysis:
      custom_conditions:
        - name: bullish_value
          enabled: true
          ma_order: [5, 20, 60]
          metrics:
            - {metric: per, op: "<", value: 5.0}
            - {metric: pbr, op: "<", value: 0.5}
        - name: ma5_above_ma120
          enabled: true
          ma_above: [[5, 120]]
          metrics: []
    """
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Condition Settings")
        self.resize(860, 420)
        self.config = config
        self._build_ui()
        self.load_from_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        help_label = QLabel(
            "조건식 편집: MA Order 예) 5>20>60, MA Above 예) 5>120. "
            "PER/PBR 값은 비워두면 조건에서 제외됩니다."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_preset = QPushButton("Load Presets")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_ok = QPushButton("Save")
        self.btn_cancel = QPushButton("Cancel")

        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_preset)
        btns.addWidget(self.btn_remove)
        btns.addStretch(1)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_add.clicked.connect(self.add_empty_row)
        self.btn_preset.clicked.connect(self.load_presets)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_ok.clicked.connect(self.on_save)
        self.btn_cancel.clicked.connect(self.reject)

    def add_condition_row(self, name="", enabled=True, ma_order="", ma_above="", per_lt="", pbr_lt=""):
        row = self.table.rowCount()
        self.table.insertRow(row)

        chk = QCheckBox()
        chk.setChecked(bool(enabled))
        chk.setStyleSheet("margin-left: 24px;")
        self.table.setCellWidget(row, 0, chk)

        values = [name, ma_order, ma_above, str(per_lt) if per_lt is not None else "", str(pbr_lt) if pbr_lt is not None else ""]
        for col, value in enumerate(values, start=1):
            item = QTableWidgetItem(str(value))
            if col == 1:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    def add_empty_row(self):
        self.add_condition_row(name="custom_condition", enabled=True)

    def load_presets(self):
        self.table.setRowCount(0)
        self.add_condition_row("bullish_value", True, "5>20>60", "", "5.0", "0.5")
        self.add_condition_row("ma5_above_ma120", True, "", "5>120", "", "")

    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def load_from_config(self):
        self.table.setRowCount(0)
        analysis = self.config.get("analysis", {})
        custom = analysis.get("custom_conditions", [])

        if not custom:
            # 기존 config 조건을 UI preset으로 보여줌
            self.load_presets()
            return

        for item in custom:
            name = item.get("name", "")
            enabled = item.get("enabled", True)

            ma_order = ""
            if item.get("ma_order"):
                ma_order = ">".join(str(x) for x in item.get("ma_order", []))

            ma_above = ""
            if item.get("ma_above"):
                parts = []
                for pair in item.get("ma_above", []):
                    if isinstance(pair, (list, tuple)) and len(pair) == 2:
                        parts.append(f"{pair[0]}>{pair[1]}")
                ma_above = ",".join(parts)

            per_lt = ""
            pbr_lt = ""
            for rule in item.get("metrics", []):
                if rule.get("metric") == "per" and rule.get("op") == "<":
                    per_lt = rule.get("value", "")
                if rule.get("metric") == "pbr" and rule.get("op") == "<":
                    pbr_lt = rule.get("value", "")

            self.add_condition_row(name, enabled, ma_order, ma_above, per_lt, pbr_lt)

    def parse_ma_order(self, text):
        text = (text or "").strip()
        if not text:
            return []
        try:
            parts = [int(x.strip().lower().replace("ma", "")) for x in text.split(">") if x.strip()]
            if len(parts) < 2:
                raise ValueError
            return parts
        except Exception:
            raise ValueError(f"Invalid MA Order: {text}. Example: 5>20>60")

    def parse_ma_above(self, text):
        text = (text or "").strip()
        if not text:
            return []
        pairs = []
        try:
            for chunk in text.split(","):
                if not chunk.strip():
                    continue
                left, right = chunk.split(">")
                pairs.append([int(left.strip().lower().replace("ma", "")), int(right.strip().lower().replace("ma", ""))])
            return pairs
        except Exception:
            raise ValueError(f"Invalid MA Above: {text}. Example: 5>120")

    def parse_float_optional(self, text):
        text = (text or "").strip()
        if text == "":
            return None
        return float(text)

    def collect_conditions(self):
        result = []
        for row in range(self.table.rowCount()):
            enabled_widget = self.table.cellWidget(row, 0)
            enabled = enabled_widget.isChecked() if enabled_widget else True

            def cell(col):
                item = self.table.item(row, col)
                return item.text().strip() if item else ""

            name = cell(1)
            if not name:
                raise ValueError(f"Row {row + 1}: condition name is empty.")

            ma_order = self.parse_ma_order(cell(2))
            ma_above = self.parse_ma_above(cell(3))
            per_lt = self.parse_float_optional(cell(4))
            pbr_lt = self.parse_float_optional(cell(5))

            metrics = []
            if per_lt is not None:
                metrics.append({"metric": "per", "op": "<", "value": per_lt})
            if pbr_lt is not None:
                metrics.append({"metric": "pbr", "op": "<", "value": pbr_lt})

            result.append({
                "name": name,
                "enabled": enabled,
                "ma_order": ma_order,
                "ma_above": ma_above,
                "metrics": metrics,
            })

        return result

    def on_save(self):
        try:
            conditions = self.collect_conditions()
            if not conditions:
                QMessageBox.warning(self, "No conditions", "At least one condition is required.")
                return

            self.config.setdefault("analysis", {})
            self.config["analysis"]["custom_conditions"] = conditions
            self.config.setdefault("alert", {})
            self.config["alert"]["include_conditions"] = [c["name"] for c in conditions if c.get("enabled", True)]
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Condition error", str(e))
