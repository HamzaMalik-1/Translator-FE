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
            "gemini-3-pro-preview"
            "gemini-2.5-flash", 
            "gemini-flash-latest",
            "gemini-1.5-flash-8b",
            "gemini-pro-latest",
            "gemini-2.0-flash-lite"
        ]
        
        print("Connecting to Google AI...")
        for model_name in candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                test_model.generate_content("Hi") 
                self.model = test_model
                print(f"SUCCESS: Connected and verified '{model_name}'")
                return
            except Exception:
                continue
        print("\nCRITICAL ERROR: No models are working.")

    def retry_api_call(self, prompt, retries=3, delay=2):
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                return response
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay += 2
                    else:
                        raise Exception("Server is busy (Rate Limit).")
                else:
                    raise e

    # ============================================================
    # NEW WORKFLOW: 2-Step Context Aware Translation
    # ============================================================

    def translate_text(self, text, source_lang, target_lang):
        if not self.model: return {"error": "AI Model not connected."}

        try:
            # STEP 1: Detect Context & Simplify (No Translation)
            context = self._detect_context(text)
            category = context.get("category", "General")
            explanation = context.get("simplified_explanation", "No explanation provided.")
            
            print(f"Detected: {category} | Context: {explanation}")

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
        """
        Step 1: Ask AI to categorize AND simplify the text.
        - Categorizes into: [Medical, Legal, Slang, Poetic, General]
        - Simplifies: Explains idioms, memes, or complex jargon in plain English.
        """
        prompt = f"""
        Analyze the following text to understand its core meaning and context.
        
        Input Text: "{text}"

        Perform two tasks:
        1. Categorize it into exactly ONE of these categories: [Medical, Legal, Slang, Meme Poetic, General].
        2. Provide a "simplified_explanation" (How to say this in simple, plain English?):
           - If it's a MEME: Explain the subtext, vibe, or how it is used socially (not the literal words).
           - If it's an IDIOM/METAPHOR: Explain the actual definition.
           - If it's MEDICAL/LEGAL: Rewrite the jargon in simple terms.
           - If it's already simple: Return the original text.

        Strictly output a JSON object with these keys:
        {{
            "category": "CategoryName",
            "simplified_explanation": "The simple plain English explanation..."
        }}
        """
        response = self.retry_api_call(prompt)
        return self._parse_json(response.text)

    # --- Specialized Translation Functions ---

    # ============================================================
    # SPECIALIZED TRANSLATION FUNCTIONS (Now Context-Aware)
    # ============================================================

    def _translate_medical(self, text, src, tgt, explanation):
        instruction = f"""
        ACT AS A SENIOR MEDICAL TRANSLATOR.
        - Core Meaning: {explanation}
        - Task: Translate strictly for a clinical environment.
        - Use precise medical terminology (e.g., 'Abdomen' instead of 'Belly').
        - Tone: Clinical, Objective, Professional.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _translate_legal(self, text, src, tgt, explanation):
        instruction = f"""
        ACT AS A LEGAL EXPERT.
        - Core Meaning: {explanation}
        - Task: Translate for a legal contract or court document.
        - Use formal legal terminology and phrasing.
        - Ensure zero ambiguity.
        - Tone: Authoritative, Formal, Precise.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _translate_slang(self, text, src, tgt, explanation):
        instruction = f"""
        ACT AS A NATIVE LOCAL SPEAKER (CASUAL/STREET).
        - Core Meaning: {explanation}
        - Task: Translate the *vibe* and meaning, not the literal words.
        - If the idiom doesn't exist in the target language, use the closest local equivalent.
        - Tone: Friendly, Informal, conversational.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _translate_meme(self, text, src, tgt, explanation):
        instruction = f"""
        ACT AS A CULTURAL EXPERT & INTERNET HISTORIAN.
        - Core Meaning/Joke: {explanation}
        - Task: Translate this meme/internet reference.
        - Do NOT translate literally if it kills the joke. Adapt it so it is funny/relatable in the target language culture.
        - Tone: Humorous, Sarcastic, or Viral-style.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _translate_poetic(self, text, src, tgt, explanation):
        instruction = f"""
        ACT AS A POET AND LITERARY TRANSLATOR.
        - Core Meaning: {explanation}
        - Task: Translate while preserving the emotion, rhyme scheme (if possible), and meter.
        - Prioritize beauty and flow over literal accuracy.
        - Tone: Artistic, Emotional, Expressive.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _translate_general(self, text, src, tgt, category, explanation):
        instruction = f"""
        ACT AS A PROFESSIONAL LINGUIST.
        - Category: {category}
        - Core Meaning: {explanation}
        - Task: Provide a standard, high-quality translation.
        - Tone: Neutral and Polite.
        """
        return self._execute_translation(text, src, tgt, instruction)

    def _execute_translation(self, text, src, tgt, custom_instruction):
        # Logic to skip synonyms for long text
        is_long = len(text.split()) > 20
        synonym_instruction = "Return empty lists [] for synonyms/antonyms." if is_long else "Provide 3 synonyms and 3 antonyms."

        prompt = f"""
        {custom_instruction}
        
        Task: Translate from {src} to {tgt}.
        Input Text: "{text}"
        
        {synonym_instruction}
        
        Strictly output JSON with these exact keys:
        - "translation": The translated text.
        - "synonyms": List of strings.
        - "antonyms": List of strings.
        - "sentence_structure": Brief analysis (e.g., "Compound, SVO").
        - "grammar_details": Brief grammar notes.
        - "grammar_correction": Corrected text or "No errors found".
        """
        response = self.retry_api_call(prompt)
        return self._parse_json(response.text)

    def _parse_json(self, text):
        try:
            clean_text = text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except:
            return {}

    # --- Single Word Analysis (Unchanged) ---
    def analyze_single_word(self, word):
        if not self.model: return {"error": "AI Model not connected."}
        prompt = f"""
        Analyze word: "{word}".
        Strictly output JSON:
        - "definition": Short definition.
        - "synonyms": List of 3 synonyms.
        - "antonyms": List of 3 antonyms.
        - "part_of_speech": e.g. Noun.
        """
        try:
            response = self.retry_api_call(prompt)
            return self._parse_json(response.text)
        except Exception as e:
            return {"error": str(e)}

    # --- Audio Functions (Unchanged) ---
    def text_to_speech(self, text, language_name):
        lang_map = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh-CN", "Russian": "ru", "Urdu": "ur", "Hindi": "hi", "Arabic": "ar", "Auto Detect": "en"}
        lang_code = lang_map.get(language_name, "en")
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            filename = "temp_audio.mp3"
            if os.path.exists(filename):
                try:
                    pygame.mixer.music.unload()
                    os.remove(filename)
                except: pass
            tts.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
        except Exception as e: print(f"TTS Error: {e}")

    def listen_audio(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5)
                return recognizer.recognize_google(audio)
            except: return None