import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
import pygame
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

class AIService:
    def __init__(self):
        self.model = None
        pygame.mixer.init()

        if not API_KEY:
            print("CRITICAL ERROR: 'GEMINI_API_KEY' not found in .env file.")
            return

        genai.configure(api_key=API_KEY)
        self.connect_to_model()

    def connect_to_model(self):
        """
        Robustly finds a working model by testing them.
        """
        candidates = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp", 
            "gemini-pro"
        ]
        
        print("Connecting to Google AI...")
        for model_name in candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                # Simple handshake test
                test_model.generate_content("Hi") 
                self.model = test_model
                print(f"SUCCESS: Connected and verified '{model_name}'")
                return
            except Exception:
                continue
        print("\nCRITICAL ERROR: No models are working. Check API Key/Quota.")

    def retry_api_call(self, prompt, retries=3, delay=2):
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                return response
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay += 2
                    else:
                        raise Exception("Server is busy (Rate Limit).")
                else:
                    raise e

    # ============================================================
    # WORKFLOW: Context Aware + Dual Analysis Translation
    # ============================================================

    def translate_text(self, text, source_lang, target_lang):
        if not self.model: return {"error": "AI Model not connected."}

        try:
            # STEP 1: Detect Context & Simplify
            context = self._detect_context(text)
            category = context.get("category", "General")
            explanation = context.get("simplified_explanation", "No explanation provided.")
            
            print(f"Detected: {category} | Context: {explanation}")

            # STEP 2: Route to specialized translation logic
            if category == "Medical":
                return self._translate_medical(text, source_lang, target_lang, explanation)
            elif category == "Legal":
                return self._translate_legal(text, source_lang, target_lang, explanation)
            elif category == "Slang":
                return self._translate_slang(text, source_lang, target_lang, explanation)
            elif category == "Meme":
                return self._translate_meme(text, source_lang, target_lang, explanation)
            elif category == "Poetic":
                return self._translate_poetic(text, source_lang, target_lang, explanation)
            else:
                return self._translate_general(text, source_lang, target_lang, category, explanation)

        except Exception as e:
            return {"error": str(e)}

    def _detect_context(self, text):
        prompt = f"""
        Analyze input: "{text}"
        1. Categorize into ONE: [Medical, Legal, Slang, Meme, Poetic, General].
        2. Simplify explanation.
        Output JSON: {{ "category": "...", "simplified_explanation": "..." }}
        """
        try:
            response = self.retry_api_call(prompt)
            return self._parse_json(response.text)
        except:
            return {"category": "General", "simplified_explanation": ""}

    # --- Specialized Translation Callers ---

    def _translate_medical(self, text, src, tgt, explanation):
        instr = f"ACT AS A MEDICAL TRANSLATOR. Use precise terminology. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    def _translate_legal(self, text, src, tgt, explanation):
        instr = f"ACT AS A LEGAL EXPERT. Use formal phrasing. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    def _translate_slang(self, text, src, tgt, explanation):
        instr = f"ACT AS A LOCAL SLANG EXPERT. Translate the vibe/meaning, not literal words. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    def _translate_meme(self, text, src, tgt, explanation):
        instr = f"ACT AS A CULTURAL EXPERT. Translate this meme/joke so it's funny in target culture. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    def _translate_poetic(self, text, src, tgt, explanation):
        instr = f"ACT AS A POET. Preserve rhyme and meter if possible. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    def _translate_general(self, text, src, tgt, category, explanation):
        instr = f"ACT AS A PROFESSIONAL LINGUIST. Category: {category}. Context: {explanation}"
        return self._execute_translation(text, src, tgt, instr)

    # --- CORE LOGIC (UPDATED FOR DUAL PANELS) ---

    def _execute_translation(self, text, src, tgt, custom_instruction):
        # Logic to skip synonyms for long text
        is_long = len(text.split()) > 30
        synonym_instruction = "Return empty lists [] for synonyms/antonyms." if is_long else "Provide 3 synonyms and 3 antonyms."

        prompt = f"""
        {custom_instruction}
        
        Task: 
        1. Translate the Input Text from {src} to {tgt}.
        2. Analyze the SOURCE text ({src}).
        3. Analyze the TARGET text ({tgt}).

        Input Text: "{text}"
        
        {synonym_instruction}
        
        Strictly output this NESTED JSON structure:
        {{
            "translation": "The translated text",
            "source_analysis": {{
                "structure": "Brief sentence structure (e.g. SVO)",
                "grammar": "Key grammar details",
                "correction": "Corrected text or 'No errors found'",
                "synonyms": ["list", "of", "words"],
                "antonyms": ["list", "of", "words"]
            }},
            "target_analysis": {{
                "structure": "Brief structure of translation",
                "grammar": "Key grammar details of translation",
                "synonyms": ["list", "of", "words"],
                "antonyms": ["list", "of", "words"]
            }}
        }}
        """
        response = self.retry_api_call(prompt)
        return self._parse_json(response.text)

    def _parse_json(self, text):
        try:
            clean_text = text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except:
            return {}

    # --- Single Word Analysis ---
    def analyze_single_word(self, word):
        if not self.model: return {"error": "AI Model not connected."}
        prompt = f"""
        Analyze word: "{word}".
        Strictly output JSON:
        {{
            "definition": "Short definition",
            "synonyms": ["syn1", "syn2", "syn3"],
            "antonyms": ["ant1", "ant2", "ant3"],
            "part_of_speech": "e.g. Noun"
        }}
        """
        try:
            response = self.retry_api_call(prompt)
            return self._parse_json(response.text)
        except Exception as e:
            return {"error": str(e)}

    # --- Audio Functions ---
    def text_to_speech(self, text, language_name):
        lang_map = {
            "English": "en", "Spanish": "es", "French": "fr", "German": "de", 
            "Japanese": "ja", "Chinese": "zh-CN", "Russian": "ru", 
            "Urdu": "ur", "Hindi": "hi", "Arabic": "ar", "Auto Detect": "en"
        }
        lang_code = lang_map.get(language_name, "en")
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            filename = "temp_audio.mp3"
            
            # Clean up old file
            if os.path.exists(filename):
                try:
                    pygame.mixer.music.unload()
                    os.remove(filename)
                except: pass
            
            tts.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            print(f"TTS Error: {e}")

    def listen_audio(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                print("Listening...")
                audio = recognizer.listen(source, timeout=5)
                return recognizer.recognize_google(audio)
            except Exception as e:
                print(f"Mic Error: {e}")
                return None