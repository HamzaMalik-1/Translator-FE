import sys
import pyperclip
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QPushButton, QComboBox, 
                               QLabel, QFrame, QProgressBar, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont

# Import our modules
from backend import AIService
from worker import TranslationWorker, AudioWorker, TTSWorker, WordAnalysisWorker

# --- HELPER CLASS: Analysis Panel (Reusable Card) ---
class AnalysisPanel(QScrollArea):
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

    def update_data(self, data, is_source=False):
        """
        Updates labels and applies RTL alignment AND Urdu Label Translation.
        """
        def fmt_list(key):
            val = data.get(key, [])
            return ", ".join(val) if val else "-"

        # Helper to check for Urdu characters
        def is_urdu(text):
            return bool(re.search(r'[\u0600-\u06FF]', str(text)))

        # Urdu Label Mappings
        URDU_LABELS = {
            "Structure": "ساخت",
            "Grammar": "قواعد",
            "Synonyms": "مترادفات",
            "Antonyms": "متضاد",
            "Correction": "تصحیح"
        }

        # 1. Extract Raw Data
        raw_struct = data.get('structure', '-')
        raw_grammar = data.get('grammar', '-')
        raw_syns = fmt_list('synonyms')
        raw_ants = fmt_list('antonyms')
        raw_corr = data.get("correction", "No data")

        # 2. Detect Language (Check structure field to decide panel language)
        # If the content is Urdu, we switch the Headers to Urdu too.
        is_content_urdu = is_urdu(raw_struct) or is_urdu(raw_grammar)

        # 3. Helper to format the final string (<b>Label:</b> Value)
        def set_label_text(key, value, is_urdu_mode):
            label_title = URDU_LABELS[key] if is_urdu_mode else key
            return f"<b>{label_title}:</b> {value}"

        # 4. Update Standard Labels
        self.labels["Structure"].setText(set_label_text("Structure", raw_struct, is_content_urdu))
        self.labels["Grammar"].setText(set_label_text("Grammar", raw_grammar, is_content_urdu))
        self.labels["Synonyms"].setText(set_label_text("Synonyms", raw_syns, is_content_urdu))
        self.labels["Antonyms"].setText(set_label_text("Antonyms", raw_ants, is_content_urdu))

        # 5. Handle Correction (Source Only)
        if is_source:
            if raw_corr and raw_corr != "No errors found" and raw_corr != "Correct":
                self.labels["Correction"].show()
                # Check if correction itself is Urdu
                corr_is_urdu = is_urdu(raw_corr)
                label_title = URDU_LABELS["Correction"] if corr_is_urdu else "Correction"
                
                self.labels["Correction"].setText(f"<b>{label_title}:</b> {raw_corr}")
                self.labels["Correction"].setStyleSheet("color: #D93025; font-size: 14px;") 
                
                if corr_is_urdu: self.labels["Correction"].setAlignment(Qt.AlignRight)
                else: self.labels["Correction"].setAlignment(Qt.AlignLeft)
            else:
                self.labels["Correction"].show()
                # "Perfect" message
                msg = "زبردست! ✅" if is_content_urdu else "Perfect! ✅"
                label_title = URDU_LABELS["Correction"] if is_content_urdu else "Correction"
                
                self.labels["Correction"].setText(f"<b>{label_title}:</b> {msg}")
                self.labels["Correction"].setStyleSheet("color: #188038; font-size: 14px;")
                
                if is_content_urdu: self.labels["Correction"].setAlignment(Qt.AlignRight)
                else: self.labels["Correction"].setAlignment(Qt.AlignLeft)
        else:
            self.labels["Correction"].hide()

        # 6. Apply Alignment & Fonts
        for key, lbl in self.labels.items():
            if key == "Correction": continue 
            
            # Use the panel-wide language detection for alignment consistency
            if is_content_urdu:
                lbl.setAlignment(Qt.AlignRight)
                lbl.setFont(QFont("Noto Nastaliq Urdu", 12)) 
            else:
                lbl.setAlignment(Qt.AlignLeft)
                lbl.setFont(QFont("Segoe UI", 10))


# --- MAIN APP ---
class GeminiTranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.ai_service = AIService()
        self.setWindowTitle("Gemini AI Translator")
        self.resize(1100, 900)
        
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

        # 1. HEADER
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        self.combo_source = QComboBox()
        self.combo_source.addItems(["Auto Detect", "English", "Urdu", "Spanish", "French", "German", "Chinese", "Arabic"])
        self.combo_source.setFixedWidth(220)
        self.combo_source.setCursor(Qt.PointingHandCursor)
        self.combo_source.setStyleSheet("padding: 8px; font-size: 14px;")

        self.btn_swap = QPushButton("⇄")
        self.btn_swap.setFixedSize(40, 40)
        self.btn_swap.setCursor(Qt.PointingHandCursor)
        self.btn_swap.clicked.connect(self.swap_languages)
        self.btn_swap.setStyleSheet("""
            QPushButton { border: 1px solid #DADCE0; border-radius: 20px; font-size: 20px; color: #5F6368; background-color: white; }
            QPushButton:hover { background-color: #F1F3F4; }
        """)

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

        # 2. INPUT/OUTPUT CARDS
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left Card
        input_card = QFrame()
        input_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; }")
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text here...")
        self.input_text.setFrameShape(QFrame.NoFrame)
        self.input_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")
        
        input_toolbar = QFrame()
        input_toolbar.setStyleSheet("QFrame { border-top: 1px solid #F1F3F4; background-color: transparent; }")
        it_layout = QHBoxLayout(input_toolbar)
        it_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_mic = self.create_icon_btn("🎤", "Voice Input", self.start_voice_input)
        self.btn_input_speak = self.create_icon_btn("🔊", "Listen", self.speak_input)
        self.btn_paste = self.create_icon_btn("📋", "Paste", self.paste_from_clipboard)
        self.btn_analyze_word = self.create_icon_btn("🔍", "Define Word", self.analyze_selected_word)
        
        it_layout.addWidget(self.btn_mic)
        it_layout.addWidget(self.btn_input_speak)
        it_layout.addStretch()
        it_layout.addWidget(self.btn_analyze_word)
        it_layout.addWidget(self.btn_paste)
        
        input_card_layout.addWidget(self.input_text)
        input_card_layout.addWidget(input_toolbar)

        # Right Card
        output_card = QFrame()
        output_card.setStyleSheet("QFrame { background-color: #F8F9FA; border: 1px solid #DADCE0; border-radius: 8px; }")
        output_card_layout = QVBoxLayout(output_card)
        output_card_layout.setContentsMargins(0, 0, 0, 0)
        
        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("Translation...")
        self.output_text.setReadOnly(True)
        self.output_text.setFrameShape(QFrame.NoFrame)
        self.output_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")
        
        output_toolbar = QFrame()
        output_toolbar.setStyleSheet("QFrame { border-top: 1px solid #E0E0E0; background-color: transparent; }")
        ot_layout = QHBoxLayout(output_toolbar)
        ot_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_output_speak = self.create_icon_btn("🔊", "Listen", self.speak_result)
        self.btn_output_copy = self.create_icon_btn("📄", "Copy Result", self.copy_output_result)
        
        ot_layout.addWidget(self.btn_output_speak)
        ot_layout.addStretch()
        ot_layout.addWidget(self.btn_output_copy)
        
        output_card_layout.addWidget(self.output_text)
        output_card_layout.addWidget(output_toolbar)

        content_layout.addWidget(input_card)
        content_layout.addWidget(output_card)
        main_layout.addLayout(content_layout)

        # 3. TRANSLATE BUTTON
        btn_container = QHBoxLayout()
        self.btn_translate = QPushButton("Translate")
        self.btn_translate.setCursor(Qt.PointingHandCursor)
        self.btn_translate.setFixedSize(200, 48)
        self.btn_translate.setStyleSheet("""
            QPushButton { background-color: #1A73E8; color: white; font-weight: bold; font-size: 16px; border-radius: 24px; border: none; }
            QPushButton:hover { background-color: #1765CC; }
            QPushButton:disabled { background-color: #AECBFA; }
        """)
        self.btn_translate.clicked.connect(self.start_translation)
        
        btn_container.addStretch()
        btn_container.addWidget(self.btn_translate)
        btn_container.addStretch()
        main_layout.addLayout(btn_container)

        self.loader = QProgressBar()
        self.loader.setFixedHeight(4)
        self.loader.setTextVisible(False)
        self.loader.setStyleSheet("QProgressBar {background-color: transparent; border: none;} QProgressBar::chunk {background-color: #1A73E8;}")
        self.loader.hide()
        main_layout.addWidget(self.loader)

        # 4. DUAL SMART ANALYSIS
        analysis_container = QHBoxLayout()
        analysis_container.setSpacing(20)

        self.left_analysis = AnalysisPanel("Source Analysis")
        self.right_analysis = AnalysisPanel("Target Analysis")

        analysis_container.addWidget(self.left_analysis)
        analysis_container.addWidget(self.right_analysis)
        main_layout.addLayout(analysis_container)

    def create_icon_btn(self, text, tooltip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(40, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.setStyleSheet("QPushButton { border: none; border-radius: 20px; font-size: 18px; background-color: transparent; color: #5F6368; } QPushButton:hover { background-color: #F1F3F4; color: #202124; }")
        return btn

    # --- Logic ---

    def swap_languages(self):
        original_source = self.combo_source.currentText()
        tgt_txt = self.combo_target.currentText()
        
        self.combo_source.setCurrentText(tgt_txt)
        
        if original_source == "Auto Detect":
            self.combo_target.setCurrentText("English")
        else:
            self.combo_target.setCurrentText(original_source)
            
        current_output = self.output_text.toPlainText()
        if current_output:
            self.input_text.setText(current_output)
            self.output_text.clear()
            self.left_analysis.lbl_title.setText(f"{tgt_txt} Analysis")
            self.right_analysis.lbl_title.setText(f"{original_source} Analysis")

    def start_translation(self):
        text = self.input_text.toPlainText()
        if not text: return

        self.set_loading(True)
        self.output_text.clear()
        
        src_lang = self.combo_source.currentText()
        tgt_lang = self.combo_target.currentText()
        
        self.left_analysis.lbl_title.setText(f"{src_lang} Analysis")
        self.right_analysis.lbl_title.setText(f"{tgt_lang} Analysis")
        
        self.worker = TranslationWorker(self.ai_service, text, src_lang, tgt_lang)
        self.worker.finished.connect(self.handle_translation_result)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_translation_result(self, result):
        self.set_loading(False)
        self.output_text.setText(result.get("translation", ""))
        
        src_data = result.get("source_analysis", {})
        self.left_analysis.update_data(src_data, is_source=True)

        tgt_data = result.get("target_analysis", {})
        self.right_analysis.update_data(tgt_data, is_source=False)

    def analyze_selected_word(self):
        cursor = self.input_text.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if not selected_text or len(selected_text.split()) > 3:
             QMessageBox.warning(self, "Selection Error", "Please select exactly one word.")
             return

        self.set_loading(True)
        self.left_analysis.lbl_title.setText(f"Word Analysis: '{selected_text}'")
        
        self.word_worker = WordAnalysisWorker(self.ai_service, selected_text)
        self.word_worker.finished.connect(self.handle_word_result)
        self.word_worker.error.connect(self.handle_error)
        self.word_worker.start()

    def handle_word_result(self, result):
        self.set_loading(False)
        data = {
            "structure": f"Definition: {result.get('definition', '-')}",
            "grammar": f"Part of Speech: {result.get('part_of_speech', '-')}",
            "synonyms": result.get("synonyms", []),
            "antonyms": result.get("antonyms", []),
            "correction": "" 
        }
        self.left_analysis.update_data(data, is_source=False)

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