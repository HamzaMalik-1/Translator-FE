"""
JSON parsing utilities
"""
import json
import re

def parse_json_response(text):
    """
    Parse JSON from Gemini API response, handling markdown code blocks
    """
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