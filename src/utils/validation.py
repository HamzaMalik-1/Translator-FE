"""
Validation utilities for translation results
"""
import re
from .language_utils import clean_urdu_text, clean_english_text

def validate_language_purity(result, source_lang, target_lang):
    """
    Validates and cleans language mixing in the result
    """
    def clean_urdu_field(field_value):
        """Remove English text from Urdu fields"""
        return clean_urdu_text(field_value)
    
    def clean_english_field(field_value, lang):
        """Ensure non-Urdu fields don't have Urdu"""
        return clean_english_text(field_value, lang)
    
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