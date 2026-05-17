import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
from PySide6.QtWidgets import QApplication
from vault_gui import VaultWindow

app = QApplication(sys.argv)
win = VaultWindow()
sys.stdout = win.original_stdout
print("monitor_panel in dir(win)?", "monitor_panel" in dir(win))
