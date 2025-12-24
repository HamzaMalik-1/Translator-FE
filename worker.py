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

# EXISTING WORKER FOR SINGLE WORD ANALYSIS (Source language only)
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

# NEW WORKER FOR BILINGUAL WORD ANALYSIS AND TRANSLATION
class BilingualWordAnalysisWorker(QThread):
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
            # First analyze the word in source language
            source_result = self.ai_service.analyze_single_word(self.word)
            if "error" in source_result: 
                self.error.emit(source_result["error"])
                return
            
            # Then translate the word to target language
            translation_result = self.ai_service.translate_text(
                self.word, 
                self.source_lang, 
                self.target_lang
            )
            
            if "error" in translation_result:
                self.error.emit(translation_result["error"])
                return
            
            # Combine both results
            combined_result = {
                "source_analysis": source_result,
                "target_analysis": translation_result.get("target_analysis", {}),
                "translation": translation_result.get("translation", "")
            }
            
            self.finished.emit(combined_result)
            
        except Exception as e: 
            self.error.emit(str(e))

# Alternative: Direct bilingual analysis (more efficient)
class DirectBilingualWordWorker(QThread):
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

# OPTIMIZED WORKER FOR BILINGUAL WORD ANALYSIS WITH FALLBACK
class OptimizedBilingualWordWorker(QThread):
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
            # Try direct bilingual analysis first (more efficient)
            result = self.ai_service.analyze_and_translate_word(
                self.word, 
                self.source_lang, 
                self.target_lang
            )
            
            if "error" in result:
                # Fallback to two-step method if direct method fails
                print("Direct bilingual method failed, trying fallback...")
                result = self._fallback_analysis()
            
            if "error" in result: 
                self.error.emit(result["error"])
            else: 
                self.finished.emit(result)
                
        except Exception as e: 
            self.error.emit(str(e))
    
    def _fallback_analysis(self):
        """Fallback method using two API calls"""
        try:
            # Analyze word in source language
            source_result = self.ai_service.analyze_single_word(self.word)
            if "error" in source_result:
                return source_result
            
            # Translate the word
            translation_result = self.ai_service.translate_text(
                self.word, 
                self.source_lang, 
                self.target_lang
            )
            
            if "error" in translation_result:
                return translation_result
            
            # Combine results
            return {
                "source_analysis": source_result,
                "target_analysis": translation_result.get("target_analysis", {}),
                "translation": translation_result.get("translation", "")
            }
            
        except Exception as e:
            return {"error": str(e)}