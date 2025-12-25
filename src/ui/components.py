"""
UI Components for the translator app
"""
import re
import re
import pyperclip
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QMenu, QFrame, QProgressBar, QMessageBox  # Added QPushButton here
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QContextMenuEvent
from src.utils.language_utils import is_urdu, has_english, format_synonyms_antonyms
# Urdu Label Mappings
URDU_LABELS = {
    "Structure": "ساخت",
    "Grammar": "قواعد",
    "Synonyms": "مترادفات",
    "Antonyms": "متضاد",
    "Correction": "تصحیح"
}

class AnalysisPanel(QScrollArea):
    """Reusable analysis panel widget"""
    
    def __init__(self, title="Analysis"):
        super().__init__()
        self.setWidgetResizable(True)
        self.setMaximumHeight(250)
        # Modern Card Style
        self.setStyleSheet("""
            QScrollArea { background-color: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; }
            QScrollBar:vertical { border: none; background: #F1F3F4; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #C1C1C1; min-height: 20px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12) 

        # Title Label
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #1A73E8; font-weight: bold; font-size: 14px; border: none; margin-bottom: 5px;")
        self.layout.addWidget(self.lbl_title)

        # Content Labels (Stored in a dict for easy updating)
        self.labels = {}
        # Keys used internally
        self.keys = ["Structure", "Grammar", "Synonyms", "Antonyms", "Correction"]
        
        for key in self.keys:
            lbl = QLabel(f"{key}: -")
            lbl.setWordWrap(True)
            # Default style
            lbl.setStyleSheet("font-size: 14px; color: #3C4043; border: none; line-height: 1.4;")
            self.layout.addWidget(lbl)
            self.labels[key] = lbl

        self.labels["Correction"].hide() 
        self.layout.addStretch()
        self.setWidget(self.content_widget)

    def update_data(self, data, is_source=False, force_language=None):
        """
        Updates labels and applies RTL alignment AND Urdu Label Translation.
        force_language: Optional parameter to force language detection ('urdu' or 'english')
        """
        # 1. Extract Raw Data
        raw_struct = data.get('structure', '-')
        raw_grammar = data.get('grammar', '-')
        raw_syns = format_synonyms_antonyms(data.get('synonyms', []))
        raw_ants = format_synonyms_antonyms(data.get('antonyms', []))
        raw_corr = data.get("correction", "No data")

        # 2. Clean Urdu data (remove English text)
        if force_language == 'urdu':
            from src.utils.language_utils import clean_urdu_text
            raw_struct = clean_urdu_text(raw_struct)
            raw_grammar = clean_urdu_text(raw_grammar)
            raw_syns = clean_urdu_text(raw_syns) if isinstance(raw_syns, str) else raw_syns
            raw_ants = clean_urdu_text(raw_ants) if isinstance(raw_ants, str) else raw_ants
            raw_corr = clean_urdu_text(raw_corr)

        # 3. Detect Language 
        # Use force_language if provided, otherwise auto-detect
        if force_language == 'urdu':
            is_content_urdu = True
        elif force_language == 'english':
            is_content_urdu = False
        else:
            # Auto-detect based on cleaned content
            is_content_urdu = is_urdu(raw_struct) or is_urdu(raw_grammar)

        # 4. Helper to format the final string (<b>Label:</b> Value)
        def set_label_text(key, value, is_urdu_mode):
            label_title = URDU_LABELS[key] if is_urdu_mode else key
            return f"<b>{label_title}:</b> {value}"

        # 5. Update Standard Labels
        self.labels["Structure"].setText(set_label_text("Structure", raw_struct, is_content_urdu))
        self.labels["Grammar"].setText(set_label_text("Grammar", raw_grammar, is_content_urdu))
        self.labels["Synonyms"].setText(set_label_text("Synonyms", raw_syns, is_content_urdu))
        self.labels["Antonyms"].setText(set_label_text("Antonyms", raw_ants, is_content_urdu))

        # 6. Handle Correction (Source Only)
        if is_source:
            if raw_corr and raw_corr != "No data" and raw_corr != "No errors found" and raw_corr != "Correct":
                self.labels["Correction"].show()
                # Check if correction itself is Urdu
                corr_is_urdu = is_urdu(raw_corr) if not force_language else (force_language == 'urdu')
                label_title = URDU_LABELS["Correction"] if corr_is_urdu else "Correction"
                
                self.labels["Correction"].setText(f"<b>{label_title}:</b> {raw_corr}")
                self.labels["Correction"].setStyleSheet("color: #D93025; font-size: 14px;") 
                
                if corr_is_urdu: 
                    self.labels["Correction"].setAlignment(Qt.AlignRight)
                else: 
                    self.labels["Correction"].setAlignment(Qt.AlignLeft)
            else:
                self.labels["Correction"].show()
                # "Perfect" message
                msg = "زبردست! ✅" if is_content_urdu else "Perfect! ✅"
                label_title = URDU_LABELS["Correction"] if is_content_urdu else "Correction"
                
                self.labels["Correction"].setText(f"<b>{label_title}:</b> {msg}")
                self.labels["Correction"].setStyleSheet("color: #188038; font-size: 14px;")
                
                if is_content_urdu: 
                    self.labels["Correction"].setAlignment(Qt.AlignRight)
                else: 
                    self.labels["Correction"].setAlignment(Qt.AlignLeft)
        else:
            self.labels["Correction"].hide()

        # 7. Apply Alignment & Fonts
        for key, lbl in self.labels.items():
            if key == "Correction": 
                continue 
            
            # Use the panel-wide language detection for alignment consistency
            if is_content_urdu:
                lbl.setAlignment(Qt.AlignRight)
                # Try multiple Urdu fonts with fallbacks
                urdu_fonts = ["Noto Nastaliq Urdu", "Jameel Noori Nastaleeq", "Urdu Naskh Asiatype", "Arial"]
                font_found = False
                for font_name in urdu_fonts:
                    font = QFont(font_name, 12)
                    if font.exactMatch() or font_name == "Arial":  # Arial as last resort
                        lbl.setFont(font)
                        font_found = True
                        break
                if not font_found:
                    lbl.setFont(QFont("Segoe UI", 10))  # Fallback to Segoe UI
            else:
                lbl.setAlignment(Qt.AlignLeft)
                lbl.setFont(QFont("Segoe UI", 10))


class BilingualTextEdit(QTextEdit):
    """Custom text edit with bilingual context menu"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu(self)
        
        # Create bilingual menu items
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        menu.addAction(redo_action)
        
        menu.addSeparator()
        
        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.cut)
        menu.addAction(cut_action)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)
        
        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(lambda: self.textCursor().removeSelectedText())
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)
        
        # Apply custom styling to the menu
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #DADCE0;
                border-radius: 8px;
                padding: 8px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
                color: #202124;
                font-size: 14px;
                min-width: 200px;
            }
            QMenu::item:selected {
                background-color: #E8F0FE;
                color: #1A73E8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #F1F3F4;
                margin: 4px 0;
            }
        """)
        
        menu.exec(event.globalPos())


class IconButton(QPushButton):
    """Custom icon button with hover effects"""
    
    def __init__(self, text, tooltip, callback, parent=None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(callback)
        self.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 20px; 
                font-size: 18px; 
                background-color: transparent; 
                color: #5F6368; 
            } 
            QPushButton:hover { 
                background-color: #F1F3F4; 
                color: #202124; 
            }
        """)