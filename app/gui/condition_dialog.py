from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QCheckBox, QHeaderView, QLabel, QMessageBox,
    QComboBox
)

METRIC_COLUMNS = [
    ("PER", "per"),
    ("PBR", "pbr"),
    ("ROE", "roe"),
    ("EPS", "eps"),
    ("BPS", "bps"),
    ("매출액", "sales"),
    ("영업이익", "operating_profit"),
    ("순이익", "net_income"),
    ("시가총액", "market_cap"),
    ("외인소진률", "foreign_exhaustion_rate"),
    ("거래량", "volume_today"),
    ("거래량MA20", "volume_ma20"),
    ("거래량배율", "volume_ratio"),
]

COLUMNS = ["Enabled", "Operand", "Name", "MA Order", "MA Above"] + [f"{label} 조건" for label, _ in METRIC_COLUMNS]

class ConditionDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Condition Settings")
        self.resize(1500, 560)
        self.config = config
        self._build_ui()
        self.load_from_config()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        help_label = QLabel(
            "Operand는 한 조건행 내부 결합 방식입니다. "
            "AND=모든 입력 조건 만족, OR=하나 이상 만족. "
            "MA Order 예) 5>20>60, MA Above 예) 5>120. "
            "지표 조건 예) <5, >10, >=0. 복수 조건은 >2,<10 처럼 콤마로 입력."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
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

    def add_condition_row(self, name="", enabled=True, operand="AND", ma_order="", ma_above="", metric_values=None):
        metric_values = metric_values or {}
        row = self.table.rowCount()
        self.table.insertRow(row)

        chk = QCheckBox()
        chk.setChecked(bool(enabled))
        chk.setStyleSheet("margin-left: 24px;")
        self.table.setCellWidget(row, 0, chk)

        combo = QComboBox()
        combo.addItems(["AND", "OR"])
        combo.setCurrentText((operand or "AND").upper())
        self.table.setCellWidget(row, 1, combo)

        for col, value in enumerate([name, ma_order, ma_above], start=2):
            self.table.setItem(row, col, QTableWidgetItem(str(value or "")))

        start = 5
        for i, (_, metric) in enumerate(METRIC_COLUMNS):
            value = metric_values.get(metric, "")
            if isinstance(value, list):
                value = ",".join(value)
            self.table.setItem(row, start + i, QTableWidgetItem(str(value)))

    def add_empty_row(self):
        self.add_condition_row(name="custom_condition", enabled=True, operand="AND")

    def load_presets(self):
        self.table.setRowCount(0)
        self.add_condition_row("bullish_value", True, "AND", "5>20>60", "", {
            "per": "<5.0",
            "pbr": "<0.5",
            "roe": ">10",
            "operating_profit": ">0",
            "net_income": ">0",
        })
        self.add_condition_row("ma5_above_ma120", True, "AND", "", "5>120", {})
        self.add_condition_row("volume_spike_value", True, "AND", "5>20", "", {
            "volume_ratio": ">2,<10",
            "volume_today": ">1000000",
            "per": "<10",
            "pbr": "<1",
        })
        self.add_condition_row("foreign_or_value", True, "OR", "", "", {
            "foreign_exhaustion_rate": ">20",
            "roe": ">10",
            "pbr": "<0.5",
        })

    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def load_from_config(self):
        self.table.setRowCount(0)
        custom = self.config.get("analysis", {}).get("custom_conditions", [])
        if not custom:
            self.load_presets()
            return

        for item in custom:
            ma_order = ">".join(str(x) for x in item.get("ma_order", [])) if item.get("ma_order") else ""
            ma_above = ",".join(
                f"{p[0]}>{p[1]}" for p in item.get("ma_above", [])
                if isinstance(p, (list, tuple)) and len(p) == 2
            )
            metric_values = {}
            for rule in item.get("metrics", []):
                metric = rule.get("metric")
                if metric:
                    value = f"{rule.get('op', '<')}{rule.get('value', '')}"
                    old = metric_values.get(metric)
                    if old:
                        metric_values[metric] = old + "," + value
                    else:
                        metric_values[metric] = value

            self.add_condition_row(
                item.get("name", ""),
                item.get("enabled", True),
                item.get("operand", "AND"),
                ma_order,
                ma_above,
                metric_values,
            )

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

    def parse_metric_rules(self, metric, text):
        text = (text or "").strip()
        if not text:
            return []
        rules = []
        for chunk in text.split(","):
            chunk = chunk.strip()
            if chunk:
                rules.append(self.parse_single_metric_rule(metric, chunk))
        return rules

    def parse_single_metric_rule(self, metric, text):
        for op in [">=", "<=", "!=", "==", ">", "<"]:
            if text.startswith(op):
                value_text = text[len(op):].strip()
                break
        else:
            op = "<"
            value_text = text
        try:
            value = float(value_text.replace(",", ""))
        except Exception:
            raise ValueError(f"Invalid metric rule for {metric}: {text}. Example: <5 or >2,<10")
        return {"metric": metric, "op": op, "value": value}

    def collect_conditions(self):
        result = []
        for row in range(self.table.rowCount()):
            enabled_widget = self.table.cellWidget(row, 0)
            enabled = enabled_widget.isChecked() if enabled_widget else True

            operand_widget = self.table.cellWidget(row, 1)
            operand = operand_widget.currentText() if operand_widget else "AND"

            def cell(col):
                item = self.table.item(row, col)
                return item.text().strip() if item else ""

            name = cell(2)
            if not name:
                raise ValueError(f"Row {row + 1}: condition name is empty.")

            metrics = []
            start = 5
            for i, (_, metric) in enumerate(METRIC_COLUMNS):
                metrics.extend(self.parse_metric_rules(metric, cell(start + i)))

            result.append({
                "name": name,
                "enabled": enabled,
                "operand": operand,
                "ma_order": self.parse_ma_order(cell(3)),
                "ma_above": self.parse_ma_above(cell(4)),
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
