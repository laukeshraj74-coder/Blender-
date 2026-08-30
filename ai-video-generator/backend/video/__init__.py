"""
FFmpeg integration module for AI Video Generator.
Handles FFmpeg detection and basic operations.
"""

import os
import subprocess
from pathlib import Path
from backend.utils.logger import get_logger

logger = get_logger()


class FFmpegManager:
    """Manages FFmpeg detection and operations."""
    
    def __init__(self, config):
        """Initialize FFmpeg manager with configuration."""
        self.config = config
        self.executable_path = config.get('ffmpeg', 'executable_path') or ''
    
    def detect_ffmpeg(self):
        """Attempt to detect FFmpeg installation."""
        logger.info("Detecting FFmpeg", component="FFmpeg")
        
        # Check configured path first
        if self.executable_path and Path(self.executable_path).exists():
            logger.info(f"FFmpeg found at configured path: {self.executable_path}", component="FFmpeg")
            return {
                "found": True,
                "path": self.executable_path,
                "version": self._get_version(self.executable_path)
            }
        
        # Common installation paths on Windows
        common_paths = [
            r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ]
        
        # Also check PATH
        ffmpeg_in_path = self._find_in_path('ffmpeg')
        if ffmpeg_in_path:
            common_paths.append(ffmpeg_in_path)
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"FFmpeg detected at: {path}", component="FFmpeg")
                return {
                    "found": True,
                    "path": path,
                    "version": self._get_version(path)
                }
        
        logger.warning("FFmpeg not found", component="FFmpeg")
        return {
            "found": False,
            "path": None,
            "version": None
        }
    
    def _find_in_path(self, executable_name):
        """Search for executable in system PATH."""
        path_env = os.environ.get('PATH', '')
        for directory in path_env.split(os.pathsep):
            candidate = Path(directory) / executable_name
            if candidate.exists():
                return str(candidate)
            # Try with .exe extension on Windows
            candidate_exe = Path(directory) / f"{executable_name}.exe"
            if candidate_exe.exists():
                return str(candidate_exe)
        return None
    
    def _get_version(self, executable_path):
        """Get FFmpeg version string."""
        try:
            result = subprocess.run(
                [executable_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # First line usually contains version info
                return result.stdout.split('\n')[0] if result.stdout else None
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Error getting FFmpeg version: {e}", component="FFmpeg")
        return None
    
    def is_available(self):
        """Check if FFmpeg is available."""
        result = self.detect_ffmpeg()
        return result.get('found', False)


def get_ffmpeg_manager(config):
    """Create FFmpeg manager instance."""
    return FFmpegManager(config)
