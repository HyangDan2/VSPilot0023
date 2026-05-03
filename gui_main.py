import sys
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kiwoom Static Scanner")
    win = MainWindow()
    win.resize(1200, 760)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
