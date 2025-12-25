#!/usr/bin/env python3
"""
Entry point script for Gemini AI Translator
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import and run the main function
    from src.main import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"Error importing module: {e}")
    print("Make sure you're running from the project root directory.")
    print("Project structure should be:")
    print("  translator_app/")
    print("  ├── run.py")
    print("  ├── src/")
    print("  │   └── main.py")
    print("  └── ...")
    sys.exit(1)
except Exception as e:
    print(f"Error running application: {e}")
    sys.exit(1)