"""
Project management for AI Video Generator.
Handles creation, loading, and storage of video projects.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class ProjectManager:
    """Manages video projects with local JSON storage."""
    
    def __init__(self, projects_dir=None):
        """Initialize project manager."""
        if projects_dir is None:
            app_data = Path(os.environ.get('APPDATA', Path.home() / '.local' / 'share'))
            self.projects_dir = app_data / 'AIVideoGenerator' / 'projects'
        else:
            self.projects_dir = Path(projects_dir)
        
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.projects_dir / 'index.json'
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure project index file exists."""
        if not self.index_file.exists():
            self._save_index([])
    
    def _load_index(self):
        """Load project index."""
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_index(self, index):
        """Save project index."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
            return True
        except IOError:
            return False
    
    def create_project(self, prompt, attachments=None):
        """Create a new project."""
        project_id = str(uuid.uuid4())
        project_dir = self.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        project = {
            "id": project_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "prompt": prompt,
            "attachments": attachments or [],
            "status": "draft",
            "script": None,
            "storyboard": None,
            "generated_assets": [],
            "audio": None,
            "subtitles": None,
            "final_video": None
        }
        
        # Save project metadata
        project_file = project_dir / 'project.json'
        try:
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project, f, indent=2)
            
            # Add to index
            index = self._load_index()
            index.append({
                "id": project_id,
                "created_at": project["created_at"],
                "prompt": prompt,
                "status": project["status"]
            })
            self._save_index(index)
            
            return project
        except IOError as e:
            return None
    
    def get_project(self, project_id):
        """Get a project by ID."""
        project_file = self.projects_dir / project_id / 'project.json'
        if project_file.exists():
            try:
                with open(project_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def update_project(self, project_id, updates):
        """Update a project's fields."""
        project = self.get_project(project_id)
        if not project:
            return None
        
        project.update(updates)
        project["updated_at"] = datetime.now().isoformat()
        
        project_file = self.projects_dir / project_id / 'project.json'
        try:
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project, f, indent=2)
            
            # Update index
            index = self._load_index()
            for i, p in enumerate(index):
                if p["id"] == project_id:
                    index[i] = {
                        "id": project_id,
                        "created_at": project["created_at"],
                        "prompt": project["prompt"],
                        "status": project["status"]
                    }
                    break
            self._save_index(index)
            
            return project
        except IOError:
            return None
    
    def delete_project(self, project_id):
        """Delete a project."""
        project_dir = self.projects_dir / project_id
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
            
            # Remove from index
            index = self._load_index()
            index = [p for p in index if p["id"] != project_id]
            self._save_index(index)
            return True
        return False
    
    def list_projects(self, limit=50):
        """List all projects, most recent first."""
        index = self._load_index()
        index.sort(key=lambda x: x["created_at"], reverse=True)
        return index[:limit]
    
    def get_project_dir(self, project_id):
        """Get the directory path for a project."""
        return self.projects_dir / project_id


# Global instance
_project_manager_instance = None

def get_project_manager():
    """Get or create global project manager instance."""
    global _project_manager_instance
    if _project_manager_instance is None:
        _project_manager_instance = ProjectManager()
    return _project_manager_instance
