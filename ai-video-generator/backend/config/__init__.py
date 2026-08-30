"""
Configuration management for AI Video Generator backend.
Handles settings persistence and retrieval.
"""

import json
import os
from pathlib import Path

class Config:
    """Manages application configuration with local JSON storage."""
    
    DEFAULT_CONFIG = {
        "ai": {
            "provider": "openai",
            "api_key": "",
            "model": "auto",
            "base_url": ""
        },
        "blender": {
            "executable_path": ""
        },
        "ffmpeg": {
            "executable_path": ""
        },
        "audio": {
            "tts_provider": "system",
            "voice": ""
        },
        "general": {
            "theme": "dark",
            "output_directory": "",
            "language": "en"
        }
    }
    
    def __init__(self, config_path=None):
        """Initialize configuration manager."""
        if config_path is None:
            # Use app data directory
            app_data = Path(os.environ.get('APPDATA', Path.home() / '.local' / 'share'))
            app_dir = app_data / 'AIVideoGenerator'
            app_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = app_dir / 'config.json'
        else:
            self.config_path = Path(config_path)
        
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or return defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    stored = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._merge_configs(self.DEFAULT_CONFIG, stored)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Could not load config: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def _merge_configs(self, default, stored):
        """Recursively merge stored config with defaults."""
        result = default.copy()
        for key, value in stored.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key] = self._merge_configs(result[key], value)
                else:
                    result[key] = value
        return result
    
    def save(self):
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            return True
        except IOError as e:
            print(f"[ERROR] Could not save config: {e}")
            return False
    
    def get(self, *keys, default=None):
        """Get a configuration value by nested keys.
        
        Args:
            *keys: Variable number of keys to traverse nested config.
            default: Default value to return if key path is not found.
                     Can be any type including dict/list.
        
        Returns:
            The configuration value at the specified path, or default if not found.
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *keys_and_value):
        """Set a configuration value. Last argument is the value, rest are keys."""
        if len(keys_and_value) < 2:
            return False
        
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]
        
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        return True
    
    def get_all(self):
        """Return complete configuration."""
        return self.config.copy()


# Global config instance
_config_instance = None

def get_config():
    """Get or create global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
