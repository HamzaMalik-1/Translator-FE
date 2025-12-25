import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
import pygame
import json
import os
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import threading
from queue import Queue

load_dotenv()

class APIKeyManager:
    """Manages multiple API keys with quota tracking and failover"""
    
    def __init__(self):
        self.api_keys = []
        self.current_key_index = 0
        self.key_usage = {}  # Track usage per key
        self.key_errors = {}  # Track errors per key
        self.key_enabled = {}  # Track if key is enabled
        self.lock = threading.Lock()
        self.load_api_keys()
        
    def load_api_keys(self):
        """Load API keys from environment variables"""
        # Try to load multiple keys: GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
        api_keys = []
        i = 1
        
        # First try the main key
        main_key = os.getenv("GEMINI_API_KEY")
        if main_key:
            api_keys.append(main_key)
            print(f"Loaded main API key")
        
        # Try numbered keys
        while True:
            key_name = f"GEMINI_API_KEY_{i}"
            key = os.getenv(key_name)
            if key:
                api_keys.append(key)
                print(f"Loaded {key_name}")
                i += 1
            else:
                break
        
        # Try comma-separated list
        key_list = os.getenv("GEMINI_API_KEYS")
        if key_list:
            keys = [k.strip() for k in key_list.split(",") if k.strip()]
            api_keys.extend(keys)
            print(f"Loaded {len(keys)} keys from GEMINI_API_KEYS")
        
        if not api_keys:
            print("CRITICAL ERROR: No API keys found in environment variables.")
            print("Add keys as: GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.")
            return
        
        self.api_keys = api_keys
        
        # Initialize tracking for each key
        for idx, key in enumerate(api_keys):
            self.key_usage[idx] = {
                'count': 0,
                'last_used': None,
                'quota_exceeded': False,
                'quota_reset_time': None
            }
            self.key_errors[idx] = {
                'error_count': 0,
                'last_error': None,
                'consecutive_errors': 0
            }
            self.key_enabled[idx] = True
        
        print(f"Loaded {len(api_keys)} API keys")
    
    def get_current_key(self):
        """Get the currently active API key"""
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.current_key_index]
    
    def get_next_key(self):
        """Rotate to the next available API key"""
        with self.lock:
            if not self.api_keys:
                return None
            
            original_index = self.current_key_index
            start_index = (self.current_key_index + 1) % len(self.api_keys)
            
            # Try to find an enabled key
            for i in range(len(self.api_keys)):
                idx = (start_index + i) % len(self.api_keys)
                if self.key_enabled[idx]:
                    self.current_key_index = idx
                    print(f"Switched to API key {idx + 1}")
                    return self.api_keys[idx]
            
            # If no enabled keys found, reset all and use the original
            print("All keys disabled, resetting...")
            for idx in range(len(self.api_keys)):
                self.key_enabled[idx] = True
                self.key_errors[idx]['consecutive_errors'] = 0
            
            self.current_key_index = original_index
            return self.api_keys[original_index]
    
    def record_success(self, key_index):
        """Record successful API call"""
        with self.lock:
            if key_index in self.key_usage:
                self.key_usage[key_index]['count'] += 1
                self.key_usage[key_index]['last_used'] = datetime.now()
                self.key_usage[key_index]['quota_exceeded'] = False
                self.key_errors[key_index]['consecutive_errors'] = 0
    
    def record_error(self, key_index, error_message):
        """Record API error and handle key disabling"""
        with self.lock:
            if key_index not in self.key_errors:
                return
            
            self.key_errors[key_index]['error_count'] += 1
            self.key_errors[key_index]['last_error'] = error_message
            self.key_errors[key_index]['consecutive_errors'] += 1
            
            # Check for quota exceeded
            if "quota" in error_message.lower() or "429" in error_message:
                self.key_usage[key_index]['quota_exceeded'] = True
                # Set reset time to 1 hour from now
                self.key_usage[key_index]['quota_reset_time'] = datetime.now() + timedelta(hours=1)
                print(f"Key {key_index + 1} quota exceeded. Will retry after 1 hour.")
                # Disable key temporarily
                self.key_enabled[key_index] = False
            
            # Disable key if too many consecutive errors
            if self.key_errors[key_index]['consecutive_errors'] > 5:
                print(f"Key {key_index + 1} disabled due to {self.key_errors[key_index]['consecutive_errors']} consecutive errors")
                self.key_enabled[key_index] = False
                # Re-enable after 30 minutes
                threading.Timer(1800, self.enable_key, args=[key_index]).start()
    
    def enable_key(self, key_index):
        """Re-enable a disabled key"""
        with self.lock:
            if key_index in self.key_enabled:
                self.key_enabled[key_index] = True
                self.key_errors[key_index]['consecutive_errors'] = 0
                print(f"Key {key_index + 1} re-enabled")
    
    def check_quota_reset(self):
        """Check if any keys need to be re-enabled after quota reset"""
        with self.lock:
            now = datetime.now()
            for idx in self.key_usage:
                reset_time = self.key_usage[idx].get('quota_reset_time')
                if reset_time and now >= reset_time and self.key_usage[idx]['quota_exceeded']:
                    self.key_usage[idx]['quota_exceeded'] = False
                    self.key_usage[idx]['quota_reset_time'] = None
                    self.key_enabled[idx] = True
                    self.key_errors[idx]['consecutive_errors'] = 0
                    print(f"Key {idx + 1} quota reset")
    
    def get_status(self):
        """Get status of all API keys"""
        with self.lock:
            status = []
            for idx in range(len(self.api_keys)):
                status.append({
                    'key_index': idx + 1,
                    'enabled': self.key_enabled.get(idx, False),
                    'usage_count': self.key_usage.get(idx, {}).get('count', 0),
                    'quota_exceeded': self.key_usage.get(idx, {}).get('quota_exceeded', False),
                    'error_count': self.key_errors.get(idx, {}).get('error_count', 0),
                    'consecutive_errors': self.key_errors.get(idx, {}).get('consecutive_errors', 0)
                })
            return status


class AIService:
    def __init__(self):
        self.model = None
        self.key_manager = APIKeyManager()
        pygame.mixer.init()
        
        if not self.key_manager.api_keys:
            print("CRITICAL ERROR: No API keys available.")
            return
        
        # Configure with first key
        self.configure_with_current_key()
        self.connect_to_model()

    def configure_with_current_key(self):
        """Configure Gemini with the current API key"""
        current_key = self.key_manager.get_current_key()
        if current_key:
            genai.configure(api_key=current_key)
            print(f"Configured with API key {self.key_manager.current_key_index + 1}")
        else:
            print("ERROR: No API key available for configuration")

    def connect_to_model(self):
        """
        Robustly finds a working model by testing them with multiple keys if needed.
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
        
        # Try each key until we find one that works
        keys_tried = set()
        
        while len(keys_tried) < len(self.key_manager.api_keys):
            current_key_idx = self.key_manager.current_key_index
            current_key = self.key_manager.get_current_key()
            
            if current_key_idx in keys_tried:
                # Already tried this key, move to next
                self.key_manager.get_next_key()
                continue
                
            keys_tried.add(current_key_idx)
            
            try:
                # Configure with current key
                genai.configure(api_key=current_key)
                
                for model_name in candidates:
                    try:
                        test_model = genai.GenerativeModel(model_name)
                        # Simple handshake test
                        test_model.generate_content("Hi") 
                        self.model = test_model
                        self.key_manager.record_success(current_key_idx)
                        print(f"SUCCESS: Connected to '{model_name}' using API key {current_key_idx + 1}")
                        return
                    except Exception as e:
                        print(f"Model {model_name} failed: {str(e)[:100]}")
                        continue
                        
            except Exception as e:
                error_msg = str(e)
                print(f"Connection failed with key {current_key_idx + 1}: {error_msg}")
                self.key_manager.record_error(current_key_idx, error_msg)
                
                # Try next key
                self.key_manager.get_next_key()
                continue
        
        print("\nCRITICAL ERROR: No models are working with any API key.")

    def retry_api_call(self, prompt, retries=3, delay=2):
        """Enhanced retry with multiple API key support"""
        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                # Record success for current key
                self.key_manager.record_success(self.key_manager.current_key_index)
                return response
                
            except Exception as e:
                error_str = str(e).lower()
                current_key_idx = self.key_manager.current_key_index
                
                # Record the error
                self.key_manager.record_error(current_key_idx, str(e))
                
                # Check if we should try with a different key
                if "429" in error_str or "quota" in error_str or "resource exhausted" in error_str:
                    print(f"Key {current_key_idx + 1} quota/rate limit hit. Switching keys...")
                    
                    # Switch to next key
                    next_key = self.key_manager.get_next_key()
                    if next_key:
                        try:
                            # Reconfigure with new key
                            genai.configure(api_key=next_key)
                            # Recreate model with new configuration
                            if self.model:
                                model_name = self.model.model_name if hasattr(self.model, 'model_name') else "gemini-1.5-flash"
                                self.model = genai.GenerativeModel(model_name)
                            print(f"Retrying with API key {self.key_manager.current_key_index + 1}")
                        except Exception as config_error:
                            print(f"Failed to configure new key: {config_error}")
                            continue
                    
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay += 2  # Exponential backoff
                    else:
                        raise Exception(f"All API keys exhausted. Last error: {error_str}")
                else:
                    # For non-quota errors, retry with same key
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay += 2
                    else:
                        raise e

    def get_api_key_status(self):
        """Get current status of all API keys"""
        return self.key_manager.get_status()

    # ============================================================
    # WORKFLOW: Context Aware + Dual Analysis Translation
    # ============================================================

    def translate_text(self, text, source_lang, target_lang):
        if not self.model: 
            # Try to reconnect
            try:
                self.connect_to_model()
                if not self.model:
                    return {"error": "AI Model not connected."}
            except:
                return {"error": "AI Model not connected."}

        try:
            # STEP 1: Detect Context & Simplify
            context = self._detect_context(text)
            category = context.get("category", "General")
            explanation = context.get("simplified_explanation", "No explanation provided.")
            
            print(f"Detected: {category} | Context: {explanation} | Using API key {self.key_manager.current_key_index + 1}")

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

        # DYNAMIC LANGUAGE RULES - STRICTLY ENFORCED
        src_rule = ""
        if src == "Urdu":
            src_rule = """
            CRITICAL LANGUAGE RULES FOR URDU SOURCE:
            1. ABSOLUTELY NO ENGLISH WORDS in any 'source_analysis' field.
            2. Structure analysis: Must be 100% Urdu script. Example: "یہ سادہ جملہ ہے۔" (CORRECT), NOT "This is a simple sentence."
            3. Grammar analysis: Must use ONLY Urdu grammatical terms:
               - Noun = اسم
               - Verb = فعل
               - Adjective = صفت
               - Adverb = حال
               - Subject = فاعل
               - Object = مفعول
               - Sentence = جملہ
               - Phrase = فقرہ
            4. Synonyms: List of Urdu words ONLY in Urdu script.
            5. Antonyms: List of Urdu words ONLY in Urdu script.
            6. Correction: If perfect, write ONLY "زبردست! ✅" - no English text.
            7. ZERO tolerance for language mixing in Urdu fields.
            """
        else:
            src_rule = f"""
            CRITICAL LANGUAGE RULES FOR {src.upper()} SOURCE:
            1. ABSOLUTELY NO MIXED LANGUAGES in any 'source_analysis' field.
            2. All analysis must be in {src} only.
            3. Structure, grammar, correction: Must use {src} language only.
            4. Synonyms: List of {src} words only.
            5. Antonyms: List of {src} words only.
            6. Correction: If perfect, write ONLY "Perfect! ✅" in {src}.
            """

        tgt_rule = ""
        if tgt == "Urdu":
            tgt_rule = """
            CRITICAL LANGUAGE RULES FOR URDU TARGET:
            1. ABSOLUTELY NO ENGLISH WORDS in any 'target_analysis' field.
            2. Structure analysis: Must be 100% Urdu script. Example: "اس جملے کی ساخت سادہ ہے۔"
            3. Grammar analysis: Must use ONLY Urdu grammatical terms:
               - Noun = اسم
               - Verb = فعل
               - Adjective = صفت
               - Adverb = حال
               - Subject = فاعل
               - Object = مفعول
               - Sentence = جملہ
               - Phrase = فقرہ
            4. Synonyms: List of Urdu words ONLY in Urdu script.
            5. Antonyms: List of Urdu words ONLY in Urdu script.
            6. ZERO tolerance for language mixing in Urdu fields.
            """
        else:
            tgt_rule = f"""
            CRITICAL LANGUAGE RULES FOR {tgt.upper()} TARGET:
            1. ABSOLUTELY NO MIXED LANGUAGES in any 'target_analysis' field.
            2. All analysis must be in {tgt} only.
            3. Structure, grammar: Must use {tgt} language only.
            4. Synonyms: List of {tgt} words only.
            5. Antonyms: List of {tgt} words only.
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
        
        ==================== STRICT LANGUAGE ENFORCEMENT ====================
        {src_rule}
        {tgt_rule}
        =====================================================================
        
        STRUCTURE GUIDELINES:
        - For structure analysis: Describe the sentence type and construction
        - For grammar analysis: Break down the grammatical components
        - For synonyms/antonyms: Provide common, appropriate words/phrases
        
        IMPORTANT FOR URDU:
        - Use proper Urdu script (Nastaliq style)
        - Avoid Romanized Urdu (Urdu written in English letters)
        - Use proper Urdu punctuation
        
        JSON FIELD-SPECIFIC LANGUAGE RULES:
        1. For Urdu sections (source or target):
           - "structure": 100% Urdu script, NO English
           - "grammar": 100% Urdu script, NO English  
           - "correction": 100% Urdu script, NO English
           - "synonyms": List of Urdu words in Urdu script
           - "antonyms": List of Urdu words in Urdu script
           
        2. For English/non-Urdu sections:
           - All fields: 100% in that language, NO mixing
           
        3. The JSON keys ("structure", "grammar", etc.) stay in English.
           Only the VALUES change language based on rules above.
        
        FINAL CHECK: Before outputting, verify NO language mixing in any field.
        
        Strictly output this NESTED JSON structure:
        {{
            "translation": "The direct translated text",
            "source_analysis": {{
                "structure": "Analysis of sentence structure",
                "grammar": "Analysis of grammatical components",
                "correction": "Corrected text or 'Perfect! ✅' or 'زبردست! ✅'",
                "synonyms": ["List of synonyms in appropriate language"],
                "antonyms": ["List of antonyms in appropriate language"]
            }},
            "target_analysis": {{
                "structure": "Analysis of sentence structure",
                "grammar": "Analysis of grammatical components",
                "synonyms": ["List of synonyms in appropriate language"],
                "antonyms": ["List of antonyms in appropriate language"]
            }}
        }}
        
        ULTIMATE RULE: If analyzing Urdu text, use ZERO English words in any analysis field.
        """
        
        response = self.retry_api_call(prompt)
        result = self._parse_json(response.text)
        
        # Apply language validation to catch any remaining mixing
        return self._validate_language_purity(result, src, tgt)

    def _validate_language_purity(self, result, source_lang, target_lang):
        """
        Validates and cleans language mixing in the result
        """
        def clean_urdu_field(field_value):
            """Remove English text from Urdu fields"""
            if not field_value or not isinstance(field_value, str):
                return field_value
            
            # If it's already pure Urdu, return as is
            if re.search(r'[\u0600-\u06FF]', field_value) and not re.search(r'[a-zA-Z]', field_value):
                return field_value
            
            # Try to extract Urdu parts (between Urdu characters)
            urdu_parts = re.findall(r'[\u0600-\u06FF][\u0600-\u06FF\s\u064B-\u065F,،.!؟]*', field_value)
            if urdu_parts:
                return ' '.join(urdu_parts).strip()
            
            return field_value
        
        def clean_english_field(field_value, lang):
            """Ensure non-Urdu fields don't have Urdu"""
            if not field_value or not isinstance(field_value, str):
                return field_value
            
            # Remove Urdu script if present in non-Urdu field
            if lang != "Urdu" and re.search(r'[\u0600-\u06FF]', field_value):
                # Keep only non-Urdu characters
                cleaned = re.sub(r'[\u0600-\u06FF]', '', field_value)
                return cleaned.strip()
            
            return field_value
        
        # Clean source analysis
        if "source_analysis" in result:
            sa = result["source_analysis"]
            for field in ["structure", "grammar", "correction"]:
                if field in sa:
                    if source_lang == "Urdu":
                        sa[field] = clean_urdu_field(sa[field])
                    else:
                        sa[field] = clean_english_field(sa[field], source_lang)
            
            # Clean lists
            for field in ["synonyms", "antonyms"]:
                if field in sa and isinstance(sa[field], list):
                    if source_lang == "Urdu":
                        sa[field] = [clean_urdu_field(item) for item in sa[field]]
                    else:
                        sa[field] = [clean_english_field(item, source_lang) for item in sa[field]]
        
        # Clean target analysis
        if "target_analysis" in result:
            ta = result["target_analysis"]
            for field in ["structure", "grammar"]:
                if field in ta:
                    if target_lang == "Urdu":
                        ta[field] = clean_urdu_field(ta[field])
                    else:
                        ta[field] = clean_english_field(ta[field], target_lang)
            
            # Clean lists
            for field in ["synonyms", "antonyms"]:
                if field in ta and isinstance(ta[field], list):
                    if target_lang == "Urdu":
                        ta[field] = [clean_urdu_field(item) for item in ta[field]]
                    else:
                        ta[field] = [clean_english_field(item, target_lang) for item in ta[field]]
        
        return result

    def _parse_json(self, text):
        try:
            # Clean the text to extract JSON
            clean_text = text.strip()
            
            # Remove markdown code blocks if present
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            elif clean_text.startswith('```'):
                clean_text = clean_text[3:]
            
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            clean_text = clean_text.strip()
            
            # Parse JSON
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Raw text: {text}")
            # Try to find JSON in the text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {}
        except Exception as e:
            print(f"Error parsing JSON: {e}")
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
        
        # Source language rules - STRICTLY ENFORCED
        if is_source_urdu:
            source_instr = f"""
            FOR SOURCE ANALYSIS (URDU) - STRICT RULES:
            1. ABSOLUTELY NO ENGLISH WORDS in any field.
            2. Definition: 100% Urdu script (e.g., "پڑھنے کا عمل")
            3. Part of speech: Use ONLY Urdu terms from mapping above
            4. Synonyms: 3-5 URDU words in URDU SCRIPT ONLY
            5. Antonyms: 3-5 URDU words in URDU SCRIPT ONLY
            6. ZERO tolerance for language mixing
            7. The JSON keys stay in English, values must be pure Urdu
            """
        else:
            source_instr = f"""
            FOR SOURCE ANALYSIS ({source_lang}) - STRICT RULES:
            1. ABSOLUTELY NO MIXED LANGUAGES in any field.
            2. Definition: {source_lang} only
            3. Part of speech: English terms only (Noun, Verb, etc.)
            4. Synonyms: 3-5 words in {source_lang} only
            5. Antonyms: 3-5 words in {source_lang} only
            6. ZERO tolerance for language mixing
            """
        
        # Target language rules - STRICTLY ENFORCED
        if is_target_urdu:
            target_instr = f"""
            FOR TARGET ANALYSIS (URDU) - STRICT RULES:
            1. ABSOLUTELY NO ENGLISH WORDS in any field.
            2. Translation: 100% Urdu script
            3. Definition: 100% Urdu script
            4. Part of speech: Use ONLY Urdu terms from mapping above
            5. Synonyms: 3-5 URDU words in URDU SCRIPT ONLY
            6. Antonyms: 3-5 URDU words in URDU SCRIPT ONLY
            7. ZERO tolerance for language mixing
            8. Use proper Urdu grammar and punctuation
            """
        else:
            target_instr = f"""
            FOR TARGET ANALYSIS ({target_lang}) - STRICT RULES:
            1. ABSOLUTELY NO MIXED LANGUAGES in any field.
            2. Translation: {target_lang} only
            3. Definition: English only
            4. Part of speech: English terms only
            5. Synonyms: 3-5 words in {target_lang} only
            6. Antonyms: 3-5 words in {target_lang} only
            """
        
        prompt = f"""
        ACT AS A BILINGUAL LINGUISTIC EXPERT.
        
        Task: Analyze the word "{word}" in {source_lang} and provide its translation and analysis in {target_lang}.
        
        {pos_mappings}
        
        ==================== CRITICAL LANGUAGE RULES ====================
        IMPORTANT INSTRUCTIONS:
        {source_instr}
        
        {target_instr}
        
        ABSOLUTE REQUIREMENTS:
        1. NO MIXED LANGUAGES within any section
        2. If Urdu section: ZERO English words allowed
        3. If non-Urdu section: ZERO Urdu script allowed
        4. Each field must be PURE in its assigned language
        5. JSON keys stay in English, VALUES follow language rules above
        =================================================================
        
        Provide comprehensive bilingual analysis:
        
        1. For SOURCE language ({source_lang}):
           - Definition (100% pure language as per rules)
           - Part of speech (appropriate language terms)
           - 3-5 Synonyms (appropriate language only)
           - 3-5 Antonyms (appropriate language only)
        
        2. For TARGET language ({target_lang}):
           - Natural translation (100% pure language)
           - Definition (appropriate language only)
           - Part of speech (appropriate language terms)
           - 3-5 Synonyms (appropriate language only)
           - 3-5 Antonyms (appropriate language only)
        
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
        
        FINAL VERIFICATION: Check each field for language purity before output.
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
            
            # Apply language validation
            result = self._validate_language_purity(result, source_lang, target_lang)
            
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