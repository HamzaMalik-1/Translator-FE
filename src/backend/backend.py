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
            "gemini-pro",
            "gemma-3-4b-it",
            "gemma-2-9b-it"
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

    # --- CORE LOGIC (STRICTLY FINE-TUNED) ---

    def _execute_translation(self, text, src, tgt, custom_instruction):
        # Logic to skip synonyms for long text
        is_long = len(text.split()) > 30
        syn_instruction = "Return empty lists [] for synonyms/antonyms." if is_long else "Provide 3 synonyms and 3 antonyms."

        # DYNAMIC LANGUAGE RULES
        src_rule = ""
        if src == "Urdu":
            src_rule = """
            - Source is URDU. 
            - 'source_analysis' fields (structure, grammar, correction) MUST be in URDU SCRIPT.
            - Do NOT use English grammatical terms (e.g. don't write 'Verb', write 'فعل').
            - Synonyms and Antonyms MUST be Urdu words.
            """
        else:
            src_rule = f"""
            - Source is {src}. 
            - 'source_analysis' fields should be in English.
            - Synonyms and Antonyms MUST be in {src}.
            """

        tgt_rule = ""
        if tgt == "Urdu":
            tgt_rule = """
            - Target is URDU.
            - 'target_analysis' fields (structure, grammar) MUST be in URDU SCRIPT.
            - Do NOT use English grammatical terms (e.g. don't write 'Subject', write 'فاعل').
            - Synonyms and Antonyms MUST be Urdu words.
            """
        else:
            tgt_rule = f"""
            - Target is {tgt}.
            - 'target_analysis' fields should be in English.
            - Synonyms and Antonyms MUST be in {tgt}.
            """

        prompt = f"""
        {custom_instruction}
        
        Task: 
        1. Translate the Input Text from {src} to {tgt}.
           - **Translation Rule:** Translate naturally as a native speaker would say it.
           - **Avoid Definitions:** Do NOT define the sentence (e.g., "This means..."). Just translate it.
           - **Example:** If input is "My name is Ali", output "میرا نام علی ہے" (NOT "اسے میرا نام کہا جاتا ہے").

        2. Analyze the SOURCE text ({src}).
        3. Analyze the TARGET text ({tgt}).

        Input Text: "{text}"
        
        {syn_instruction}
        
        STRICT RULES:
        {src_rule}
        {tgt_rule}
        
        Strictly output this NESTED JSON structure:
        {{
            "translation": "The direct translated text",
            "source_analysis": {{
                "structure": "Analysis of structure",
                "grammar": "Analysis of grammar",
                "correction": "Corrected text or 'No errors found'",
                "synonyms": ["List of synonyms in {src} language"],
                "antonyms": ["List of antonyms in {src} language"]
            }},
            "target_analysis": {{
                "structure": "Analysis of structure",
                "grammar": "Analysis of grammar",
                "synonyms": ["List of synonyms in {tgt} language"],
                "antonyms": ["List of antonyms in {tgt} language"]
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

    # --- Bilingual Word Analysis and Translation ---
    def analyze_and_translate_word(self, word, source_lang, target_lang):
        """
        Analyze word in source language and get translation in target language
        Returns bilingual analysis for both panels
        """
        if not self.model: 
            return {"error": "AI Model not connected."}
        
        # Determine language settings
        is_source_urdu = (source_lang == "Urdu")
        is_target_urdu = (target_lang == "Urdu")
        
        # Source language rules
        source_instr = ""
        if is_source_urdu:
            source_instr = f"""
            FOR SOURCE ANALYSIS (URDU):
            1. Definition: Provide definition in URDU SCRIPT (e.g., "پڑھنے کا عمل")
            2. Part of speech: Use URDU terms (اسم for Noun, فعل for Verb, صفت for Adjective, etc.)
            3. Synonyms: Provide 3-5 URDU words
            4. Antonyms: Provide 3-5 URDU words
            5. ALL text in source_analysis MUST be in URDU SCRIPT, NO English mixed
            """
        else:
            source_instr = f"""
            FOR SOURCE ANALYSIS ({source_lang}):
            1. Definition: Provide definition in English
            2. Part of speech: Use English terms (Noun, Verb, Adjective, etc.)
            3. Synonyms: Provide 3-5 words in {source_lang}
            4. Antonyms: Provide 3-5 words in {source_lang}
            """
        
        # Target language rules  
        target_instr = ""
        if is_target_urdu:
            target_instr = f"""
            FOR TARGET ANALYSIS (URDU):
            1. Translation: Provide natural translation in URDU SCRIPT
            2. Definition: Provide definition in URDU SCRIPT
            3. Part of speech: Use URDU terms (اسم for Noun, فعل for Verb, etc.)
            4. Synonyms: Provide 3-5 URDU words
            5. Antonyms: Provide 3-5 URDU words
            6. ALL text in target_analysis MUST be in URDU SCRIPT, NO English mixed
            """
        else:
            target_instr = f"""
            FOR TARGET ANALYSIS ({target_lang}):
            1. Translation: Provide natural translation in {target_lang}
            2. Definition: Provide definition in English
            3. Part of speech: Use English terms (Noun, Verb, Adjective, etc.)
            4. Synonyms: Provide 3-5 words in {target_lang}
            5. Antonyms: Provide 3-5 words in {target_lang}
            """
        
        # Common part of speech mappings for consistency
        pos_mappings = """
        COMMON PART OF SPEECH MAPPINGS:
        - Noun = اسم
        - Verb = فعل  
        - Adjective = صفت
        - Adverb = حال
        - Pronoun = ضمیر
        - Preposition = حرف جار
        - Conjunction = حرف عطف
        - Interjection = حرف ندا
        """
        
        prompt = f"""
        ACT AS A BILINGUAL LINGUISTIC EXPERT.
        
        Task: Analyze the word "{word}" in {source_lang} and provide its translation and analysis in {target_lang}.
        
        {pos_mappings}
        
        IMPORTANT INSTRUCTIONS:
        {source_instr}
        {target_instr}
        
        CRITICAL: Do NOT mix languages within the same section. 
        If a section is supposed to be in Urdu, use ONLY Urdu script.
        If a section is supposed to be in English, use ONLY English.
        
        Provide comprehensive bilingual analysis:
        
        1. For SOURCE language ({source_lang}):
           - Definition (follow language rules above)
           - Part of speech (use appropriate language terms)
           - 3-5 Synonyms (in appropriate language)
           - 3-5 Antonyms (in appropriate language)
        
        2. For TARGET language ({target_lang}):
           - Natural translation of the word
           - Definition (follow language rules above)
           - Part of speech (use appropriate language terms)
           - 3-5 Synonyms (in appropriate language)
           - 3-5 Antonyms (in appropriate language)
        
        Strictly output this JSON format:
        {{
            "source_analysis": {{
                "word": "{word}",
                "language": "{source_lang}",
                "definition": "definition",
                "part_of_speech": "part of speech",
                "synonyms": ["syn1", "syn2", "syn3"],
                "antonyms": ["ant1", "ant2", "ant3"]
            }},
            "target_analysis": {{
                "translation": "natural translation",
                "language": "{target_lang}",
                "definition": "definition",
                "part_of_speech": "part of speech",
                "synonyms": ["syn1", "syn2", "syn3"],
                "antonyms": ["ant1", "ant2", "ant3"]
            }}
        }}
        
        REMEMBER: No mixed language content. Each section must be purely in its assigned language.
        """
        
        try:
            response = self.retry_api_call(prompt)
            result = self._parse_json(response.text)
            
            # Ensure we have proper structure
            if "source_analysis" not in result:
                result["source_analysis"] = {}
            if "target_analysis" not in result:
                result["target_analysis"] = {}
            
            # Add translation at root level for convenience
            if "target_analysis" in result and "translation" in result["target_analysis"]:
                result["translation"] = result["target_analysis"]["translation"]
            
            return result
        except Exception as e:
            print(f"Error in bilingual word analysis: {e}")
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