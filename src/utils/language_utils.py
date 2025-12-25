"""
Language utilities for translation and validation
"""
import re

def is_urdu(text):
    """Check if text contains Urdu characters"""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', str(text)))

def has_english(text):
    """Check if text contains English letters"""
    if not text or not isinstance(text, str):
        return False
    return bool(re.search(r'[a-zA-Z]', str(text)))

def clean_urdu_text(text):
    """Remove English text from Urdu content"""
    if not text or not isinstance(text, str):
        return text
    
    # If it's already pure Urdu, return as is
    if is_urdu(text) and not has_english(text):
        return text
    
    # Extract Urdu parts and join them
    urdu_parts = re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF][\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s\u064B-\u065F,،.۔!؟:؛]*', text)
    if urdu_parts:
        cleaned = ' '.join(urdu_parts).strip()
        # Clean up extra punctuation
        cleaned = re.sub(r'[\s,،]+$', '', cleaned)
        return cleaned if cleaned else text
    
    return text

def clean_english_text(text, lang):
    """Ensure non-Urdu fields don't have Urdu"""
    if not text or not isinstance(text, str):
        return text
    
    # Remove Urdu script if present in non-Urdu field
    if lang != "Urdu" and is_urdu(text):
        # Keep only non-Urdu characters
        cleaned = re.sub(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', text)
        return cleaned.strip()
    
    return text

def get_language_rules(src, tgt):
    """Generate language rules for translation prompts"""
    from src.config.settings import URDU_GRAMMAR_TERMS
    
    src_rule = ""
    if src == "Urdu":
        src_rule = f"""
        CRITICAL LANGUAGE RULES FOR URDU SOURCE:
        1. ABSOLUTELY NO ENGLISH WORDS in any 'source_analysis' field.
        2. Structure analysis: Must be 100% Urdu script. Example: "یہ سادہ جملہ ہے۔" (CORRECT), NOT "This is a simple sentence."
        3. Grammar analysis: Must use ONLY Urdu grammatical terms:
           - Noun = {URDU_GRAMMAR_TERMS['Noun']}
           - Verb = {URDU_GRAMMAR_TERMS['Verb']}
           - Adjective = {URDU_GRAMMAR_TERMS['Adjective']}
           - Adverb = {URDU_GRAMMAR_TERMS['Adverb']}
           - Subject = {URDU_GRAMMAR_TERMS['Subject']}
           - Object = {URDU_GRAMMAR_TERMS['Object']}
           - Sentence = {URDU_GRAMMAR_TERMS['Sentence']}
           - Phrase = {URDU_GRAMMAR_TERMS['Phrase']}
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
        tgt_rule = f"""
        CRITICAL LANGUAGE RULES FOR URDU TARGET:
        1. ABSOLUTELY NO ENGLISH WORDS in any 'target_analysis' field.
        2. Structure analysis: Must be 100% Urdu script. Example: "اس جملے کی ساخت سادہ ہے۔"
        3. Grammar analysis: Must use ONLY Urdu grammatical terms:
           - Noun = {URDU_GRAMMAR_TERMS['Noun']}
           - Verb = {URDU_GRAMMAR_TERMS['Verb']}
           - Adjective = {URDU_GRAMMAR_TERMS['Adjective']}
           - Adverb = {URDU_GRAMMAR_TERMS['Adverb']}
           - Subject = {URDU_GRAMMAR_TERMS['Subject']}
           - Object = {URDU_GRAMMAR_TERMS['Object']}
           - Sentence = {URDU_GRAMMAR_TERMS['Sentence']}
           - Phrase = {URDU_GRAMMAR_TERMS['Phrase']}
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
    
    return src_rule, tgt_rule

def format_synonyms_antonyms(data_list):
    """Format synonyms/antonyms list for display"""
    if not data_list or not isinstance(data_list, list):
        return "-"
    # Filter out any empty strings
    filtered = [item for item in data_list if item and str(item).strip()]
    return ", ".join(filtered) if filtered else "-"