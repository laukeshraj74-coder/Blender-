"""
AI Service for video request understanding.
Handles structured analysis of user video generation requests.
"""

import json
from typing import Dict, Any, List, Optional
from backend.utils.logger import get_logger

logger = get_logger()


# Schema for video request understanding
VIDEO_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["title", "topic", "video_type", "tone", "target_duration_seconds"],
    "properties": {
        "title": {"type": "string", "description": "Video title"},
        "topic": {"type": "string", "description": "Main topic or subject"},
        "video_type": {
            "type": "string",
            "enum": ["documentary", "tutorial", "narrative", "promotional", "educational", "entertainment", "other"]
        },
        "tone": {"type": "string", "description": "Desired tone (cinematic, casual, professional, etc.)"},
        "target_duration_seconds": {"type": "integer", "description": "Target duration in seconds"},
        "visual_style": {"type": "string", "description": "Visual style description"},
        "language": {"type": "string", "description": "Primary language"},
        "requirements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific requirements"
        },
        "key_scenes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key scenes or segments"
        },
        "narration_style": {"type": "string", "description": "Narration style if applicable"}
    }
}


class VideoRequestAnalyzer:
    """Analyzes and structures user video generation requests."""
    
    def __init__(self, ai_provider):
        """Initialize with AI provider."""
        self.ai_provider = ai_provider
    
    def analyze_request(
        self,
        user_prompt: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a user's video generation request.
        
        Args:
            user_prompt: The user's natural language request
            attachments: List of attachment metadata
        
        Returns:
            Structured analysis result or error dict
        """
        logger.info("Analyzing video request", component="AI.Service")
        
        # Build system prompt
        system_prompt = """You are an expert video production assistant. Your task is to analyze user requests for AI-generated videos and extract structured information.

Always respond with valid JSON matching this schema:
{
    "title": "Video title",
    "topic": "Main topic",
    "video_type": "documentary|tutorial|narrative|promotional|educational|entertainment|other",
    "tone": "Description of tone",
    "target_duration_seconds": 600,
    "visual_style": "Visual style description",
    "language": "Language code or name",
    "requirements": ["list", "of", "requirements"],
    "key_scenes": ["scene 1", "scene 2"],
    "narration_style": "Narration style if applicable"
}

Be concise but complete. Infer reasonable values when not explicitly stated."""

        # Build user prompt with attachment context
        user_message = user_prompt
        
        if attachments:
            attachment_info = []
            for att in attachments:
                info = f"- {att.get('filename', 'unknown')}"
                if att.get('type'):
                    info += f" ({att.get('type')})"
                if att.get('size'):
                    size_kb = att.get('size', 0) / 1024
                    info += f" [{size_kb:.1f} KB]"
                if att.get('duration'):
                    info += f" [{att.get('duration')}s]"
                if att.get('width') and att.get('height'):
                    info += f" [{att.get('width')}x{att.get('height')}]"
                attachment_info.append(info)
            
            if attachment_info:
                user_message += "\n\nAttached media:\n" + "\n".join(attachment_info)
        
        # Call AI with JSON expectation
        result = self.ai_provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_message,
            expect_json=True,
            temperature=0.3,  # Lower temperature for more deterministic output
            max_tokens=2048
        )
        
        if not result.get('success'):
            logger.error(f"AI analysis failed: {result.get('error', {}).get('message')}", component="AI.Service")
            return result
        
        # Validate the response structure
        data = result.get('data', {})
        validation = self._validate_analysis(data)
        
        if not validation['valid']:
            logger.warning(f"Analysis validation issues: {validation['issues']}", component="AI.Service")
            # Still return the data but note the issues
            result['validation_issues'] = validation['issues']
        
        logger.info("Video request analyzed successfully", component="AI.Service")
        return result
    
    def _validate_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the analysis result against schema."""
        issues = []
        
        if not isinstance(data, dict):
            return {"valid": False, "issues": ["Response is not a JSON object"]}
        
        # Check required fields
        required = VIDEO_REQUEST_SCHEMA['required']
        for field in required:
            if field not in data:
                issues.append(f"Missing required field: {field}")
        
        # Validate video_type enum
        valid_types = VIDEO_REQUEST_SCHEMA['properties']['video_type']['enum']
        if 'video_type' in data and data['video_type'] not in valid_types:
            issues.append(f"Invalid video_type: {data['video_type']}")
        
        # Validate duration is positive
        if 'target_duration_seconds' in data:
            try:
                duration = int(data['target_duration_seconds'])
                if duration <= 0:
                    issues.append("target_duration_seconds must be positive")
                elif duration > 7200:  # Max 2 hours
                    issues.append("target_duration_seconds exceeds maximum (2 hours)")
            except (ValueError, TypeError):
                issues.append("target_duration_seconds must be a number")
        
        # Validate arrays
        for array_field in ['requirements', 'key_scenes']:
            if array_field in data and not isinstance(data[array_field], list):
                issues.append(f"{array_field} must be an array")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }


def get_video_request_analyzer(ai_provider):
    """Create video request analyzer instance."""
    return VideoRequestAnalyzer(ai_provider)
