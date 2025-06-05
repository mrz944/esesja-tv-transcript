import os
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init()

class Config:
    """Configuration manager for the esesja.tv scraper."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self._ensure_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        dirs = [
            self.config['storage']['videos_dir'],
            self.config['storage']['transcripts_dir'],
            self.config['storage']['logs_dir']
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'scraping.base_url')."""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value

class Logger:
    """Enhanced logger with colored output and file logging."""
    
    def __init__(self, name: str, config: Config):
        self.config = config
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        log_file = Path(config.get('storage.logs_dir')) / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def success(self, message: str):
        """Log success message with green color."""
        self.logger.info(f"SUCCESS: {message}")

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.WHITE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
        'SUCCESS': Fore.GREEN
    }
    
    def format(self, record):
        # Add color based on level
        level_color = self.COLORS.get(record.levelname, Fore.WHITE)
        
        # Special handling for SUCCESS messages
        if hasattr(record, 'msg') and record.msg.startswith('SUCCESS:'):
            level_color = self.COLORS['SUCCESS']
            record.msg = record.msg.replace('SUCCESS: ', '')
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Create colored message
        colored_message = f"{Fore.BLUE}[{timestamp}]{Style.RESET_ALL} {level_color}{record.levelname}{Style.RESET_ALL}: {record.getMessage()}"
        
        return colored_message

class ProgressTracker:
    """Track processing progress and allow resuming."""
    
    def __init__(self, config: Config):
        self.config = config
        self.progress_file = Path(config.get('storage.progress_file'))
        self.progress_data = self._load_progress()
    
    def _load_progress(self) -> Dict[str, Any]:
        """Load progress from JSON file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return {
            'videos': {},
            'last_updated': None,
            'total_processed': 0,
            'total_failed': 0
        }
    
    def save_progress(self):
        """Save current progress to file."""
        self.progress_data['last_updated'] = datetime.now().isoformat()
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
    
    def is_processed(self, video_url: str) -> bool:
        """Check if video has been successfully processed."""
        return (video_url in self.progress_data['videos'] and 
                self.progress_data['videos'][video_url].get('status') == 'completed')
    
    def mark_completed(self, video_url: str, video_data: Dict[str, Any]):
        """Mark video as completed."""
        self.progress_data['videos'][video_url] = {
            **video_data,
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        }
        self.progress_data['total_processed'] += 1
        self.save_progress()
    
    def mark_failed(self, video_url: str, error: str):
        """Mark video as failed."""
        self.progress_data['videos'][video_url] = {
            'status': 'failed',
            'error': error,
            'failed_at': datetime.now().isoformat()
        }
        self.progress_data['total_failed'] += 1
        self.save_progress()
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        completed = sum(1 for v in self.progress_data['videos'].values() 
                       if v.get('status') == 'completed')
        failed = sum(1 for v in self.progress_data['videos'].values() 
                    if v.get('status') == 'failed')
        
        return {
            'completed': completed,
            'failed': failed,
            'total': len(self.progress_data['videos'])
        }

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove extra whitespace and limit length
    filename = ' '.join(filename.split())
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def print_banner():
    """Print application banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    esesja.tv Video Scraper                   ║
║                   and Transcript Generator                   ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)
