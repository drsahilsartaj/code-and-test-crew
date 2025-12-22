"""Main entry point for the Intelligent Code Generation Crew."""

import os
import sys

# Ensure we're in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create necessary directories
os.makedirs("outputs", exist_ok=True)
os.makedirs("logs", exist_ok=True)

from gui.app import main

if __name__ == "__main__":
    main()
