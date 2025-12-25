"""
Utility functions module
"""
from .json_parser import parse_json_response
from .language_utils import (
    is_urdu, has_english, clean_urdu_text, clean_english_text,
    get_language_rules, format_synonyms_antonyms
)
from .validation import validate_language_purity