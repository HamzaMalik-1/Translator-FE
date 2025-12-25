"""
Configuration settings and constants for the translator app
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEYS = []

# Load API keys from environment
def load_api_keys():
    """Load all API keys from environment variables"""
    keys = []
    
    # Main key
    main_key = os.getenv("GEMINI_API_KEY")
    if main_key:
        keys.append(main_key)
    
    # Numbered keys
    i = 1
    while True:
        key_name = f"GEMINI_API_KEY_{i}"
        key = os.getenv(key_name)
        if key:
            keys.append(key)
            i += 1
        else:
            break
    
    # Comma-separated list
    key_list = os.getenv("GEMINI_API_KEYS")
    if key_list:
        keys.extend([k.strip() for k in key_list.split(",") if k.strip()])
    
    return keys

# Model candidates
MODEL_CANDIDATES = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-exp", 
    "gemini-pro",
    "gemma-3-4b-it",
    "gemma-2-9b-it"
]

# Language mapping for TTS
LANGUAGE_MAP = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Chinese": "zh-CN",
    "Russian": "ru",
    "Urdu": "ur",
    "Hindi": "hi",
    "Arabic": "ar",
    "Auto Detect": "en"
}

# Urdu grammatical terms
URDU_GRAMMAR_TERMS = {
    "Noun": "اسم",
    "Verb": "فعل",
    "Adjective": "صفت",
    "Adverb": "حال",
    "Subject": "فاعل",
    "Object": "مفعول",
    "Sentence": "جملہ",
    "Phrase": "فقرہ",
    "Pronoun": "ضمیر",
    "Preposition": "حرف جار",
    "Conjunction": "حرف عطف",
    "Interjection": "حرف ندا"
}

# Part of speech mappings for bilingual analysis
POS_MAPPINGS = """
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

# Context categories
CONTEXT_CATEGORIES = ["Medical", "Legal", "Slang", "Meme", "Poetic", "General"]

# App settings
APP_NAME = "Gemini AI Translator"
APP_VERSION = "1.0.0"
WINDOW_SIZE = (1100, 900)