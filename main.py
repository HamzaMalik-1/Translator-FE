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
        self.resize(900, 850)
        
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
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.combo_source = QComboBox()
        self.combo_source.addItems(["Auto Detect", "English", "Spanish", "French", "German", "Japanese", "Chinese", "Urdu", "Hindi", "Arabic"])
        self.combo_source.setCursor(Qt.PointingHandCursor)
        
        arrow_label = QLabel("➝")
        arrow_label.setStyleSheet("color: #5F6368; font-size: 18px;")
        
        self.combo_target = QComboBox()
        self.combo_target.addItems(["Spanish", "English", "French", "German", "Japanese", "Chinese", "Russian", "Urdu", "Hindi", "Arabic"])
        self.combo_target.setCursor(Qt.PointingHandCursor)
        
        header_layout.addWidget(self.combo_source)
        header_layout.addWidget(arrow_label)
        header_layout.addWidget(self.combo_target)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Input Area ---
        input_container = QFrame()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0,0,0,0)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text here...")
        self.input_text.setFixedHeight(150)
        
        # --- Input Toolbar ---
        input_toolbar = QHBoxLayout()
        
        self.btn_paste = QPushButton("📋 Paste")
        self.btn_paste.setObjectName("IconBtn")
        self.btn_paste.clicked.connect(self.paste_from_clipboard)

        self.btn_input_copy = QPushButton("📄 Copy")
        self.btn_input_copy.setObjectName("IconBtn")
        self.btn_input_copy.clicked.connect(self.copy_input_text)
        
        # Analyze Button
        self.btn_analyze_word = QPushButton("🔍 Define Word")
        self.btn_analyze_word.setObjectName("IconBtn")
        self.btn_analyze_word.setToolTip("Highlight a word and click to see details")
        self.btn_analyze_word.clicked.connect(self.analyze_selected_word)
        
        self.btn_input_speak = QPushButton("🔊 Listen")
        self.btn_input_speak.setObjectName("IconBtn")
        self.btn_input_speak.clicked.connect(self.speak_input)

        self.btn_mic = QPushButton("🎤 Voice Input")
        self.btn_mic.setObjectName("IconBtn")
        self.btn_mic.clicked.connect(self.start_voice_input)
        
        input_toolbar.addWidget(self.btn_paste)
        input_toolbar.addWidget(self.btn_input_copy)
        input_toolbar.addWidget(self.btn_analyze_word)
        input_toolbar.addWidget(self.btn_input_speak)
        input_toolbar.addStretch()
        input_toolbar.addWidget(self.btn_mic)
        
        input_layout.addWidget(self.input_text)
        input_layout.addLayout(input_toolbar)
        main_layout.addWidget(input_container)

        # --- Translate Button ---
        action_layout = QHBoxLayout()
        self.btn_translate = QPushButton("Translate")
        self.btn_translate.setObjectName("PrimaryBtn")
        self.btn_translate.setCursor(Qt.PointingHandCursor)
        self.btn_translate.clicked.connect(self.start_translation)
        
        self.loader = QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setFixedHeight(4)
        self.loader.setTextVisible(False)
        self.loader.setStyleSheet("QProgressBar {background-color: transparent; border: none;} QProgressBar::chunk {background-color: #1A73E8;}")
        self.loader.hide()

        action_layout.addWidget(self.btn_translate)
        main_layout.addLayout(action_layout)
        main_layout.addWidget(self.loader)

        # --- Divider ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #DADCE0;")
        main_layout.addWidget(line)

        # --- Output Area ---
        self.output_text = QTextEdit()
        self.output_text.setObjectName("ResultArea")
        self.output_text.setReadOnly(True)
        self.output_text.setFixedHeight(150)
        self.output_text.setPlaceholderText("Translation will appear here...")
        
        output_toolbar = QHBoxLayout()
        self.btn_output_speak = QPushButton("🔊 Listen")
        self.btn_output_speak.setObjectName("IconBtn")
        self.btn_output_speak.clicked.connect(self.speak_result)
        
        self.btn_output_copy = QPushButton("📋 Copy Result")
        self.btn_output_copy.setObjectName("IconBtn")
        self.btn_output_copy.clicked.connect(self.copy_output_result)
        
        output_toolbar.addStretch()
        output_toolbar.addWidget(self.btn_output_speak)
        output_toolbar.addWidget(self.btn_output_copy)

        main_layout.addWidget(self.output_text)
        main_layout.addLayout(output_toolbar)

        # --- Smart Analysis (Scrollable) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(250)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 8px; }
            QScrollBar:vertical { border: none; background: #F1F3F4; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #C1C1C1; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)


        self.analysis_content = QWidget()
        self.analysis_content.setStyleSheet("background-color: transparent;")
        
        analysis_layout = QVBoxLayout(self.analysis_content)
        analysis_layout.setContentsMargins(15, 15, 15, 15)
        analysis_layout.setSpacing(10)

        self.lbl_analysis_title = QLabel("Smart Analysis")
        self.lbl_analysis_title.setStyleSheet("color: #1A73E8; font-weight: bold; font-size: 15px; border: none;")
        analysis_layout.addWidget(self.lbl_analysis_title)

        # Labels
        self.lbl_structure = QLabel("Structure: -")
        self.lbl_structure.setWordWrap(True)
        self.lbl_structure.setStyleSheet("font-size: 13px; color: #3C4043; border: none;")
        
        self.lbl_details = QLabel("Grammar Details: -")
        self.lbl_details.setWordWrap(True)
        self.lbl_details.setStyleSheet("font-size: 13px; color: #3C4043; border: none;")
        
        self.lbl_grammar = QLabel("Grammar Check: -")
        self.lbl_grammar.setWordWrap(True)
        self.lbl_grammar.setStyleSheet("font-size: 13px; color: #3C4043; border: none;")

        self.lbl_synonyms = QLabel("Synonyms: -")
        self.lbl_synonyms.setWordWrap(True)
        self.lbl_synonyms.setStyleSheet("font-size: 13px; color: #5F6368; border: none;")
        
        self.lbl_antonyms = QLabel("Antonyms: -")
        self.lbl_antonyms.setWordWrap(True)
        self.lbl_antonyms.setStyleSheet("font-size: 13px; color: #5F6368; border: none;")

        analysis_layout.addWidget(self.lbl_structure)
        analysis_layout.addWidget(self.lbl_details)
        analysis_layout.addWidget(self.lbl_grammar)
        analysis_layout.addWidget(self.lbl_synonyms)
        analysis_layout.addWidget(self.lbl_antonyms)
        analysis_layout.addStretch()

        self.scroll_area.setWidget(self.analysis_content)
        main_layout.addWidget(self.scroll_area)
        main_layout.addStretch()

    # --- Logic ---

    def start_translation(self):
        text = self.input_text.toPlainText()
        if not text: return

        self.set_loading(True)
        self.output_text.clear()
        
        # Reset labels
        self.lbl_analysis_title.setText("Smart Analysis (Translation)")
        self.lbl_structure.show()
        self.lbl_details.show()
        self.lbl_grammar.show()
        
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
            syns = "<i>Hidden for Paragraph (Highlight a word and click 'Define Word')</i>"
            ants = "<i>Hidden for Paragraph</i>"

        self.lbl_synonyms.setText(f"<b>Synonyms:</b> {syns}")
        self.lbl_antonyms.setText(f"<b>Antonyms:</b> {ants}")
        self.lbl_structure.setText(f"<b>Structure:</b> {structure}")
        self.lbl_details.setText(f"<b>Details:</b> {details}")
        
        if grammar != "No errors found":
            self.lbl_grammar.setText(f"<b>Correction:</b> {grammar}")
            self.lbl_grammar.setStyleSheet("color: #D93025; font-size: 13px; border: none;")
        else:
            self.lbl_grammar.setText("<b>Grammar:</b> Perfect! ✅")
            self.lbl_grammar.setStyleSheet("color: #188038; font-size: 13px; border: none;")

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
        self.lbl_structure.hide()
        self.lbl_grammar.hide()
        
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
        
        self.lbl_details.show()
        self.lbl_details.setText(f"<b>Definition ({pos}):</b> {definition}")
        self.lbl_synonyms.setText(f"<b>Synonyms:</b> {syns}")
        self.lbl_antonyms.setText(f"<b>Antonyms:</b> {ants}")

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
            self.btn_input_speak.setText("...")
            self.tts_worker = TTSWorker(self.ai_service, text, lang)
            self.tts_worker.finished.connect(lambda: self.reset_speak_btn(self.btn_input_speak, "🔊 Listen"))
            self.tts_worker.start()

    def speak_result(self):
        text = self.output_text.toPlainText()
        lang = self.combo_target.currentText()
        if text:
            self.btn_output_speak.setDisabled(True)
            self.btn_output_speak.setText("...")
            self.tts_worker_out = TTSWorker(self.ai_service, text, lang)
            self.tts_worker_out.finished.connect(lambda: self.reset_speak_btn(self.btn_output_speak, "🔊 Listen"))
            self.tts_worker_out.start()

    def reset_speak_btn(self, btn, original_text):
        btn.setDisabled(False)
        btn.setText(original_text)

    def paste_from_clipboard(self):
        self.input_text.setText(pyperclip.paste())

    def copy_input_text(self):
        self.copy_to_clip(self.input_text.toPlainText(), self.btn_input_copy, "📄 Copy")

    def copy_output_result(self):
        self.copy_to_clip(self.output_text.toPlainText(), self.btn_output_copy, "📋 Copy Result")

    def copy_to_clip(self, text, button, original_text):
        if text:
            pyperclip.copy(text)
            button.setText("Copied!")
            QTimer.singleShot(2000, lambda: button.setText(original_text))

    def set_loading(self, is_loading):
        if is_loading:
            self.loader.show()
            self.btn_translate.setDisabled(True)
            self.btn_translate.setText("Processing...")
        else:
            self.loader.hide()
            self.btn_translate.setDisabled(False)
            self.btn_translate.setText("Translate")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GeminiTranslatorApp()
    window.show()
    sys.exit(app.exec())