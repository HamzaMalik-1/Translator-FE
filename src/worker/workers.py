"""
Worker threads for background tasks
"""
from PySide6.QtCore import QThread, Signal

class TranslationWorker(QThread):
    """Worker for translation tasks"""
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
            if "error" in result: 
                self.error.emit(result["error"])
            else: 
                self.finished.emit(result)
        except Exception as e: 
            self.error.emit(str(e))


class AudioWorker(QThread):
    """Worker for audio input tasks"""
    finished = Signal(str)
    
    def __init__(self, audio_service):
        super().__init__()
        self.audio_service = audio_service
    
    def run(self):
        text = self.audio_service.listen_audio()
        if text: 
            self.finished.emit(text)
        else: 
            self.finished.emit("")


class TTSWorker(QThread):
    """Worker for text-to-speech tasks"""
    finished = Signal()
    
    def __init__(self, audio_service, text, lang):
        super().__init__()
        self.audio_service = audio_service
        self.text = text
        self.lang = lang
    
    def run(self):
        self.audio_service.text_to_speech(self.text, self.lang)
        self.finished.emit()


class WordAnalysisWorker(QThread):
    """Worker for single word analysis tasks"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, ai_service, word):
        super().__init__()
        self.ai_service = ai_service
        self.word = word
    
    def run(self):
        try:
            result = self.ai_service.analyze_single_word(self.word)
            if "error" in result: 
                self.error.emit(result["error"])
            else: 
                self.finished.emit(result)
        except Exception as e: 
            self.error.emit(str(e))


class DirectBilingualWordWorker(QThread):
    """Worker for bilingual word analysis tasks"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, ai_service, word, source_lang, target_lang):
        super().__init__()
        self.ai_service = ai_service
        self.word = word
        self.source_lang = source_lang
        self.target_lang = target_lang
    
    def run(self):
        if not self.word.strip():
            self.error.emit("Word is empty.")
            return
        try:
            # Use the direct bilingual analysis method
            result = self.ai_service.analyze_and_translate_word(
                self.word, 
                self.source_lang, 
                self.target_lang
            )
            if "error" in result: 
                self.error.emit(result["error"])
            else: 
                self.finished.emit(result)
        except Exception as e: 
            self.error.emit(str(e))