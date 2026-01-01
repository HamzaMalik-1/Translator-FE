#!/usr/bin/env python3
import importlib
import sys

REQUIRED_PACKAGES = [
    ("PySide6", "PySide6"),
    ("google.generativeai", "google-generativeai"),
    ("speech_recognition", "SpeechRecognition"),
    ("gtts", "gTTS"),
    ("pygame", "pygame"),
    ("pyperclip", "pyperclip"),
    ("dotenv", "python-dotenv"),
    ("pyaudio", "PyAudio"),
    ("pyttsx3", "pyttsx3"),
    ("regex", "regex"),
]

def check_package(package_name, pip_name):
    """Check if a package is installed"""
    try:
        importlib.import_module(package_name)
        return True, f"✓ {pip_name} ({package_name})"
    except ImportError:
        return False, f"✗ {pip_name} ({package_name})"

def main():
    print("Checking dependencies for Gemini Translator...")
    print("=" * 50)
    
    all_ok = True
    results = []
    
    for package_name, pip_name in REQUIRED_PACKAGES:
        success, message = check_package(package_name, pip_name)
        results.append((success, message))
        if not success:
            all_ok = False
    
    # Print results
    for success, message in results:
        print(message)
    
    print("=" * 50)
    
    if all_ok:
        print("✅ All dependencies are installed!")
    else:
        print("❌ Some dependencies are missing.")
        print("\nTo install missing packages:")
        print("  pip install -r requirements.txt")
        print("\nOr install individually:")
        for success, message in results:
            if not success:
                pip_name = message.split(" ")[1]
                print(f"  pip install {pip_name}")

if __name__ == "__main__":
    main()