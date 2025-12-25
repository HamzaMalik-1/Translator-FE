#!/usr/bin/env python3
import subprocess
import sys
import platform

def install_requirements():
    """Install all requirements with platform-specific handling"""
    
    print("Installing Gemini Translator requirements...")
    print(f"Platform: {platform.system()}")
    
    # Common packages
    packages = [
        "PySide6>=6.5.0",
        "google-generativeai>=0.3.0", 
        "SpeechRecognition>=3.10.0",
        "gTTS>=2.3.0",
        "pygame>=2.5.0",
        "pyperclip>=1.8.2",
        "python-dotenv>=1.0.0",
        "regex>=2022.10.31",
        "chardet>=5.1.0",
        "pyttsx3>=2.90",  # Backup TTS
    ]
    
    # Platform-specific handling
    system = platform.system()
    
    if system == "Windows":
        print("Windows detected - PyAudio may need manual installation")
        packages.append("PyAudio>=0.2.11")
        
    elif system == "Linux":
        print("Linux detected - installing system dependencies may be needed")
        packages.append("PyAudio>=0.2.11")
        
        # Try to install system dependencies
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y", 
                          "python3-dev", "portaudio19-dev", "python3-pyaudio"], 
                         check=False)
        except:
            print("Note: System package installation may need manual setup")
            
    elif system == "Darwin":  # macOS
        print("macOS detected - ensure portaudio is installed via Homebrew")
        packages.append("PyAudio>=0.2.11")
    
    # Install packages
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
            print(f"  Try: pip install {package}")
    
    print("\nInstallation complete!")
    print("\nIf PyAudio fails, try these alternatives:")
    print("  Windows: Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/")
    print("  macOS:   brew install portaudio")
    print("  Linux:   sudo apt-get install python3-pyaudio")

if __name__ == "__main__":
    install_requirements()