# run.py at project root
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the main function from app/main.py
from app.main import main

if __name__ == "__main__":
    main()