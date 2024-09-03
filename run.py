import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(__file__))

from src.main import main

if __name__ == "__main__":
    main()