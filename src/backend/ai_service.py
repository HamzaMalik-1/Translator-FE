"""
Main AI Service for translation and analysis
"""
import google.generativeai as genai
import time
from src.backend.api_key_manager import APIKeyManager
from src.utils.json_parser import parse_json_response
from src.utils.language_utils import get_language_rules, is_urdu
from src.utils.validation import validate_language_purity
from src.config.settings import MODEL_CANDIDATES, CONTEXT_CATEGORIES, POS_MAPPINGS

class AIService:
    """Main AI service for translation and analysis"""
    
    def __init__(self):
        self.model = None
        self.key_manager = APIKeyManager()
        
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
                
                for model_name in MODEL_CANDIDATES:
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
        1. Categorize into ONE: {CONTEXT_CATEGORIES}.
        2. Simplify explanation.
        Output JSON: {{ "category": "...", "simplified_explanation": "..." }}
        """
        try:
            response = self.retry_api_call(prompt)
            return parse_json_response(response.text)
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

        # Get language rules
        src_rule, tgt_rule = get_language_rules(src, tgt)

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
        result = parse_json_response(response.text)
        
        # Apply language validation to catch any remaining mixing
        return validate_language_purity(result, src, tgt)

    # --- Single Word Analysis ---
    def analyze_single_word(self, word):
        if not self.model: 
            return {"error": "AI Model not connected."}
        
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
            return parse_json_response(response.text)
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
        
        {POS_MAPPINGS}
        
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
            result = parse_json_response(response.text)
            
            # Ensure we have proper structure
            if "source_analysis" not in result:
                result["source_analysis"] = {}
            if "target_analysis" not in result:
                result["target_analysis"] = {}
            
            # Add translation at root level for convenience
            if "target_analysis" in result and "translation" in result["target_analysis"]:
                result["translation"] = result["target_analysis"]["translation"]
            
            # Apply language validation
            result = validate_language_purity(result, source_lang, target_lang)
            
            return result
        except Exception as e:
            print(f"Error in bilingual word analysis: {e}")
            return {"error": str(e)}