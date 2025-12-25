#!/usr/bin/env python3
"""
Gold Standard Web UI Launcher
Quick start script for the web interface
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == '__main__':
    # Set default environment variables
    os.environ.setdefault('WEB_UI_HOST', '0.0.0.0')
    os.environ.setdefault('WEB_UI_PORT', '5000')
    os.environ.setdefault('FLASK_DEBUG', 'false')
    
    # Import and run the app
    from web_ui.app import main
    main()
