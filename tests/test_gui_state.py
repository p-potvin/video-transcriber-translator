import sys
import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Append the project root so we can import vault_gui
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vault_gui import VaultWindow
from tests.utils.layout_auditor import audit_widget_tree

def test_gui_hiding_monitor(qtbot):
    """
    Test that hiding the activity monitor does not squish or overlap the remaining components.
    """
    window = VaultWindow()
    qtbot.addWidget(window)
    
    # Wait for it to become visible and processed
    window.show()
    qtbot.waitExposed(window)
    
    # Intentionally agitate the UI by collapsing the monitor panel
    if hasattr(window, 'toggle_monitor_btn'):
        window.toggle_monitor_btn.click()
    else:
        pytest.fail("Could not find toggle_monitor_btn")
    
    # Wait for qt event loop to process layout changes
    qtbot.wait(200)

    # Let's also shrink the window size to a ridiculous minimum to force responsive boundaries
    window.resize(600, 400)
    qtbot.wait(200)

    # Run the layout auditor
    errors = audit_widget_tree(window)
    
    if errors:
        pytest.fail("Layout issues detected:\n" + "\n".join(errors))
