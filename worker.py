from PySide6.QtCore import QThread, Signal

class TranslationWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    def __init__(self, ai_service, text, src, tgt):
        super().__init__()
        self.ai_service = ai_service
        self.text = text
        self.src = src
        self.tgt = tgt
    def run(self):
        if not self.text.strip():
            self.error.emit("Input text is empty.")
            return
        try:
            result = self.ai_service.translate_text(self.text, self.src, self.tgt)
            if "error" in result: self.error.emit(result["error"])
            else: self.finished.emit(result)
        except Exception as e: self.error.emit(str(e))

class AudioWorker(QThread):
    finished = Signal(str)
    def __init__(self, ai_service):
        super().__init__()
        self.ai_service = ai_service
    def run(self):
        text = self.ai_service.listen_audio()
        if text: self.finished.emit(text)
        else: self.finished.emit("") 

class TTSWorker(QThread):
    finished = Signal()
    def __init__(self, ai_service, text, lang):
        super().__init__()
        self.ai_service = ai_service
        self.text = text
        self.lang = lang
    def run(self):
        self.ai_service.text_to_speech(self.text, self.lang)
        self.finished.emit()

# NEW WORKER FOR SELECTED WORD
class WordAnalysisWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    def __init__(self, ai_service, word):
        super().__init__()
        self.ai_service = ai_service
        self.word = word
    def run(self):
        try:
            result = self.ai_service.analyze_single_word(self.word)
            if "error" in result: self.error.emit(result["error"])
            else: self.finished.emit(result)
        except Exception as e: self.error.emit(str(e))