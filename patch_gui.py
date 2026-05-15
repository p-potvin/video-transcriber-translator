import sys
import re

with open("vault_gui.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add STRINGS dictionary
strings_dict = """
STRINGS = {
    "EN": {
        "theme": "Theme",
        "lang": "Language",
        "mode": "Mode",
        "pipeline_config": "PIPELINE CONFIGURATION",
        "input": "Input File or Directory",
        "browse_file": "File…",
        "browse_folder": "Folder…",
        "skip_subdirs": "Skip Subdirectories",
        "asr_engine": "ASR Engine",
        "target_langs": "Target Languages (comma-separated)",
        "translator": "Translator Backend",
        "translate_mode": "Translate Mode",
        "source_lang": "Source Language",
        "max_dur": "Max Duration",
        "delay": "Audio Delay",
        "isolate": "Isolate Vocals",
        "skip_orig": "Skip Original SRT",
        "overwrite": "Overwrite Existing Files",
        "continue_err": "Continue on Error",
        "initiate": "▶  INITIATE PIPELINE",
        "activity": "ACTIVITY MONITOR",
        "hide": "Hide",
        "show": "Show",
        "ready": "Ready",
        "footer": "© 2026 VaultWares — All processing is local. No data leaves your machine."
    },
    "QC": {
        "theme": "Thème",
        "lang": "Langue",
        "mode": "Mode",
        "pipeline_config": "CONFIGURATION DU PIPELINE",
        "input": "Fichier ou Répertoire d'Entrée",
        "browse_file": "Fichier…",
        "browse_folder": "Dossier…",
        "skip_subdirs": "Ignorer les Sous-Dossiers",
        "asr_engine": "Moteur ASR",
        "target_langs": "Langues Cibles (séparées par des virgules)",
        "translator": "Moteur de Traduction",
        "translate_mode": "Mode de Traduction",
        "source_lang": "Langue Source",
        "max_dur": "Durée Maximale",
        "delay": "Délai Audio",
        "isolate": "Isoler la Voix",
        "skip_orig": "Ignorer le SRT Original",
        "overwrite": "Écraser les Fichiers",
        "continue_err": "Continuer si Erreur",
        "initiate": "▶  LANCER LE PIPELINE",
        "activity": "MONITEUR D'ACTIVITÉ",
        "hide": "Masquer",
        "show": "Afficher",
        "ready": "Prêt",
        "footer": "© 2026 VaultWares — Tout le traitement est local. Aucune donnée ne quitte votre machine."
    }
}
"""

if "STRINGS = {" not in code:
    code = code.replace("class VaultWindow(QMainWindow):", strings_dict + "\nclass VaultWindow(QMainWindow):")

# 2. Add language and mode state to init
init_repl = """
        self.current_lang = "EN"
        # Determine OS mode (simplified, defaulting to dark as requested if unavailable)
        self.current_mode = "dark"
        self.current_theme = self.exporter.get_theme_by_name("Golden Slate")

        self.init_ui()
"""
code = re.sub(r'        self\.current_theme = self\.themes\[0\]\s*self\.init_ui\(\)', init_repl, code, flags=re.DOTALL)

# 3. Update header construction
header_repl = """
    def _build_header(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 4)

        logo_label = QLabel()
        logo_path = "vault-themes/assets/logos/vaultwares-minimal-gold-filled.png"
        logo_pix = QPixmap(logo_path)
        if not logo_pix.isNull():
            logo_label.setPixmap(logo_pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setWindowIcon(QIcon(logo_path))
        logo_label.setObjectName("LogoLabel")
        logo_label.setFixedSize(36, 36)
        logo_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel()
        self.title_label.setTextFormat(Qt.RichText)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 300; letter-spacing: 1px;")

        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Mode switch
        self.mode_label = QLabel(STRINGS[self.current_lang]["mode"])
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Dark", "Light"])
        self.mode_combo.setCurrentText("Dark")
        self.mode_combo.currentTextChanged.connect(self.change_mode)

        # Theme selector
        self.theme_label = QLabel(STRINGS[self.current_lang]["theme"])
        self.theme_combo = QComboBox()
        self.theme_combo.setFixedWidth(200)
        for t in self.themes:
            self.theme_combo.addItem(t.name)
        self.theme_combo.setCurrentText(self.current_theme.name)
        self.theme_combo.currentTextChanged.connect(self.change_theme)

        # Language switch
        self.lang_label = QLabel(STRINGS[self.current_lang]["lang"])
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["EN", "QC"])
        self.lang_combo.setCurrentText(self.current_lang)
        self.lang_combo.currentTextChanged.connect(self.change_language)

        layout.addWidget(logo_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addItem(spacer)
        
        layout.addWidget(self.mode_label)
        layout.addWidget(self.mode_combo)
        layout.addSpacing(6)
        
        layout.addWidget(self.theme_label)
        layout.addWidget(self.theme_combo)
        layout.addSpacing(6)
        
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_combo)

        return w
"""
code = re.sub(r'    def _build_header\(self\) -> QWidget:.*?(?=    def _build_config_panel)', header_repl, code, flags=re.DOTALL)

# Add new methods to handle language and mode changes
methods_add = """
    def change_mode(self, mode_str: str):
        self.current_mode = mode_str.lower()
        if self.current_mode == "dark":
            self.theme_combo.setCurrentText("Golden Slate")
        else:
            self.theme_combo.setCurrentText("Codex Solarized Light Revisited")

    def change_language(self, lang_code: str):
        self.current_lang = lang_code
        self.update_ui_strings()

    def update_ui_strings(self):
        s = STRINGS[self.current_lang]
        self.mode_label.setText(s["mode"])
        self.theme_label.setText(s["theme"])
        self.lang_label.setText(s["lang"])
        
        self.config_panel.findChild(QLabel, "SectionTitleConfig").setText(s["pipeline_config"])
        self.monitor_panel.findChild(QLabel, "SectionTitleMonitor").setText(s["activity"])
        self.footer_label.setText(s["footer"])
        
        self.browse_file_btn.setText(s["browse_file"])
        self.browse_folder_btn.setText(s["browse_folder"])
        self.skip_subdirs_check.setText(s["skip_subdirs"])
        self.vocal_check.setText(s["isolate"])
        self.skip_orig_check.setText(s["skip_orig"])
        self.overwrite_check.setText(s["overwrite"])
        self.continue_err_check.setText(s["continue_err"])
        self.start_btn.setText(s["initiate"])
        
        self.toggle_monitor_btn.setText(s["hide"] if self.split.orientation() == Qt.Horizontal else s["show"])
        
        # Labels are harder since they are just in layouts. We can rebuild or keep track.
        # For a full implementation we'd track label references, but let's just do the ones we can grab or we update _build_config_panel
"""
code = code.replace("    def change_theme(self, theme_name: str):", methods_add + "\n    def change_theme(self, theme_name: str):")

# Fix missing label references in _build_config_panel
config_panel_repl = """
        # Title
        self.config_title = QLabel(STRINGS[self.current_lang]["pipeline_config"])
        self.config_title.setObjectName("SectionTitleConfig")
        layout.addWidget(self.config_title)
"""
code = code.replace("""        # Title
        title = QLabel("PIPELINE CONFIGURATION")
        title.setObjectName("SectionTitleConfig")
        layout.addWidget(title)""", config_panel_repl)

# Fix missing label references in _build_monitor_panel
monitor_panel_repl = """
        # Header row
        monitor_row = QHBoxLayout()
        self.monitor_title = QLabel(STRINGS[self.current_lang]["activity"])
        self.monitor_title.setObjectName("SectionTitleMonitor")
        monitor_row.addWidget(self.monitor_title)
"""
code = code.replace("""        # Header row
        monitor_row = QHBoxLayout()
        title = QLabel("ACTIVITY MONITOR")
        title.setObjectName("SectionTitleMonitor")
        monitor_row.addWidget(title)""", monitor_panel_repl)

# Fix footer 
code = code.replace("""        footer = QLabel("© 2026 VaultWares — All processing is local. No data leaves your machine.")""", """        self.footer_label = QLabel(STRINGS[self.current_lang]["footer"])""")
code = code.replace("""        footer.setAlignment(Qt.AlignCenter)""", """        self.footer_label.setAlignment(Qt.AlignCenter)""")
code = code.replace("""        footer.setObjectName("FooterLabel")""", """        self.footer_label.setObjectName("FooterLabel")""")
code = code.replace("""        root_layout.addWidget(footer)""", """        root_layout.addWidget(self.footer_label)""")

with open("vault_gui_updated.py", "w", encoding="utf-8") as f:
    f.write(code)
