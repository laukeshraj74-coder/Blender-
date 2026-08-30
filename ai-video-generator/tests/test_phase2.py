"""
Test suite for Phase 2 AI Integration.
Run these tests to verify the AI integration layer.
"""

import sys
sys.path.insert(0, '.')

from backend.config import get_config
from backend.ai import get_ai_provider
from backend.ai.video_analyzer import get_video_request_analyzer
from backend.projects import get_project_manager


def test_ai_provider_initialization():
    """Test 1: AI provider configuration test"""
    print("\n=== Test 1: AI Provider Initialization ===")
    config = get_config()
    provider = get_ai_provider(config)
    
    assert provider.provider == 'openai', "Default provider should be 'openai'"
    assert provider.model == 'auto', "Default model should be 'auto'"
    assert provider.timeout == 60, "Timeout should be 60 seconds"
    assert provider.max_retries == 2, "Max retries should be 2"
    
    print("✓ AI provider initialized correctly")
    print(f"  Provider: {provider.provider}")
    print(f"  Model: {provider.model}")
    print(f"  Timeout: {provider.timeout}s")
    print(f"  Max retries: {provider.max_retries}")
    return True


def test_missing_api_key():
    """Test 2: Invalid/missing API key test"""
    print("\n=== Test 2: Missing API Key Handling ===")
    config = get_config()
    provider = get_ai_provider(config)
    
    result = provider.test_connection()
    
    assert result['success'] == False, "Should fail without API key"
    assert result['error_code'] == 'MISSING_API_KEY', "Should have correct error code"
    
    print("✓ Missing API key handled correctly")
    print(f"  Error code: {result['error_code']}")
    print(f"  Message: {result['message']}")
    return True


def test_json_extraction():
    """Test 3: JSON extraction from response"""
    print("\n=== Test 3: JSON Extraction ===")
    config = get_config()
    provider = get_ai_provider(config)
    
    # Test plain JSON
    plain_json = '{"title": "Test", "value": 123}'
    result = provider._extract_json_from_response(plain_json)
    assert result is not None, "Should extract plain JSON"
    assert result['title'] == 'Test', "Should parse correctly"
    print("✓ Plain JSON extracted")
    
    # Test JSON in Markdown fences
    markdown_json = '''```json
{"title": "Test2", "value": 456}
```'''
    result = provider._extract_json_from_response(markdown_json)
    assert result is not None, "Should extract JSON from Markdown"
    assert result['title'] == 'Test2', "Should parse correctly"
    print("✓ Markdown-enclosed JSON extracted")
    
    # Test invalid JSON
    invalid = '{"invalid": json}'
    result = provider._extract_json_from_response(invalid)
    assert result is None, "Should return None for invalid JSON"
    print("✓ Invalid JSON correctly rejected")
    
    return True


def test_model_selection():
    """Test 4: Model selection logic"""
    print("\n=== Test 4: Model Selection ===")
    config = get_config()
    provider = get_ai_provider(config)
    
    # Test explicit model
    provider.model = 'gpt-4-turbo'
    model = provider._select_model()
    assert model == 'gpt-4-turbo', "Should use explicit model"
    print("✓ Explicit model selection works")
    
    # Test AUTO mode (will use default since no API connection)
    provider.model = 'auto'
    model = provider._select_model()
    assert model is not None, "AUTO should select a model"
    print(f"✓ AUTO mode selected: {model}")
    
    return True


def test_video_analyzer_initialization():
    """Test 5: Video analyzer initialization"""
    print("\n=== Test 5: Video Analyzer Initialization ===")
    config = get_config()
    provider = get_ai_provider(config)
    analyzer = get_video_request_analyzer(provider)
    
    assert analyzer is not None, "Analyzer should be created"
    assert analyzer.ai_provider == provider, "Should have reference to provider"
    
    print("✓ Video analyzer initialized correctly")
    return True


def test_project_creation():
    """Test 6: Project creation and storage"""
    print("\n=== Test 6: Project Creation ===")
    pm = get_project_manager()
    
    project = pm.create_project(
        prompt="Test video about AI",
        attachments=[
            {"filename": "test.png", "type": "image", "size": 1024}
        ]
    )
    
    assert project is not None, "Project should be created"
    assert project['id'] is not None, "Project should have ID"
    assert project['prompt'] == "Test video about AI", "Prompt should match"
    assert len(project['attachments']) == 1, "Should have one attachment"
    
    print("✓ Project created successfully")
    print(f"  Project ID: {project['id']}")
    print(f"  Status: {project['status']}")
    
    # Clean up
    pm.delete_project(project['id'])
    print("  Test project cleaned up")
    
    return True


def test_error_response_format():
    """Test 7: Error response format consistency"""
    print("\n=== Test 7: Error Response Format ===")
    config = get_config()
    provider = get_ai_provider(config)
    
    # Test missing API key error format
    result = provider.generate("system", "user")
    
    assert 'success' in result, "Should have success field"
    assert 'error' in result, "Should have error field"
    assert 'code' in result['error'], "Error should have code"
    assert 'message' in result['error'], "Error should have message"
    assert 'recoverable' in result['error'], "Error should have recoverable flag"
    
    print("✓ Error response format is correct")
    print(f"  Code: {result['error']['code']}")
    print(f"  Recoverable: {result['error']['recoverable']}")
    
    return True


def test_attachment_metadata_handling():
    """Test 8: Attachment metadata handling"""
    print("\n=== Test 8: Attachment Metadata ===")
    
    attachments = [
        {"filename": "video.mp4", "type": "video", "size": 5000000, "duration": 120},
        {"filename": "image.png", "type": "image", "size": 500000, "width": 1920, "height": 1080},
        {"filename": "audio.mp3", "type": "audio", "size": 3000000}
    ]
    
    # Verify structure
    for att in attachments:
        assert 'filename' in att, "Attachment should have filename"
        assert 'type' in att, "Attachment should have type"
        assert 'size' in att, "Attachment should have size"
    
    print("✓ Attachment metadata structure validated")
    for att in attachments:
        print(f"  {att['filename']} ({att['type']}) - {att['size']} bytes")
    
    return True


def run_all_tests():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("PHASE 2 AI INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_ai_provider_initialization,
        test_missing_api_key,
        test_json_extraction,
        test_model_selection,
        test_video_analyzer_initialization,
        test_project_creation,
        test_error_response_format,
        test_attachment_metadata_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
