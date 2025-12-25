"""
Main application window
"""
import sys
import os
import pyperclip  # Add this for clipboard functionality
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QComboBox, QFrame, QMessageBox,
    QPushButton, QProgressBar  # Make sure these are imported
)
from PySide6.QtCore import Qt, QTimer
from src.config.settings import APP_NAME, WINDOW_SIZE
from src.ui.components import AnalysisPanel, BilingualTextEdit, IconButton
from src.backend.ai_service import AIService
from src.backend.audio_service import AudioService
from src.worker.workers import (
    TranslationWorker, AudioWorker, TTSWorker, 
    WordAnalysisWorker, DirectBilingualWordWorker
)

class GeminiTranslatorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.ai_service = AIService()
        self.audio_service = AudioService()
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_SIZE)
        self.current_sentence_translation = ""
        self.current_sentence_analysis = {}
        
        # Load styles
        self.load_styles()
        self.setup_ui()
        
    def load_styles(self):
        """Load application styles"""
        styles_path = os.path.join(os.path.dirname(__file__), '..', '..', 'styles.qss')
        try:
            with open(styles_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            # Fallback to trying the current directory
            try:
                with open("styles.qss", "r") as f:
                    self.setStyleSheet(f.read())
            except FileNotFoundError:
                print("Warning: Could not find styles.qss file")
                pass

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 1. HEADER
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        self.combo_source = QComboBox()
        self.combo_source.addItems(["English", "Urdu"])
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
        self.combo_target.addItems(["English", "Urdu"])
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

        # Left Card (Input)
        input_card = QFrame()
        input_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; }")
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_text = BilingualTextEdit()
        self.input_text.setPlaceholderText("Enter text here...")
        self.input_text.setFrameShape(QFrame.NoFrame)
        self.input_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")
        
        input_toolbar = QFrame()
        input_toolbar.setStyleSheet("QFrame { border-top: 1px solid #F1F3F4; background-color: transparent; }")
        it_layout = QHBoxLayout(input_toolbar)
        it_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_mic = IconButton("🎤", "Voice Input", self.start_voice_input)
        self.btn_input_speak = IconButton("🔊", "Listen", self.speak_input)
        self.btn_paste = IconButton("📋", "Paste", self.paste_from_clipboard)
        self.btn_analyze_word = IconButton("🔍", "Define Word", self.analyze_selected_word_bilingual)
        
        it_layout.addWidget(self.btn_mic)
        it_layout.addWidget(self.btn_input_speak)
        it_layout.addStretch()
        it_layout.addWidget(self.btn_analyze_word)
        it_layout.addWidget(self.btn_paste)
        
        input_card_layout.addWidget(self.input_text)
        input_card_layout.addWidget(input_toolbar)

        # Right Card (Output)
        output_card = QFrame()
        output_card.setStyleSheet("QFrame { background-color: #F8F9FA; border: 1px solid #DADCE0; border-radius: 8px; }")
        output_card_layout = QVBoxLayout(output_card)
        output_card_layout.setContentsMargins(0, 0, 0, 0)
        
        self.output_text = BilingualTextEdit()
        self.output_text.setPlaceholderText("Translation...")
        self.output_text.setReadOnly(True)
        self.output_text.setFrameShape(QFrame.NoFrame)
        self.output_text.setStyleSheet("border: none; padding: 15px; font-size: 16px; background-color: transparent;")
        
        output_toolbar = QFrame()
        output_toolbar.setStyleSheet("QFrame { border-top: 1px solid #E0E0E0; background-color: transparent; }")
        ot_layout = QHBoxLayout(output_toolbar)
        ot_layout.setContentsMargins(10, 5, 10, 5)
        
        self.btn_output_speak = IconButton("🔊", "Listen", self.speak_result)
        self.btn_output_copy = IconButton("📄", "Copy Result", self.copy_output_result)
        
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

        # Progress loader
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

        # 5. RESTORE SENTENCE BUTTON
        self.restore_btn_container = QHBoxLayout()
        self.btn_restore_sentence = QPushButton("Show Sentence Translation")
        self.btn_restore_sentence.setCursor(Qt.PointingHandCursor)
        self.btn_restore_sentence.setFixedSize(200, 32)
        self.btn_restore_sentence.setStyleSheet("""
            QPushButton { 
                background-color: #F1F3F4; 
                color: #5F6368; 
                font-size: 14px; 
                border-radius: 16px; 
                border: 1px solid #DADCE0;
            }
            QPushButton:hover { 
                background-color: #E8F0FE; 
                color: #1A73E8; 
            }
        """)
        self.btn_restore_sentence.clicked.connect(self.restore_sentence_translation)
        self.btn_restore_sentence.hide()
        
        self.restore_btn_container.addStretch()
        self.restore_btn_container.addWidget(self.btn_restore_sentence)
        self.restore_btn_container.addStretch()
        main_layout.addLayout(self.restore_btn_container)

    # --- Main Logic Methods ---
    
    def swap_languages(self):
        """Swap source and target languages"""
        original_source = self.combo_source.currentText()
        tgt_txt = self.combo_target.currentText()
        
        self.combo_source.setCurrentText(tgt_txt)
        self.combo_target.setCurrentText(original_source)
            
        current_output = self.output_text.toPlainText()
        if current_output:
            self.input_text.setText(current_output)
            self.output_text.clear()
            self.left_analysis.lbl_title.setText(f"{tgt_txt} Analysis")
            self.right_analysis.lbl_title.setText(f"{original_source} Analysis")
            self.current_sentence_translation = ""
            self.current_sentence_analysis = {}
            self.btn_restore_sentence.hide()

    def start_translation(self):
        """Start translation process"""
        text = self.input_text.toPlainText()
        if not text: 
            return

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
        """Handle translation result"""
        self.set_loading(False)
        translation = result.get("translation", "")
        self.output_text.setText(translation)
        self.current_sentence_translation = translation
        self.current_sentence_analysis = result
        
        src_data = result.get("source_analysis", {})
        self.left_analysis.update_data(src_data, is_source=True)

        tgt_data = result.get("target_analysis", {})
        self.right_analysis.update_data(tgt_data, is_source=False)
        
        self.btn_restore_sentence.hide()

    def analyze_selected_word_bilingual(self):
        """Analyze selected word in bilingual context"""
        cursor = self.input_text.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if not selected_text or len(selected_text.split()) > 3:
            QMessageBox.warning(self, "Selection Error", "Please select exactly one word (1-3 words maximum).")
            return

        self.set_loading(True)
        
        source_lang = self.combo_source.currentText()
        target_lang = self.combo_target.currentText()
        
        self.left_analysis.lbl_title.setText(f"Word Analysis ({source_lang}): '{selected_text}'")
        self.right_analysis.lbl_title.setText(f"Word Translation ({target_lang})")
        
        self.word_worker = DirectBilingualWordWorker(
            self.ai_service, 
            selected_text,
            source_lang,
            target_lang
        )
        self.word_worker.finished.connect(self.handle_bilingual_word_result)
        self.word_worker.error.connect(self.handle_error)
        self.word_worker.start()

    def handle_bilingual_word_result(self, result):
        """Handle bilingual word analysis result"""
        self.set_loading(False)
        
        # Check for errors
        if "error" in result:
            QMessageBox.warning(self, "Analysis Error", result["error"])
            return
        
        source_data = result.get("source_analysis", {})
        target_data = result.get("target_analysis", {})
        word_translation = result.get("translation", target_data.get("translation", ""))
        
        source_lang = self.combo_source.currentText()
        target_lang = self.combo_target.currentText()
        
        # Prepare data for LEFT panel (Source Language Analysis)
        if source_lang == "Urdu":
            left_display_data = {
                "structure": f"لفظ: {source_data.get('word', '')}",
                "grammar": f"قسم کلام: {source_data.get('part_of_speech', '-')}",
                "synonyms": source_data.get("synonyms", []),
                "antonyms": source_data.get("antonyms", []),
                "correction": f"تعریف: {source_data.get('definition', '-')}"
            }
            left_force_language = 'urdu'
        else:
            left_display_data = {
                "structure": f"Word: {source_data.get('word', '')}",
                "grammar": f"Part of Speech: {source_data.get('part_of_speech', '-')}",
                "synonyms": source_data.get("synonyms", []),
                "antonyms": source_data.get("antonyms", []),
                "correction": f"Definition: {source_data.get('definition', '-')}"
            }
            left_force_language = 'english'
        
        # Update left panel
        self.left_analysis.update_data(left_display_data, is_source=False, force_language=left_force_language)
        
        # Prepare data for RIGHT panel (Target Language Translation & Analysis)
        if target_lang == "Urdu":
            right_display_data = {
                "structure": f"لفظ کا ترجمہ: {word_translation}",
                "grammar": f"قسم کلام: {target_data.get('part_of_speech', '-')}",
                "synonyms": target_data.get("synonyms", []),
                "antonyms": target_data.get("antonyms", []),
                "correction": f"تعریف: {target_data.get('definition', '-')}"
            }
            right_force_language = 'urdu'
        else:
            right_display_data = {
                "structure": f"Word Translation: {word_translation}",
                "grammar": f"Part of Speech: {target_data.get('part_of_speech', '-')}",
                "synonyms": target_data.get("synonyms", []),
                "antonyms": target_data.get("antonyms", []),
                "correction": f"Definition: {target_data.get('definition', '-')}"
            }
            right_force_language = 'english'
        
        # Update right panel
        self.right_analysis.update_data(right_display_data, is_source=False, force_language=right_force_language)
        
        # Show restore button if we have a stored sentence translation
        if self.current_sentence_translation and not self.output_text.toPlainText():
            self.btn_restore_sentence.show()
        elif self.current_sentence_translation and self.output_text.toPlainText() != self.current_sentence_translation:
            self.btn_restore_sentence.show()
        else:
            self.btn_restore_sentence.hide()

    def restore_sentence_translation(self):
        """Restore the original sentence translation"""
        if self.current_sentence_translation and self.current_sentence_analysis:
            self.output_text.setText(self.current_sentence_translation)
            
            src_lang = self.combo_source.currentText()
            tgt_lang = self.combo_target.currentText()
            
            self.left_analysis.lbl_title.setText(f"{src_lang} Analysis")
            self.right_analysis.lbl_title.setText(f"{tgt_lang} Analysis")
            
            src_data = self.current_sentence_analysis.get("source_analysis", {})
            self.left_analysis.update_data(src_data, is_source=True)
            
            tgt_data = self.current_sentence_analysis.get("target_analysis", {})
            self.right_analysis.update_data(tgt_data, is_source=False)
            
            self.btn_restore_sentence.hide()
            
            QMessageBox.information(
                self, 
                "Sentence Translation Restored", 
                "The full sentence translation and analysis are now restored."
            )
        else:
            QMessageBox.warning(
                self,
                "No Sentence Data",
                "No previous sentence translation found to restore."
            )

    # --- Audio and Utility Methods ---
    
    def start_voice_input(self):
        """Start voice input"""
        self.input_text.setPlaceholderText("Listening... speak now...")
        self.btn_mic.setDisabled(True)
        self.audio_worker = AudioWorker(self.audio_service)
        self.audio_worker.finished.connect(self.handle_voice_result)
        self.audio_worker.start()

    def handle_voice_result(self, text):
        """Handle voice input result"""
        self.btn_mic.setDisabled(False)
        if text: 
            self.input_text.setText(text)
            self.input_text.setPlaceholderText("Enter text here...")
        else: 
            self.input_text.setPlaceholderText("Could not hear audio. Try again.")

    def speak_input(self):
        """Speak input text"""
        text = self.input_text.toPlainText()
        lang = self.combo_source.currentText()
        if text:
            self.btn_input_speak.setDisabled(True)
            self.tts_worker = TTSWorker(self.audio_service, text, lang)
            self.tts_worker.finished.connect(lambda: self.btn_input_speak.setDisabled(False))
            self.tts_worker.start()

    def speak_result(self):
        """Speak output text"""
        text = self.output_text.toPlainText()
        lang = self.combo_target.currentText()
        if text:
            self.btn_output_speak.setDisabled(True)
            self.tts_worker_out = TTSWorker(self.audio_service, text, lang)
            self.tts_worker_out.finished.connect(lambda: self.btn_output_speak.setDisabled(False))
            self.tts_worker_out.start()

    def paste_from_clipboard(self):
        """Paste text from clipboard"""
        import pyperclip
        self.input_text.setText(pyperclip.paste())

    def copy_output_result(self):
        """Copy output text to clipboard"""
        import pyperclip
        text = self.output_text.toPlainText()
        if text:
            pyperclip.copy(text)
            self.btn_output_copy.setStyleSheet("background-color: #E8F0FE; border-radius: 20px;")
            QTimer.singleShot(500, lambda: self.btn_output_copy.setStyleSheet("background-color: transparent; border-radius: 20px;"))

    def handle_error(self, error_msg):
        """Handle errors"""
        self.set_loading(False)
        QMessageBox.warning(self, "Notice", f"{error_msg}")

    def set_loading(self, is_loading):
        """Set loading state"""
        if is_loading:
            self.loader.show()
            self.btn_translate.setText("Translating...")
            self.btn_translate.setDisabled(True)
        else:
            self.loader.hide()
            self.btn_translate.setText("Translate")
            self.btn_translate.setDisabled(False)