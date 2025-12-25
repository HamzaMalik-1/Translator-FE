"""
Audio service for text-to-speech and speech recognition
"""
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
from src.config.settings import LANGUAGE_MAP

class AudioService:
    """Handles audio input/output functionality"""
    
    def __init__(self):
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()
    
    def text_to_speech(self, text, language_name):
        """Convert text to speech"""
        lang_code = LANGUAGE_MAP.get(language_name, "en")
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            filename = "temp_audio.mp3"
            
            # Clean up old file
            if os.path.exists(filename):
                try:
                    pygame.mixer.music.unload()
                    os.remove(filename)
                except: 
                    pass
            
            tts.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            print(f"TTS Error: {e}")
    
    def listen_audio(self):
        """Listen to audio input and convert to text"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=5)
                return self.recognizer.recognize_google(audio)
            except Exception as e:
                print(f"Mic Error: {e}")
                return None
    
    def cleanup(self):
        """Clean up audio resources"""
        try:
            pygame.mixer.quit()
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
        except:
            pass