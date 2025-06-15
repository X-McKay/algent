#!/usr/bin/env python3
"""
Test script to verify CLI installation
"""

import sys
import importlib.util

def test_import():
    """Test if CLI module can be imported"""
    try:
        from src.cli import app
        print("✅ CLI import successful")
        return True
    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
        return False

def test_typer_app():
    """Test if Typer app is properly configured"""
    try:
        from src.cli import app
        
        # Check if it's a Typer app
        if hasattr(app, 'info') and hasattr(app, 'commands'):
            print("✅ Typer app properly configured")
            return True
        else:
            print("❌ Not a valid Typer app")
            return False
    except Exception as e:
        print(f"❌ Typer app test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Algent CLI installation...")
    
    success = True
    success &= test_import()
    success &= test_typer_app()
    
    if success:
        print("\n🎉 All tests passed! CLI is ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the installation.")
        sys.exit(1)
