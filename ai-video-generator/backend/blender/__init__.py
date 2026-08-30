"""
Blender integration module for AI Video Generator.
Handles Blender detection and basic operations.
"""

import os
import subprocess
from pathlib import Path
from backend.utils.logger import get_logger

logger = get_logger()


class BlenderManager:
    """Manages Blender detection and operations."""
    
    def __init__(self, config):
        """Initialize Blender manager with configuration."""
        self.config = config
        self.executable_path = config.get('blender', 'executable_path') or ''
    
    def detect_blender(self):
        """Attempt to detect Blender installation."""
        logger.info("Detecting Blender", component="Blender")
        
        # Check configured path first
        if self.executable_path and Path(self.executable_path).exists():
            logger.info(f"Blender found at configured path: {self.executable_path}", component="Blender")
            return {
                "found": True,
                "path": self.executable_path,
                "version": self._get_version(self.executable_path)
            }
        
        # Common installation paths on Windows
        common_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender 4.0\blender.exe",
        ]
        
        # Also check PATH
        blender_in_path = self._find_in_path('blender')
        if blender_in_path:
            common_paths.append(blender_in_path)
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Blender detected at: {path}", component="Blender")
                return {
                    "found": True,
                    "path": path,
                    "version": self._get_version(path)
                }
        
        logger.warning("Blender not found", component="Blender")
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
        """Get Blender version string."""
        try:
            result = subprocess.run(
                [executable_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # First line usually contains version
                return result.stdout.split('\n')[0] if result.stdout else None
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Error getting Blender version: {e}", component="Blender")
        return None
    
    def is_available(self):
        """Check if Blender is available."""
        result = self.detect_blender()
        return result.get('found', False)


def get_blender_manager(config):
    """Create Blender manager instance."""
    return BlenderManager(config)
