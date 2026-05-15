import sys
import re

with open("vault_gui.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update minimum size
code = code.replace("self.setMinimumSize(1100, 700)", "self.setMinimumSize(400, 400)")

# 2. Add QScrollArea to init_ui
init_ui_repl = """
    def init_ui(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(self.scroll_area)
        
        root = QWidget()
        self.scroll_area.setWidget(root)
        
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 10, 16, 10)
        root_layout.setSpacing(10)

        # ── Header ────────────────────────────────────────────────────────
        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._make_separator())

        # ── Main split (config | monitor) ────────────────────────────────
        self.split = QSplitter(Qt.Horizontal)
        self.config_panel = self._build_config_panel()
        self.monitor_panel = self._build_monitor_panel()
        self.split.addWidget(self.config_panel)
        self.split.addWidget(self.monitor_panel)
        self.split.setStretchFactor(0, 4)
        self.split.setStretchFactor(1, 6)
        
        root_layout.addWidget(self.split, stretch=1)

        # ── Footer ────────────────────────────────────────────────────────
        root_layout.addWidget(self._make_separator())
        self.footer_label = QLabel(STRINGS[self.current_lang]["footer"])
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setObjectName("FooterLabel")
        root_layout.addWidget(self.footer_label)

        self._setup_accessibility()
"""
# Replace the whole init_ui function up to _build_header
code = re.sub(r'    def init_ui\(self\):.*?        self\._setup_accessibility\(\)', init_ui_repl.strip('\n'), code, flags=re.DOTALL)

# 3. Reduce spacing in header
code = code.replace("layout.addSpacing(10)", "layout.addSpacing(2)", 1)

# 4. Resize event for Splitter
resize_event = """
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() < 800:
            if self.split.orientation() != Qt.Vertical:
                self.split.setOrientation(Qt.Vertical)
                # Put monitor on top
                self.split.insertWidget(0, self.monitor_panel)
                self.split.insertWidget(1, self.config_panel)
        else:
            if self.split.orientation() != Qt.Horizontal:
                self.split.setOrientation(Qt.Horizontal)
                self.split.insertWidget(0, self.config_panel)
                self.split.insertWidget(1, self.monitor_panel)
"""
if "def resizeEvent" not in code:
    code = code.replace("    def _setup_accessibility(self):", resize_event + "\n    def _setup_accessibility(self):")


# 5. Monitor header formatting
monitor_repl = """
        # Header row
        monitor_row = QHBoxLayout()
        self.monitor_title = QLabel(STRINGS[self.current_lang]["activity"])
        self.monitor_title.setObjectName("SectionTitleMonitor")
        monitor_row.addWidget(self.monitor_title)
        monitor_row.addStretch()

        self.status_badge = QLabel(STRINGS[self.current_lang]["idle"])
        self.status_badge.setObjectName("TagBadge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        monitor_row.addWidget(self.status_badge)
        
        self.toggle_monitor_btn = QPushButton()
        self.toggle_monitor_btn.setText(STRINGS[self.current_lang]["hide"])
        self.toggle_monitor_btn.setObjectName("SecondaryBtn")
        self.toggle_monitor_btn.clicked.connect(self.toggle_monitor)
        monitor_row.addWidget(self.toggle_monitor_btn)
"""
code = re.sub(r'        # Header row.*?monitor_row\.addWidget\(self\.toggle_monitor_btn\)', monitor_repl.strip('\n'), code, flags=re.DOTALL)

# Update badge translations inside code
code = code.replace('self.status_badge.setText("RUNNING")', 'self.status_badge.setText(STRINGS[self.current_lang]["running"])')
code = code.replace('self.status_badge.setText("FAILED")', 'self.status_badge.setText(STRINGS[self.current_lang]["failed"])')
code = code.replace('self.status_badge.setText("DONE")', 'self.status_badge.setText(STRINGS[self.current_lang]["done"])')
code = code.replace('self.status_badge.setText("IDLE")', 'self.status_badge.setText(STRINGS[self.current_lang]["idle"])')

# Add missing style class SecondaryBtn to qss in qt_exporter
with open("patch_gui3_result.txt", "w", encoding="utf-8") as f:
    f.write("ready")

with open("vault_gui.py", "w", encoding="utf-8") as f:
    f.write(code)
