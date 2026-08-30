"""
Main backend server for AI Video Generator.
Provides HTTP API for frontend communication.
"""

import sys
import os
from pathlib import Path

# Handle packaged app resource path
APP_RESOURCE_PATH = os.environ.get('APP_RESOURCE_PATH')
if APP_RESOURCE_PATH:
    # Running from packaged Electron app
    BASE_DIR = Path(APP_RESOURCE_PATH)
else:
    # Running in development mode
    BASE_DIR = Path(__file__).parent.parent

# Add parent directory to path for imports
sys.path.insert(0, str(BASE_DIR))

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import uuid

from backend.config import get_config
from backend.utils.logger import get_logger
from backend.projects import get_project_manager
from backend.ai import get_ai_provider
from backend.ai.video_analyzer import get_video_request_analyzer
from backend.blender import get_blender_manager
from backend.video import get_ffmpeg_manager
from backend.audio import get_audio_manager

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Electron

# Initialize components
config = get_config()
logger = get_logger()
project_manager = get_project_manager()
ai_provider = get_ai_provider(config)
video_analyzer = get_video_request_analyzer(ai_provider)
blender_manager = get_blender_manager(config)
ffmpeg_manager = get_ffmpeg_manager(config)
audio_manager = get_audio_manager(config)

# Generation state (in-memory for Phase 1)
generation_state = {
    "is_generating": False,
    "project_id": None,
    "stage": None,
    "progress": 0,
    "message": "",
    "start_time": None,
    "cancelled": False
}
generation_lock = threading.Lock()


def log_request_info():
    """Log incoming request info."""
    logger.info(f"{request.method} {request.path}", component="API")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "backend": "running"
    })


@app.route('/api/config', methods=['GET'])
def get_configuration():
    """Get current configuration (excluding sensitive data)."""
    log_request_info()
    
    safe_config = config.get_all()
    # Remove API key from response
    if 'ai' in safe_config:
        safe_config['ai']['api_key'] = '****' if safe_config['ai'].get('api_key') else ''
    
    return jsonify(safe_config)


@app.route('/api/config', methods=['POST'])
def update_configuration():
    """Update configuration."""
    log_request_info()
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        # Update config based on sections
        for section, values in data.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    config.set(section, key, value)
        
        # Save configuration
        if config.save():
            logger.info("Configuration updated", component="Config")
            return jsonify({"success": True, "message": "Configuration saved"})
        else:
            return jsonify({"error": "Failed to save configuration"}), 500
    except Exception as e:
        logger.error(f"Config update error: {e}", component="Config")
        return jsonify({"error": str(e)}), 500


@app.route('/api/test-ai', methods=['POST'])
def test_ai_connection():
    """Test AI provider connection."""
    log_request_info()
    
    result = ai_provider.test_connection()
    return jsonify(result)


@app.route('/api/detect-blender', methods=['GET'])
def detect_blender():
    """Detect Blender installation."""
    log_request_info()
    
    result = blender_manager.detect_blender()
    return jsonify(result)


@app.route('/api/detect-ffmpeg', methods=['GET'])
def detect_ffmpeg():
    """Detect FFmpeg installation."""
    log_request_info()
    
    result = ffmpeg_manager.detect_ffmpeg()
    return jsonify(result)


@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects."""
    log_request_info()
    
    limit = request.args.get('limit', 50, type=int)
    projects = project_manager.list_projects(limit)
    return jsonify(projects)


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project."""
    log_request_info()
    
    data = request.get_json()
    if not data or not data.get('prompt'):
        return jsonify({"error": "Prompt is required"}), 400
    
    prompt = data['prompt']
    attachments = data.get('attachments', [])
    
    project = project_manager.create_project(prompt, attachments)
    if project:
        logger.info(f"Project created: {project['id']}", component="Projects")
        return jsonify(project), 201
    else:
        return jsonify({"error": "Failed to create project"}), 500


@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project."""
    log_request_info()
    
    project = project_manager.get_project(project_id)
    if project:
        return jsonify(project)
    else:
        return jsonify({"error": "Project not found"}), 404


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project."""
    log_request_info()
    
    if project_manager.delete_project(project_id):
        logger.info(f"Project deleted: {project_id}", component="Projects")
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Project not found"}), 404


@app.route('/api/generate', methods=['POST'])
def start_generation():
    """Start video generation with real AI analysis."""
    log_request_info()
    
    global generation_state
    
    with generation_lock:
        if generation_state["is_generating"]:
            return jsonify({
                "error": "Generation already in progress"
            }), 409
        
        data = request.get_json()
        if not data or not data.get('project_id'):
            return jsonify({"error": "Project ID is required"}), 400
        
        project_id = data['project_id']
        prompt = data.get('prompt', '')
        
        # Validate project exists
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        
        # Initialize generation state
        generation_state = {
            "is_generating": True,
            "project_id": project_id,
            "stage": "initializing",
            "progress": 0,
            "message": "Preparing generation",
            "start_time": time.time(),
            "cancelled": False,
            "stages": [
                {"id": "preparing", "name": "Preparing project", "status": "pending"},
                {"id": "understanding", "name": "Understanding request", "status": "pending"},
                {"id": "script", "name": "Writing script", "status": "pending"},
                {"id": "storyboard", "name": "Creating storyboard", "status": "pending"},
                {"id": "scenes", "name": "Generating scenes", "status": "pending"},
                {"id": "rendering", "name": "Rendering video", "status": "pending"},
                {"id": "narration", "name": "Generating narration", "status": "pending"},
                {"id": "subtitles", "name": "Adding subtitles", "status": "pending"},
                {"id": "finalizing", "name": "Finalizing video", "status": "pending"}
            ]
        }
        
        logger.info(f"Generation started for project: {project_id}", component="Generation")
        
        # Start generation in background thread
        thread = threading.Thread(
            target=_run_generation,
            args=(project_id, prompt, project.get('attachments', []))
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Generation started",
            "project_id": project_id
        })


def _run_generation(project_id, prompt, attachments):
    """Background generation process with real AI analysis and video generation."""
    import json
    from datetime import datetime
    
    global generation_state

    try:
        stages = generation_state["stages"]
        project_dir = project_manager.get_project_path(project_id)

        # Stage 1: Preparing project (already done)
        with generation_lock:
            stages[0]["status"] = "completed"
            stages[1]["status"] = "current"
            generation_state["stage"] = "understanding"
            generation_state["progress"] = 5
            generation_state["message"] = "Understanding your request..."

        logger.info(f"Starting AI analysis for project: {project_id}", component="Generation")

        # Check for cancellation
        if generation_state["cancelled"]:
            _handle_cancellation()
            return

        # Stage 2: Understanding request with AI
        analysis_result = video_analyzer.analyze_request(prompt, attachments)

        if not analysis_result.get('success'):
            error = analysis_result.get('error', {})
            raise Exception(f"AI analysis failed: {error.get('message', 'Unknown error')}")

        # Save AI understanding to project
        ai_understanding = {
            "analyzed_at": datetime.now().isoformat(),
            "model": analysis_result.get('model'),
            "data": analysis_result.get('data'),
            "validation_issues": analysis_result.get('validation_issues', [])
        }

        project_manager.update_project(project_id, {
            "ai_understanding": ai_understanding,
            "status": "analyzing"
        })

        logger.info(f"AI analysis completed for project: {project_id}", component="Generation")

        # Mark understanding stage as complete
        with generation_lock:
            stages[1]["status"] = "completed"
            stages[2]["status"] = "current"
            generation_state["stage"] = "creating_video_plan"
            generation_state["progress"] = 15
            generation_state["message"] = "Creating video plan..."

        # Extract video spec from AI response
        ai_data = analysis_result.get('data', {})
        
        # Create VideoSpec from AI response
        video_spec = {
            "title": ai_data.get('title', 'AI Generated Video'),
            "description": ai_data.get('description', prompt),
            "duration_seconds": min(ai_data.get('duration', 10), 10),  # Max 10 seconds for testing
            "fps": 24,
            "resolution": {"width": 640, "height": 360},  # Lower resolution for reliability
            "scenes": []
        }
        
        # Extract scenes from storyboard if available
        storyboard = ai_data.get('storyboard', [])
        if storyboard:
            for scene in storyboard[:3]:  # Limit to 3 scenes
                video_spec["scenes"].append({
                    "duration": scene.get('duration', 3),
                    "description": scene.get('description', ''),
                    "visual": scene.get('visual', ''),
                    "text": scene.get('text', ''),
                    "camera": scene.get('camera', '')
                })
        
        # If no scenes from AI, create a default one
        if not video_spec["scenes"]:
            video_spec["scenes"].append({
                "duration": video_spec["duration_seconds"],
                "description": prompt,
                "visual": "Simple 3D animation",
                "text": "",
                "camera": "static"
            })
        
        # Save video spec
        video_spec_path = project_dir / 'video_spec.json'
        with open(video_spec_path, 'w') as f:
            json.dump(video_spec, f, indent=2)
        
        logger.info(f"Video spec created: {video_spec['title']}", component="Generation")

        # Mark script/storyboard stages as complete
        with generation_lock:
            stages[2]["status"] = "completed"
            stages[3]["status"] = "completed"
            stages[4]["status"] = "current"
            generation_state["stage"] = "creating_blender_scene"
            generation_state["progress"] = 30
            generation_state["message"] = "Creating Blender scene..."

        # Generate Blender script
        render_dir = project_dir / 'render'
        render_dir.mkdir(exist_ok=True)
        
        blender_result = blender_manager.generate_script(video_spec, render_dir)
        
        if not blender_result.get('success'):
            raise Exception(f"Blender script generation failed: {blender_result.get('error', 'Unknown error')}")
        
        logger.info(f"Blender script generated: {blender_result.get('script_path')}", component="Generation")

        # Mark scenes stage complete
        with generation_lock:
            stages[4]["status"] = "completed"
            stages[5]["status"] = "current"
            generation_state["stage"] = "rendering"
            generation_state["progress"] = 40
            generation_state["message"] = "Rendering frames..."

        # Run Blender rendering
        cancel_flag = threading.Event()
        
        # Start Blender render
        script_path = blender_result.get('script_path')
        render_result = blender_manager.render(
            script_path,
            render_dir,
            timeout=600,  # 10 minute timeout
            cancel_flag=cancel_flag
        )
        
        if cancel_flag.is_set():
            _handle_cancellation()
            return
        
        if not render_result.get('success'):
            raise Exception(f"Blender rendering failed: {render_result.get('error', 'Unknown error')}")
        
        frames_rendered = render_result.get('frames_rendered', 0)
        logger.info(f"Blender rendered {frames_rendered} frames", component="Generation")

        # Update progress based on frames rendered
        total_frames = blender_result.get('total_frames', 1)
        with generation_lock:
            generation_state["message"] = f"Rendering: {frames_rendered} / {total_frames} frames"

        # Mark rendering stage complete
        with generation_lock:
            stages[5]["status"] = "completed"
            stages[6]["status"] = "completed"  # Skip narration
            stages[7]["status"] = "completed"  # Skip subtitles
            stages[8]["status"] = "current"
            generation_state["stage"] = "encoding_video"
            generation_state["progress"] = 70
            generation_state["message"] = "Encoding video..."

        # Assemble video with FFmpeg
        output_path = project_dir / 'output.mp4'
        
        ffmpeg_result = ffmpeg_manager.assemble_video(
            frames_dir=render_dir,
            output_path=output_path,
            fps=video_spec.get('fps', 24),
            audio_path=None,  # No audio for Phase 3
            timeout=300
        )
        
        if not ffmpeg_result.get('success'):
            raise Exception(f"FFmpeg assembly failed: {ffmpeg_result.get('error', 'Unknown error')}")
        
        logger.info(f"Video assembled: {output_path}", component="Generation")

        # Mark encoding complete
        with generation_lock:
            stages[8]["status"] = "completed"
            generation_state["stage"] = "verifying_video"
            generation_state["progress"] = 85
            generation_state["message"] = "Verifying video..."

        # Verify the output video
        verify_result = ffmpeg_manager.verify_video(output_path)
        
        if not verify_result.get('success'):
            logger.warning(f"Video verification warning: {verify_result.get('error', 'Unknown')}", component="Generation")
            # Don't fail, just warn - the video may still be playable
        
        # Clean up frame files
        blender_manager.cleanup_frames(render_dir)
        
        # Finalize
        project_manager.update_project(project_id, {
            "status": "completed",
            "output_video": str(output_path),
            "video_properties": verify_result if verify_result.get('success') else None,
            "completed_at": datetime.now().isoformat()
        })

        logger.info(f"Generation completed successfully for project: {project_id}", component="Generation")

        # Mark all stages complete
        with generation_lock:
            generation_state["is_generating"] = False
            generation_state["progress"] = 100
            generation_state["stage"] = "completed"
            generation_state["message"] = "Video generation completed!"

    except Exception as e:
        logger.error(f"Generation error: {e}", component="Generation")
        with generation_lock:
            generation_state["is_generating"] = False
            generation_state["stage"] = "error"
            generation_state["message"] = f"Generation failed: {str(e)}"
            # Find current stage and mark as error
            for stage in stages:
                if stage["status"] == "current":
                    stage["status"] = "error"
                    break

def _handle_cancellation():
    """Handle generation cancellation."""
    global generation_state
    
    with generation_lock:
        generation_state["is_generating"] = False
        generation_state["stage"] = "cancelled"
        generation_state["message"] = "Generation cancelled by user"
    
    logger.info("Generation cancelled", component="Generation")


@app.route('/api/generation/status', methods=['GET'])
def get_generation_status():
    """Get current generation status."""
    log_request_info()
    
    with generation_lock:
        elapsed_time = 0
        if generation_state["start_time"] and generation_state["is_generating"]:
            elapsed_time = time.time() - generation_state["start_time"]
        
        return jsonify({
            "is_generating": generation_state["is_generating"],
            "project_id": generation_state["project_id"],
            "stage": generation_state["stage"],
            "progress": generation_state["progress"],
            "message": generation_state["message"],
            "elapsed_time": elapsed_time,
            "stages": generation_state.get("stages", [])
        })


@app.route('/api/generation/cancel', methods=['POST'])
def cancel_generation():
    """Cancel ongoing generation."""
    log_request_info()
    
    global generation_state
    
    with generation_lock:
        if not generation_state["is_generating"]:
            return jsonify({
                "error": "No generation in progress"
            }), 400
        
        generation_state["cancelled"] = True
        logger.info("Generation cancellation requested", component="Generation")
        
        return jsonify({
            "success": True,
            "message": "Cancellation requested"
        })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload for attachments."""
    log_request_info()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Supported file types
    allowed_extensions = {
        'video': ['mp4', 'mov', 'webm', 'avi'],
        'audio': ['mp3', 'wav', 'm4a'],
        'image': ['png', 'jpg', 'jpeg', 'webp']
    }
    
    filename = file.filename.lower()
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    file_type = None
    for type_name, extensions in allowed_extensions.items():
        if ext in extensions:
            file_type = type_name
            break
    
    if not file_type:
        return jsonify({
            "error": f"Unsupported file type: {ext}"
        }), 400
    
    # Generate unique filename
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    
    # Save to temp directory
    temp_dir = Path(os.environ.get('TEMP', '/tmp')) / 'AIVideoGenerator' / 'uploads'
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / safe_filename
    
    try:
        file.save(str(file_path))
        logger.info(f"File uploaded: {file.filename}", component="Upload")
        
        return jsonify({
            "success": True,
            "file_id": unique_id,
            "filename": file.filename,
            "type": file_type,
            "path": str(file_path),
            "size": file_path.stat().st_size
        })
    except Exception as e:
        logger.error(f"Upload error: {e}", component="Upload")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("Backend starting", component="Server")
    
    # Run on localhost with specified port
    port = 5000
    logger.info(f"Server running on http://localhost:{port}", component="Server")
    
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
