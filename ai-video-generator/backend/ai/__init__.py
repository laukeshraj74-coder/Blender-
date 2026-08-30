"""
AI Provider module for AI Video Generator.
Handles communication with AI APIs (OpenAI-compatible).
Supports structured JSON responses and OmniRoute configuration.
"""

import requests
import json
import re
from typing import Optional, Dict, Any, List
from backend.utils.logger import get_logger

logger = get_logger()


class AIProvider:
    """Manages AI provider interactions with OpenAI-compatible APIs."""
    
    # Default models for different providers
    DEFAULT_MODELS = {
        'openai': 'gpt-4o-mini',
        'omniroute': 'auto',
        'generic': 'gpt-3.5-turbo'
    }
    
    def __init__(self, config):
        """Initialize AI provider with configuration."""
        self.config = config
        self.provider = config.get('ai', 'provider') or 'openai'
        self.api_key = config.get('ai', 'api_key') or ''
        self.model = config.get('ai', 'model') or 'auto'
        self.base_url = config.get('ai', 'base_url') or ''
        self.timeout = 60  # seconds
        self.max_retries = 2
        self._cached_models = None
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL for the provider."""
        if self.base_url:
            return self.base_url.rstrip('/')
        
        if self.provider == 'openai':
            return 'https://api.openai.com/v1'
        elif self.provider == 'omniroute':
            # OmniRoute default - user must configure actual URL
            return ''
        else:
            # Generic OpenAI-compatible
            return ''
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test AI provider connection with detailed error reporting."""
        logger.info("Testing AI connection", component="AI")
        
        if not self.api_key:
            return {
                "success": False,
                "message": "API key not configured",
                "error_code": "MISSING_API_KEY"
            }
        
        base_url = self._get_base_url()
        if not base_url:
            return {
                "success": False,
                "message": "Base URL not configured for provider",
                "error_code": "MISSING_BASE_URL"
            }
        
        endpoint = f"{base_url}/models"
        
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("AI connection successful", component="AI")
                return {
                    "success": True,
                    "message": "Connection successful",
                    "provider": self.provider,
                    "base_url": base_url
                }
            elif response.status_code == 401:
                logger.error("AI authentication failed: Invalid API key", component="AI")
                return {
                    "success": False,
                    "message": "Invalid API key",
                    "error_code": "INVALID_API_KEY"
                }
            elif response.status_code == 404:
                logger.error(f"AI endpoint not found: {endpoint}", component="AI")
                return {
                    "success": False,
                    "message": f"Endpoint not found: {endpoint}",
                    "error_code": "ENDPOINT_NOT_FOUND"
                }
            elif response.status_code == 429:
                logger.error("AI rate limit exceeded", component="AI")
                return {
                    "success": False,
                    "message": "Rate limit exceeded. Please wait and try again.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            else:
                error_msg = response.text[:200] if response.text else "Unknown error"
                logger.error(f"AI connection failed: HTTP {response.status_code} - {error_msg}", component="AI")
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {response.status_code}",
                    "error_code": f"HTTP_{response.status_code}",
                    "details": error_msg
                }
                
        except requests.exceptions.Timeout:
            logger.error("AI connection timeout", component="AI")
            return {
                "success": False,
                "message": "Connection timeout. Check your network and API endpoint.",
                "error_code": "CONNECTION_TIMEOUT"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"AI connection refused: {e}", component="AI")
            return {
                "success": False,
                "message": "Connection refused. Check your network and API endpoint.",
                "error_code": "CONNECTION_REFUSED"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"AI connection error: {e}", component="AI")
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "error_code": "CONNECTION_ERROR"
            }
    
    def get_available_models(self) -> List[str]:
        """Get available models from provider."""
        if not self.api_key:
            return []
        
        # Return cached models if available
        if self._cached_models is not None:
            return self._cached_models
        
        try:
            base_url = self._get_base_url()
            if not base_url:
                return []
            
            endpoint = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get('id', '') for m in data.get('data', [])]
                self._cached_models = models
                return models
        except Exception as e:
            logger.error(f"Failed to get models: {e}", component="AI")
        
        return []
    
    def _select_model(self) -> str:
        """Select the appropriate model based on configuration."""
        if self.model and self.model != 'auto':
            return self.model
        
        # AUTO mode: try to get models from provider
        models = self.get_available_models()
        
        if models:
            # Prefer GPT-4 variants, then GPT-3.5
            for preferred in ['gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']:
                for m in models:
                    if preferred in m.lower():
                        logger.info(f"AUTO selected model: {m}", component="AI")
                        return m
            
            # Fallback to first available model
            if models:
                logger.info(f"AUTO selected model: {models[0]}", component="AI")
                return models[0]
        
        # Final fallback to default
        default = self.DEFAULT_MODELS.get(self.provider, 'gpt-3.5-turbo')
        logger.info(f"Using default model: {default}", component="AI")
        return default
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, handling Markdown code fences."""
        if not content:
            return None
        
        # Try direct JSON parse first
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass
        
        # Look for JSON in Markdown code fences
        json_pattern = r'```(?:json)?\s*({.*?})\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0].strip())
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object anywhere in the text
        brace_match = re.search(r'\{.*\}', content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group().strip())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _make_request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        max_retries: int = None
    ) -> requests.Response:
        """Make HTTP request with retry logic for transient failures."""
        if max_retries is None:
            max_retries = self.max_retries
        
        last_error = None
        attempt = 0
        
        while attempt <= max_retries:
            try:
                headers = self._get_headers()
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # Don't retry on client errors (4xx) except 429
                if response.status_code < 500 and response.status_code != 429:
                    return response
                
                # Retry on server errors (5xx) or rate limits (429)
                if response.status_code >= 500 or response.status_code == 429:
                    attempt += 1
                    if attempt <= max_retries:
                        # Small backoff
                        import time
                        time.sleep(0.5 * attempt)
                        logger.info(f"Retrying AI request (attempt {attempt}/{max_retries})", component="AI")
                        continue
                
                return response
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                attempt += 1
                if attempt <= max_retries:
                    import time
                    time.sleep(0.5 * attempt)
                    logger.info(f"Retrying AI request after error (attempt {attempt}/{max_retries})", component="AI")
                    continue
                raise
        
        if last_error:
            raise last_error
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        expect_json: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Generate a response from the AI.
        
        Args:
            system_prompt: System instruction prompt
            user_prompt: User message prompt
            expect_json: Whether to expect and validate JSON response
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        
        Returns:
            Dict with success, data/response, model, usage, error info
        """
        if not self.api_key:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "API key not configured",
                    "recoverable": False
                }
            }
        
        base_url = self._get_base_url()
        if not base_url:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_BASE_URL",
                    "message": "Base URL not configured",
                    "recoverable": False
                }
            }
        
        model = self._select_model()
        endpoint = f"{base_url}/chat/completions"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if expect_json:
            # Request JSON mode if supported
            payload["response_format"] = {"type": "json_object"}
        
        logger.info(
            f"AI request started: model={model}, provider={self.provider}",
            component="AI"
        )
        
        start_time = __import__('time').time()
        
        try:
            response = self._make_request_with_retry(endpoint, payload)
            duration = __import__('time').time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract response content
                choices = data.get('choices', [])
                if not choices:
                    return {
                        "success": False,
                        "error": {
                            "code": "EMPTY_RESPONSE",
                            "message": "AI returned empty response",
                            "recoverable": True
                        }
                    }
                
                content = choices[0].get('message', {}).get('content', '')
                
                result = {
                    "success": True,
                    "data": content,
                    "model": model,
                    "usage": data.get('usage', {}),
                    "duration": duration
                }
                
                # If JSON expected, parse and validate
                if expect_json:
                    parsed = self._extract_json_from_response(content)
                    if parsed is None:
                        logger.error("AI returned invalid JSON", component="AI")
                        return {
                            "success": False,
                            "error": {
                                "code": "INVALID_JSON",
                                "message": "AI returned invalid JSON format",
                                "recoverable": True,
                                "raw_response": content[:500]
                            }
                        }
                    result["data"] = parsed
                
                logger.info(
                    f"AI request completed: duration={duration:.2f}s, status=success",
                    component="AI"
                )
                
                return result
                
            elif response.status_code == 401:
                logger.error("AI authentication failed", component="AI")
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid API key",
                        "recoverable": False
                    }
                }
                
            elif response.status_code == 429:
                logger.error("AI rate limit exceeded", component="AI")
                return {
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please wait.",
                        "recoverable": True
                    }
                }
                
            else:
                error_text = response.text[:200] if response.text else "Unknown error"
                logger.error(f"AI request failed: HTTP {response.status_code} - {error_text}", component="AI")
                return {
                    "success": False,
                    "error": {
                        "code": f"HTTP_{response.status_code}",
                        "message": f"AI request failed: HTTP {response.status_code}",
                        "recoverable": response.status_code >= 500,
                        "details": error_text
                    }
                }
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            duration = __import__('time').time() - start_time
            logger.error(f"AI request failed: connection error - {e}", component="AI")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Failed to connect to AI service. Check your network.",
                    "recoverable": True
                }
            }
        except Exception as e:
            duration = __import__('time').time() - start_time
            logger.error(f"AI request failed: {e}", component="AI")
            return {
                "success": False,
                "error": {
                    "code": "REQUEST_ERROR",
                    "message": f"AI request error: {str(e)}",
                    "recoverable": True
                }
            }


def get_ai_provider(config):
    """Create AI provider instance."""
    return AIProvider(config)
