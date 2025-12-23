import sys
from PyQt6.QtWidgets import QApplication
from app_window import MainInterface  # import the main window class

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainInterface()
    window.show()
    sys.exit(app.exec())
