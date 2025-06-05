#!/usr/bin/env python3
"""
Setup script for esesja.tv Video Scraper and Transcript Generator

This script helps users set up the project by:
- Checking system requirements
- Installing Python dependencies
- Verifying ffmpeg installation
- Testing Whisper model loading
- Creating necessary directories
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Print setup header."""
    print("=" * 60)
    print("esesja.tv Video Scraper - Setup Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported")
        print("   Please install Python 3.8 or higher")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def check_ffmpeg():
    """Check if ffmpeg is installed."""
    print("\n🎬 Checking ffmpeg installation...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extract version from output
            version_line = result.stdout.split('\n')[0]
            print(f"✅ {version_line}")
            return True
        else:
            print("❌ ffmpeg found but not working properly")
            return False
    except FileNotFoundError:
        print("❌ ffmpeg not found")
        print_ffmpeg_install_instructions()
        return False
    except subprocess.TimeoutExpired:
        print("❌ ffmpeg check timed out")
        return False

def print_ffmpeg_install_instructions():
    """Print platform-specific ffmpeg installation instructions."""
    system = platform.system().lower()
    
    print("\n📋 ffmpeg Installation Instructions:")
    
    if system == "darwin":  # macOS
        print("   macOS: brew install ffmpeg")
    elif system == "linux":
        print("   Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg")
        print("   CentOS/RHEL: sudo yum install ffmpeg")
        print("   Arch Linux: sudo pacman -S ffmpeg")
    elif system == "windows":
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("   Add ffmpeg.exe to your system PATH")
    else:
        print("   Please install ffmpeg for your operating system")
        print("   Visit: https://ffmpeg.org/download.html")

def install_python_dependencies():
    """Install Python dependencies from requirements.txt."""
    print("\n📦 Installing Python dependencies...")
    
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        # Use pip to install requirements
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Python dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install Python dependencies")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def test_whisper_import():
    """Test if Whisper can be imported and a model can be loaded."""
    print("\n🎤 Testing Whisper installation...")
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Try to load the smallest model to test
        print("   Loading tiny model for testing...")
        model = whisper.load_model("tiny")
        print("✅ Whisper model loaded successfully")
        
        # Clean up
        del model
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Whisper: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to load Whisper model: {e}")
        print("   This might be due to missing dependencies or insufficient memory")
        return False

def test_other_imports():
    """Test other critical imports."""
    print("\n📚 Testing other dependencies...")
    
    required_modules = [
        ("requests", "HTTP requests"),
        ("beautifulsoup4", "Web scraping"),
        ("yt_dlp", "Video downloading"),
        ("yaml", "Configuration"),
        ("tqdm", "Progress bars"),
        ("colorama", "Colored output")
    ]
    
    failed_imports = []
    
    for module_name, description in required_modules:
        try:
            if module_name == "beautifulsoup4":
                import bs4
            elif module_name == "yt_dlp":
                import yt_dlp
            else:
                __import__(module_name)
            print(f"✅ {description} - OK")
        except ImportError:
            print(f"❌ {description} - FAILED")
            failed_imports.append(module_name)
    
    return len(failed_imports) == 0

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        "data",
        "data/videos",
        "data/transcripts",
        "logs"
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created: {directory}/")
        except Exception as e:
            print(f"❌ Failed to create {directory}/: {e}")
            return False
    
    return True

def check_config_file():
    """Check if config file exists."""
    print("\n⚙️  Checking configuration...")
    
    if Path("config.yaml").exists():
        print("✅ config.yaml found")
        return True
    else:
        print("❌ config.yaml not found")
        print("   The application needs a config.yaml file to run")
        return False

def run_basic_test():
    """Run a basic test of the application."""
    print("\n🧪 Running basic functionality test...")
    
    try:
        # Try to import our modules
        from utils import Config, Logger
        print("✅ Utils module imported")
        
        # Try to load config
        if Path("config.yaml").exists():
            config = Config("config.yaml")
            print("✅ Configuration loaded")
            
            # Try to create logger
            logger = Logger("setup_test", config)
            print("✅ Logger created")
            
            return True
        else:
            print("❌ Cannot test without config.yaml")
            return False
            
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return False

def print_summary(results):
    """Print setup summary."""
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    
    all_good = True
    
    for check, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check}")
        if not status:
            all_good = False
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("🎉 Setup completed successfully!")
        print("\nYou can now run the application:")
        print("   python main.py")
        print("\nOr for help:")
        print("   python main.py --help")
    else:
        print("⚠️  Setup completed with issues")
        print("\nPlease fix the failed checks above before running the application.")
        print("Refer to the README.md for detailed installation instructions.")

def main():
    """Main setup function."""
    print_header()
    
    # Run all checks
    results = {
        "Python version (3.8+)": check_python_version(),
        "ffmpeg installation": check_ffmpeg(),
        "Python dependencies": install_python_dependencies(),
        "Whisper installation": test_whisper_import(),
        "Other dependencies": test_other_imports(),
        "Directory creation": create_directories(),
        "Configuration file": check_config_file(),
        "Basic functionality": run_basic_test()
    }
    
    # Print summary
    print_summary(results)
    
    # Return exit code
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
