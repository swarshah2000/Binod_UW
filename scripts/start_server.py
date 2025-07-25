#!/usr/bin/env python3
"""
TT FIX Order Adapter Server Startup Script
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import and run main application
from main import main
import asyncio

if __name__ == "__main__":
    print("Starting TT FIX Order Adapter Server...")
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
