"""
FFmpeg integration module for AI Video Generator.
Handles FFmpeg detection, video assembly, and verification.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from backend.utils.logger import get_logger

logger = get_logger()


class FFmpegManager:
    """Manages FFmpeg detection, video assembly, and verification."""
    
    def __init__(self, config):
        """Initialize FFmpeg manager with configuration."""
        self.config = config
        self.executable_path = config.get('ffmpeg', 'executable_path') or ''
        self.ffprobe_path = config.get('ffmpeg', 'ffprobe_path') or ''
        self._detected_path = None
        self._ffprobe_detected = None
        self._version = None
    
    def detect_ffmpeg(self) -> Dict[str, Any]:
        """Attempt to detect FFmpeg installation."""
        logger.info("Detecting FFmpeg", component="FFmpeg")
        
        # Check configured path first
        if self.executable_path and Path(self.executable_path).exists():
            logger.info(f"FFmpeg found at configured path: {self.executable_path}", component="FFmpeg")
            self._detected_path = self.executable_path
            self._version = self._get_version(self.executable_path)
            return {
                "found": True,
                "path": self.executable_path,
                "version": self._version
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
            common_paths.insert(0, ffmpeg_in_path)
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"FFmpeg detected at: {path}", component="FFmpeg")
                self._detected_path = path
                self._version = self._get_version(path)
                return {
                    "found": True,
                    "path": path,
                    "version": self._version
                }
        
        logger.warning("FFmpeg not found", component="FFmpeg")
        return {
            "found": False,
            "path": None,
            "version": None
        }
    
    def _find_in_path(self, executable_name: str) -> Optional[str]:
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
    
    def _get_version(self, executable_path: str) -> Optional[str]:
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
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        if self._detected_path and Path(self._detected_path).exists():
            return True
        result = self.detect_ffmpeg()
        return result.get('found', False)
    
    def get_executable(self) -> Optional[str]:
        """Get the FFmpeg executable path."""
        if self._detected_path and Path(self._detected_path).exists():
            return self._detected_path
        result = self.detect_ffmpeg()
        return result.get('path') if result.get('found') else None
    
    def get_ffprobe(self) -> Optional[str]:
        """Get the FFprobe executable path."""
        if self._ffprobe_detected and Path(self._ffprobe_detected).exists():
            return self._ffprobe_detected
        
        # Try to find ffprobe near ffmpeg
        ffmpeg_path = self.get_executable()
        if ffmpeg_path:
            ffprobe_candidate = Path(ffmpeg_path).parent / 'ffprobe.exe'
            if ffprobe_candidate.exists():
                self._ffprobe_detected = str(ffprobe_candidate)
                return self._ffprobe_detected
            
            ffprobe_candidate2 = Path(ffmpeg_path).parent / 'ffprobe'
            if ffprobe_candidate2.exists():
                self._ffprobe_detected = str(ffprobe_candidate2)
                return self._ffprobe_detected
        
        # Search in PATH
        ffprobe_in_path = self._find_in_path('ffprobe')
        if ffprobe_in_path:
            self._ffprobe_detected = ffprobe_in_path
            return self._ffprobe_detected
        
        return None
    
    def assemble_video(
        self,
        frames_dir: Path,
        output_path: Path,
        fps: int = 24,
        audio_path: Optional[Path] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Assemble video from PNG frames using FFmpeg."""
        logger.info("Assembling video with FFmpeg", component="FFmpeg")
        
        ffmpeg_exe = self.get_executable()
        if not ffmpeg_exe:
            return {
                "success": False,
                "error": "FFmpeg executable not found"
            }
        
        # Check frames exist
        frames = sorted(frames_dir.glob('frame_*.png'))
        if not frames:
            return {
                "success": False,
                "error": "No frame files found"
            }
        
        logger.info(f"Found {len(frames)} frames to assemble", component="FFmpeg")
        
        # Build FFmpeg command
        # Input pattern for frames
        frame_pattern = str(frames_dir / 'frame_%04d.png')
        
        cmd = [
            ffmpeg_exe,
            '-y',  # Overwrite output
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart'
        ]
        
        # Add audio if available
        if audio_path and audio_path.exists():
            cmd.extend([
                '-i', str(audio_path),
                '-c:a', 'aac',
                '-b:a', '192k'
            ])
        
        cmd.append(str(output_path))
        
        logger.info(f"Running FFmpeg: {' '.join(cmd)}", component="FFmpeg")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode == 0:
                logger.info("Video assembly completed successfully", component="FFmpeg")
                
                # Verify output exists
                if output_path.exists() and output_path.stat().st_size > 0:
                    return {
                        "success": True,
                        "output_path": str(output_path),
                        "file_size": output_path.stat().st_size,
                        "frames_used": len(frames),
                        "stderr": stderr[-500:] if len(stderr) > 500 else stderr
                    }
                else:
                    return {
                        "success": False,
                        "error": "Output file not created or empty"
                    }
            else:
                logger.error(f"FFmpeg failed with code {process.returncode}", component="FFmpeg")
                return {
                    "success": False,
                    "error": f"FFmpeg exited with code {process.returncode}",
                    "stderr": stderr[-1000:] if len(stderr) > 1000 else stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg assembly timed out", component="FFmpeg")
            process.kill()
            return {
                "success": False,
                "error": "Video assembly timed out"
            }
        except Exception as e:
            logger.error(f"FFmpeg assembly error: {e}", component="FFmpeg")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_video(self, video_path: Path) -> Dict[str, Any]:
        """Verify video file using FFprobe."""
        logger.info(f"Verifying video: {video_path}", component="FFmpeg")
        
        ffprobe_exe = self.get_ffprobe()
        if not ffprobe_exe:
            # Fallback: try using ffmpeg for probing
            ffmpeg_exe = self.get_executable()
            if not ffmpeg_exe:
                return {
                    "success": False,
                    "error": "Neither FFmpeg nor FFprobe found"
                }
            ffprobe_exe = ffmpeg_exe
        
        if not video_path.exists():
            return {
                "success": False,
                "error": "Video file does not exist"
            }
        
        if video_path.stat().st_size == 0:
            return {
                "success": False,
                "error": "Video file is empty"
            }
        
        try:
            cmd = [
                ffprobe_exe,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"FFprobe failed with code {result.returncode}"
                }
            
            probe_data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = None
            format_info = probe_data.get('format', {})
            
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return {
                    "success": False,
                    "error": "No video stream found"
                }
            
            # Validate required properties
            width = video_stream.get('width')
            height = video_stream.get('height')
            duration = format_info.get('duration')
            codec = video_stream.get('codec_name')
            
            if not width or not height:
                return {
                    "success": False,
                    "error": "Video dimensions not found"
                }
            
            if not duration:
                return {
                    "success": False,
                    "error": "Video duration not found"
                }
            
            # Calculate FPS if available
            fps = None
            if 'r_frame_rate' in video_stream:
                fps_str = video_stream['r_frame_rate']
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    if den > 0:
                        fps = round(num / den, 2)
            
            logger.info(f"Video verified: {width}x{height}, {duration}s, codec={codec}", component="FFmpeg")
            
            return {
                "success": True,
                "valid": True,
                "width": width,
                "height": height,
                "duration": float(duration),
                "codec": codec,
                "fps": fps,
                "file_size": video_path.stat().st_size,
                "format": format_info.get('format_name'),
                "bit_rate": format_info.get('bit_rate')
            }
            
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse FFprobe output"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Verification timed out"
            }
        except Exception as e:
            logger.error(f"Video verification error: {e}", component="FFmpeg")
            return {
                "success": False,
                "error": str(e)
            }


def get_ffmpeg_manager(config):
    """Create FFmpeg manager instance."""
    return FFmpegManager(config)
