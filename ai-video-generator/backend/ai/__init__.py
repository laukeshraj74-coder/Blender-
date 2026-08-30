"""
AI Provider module for AI Video Generator.
Handles communication with AI APIs (OpenAI-compatible).
"""

import requests
from backend.utils.logger import get_logger

logger = get_logger()


class AIProvider:
    """Manages AI provider interactions."""
    
    def __init__(self, config):
        """Initialize AI provider with configuration."""
        self.config = config
        self.provider = config.get('ai', 'provider') or 'openai'
        self.api_key = config.get('ai', 'api_key') or ''
        self.model = config.get('ai', 'model') or 'auto'
        self.base_url = config.get('ai', 'base_url') or ''
    
    def test_connection(self):
        """Test AI provider connection."""
        logger.info("Testing AI connection", component="AI")
        
        if not self.api_key:
            return {
                "success": False,
                "message": "API key not configured"
            }
        
        # Determine endpoint
        if self.provider == 'openai':
            base_url = self.base_url or 'https://api.openai.com/v1'
            endpoint = f"{base_url}/models"
        else:
            # Generic OpenAI-compatible
            base_url = self.base_url
            endpoint = f"{base_url}/models"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("AI connection successful", component="AI")
                return {
                    "success": True,
                    "message": "Connection successful"
                }
            else:
                logger.error(f"AI connection failed: {response.status_code}", component="AI")
                return {
                    "success": False,
                    "message": f"Connection failed: {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"AI connection error: {e}", component="AI")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}"
            }
    
    def get_available_models(self):
        """Get available models from provider."""
        if not self.api_key:
            return []
        
        try:
            if self.provider == 'openai':
                base_url = self.base_url or 'https://api.openai.com/v1'
            else:
                base_url = self.base_url
            
            endpoint = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return [m.get('id', '') for m in data.get('data', [])]
        except Exception as e:
            logger.error(f"Failed to get models: {e}", component="AI")
        
        return []


def get_ai_provider(config):
    """Create AI provider instance."""
    return AIProvider(config)
