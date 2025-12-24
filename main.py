import sys
import pyperclip
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QPushButton, QComboBox, 
                               QLabel, QFrame, QProgressBar, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont

# Import our modules
from backend import AIService
from worker import TranslationWorker, AudioWorker, TTSWorker, WordAnalysisWorker

class GeminiTranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ai_service = AIService()
        self.setWindowTitle("Gemini AI Translator")
        self.resize(1000, 800) # Slightly wider for comfortable side-by-side view
        
        # Load Styles
        try:
            with open("styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # =======================================================
        # 1. HEADER (Language Selection & Swap) - Kept Original
        # =======================================================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Source Language
        self.combo_source = QComboBox()
        self.combo_source.addItems(["Auto Detect", "English", "Urdu", "Spanish", "French", "German", "Chinese", "Arabic"])
        self.combo_source.setFixedWidth(220)
        self.combo_source.setCursor(Qt.PointingHandCursor)
        self.combo_source.setStyleSheet("padding: 8px; font-size: 14px;")

        # Swap Button (Center)
        self.btn_swap = QPushButton("⇄")
        self.btn_swap.setFixedSize(40, 40)
        self.btn_swap.setCursor(Qt.PointingHandCursor)
        self.btn_swap.setStyleSheet("""
            QPushButton {
                border: 1px solid #DADCE0;
                border-radius: 20px;
                font-size: 20px;
                color: #5F6368;
                background-color: white;
            }
            QPushButton:hover { background-color: #F1F3F4; }
        """)
        self.btn_swap.clicked.connect(self.swap_languages)

        # Target Language
        self.combo_target = QComboBox()
        self.combo_target.addItems(["English", "Urdu", "Spanish", "French", "German", "Chinese", "Arabic"])
        self.combo_target.setCurrentText("Urdu")
        self.combo_target.setFixedWidth(220)
        self.combo_target.setCursor(Qt.PointingHandCursor)
        self.combo_target.setStyleSheet("padding: 8px; font-size: 14px;")

        header_layout.addStretch()
        header_layout.addWidget(self.combo_source)
        header_layout.addWidget(self.btn_swap)
        header_layout.addWidget(self.combo_target)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # =======================================================
        # 2. MAIN CONTENT (Side-by-Side Input/Output Cards)
        # =======================================================
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # --- LEFT CARD (INPUT) ---
        input_card = QFrame()
        input_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; }")
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(0, 0, 0, 0)
        input_card_layout.setSpacing(0)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text here...")
        self.input_text.setFrameShape(QFrame.NoFrame)
        self.input_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")

        # Input Toolbar (Bottom of Left Card)
        input_toolbar = QFrame()
        input_toolbar.setStyleSheet("QFrame { border-top: 1px solid #F1F3F4; background-color: transparent; border-left: none; border-right: none; border-bottom: none;}")
        input_toolbar_layout = QHBoxLayout(input_toolbar)
        input_toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # Toolbar Buttons
        self.btn_mic = self.create_icon_btn("🎤", "Voice Input", self.start_voice_input)
        self.btn_input_speak = self.create_icon_btn("🔊", "Listen", self.speak_input)
        self.btn_paste = self.create_icon_btn("📋", "Paste", self.paste_from_clipboard)
        self.btn_analyze_word = self.create_icon_btn("🔍", "Define Word", self.analyze_selected_word)
        
        # Layout Input Toolbar
        input_toolbar_layout.addWidget(self.btn_mic)
        input_toolbar_layout.addWidget(self.btn_input_speak)
        input_toolbar_layout.addStretch()
        input_toolbar_layout.addWidget(self.btn_analyze_word)
        input_toolbar_layout.addWidget(self.btn_paste)

        input_card_layout.addWidget(self.input_text)
        input_card_layout.addWidget(input_toolbar)

        # --- RIGHT CARD (OUTPUT) ---
        output_card = QFrame()
        output_card.setStyleSheet("QFrame { background-color: #F8F9FA; border: 1px solid #DADCE0; border-radius: 8px; }")
        output_card_layout = QVBoxLayout(output_card)
        output_card_layout.setContentsMargins(0, 0, 0, 0)
        output_card_layout.setSpacing(0)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("Translation...")
        self.output_text.setReadOnly(True)
        self.output_text.setFrameShape(QFrame.NoFrame)
        self.output_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")

        # Output Toolbar (Bottom of Right Card)
        output_toolbar = QFrame()
        output_toolbar.setStyleSheet("QFrame { border-top: 1px solid #E0E0E0; background-color: transparent; border-left: none; border-right: none; border-bottom: none; }")
        output_toolbar_layout = QHBoxLayout(output_toolbar)
        output_toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_output_speak = self.create_icon_btn("🔊", "Listen", self.speak_result)
        self.btn_output_copy = self.create_icon_btn("📄", "Copy Result", self.copy_output_result)

        # Layout Output Toolbar
        output_toolbar_layout.addWidget(self.btn_output_speak)
        output_toolbar_layout.addStretch()
        output_toolbar_layout.addWidget(self.btn_output_copy)

        output_card_layout.addWidget(self.output_text)
        output_card_layout.addWidget(output_toolbar)

        # Add both cards to main horizontal layout
        content_layout.addWidget(input_card)
        content_layout.addWidget(output_card)
        main_layout.addLayout(content_layout)

        # =======================================================
        # 3. TRANSLATE BUTTON
        # =======================================================
        btn_container = QHBoxLayout()
        self.btn_translate = QPushButton("Translate")
        self.btn_translate.setCursor(Qt.PointingHandCursor)
        self.btn_translate.setFixedSize(200, 48)
        self.btn_translate.setStyleSheet("""
            QPushButton {
                background-color: #1A73E8; 
                color: white; 
                font-weight: bold; 
                font-size: 16px; 
                border-radius: 24px;
                border: none;
            }
            QPushButton:hover { background-color: #1765CC; }
            QPushButton:pressed { background-color: #1659B2; }
            QPushButton:disabled { background-color: #AECBFA; }
        """)
        self.btn_translate.clicked.connect(self.start_translation)
        
        btn_container.addStretch()
        btn_container.addWidget(self.btn_translate)
        btn_container.addStretch()
        
        main_layout.addLayout(btn_container)

        # Progress Bar (Hidden)
        self.loader = QProgressBar()
        self.loader.setFixedHeight(4)
        self.loader.setTextVisible(False)
        self.loader.setStyleSheet("QProgressBar {background-color: transparent; border: none;} QProgressBar::chunk {background-color: #1A73E8;}")
        self.loader.hide()
        main_layout.addWidget(self.loader)

        # =======================================================
        # 4. SMART ANALYSIS (Scrollable)
        # =======================================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(220)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; margin-top: 10px; }
            QScrollBar:vertical { border: none; background: #F1F3F4; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #C1C1C1; min-height: 20px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.analysis_content = QWidget()
        self.analysis_content.setStyleSheet("background-color: transparent;")
        
        analysis_layout = QVBoxLayout(self.analysis_content)
        analysis_layout.setContentsMargins(20, 20, 20, 20)
        analysis_layout.setSpacing(10)

        self.lbl_analysis_title = QLabel("Smart Analysis")
        self.lbl_analysis_title.setStyleSheet("color: #1A73E8; font-weight: bold; font-size: 15px; border: none;")
        analysis_layout.addWidget(self.lbl_analysis_title)

        # Analysis Labels
        self.lbl_structure = QLabel("Structure: -")
        self.lbl_details = QLabel("Grammar Details: -")
        self.lbl_grammar = QLabel("Grammar Check: -")
        self.lbl_synonyms = QLabel("Synonyms: -")
        self.lbl_antonyms = QLabel("Antonyms: -")

        for lbl in [self.lbl_structure, self.lbl_details, self.lbl_grammar, self.lbl_synonyms, self.lbl_antonyms]:
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 14px; color: #3C4043; border: none;")
            analysis_layout.addWidget(lbl)

        analysis_layout.addStretch()
        self.scroll_area.setWidget(self.analysis_content)
        main_layout.addWidget(self.scroll_area)

    # --- Helper to create consistent icon buttons ---
    def create_icon_btn(self, text, tooltip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 20px; 
                font-size: 18px; 
                background-color: transparent;
                color: #5F6368;
            } 
            QPushButton:hover { background-color: #F1F3F4; color: #202124; }
        """)
        return btn

    # --- Logic ---

    def swap_languages(self):
        src_idx = self.combo_source.currentIndex()
        tgt_txt = self.combo_target.currentText()
        
        # Swap combo box texts (approximation)
        self.combo_source.setCurrentText(tgt_txt)
        
        # Swap text content
        input_text = self.input_text.toPlainText()
        output_text = self.output_text.toPlainText()
        
        if output_text:
            self.input_text.setText(output_text)
            self.output_text.clear()

    def start_translation(self):
        text = self.input_text.toPlainText()
        if not text: return

        self.set_loading(True)
        self.output_text.clear()
        
        self.lbl_analysis_title.setText("Smart Analysis (Translation)")
        
        self.worker = TranslationWorker(self.ai_service, text, self.combo_source.currentText(), self.combo_target.currentText())
        self.worker.finished.connect(self.handle_translation_result)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_translation_result(self, result):
        self.set_loading(False)
        self.output_text.setText(result.get("translation", ""))
        
        structure = result.get("sentence_structure", "-")
        details = result.get("grammar_details", "-")
        grammar = result.get("grammar_correction", "No data")
        
        syns_list = result.get("synonyms", [])
        ants_list = result.get("antonyms", [])
        
        if syns_list:
            syns = ", ".join(syns_list)
            ants = ", ".join(ants_list)
        else:
            syns = "<i>Hidden for Paragraph</i>"
            ants = "<i>Hidden for Paragraph</i>"

        self.lbl_synonyms.setText(f"<b>Synonyms:</b> {syns}")
        self.lbl_antonyms.setText(f"<b>Antonyms:</b> {ants}")
        self.lbl_structure.setText(f"<b>Structure:</b> {structure}")
        self.lbl_details.setText(f"<b>Details:</b> {details}")
        
        if grammar != "No errors found":
            self.lbl_grammar.setText(f"<b>Correction:</b> {grammar}")
            self.lbl_grammar.setStyleSheet("color: #D93025; font-size: 14px; border: none;")
        else:
            self.lbl_grammar.setText("<b>Grammar:</b> Perfect! ✅")
            self.lbl_grammar.setStyleSheet("color: #188038; font-size: 14px; border: none;")

    def analyze_selected_word(self):
        cursor = self.input_text.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if not selected_text:
            QMessageBox.information(self, "No Selection", "Please highlight a word in the input box first.")
            return
            
        if len(selected_text.split()) > 3:
             QMessageBox.warning(self, "Selection Too Long", "Please select only one or two words to define.")
             return

        self.set_loading(True)
        self.lbl_analysis_title.setText(f"Word Analysis: '{selected_text}'")
        
        self.word_worker = WordAnalysisWorker(self.ai_service, selected_text)
        self.word_worker.finished.connect(self.handle_word_result)
        self.word_worker.error.connect(self.handle_error)
        self.word_worker.start()

    def handle_word_result(self, result):
        self.set_loading(False)
        definition = result.get("definition", "-")
        pos = result.get("part_of_speech", "-")
        syns = ", ".join(result.get("synonyms", []))
        ants = ", ".join(result.get("antonyms", []))
        
        self.lbl_details.setText(f"<b>Definition ({pos}):</b> {definition}")
        self.lbl_synonyms.setText(f"<b>Synonyms:</b> {syns}")
        self.lbl_antonyms.setText(f"<b>Antonyms:</b> {ants}")
        self.lbl_structure.setText("")
        self.lbl_grammar.setText("")

    def handle_error(self, error_msg):
        self.set_loading(False)
        QMessageBox.warning(self, "Notice", f"{error_msg}")

    # --- Standard Handlers ---
    def start_voice_input(self):
        self.input_text.setPlaceholderText("Listening... speak now...")
        self.btn_mic.setDisabled(True)
        self.audio_worker = AudioWorker(self.ai_service)
        self.audio_worker.finished.connect(self.handle_voice_result)
        self.audio_worker.start()

    def handle_voice_result(self, text):
        self.btn_mic.setDisabled(False)
        if text: self.input_text.setText(text)
        else: self.input_text.setPlaceholderText("Could not hear audio. Try again.")

    def speak_input(self):
        text = self.input_text.toPlainText()
        lang = self.combo_source.currentText()
        if text:
            self.btn_input_speak.setDisabled(True)
            self.tts_worker = TTSWorker(self.ai_service, text, lang)
            self.tts_worker.finished.connect(lambda: self.btn_input_speak.setDisabled(False))
            self.tts_worker.start()

    def speak_result(self):
        text = self.output_text.toPlainText()
        lang = self.combo_target.currentText()
        if text:
            self.btn_output_speak.setDisabled(True)
            self.tts_worker_out = TTSWorker(self.ai_service, text, lang)
            self.tts_worker_out.finished.connect(lambda: self.btn_output_speak.setDisabled(False))
            self.tts_worker_out.start()

    def paste_from_clipboard(self):
        self.input_text.setText(pyperclip.paste())

    def copy_output_result(self):
        text = self.output_text.toPlainText()
        if text:
            pyperclip.copy(text)
            self.btn_output_copy.setStyleSheet("background-color: #E8F0FE; border-radius: 20px;")
            QTimer.singleShot(500, lambda: self.btn_output_copy.setStyleSheet("background-color: transparent; border-radius: 20px;"))

    def set_loading(self, is_loading):
        if is_loading:
            self.loader.show()
            self.btn_translate.setText("Translating...")
            self.btn_translate.setDisabled(True)
        else:
            self.loader.hide()
            self.btn_translate.setText("Translate")
            self.btn_translate.setDisabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeminiTranslatorApp()
    window.show()
    sys.exit(app.exec())