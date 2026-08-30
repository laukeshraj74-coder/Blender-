"""
Blender integration module for AI Video Generator.
Handles Blender detection, script generation, and rendering.
"""

import os
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.utils.logger import get_logger

logger = get_logger()


class BlenderManager:
    """Manages Blender detection, script generation, and rendering operations."""
    
    def __init__(self, config):
        """Initialize Blender manager with configuration."""
        self.config = config
        self.executable_path = config.get('blender', 'executable_path') or ''
        self._detected_path = None
        self._version = None
        
    def detect_blender(self) -> Dict[str, Any]:
        """Attempt to detect Blender installation."""
        logger.info("Detecting Blender", component="Blender")
        
        # Check configured path first
        if self.executable_path and Path(self.executable_path).exists():
            logger.info(f"Blender found at configured path: {self.executable_path}", component="Blender")
            self._detected_path = self.executable_path
            self._version = self._get_version(self.executable_path)
            return {
                "found": True,
                "path": self.executable_path,
                "version": self._version
            }
        
        # Common installation paths on Windows
        common_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files (x86)\Blender Foundation\Blender 4.0\blender.exe",
        ]
        
        # Also check PATH
        blender_in_path = self._find_in_path('blender')
        if blender_in_path:
            common_paths.insert(0, blender_in_path)
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"Blender detected at: {path}", component="Blender")
                self._detected_path = path
                self._version = self._get_version(path)
                return {
                    "found": True,
                    "path": path,
                    "version": self._version
                }
        
        logger.warning("Blender not found", component="Blender")
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
    
    def is_available(self) -> bool:
        """Check if Blender is available."""
        if self._detected_path and Path(self._detected_path).exists():
            return True
        result = self.detect_blender()
        return result.get('found', False)
    
    def get_executable(self) -> Optional[str]:
        """Get the Blender executable path."""
        if self._detected_path and Path(self._detected_path).exists():
            return self._detected_path
        result = self.detect_blender()
        return result.get('path') if result.get('found') else None
    
    def generate_script(self, video_spec: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Generate a Blender Python script from video specification."""
        logger.info("Generating Blender script", component="Blender")
        
        try:
            # Extract video spec details
            resolution = video_spec.get('resolution', {'width': 1280, 'height': 720})
            duration = video_spec.get('duration_seconds', 10)
            fps = video_spec.get('fps', 24)
            scenes = video_spec.get('scenes', [])
            
            # Calculate frames
            total_frames = int(duration * fps)
            if total_frames < 1:
                total_frames = 1
            if total_frames > 1000:  # Safety limit
                total_frames = 1000
            
            # Generate the script
            script_content = self._generate_blender_script(
                resolution=resolution,
                fps=fps,
                total_frames=total_frames,
                scenes=scenes,
                title=video_spec.get('title', 'AI Video'),
                output_dir=output_dir
            )
            
            # Save script
            script_path = output_dir / 'blender_script.py'
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logger.info(f"Blender script generated: {script_path}", component="Blender")
            
            return {
                "success": True,
                "script_path": str(script_path),
                "total_frames": total_frames,
                "resolution": resolution,
                "fps": fps
            }
            
        except Exception as e:
            logger.error(f"Failed to generate Blender script: {e}", component="Blender")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_blender_script(
        self,
        resolution: Dict[str, int],
        fps: int,
        total_frames: int,
        scenes: List[Dict[str, Any]],
        title: str,
        output_dir: Path
    ) -> str:
        """Generate actual Blender Python script content."""
        
        width = resolution.get('width', 1280)
        height = resolution.get('height', 720)
        
        # Ensure reasonable resolution for low-end hardware
        if width > 1920 or height > 1080:
            scale = min(1920 / width, 1080 / height)
            width = int(width * scale)
            height = int(height * scale)
        
        # For very low-end hardware, use even lower resolution
        if width > 1280 or height > 720:
            width = 1280
            height = 720
        
        # Build script using string formatting (avoiding nested f-string issues)
        lines = []
        lines.append("# Blender script generated by AI Video Generator")
        lines.append(f"# Title: {title}")
        lines.append(f"# Resolution: {width}x{height}")
        lines.append(f"# FPS: {fps}")
        lines.append(f"# Total Frames: {total_frames}")
        lines.append("")
        lines.append("import bpy")
        lines.append("import math")
        lines.append("from mathutils import Euler")
        lines.append("")
        lines.append("# Clear existing scene")
        lines.append("bpy.ops.wm.read_factory_settings(use_empty=True)")
        lines.append("")
        lines.append("# Set up scene")
        lines.append("scene = bpy.context.scene")
        lines.append("scene.name = \"AIVideoScene\"")
        lines.append("")
        lines.append("# Set render settings - use Eevee for CPU-friendly rendering")
        lines.append("scene.render.engine = 'BLENDER_EEVEE'")
        lines.append(f"scene.render.resolution_x = {width}")
        lines.append(f"scene.render.resolution_y = {height}")
        lines.append("scene.render.resolution_percentage = 100")
        lines.append(f"scene.render.fps = {fps}")
        lines.append("scene.frame_start = 1")
        lines.append(f"scene.frame_end = {total_frames}")
        lines.append("")
        lines.append("# Set output format to PNG sequence")
        lines.append("scene.render.image_settings.file_format = 'PNG'")
        lines.append("scene.render.image_settings.color_mode = 'RGBA'")
        lines.append("scene.render.image_settings.compression = 15")
        lines.append("")
        lines.append("# Set output directory")
        lines.append(f"output_dir = r\"{output_dir.as_posix()}\"")
        lines.append("scene.render.filepath = output_dir + \"/frame_\"")
        lines.append("")
        lines.append("# Create world background")
        lines.append("world = bpy.data.worlds.new(\"AIWorld\")")
        lines.append("scene.world = world")
        lines.append("world.use_nodes = True")
        lines.append("bg_node = world.node_tree.nodes.get('Background')")
        lines.append("if bg_node:")
        lines.append("    bg_node.inputs['Color'].default_value = (0.05, 0.05, 0.1, 1.0)")
        lines.append("    bg_node.inputs['Strength'].default_value = 0.5")
        lines.append("")
        lines.append("# Create camera")
        lines.append("camera_data = bpy.data.cameras.new(name='Camera')")
        lines.append("camera_object = bpy.data.objects.new('Camera', camera_data)")
        lines.append("scene.collection.objects.link(camera_object)")
        lines.append("scene.camera = camera_object")
        lines.append("camera_object.location = (0, -8, 3)")
        lines.append("camera_object.rotation_euler = Euler((math.radians(75), 0, 0), 'XYZ')")
        lines.append("camera_data.lens = 35")
        lines.append("")
        lines.append("# Create sun light")
        lines.append("sun_data = bpy.data.lights.new(name='Sun', type='SUN')")
        lines.append("sun_object = bpy.data.objects.new('Sun', sun_data)")
        lines.append("scene.collection.objects.link(sun_object)")
        lines.append("sun_object.location = (5, -5, 10)")
        lines.append("sun_object.rotation_euler = Euler((math.radians(45), math.radians(30), math.radians(45)), 'XYZ')")
        lines.append("sun_data.energy = 3.0")
        lines.append("")
        lines.append("# Helper function to create spheres")
        lines.append("def create_sphere(name, location, radius=1.0, color=(1, 1, 1, 1)):")
        lines.append("    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=32, ring_count=16)")
        lines.append("    obj = bpy.context.active_object")
        lines.append("    obj.name = name")
        lines.append("    mat = bpy.data.materials.new(name=name + '_Mat')")
        lines.append("    mat.use_nodes = True")
        lines.append("    bsdf = mat.node_tree.nodes.get('Principled BSDF')")
        lines.append("    if bsdf:")
        lines.append("        bsdf.inputs['Base Color'].default_value = color")
        lines.append("    obj.data.materials.append(mat)")
        lines.append("    return obj")
        lines.append("")
        lines.append("# Helper function to create cubes")
        lines.append("def create_cube(name, location, size=1.0, color=(1, 1, 1, 1)):")
        lines.append("    bpy.ops.mesh.primitive_cube_add(size=size, location=location)")
        lines.append("    obj = bpy.context.active_object")
        lines.append("    obj.name = name")
        lines.append("    mat = bpy.data.materials.new(name=name + '_Mat')")
        lines.append("    mat.use_nodes = True")
        lines.append("    bsdf = mat.node_tree.nodes.get('Principled BSDF')")
        lines.append("    if bsdf:")
        lines.append("        bsdf.inputs['Base Color'].default_value = color")
        lines.append("    obj.data.materials.append(mat)")
        lines.append("    return obj")
        lines.append("")
        lines.append("# Helper function to create text")
        lines.append("def create_text(name, text, location, size=1.0, color=(1, 1, 1, 1)):")
        lines.append("    bpy.ops.object.text_add(location=location)")
        lines.append("    obj = bpy.context.active_object")
        lines.append("    obj.name = name")
        lines.append("    obj.data.body = text")
        lines.append("    obj.data.size = size")
        lines.append("    mat = bpy.data.materials.new(name=name + '_Mat')")
        lines.append("    mat.use_nodes = True")
        lines.append("    bsdf = mat.node_tree.nodes.get('Principled BSDF')")
        lines.append("    if bsdf:")
        lines.append("        bsdf.inputs['Base Color'].default_value = color")
        lines.append("    obj.data.materials.append(mat)")
        lines.append("    return obj")
        lines.append("")
        lines.append("# Create scene objects")
        lines.append("objects_created = []")
        lines.append("")
        
        # Add objects based on scenes
        objects_added = []
        if scenes:
            for i, scene_info in enumerate(scenes[:3]):
                scene_desc = scene_info.get('description', '').lower()
                
                if 'earth' in scene_desc or 'planet' in scene_desc or 'sphere' in scene_desc:
                    loc_x = i * 2 - 2
                    lines.append(f"# Scene {i+1}: Create sphere (Earth-like)")
                    lines.append(f'sphere{i} = create_sphere("Sphere_{i}", location=({loc_x}, 0, 1), radius=1.0, color=(0.2, 0.5, 1.0, 1.0))')
                    lines.append(f'objects_created.append(sphere{i})')
                    objects_added.append(f'Sphere_{i}')
                    lines.append("")
                
                if 'sun' in scene_desc or 'star' in scene_desc:
                    lines.append(f"# Scene {i+1}: Create sun-like sphere")
                    lines.append(f'sun{i} = create_sphere("Sun_{i}", location=(-2, -1, 2), radius=1.5, color=(1.0, 0.8, 0.2, 1.0))')
                    lines.append(f'objects_created.append(sun{i})')
                    objects_added.append(f'Sun_{i}')
                    lines.append("")
                
                if 'cube' in scene_desc or 'box' in scene_desc:
                    lines.append(f"# Scene {i+1}: Create cube")
                    lines.append(f'cube{i} = create_cube("Cube_{i}", location=({i}, 1, 0.5), size=1.0, color=(0.8, 0.8, 0.8, 1.0))')
                    lines.append(f'objects_created.append(cube{i})')
                    objects_added.append(f'Cube_{i}')
                    lines.append("")
        
        # If no specific objects, create default animation
        if not objects_added:
            lines.append("# Default scene: Earth-Moon-Sun animation")
            lines.append('earth = create_sphere("Earth", location=(0, 0, 1), radius=1.0, color=(0.2, 0.5, 1.0, 1.0))')
            lines.append('objects_created.append(earth)')
            lines.append("")
            lines.append('moon = create_sphere("Moon", location=(3, 0, 1), radius=0.3, color=(0.7, 0.7, 0.7, 1.0))')
            lines.append('objects_created.append(moon)')
            lines.append("")
            lines.append('sun = create_sphere("Sun", location=(-5, -2, 3), radius=2.0, color=(1.0, 0.9, 0.3, 1.0))')
            lines.append('objects_created.append(sun)')
            lines.append("")
            safe_title = title.replace('"', '\\"')
            lines.append(f'# Add title text')
            lines.append(f'title_obj = create_text("Title", text="{safe_title}", location=(0, -3, 4), size=0.8, color=(1.0, 1.0, 1.0, 1.0))')
            lines.append('objects_created.append(title_obj)')
            lines.append("")
        
        # Add animation loop
        lines.append("# Animate objects")
        lines.append(f"for frame in range(1, {total_frames + 1}):")
        lines.append("    bpy.context.scene.frame_set(frame)")
        lines.append("")
        lines.append("    # Rotate Earth")
        lines.append('    earth = bpy.data.objects.get("Earth")')
        lines.append("    if earth:")
        lines.append("        earth.rotation_euler.z = math.radians(frame * 2)")
        lines.append('        earth.keyframe_insert(data_path="rotation_euler", frame=frame)')
        lines.append("")
        lines.append("    # Orbit Moon around Earth")
        lines.append('    moon = bpy.data.objects.get("Moon")')
        lines.append("    if moon:")
        lines.append("        angle = math.radians(frame * 3)")
        lines.append("        moon.location.x = math.cos(angle) * 3")
        lines.append("        moon.location.y = math.sin(angle) * 3")
        lines.append('        moon.keyframe_insert(data_path="location", frame=frame)')
        lines.append("")
        lines.append("    # Pulse Sun")
        lines.append('    sun = bpy.data.objects.get("Sun")')
        lines.append("    if sun:")
        lines.append("        scale = 1.0 + 0.1 * math.sin(math.radians(frame * 5))")
        lines.append("        sun.scale = (scale, scale, scale)")
        lines.append('        sun.keyframe_insert(data_path="scale", frame=frame)')
        lines.append("")
        lines.append("# Print completion message")
        lines.append(f'print(f"Blender script prepared: {total_frames} frames at {width}x{height}")')
        
        return "\n".join(lines)
    
    def render(
        self,
        script_path: str,
        output_dir: Path,
        timeout: int = 600,
        cancel_flag: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute Blender rendering."""
        logger.info("Starting Blender render", component="Blender")
        
        blender_exe = self.get_executable()
        if not blender_exe:
            return {
                "success": False,
                "error": "Blender executable not found"
            }
        
        try:
            # Prepare command
            cmd = [
                blender_exe,
                '--background',
                '--python', script_path
            ]
            
            logger.info(f"Running Blender: {' '.join(cmd)}", component="Blender")
            
            # Run Blender
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor process with cancellation support
            stdout_lines = []
            stderr_lines = []
            
            while True:
                # Check for cancellation
                if cancel_flag and cancel_flag.is_set():
                    logger.info("Blender render cancelled", component="Blender")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return {
                        "success": False,
                        "error": "Render cancelled by user",
                        "cancelled": True
                    }
                
                # Check timeout
                elapsed = (process.poll() is None) and timeout > 0
                
                try:
                    stdout, stderr = process.communicate(timeout=min(5, timeout))
                    stdout_lines.append(stdout)
                    stderr_lines.append(stderr)
                    break
                except subprocess.TimeoutExpired:
                    timeout -= 5
                    continue
            
            full_stdout = ''.join(stdout_lines)
            full_stderr = ''.join(stderr_lines)
            
            if process.returncode == 0:
                logger.info("Blender render completed successfully", component="Blender")
                
                # Find rendered frames
                render_dir = output_dir
                frames = list(render_dir.glob('frame_*.png'))
                
                return {
                    "success": True,
                    "frames_rendered": len(frames),
                    "output_dir": str(output_dir),
                    "stdout": full_stdout[-1000:] if len(full_stdout) > 1000 else full_stdout,
                    "stderr": full_stderr[-1000:] if len(full_stderr) > 1000 else full_stderr
                }
            else:
                logger.error(f"Blender render failed with code {process.returncode}", component="Blender")
                return {
                    "success": False,
                    "error": f"Blender exited with code {process.returncode}",
                    "stderr": full_stderr[-1000:] if len(full_stderr) > 1000 else full_stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Blender render timed out", component="Blender")
            process.kill()
            return {
                "success": False,
                "error": "Render timed out"
            }
        except Exception as e:
            logger.error(f"Blender render error: {e}", component="Blender")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_frames(self, output_dir: Path):
        """Clean up temporary frame files after video assembly."""
        try:
            frames = list(output_dir.glob('frame_*.png'))
            for frame in frames:
                frame.unlink()
            logger.info(f"Cleaned up {len(frames)} frame files", component="Blender")
        except Exception as e:
            logger.error(f"Error cleaning up frames: {e}", component="Blender")


def get_blender_manager(config):
    """Create Blender manager instance."""
    return BlenderManager(config)
