"""
Comprehensive test suite for Config.get() bug fix and regression testing.
Tests the fix for dictionary default value handling.
"""

import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from config import Config


def test_scalar_default():
    """Test 1: Scalar default value for missing key."""
    print("\n=== Test 1: Scalar Default ===")
    c = Config()
    result = c.get('ai', 'nonexistent_key', default='fallback')
    assert result == 'fallback', f"Expected 'fallback', got {result}"
    print("  PASS: Scalar default works correctly")
    return True


def test_dict_default():
    """Test 2: Dictionary default value for missing key."""
    print("\n=== Test 2: Dictionary Default ===")
    c = Config()
    dict_default = {'nested': 'value', 'count': 42}
    result = c.get('ai', 'nonexistent_key', default=dict_default)
    assert result == dict_default, f"Expected {dict_default}, got {result}"
    assert isinstance(result, dict), "Result should be a dict"
    print("  PASS: Dictionary default works correctly")
    return True


def test_missing_key():
    """Test 3: Missing key returns None by default (backward compatibility)."""
    print("\n=== Test 3: Missing Key (None default) ===")
    c = Config()
    result = c.get('ai', 'nonexistent_key')
    assert result is None, f"Expected None, got {result}"
    print("  PASS: Missing key returns None by default")
    return True


def test_existing_key():
    """Test 4: Existing key returns actual value, not default."""
    print("\n=== Test 4: Existing Key ===")
    c = Config()
    result = c.get('ai', 'provider', default='should_not_use_this')
    assert result == 'openai', f"Expected 'openai', got {result}"
    assert result != 'should_not_use_this', "Should not return default for existing key"
    print("  PASS: Existing key returns actual value")
    return True


def test_nested_config():
    """Test 5: Nested configuration access."""
    print("\n=== Test 5: Nested Configuration ===")
    c = Config()
    
    # Get nested value
    result = c.get('general', 'theme')
    assert result == 'dark', f"Expected 'dark', got {result}"
    
    # Get entire section as dict
    result = c.get('ai')
    assert isinstance(result, dict), "Should return dict for section"
    assert result['provider'] == 'openai', "Nested value should match"
    
    # Missing nested with dict default
    nested_dict = {'a': 1, 'b': [1, 2, 3]}
    result = c.get('general', 'missing', 'nested', default=nested_dict)
    assert result == nested_dict, f"Expected {nested_dict}, got {result}"
    
    print("  PASS: Nested configuration works correctly")
    return True


def test_list_default():
    """Test 6: List as default value."""
    print("\n=== Test 6: List Default ===")
    c = Config()
    list_default = [1, 2, 3]
    result = c.get('missing', 'key', default=list_default)
    assert result == list_default, f"Expected {list_default}, got {result}"
    assert isinstance(result, list), "Result should be a list"
    print("  PASS: List default works correctly")
    return True


def test_empty_string_default():
    """Test 7: Empty string as default."""
    print("\n=== Test 7: Empty String Default ===")
    c = Config()
    result = c.get('missing', 'key', default='')
    assert result == '', f"Expected empty string, got {result}"
    print("  PASS: Empty string default works correctly")
    return True


def test_zero_default():
    """Test 8: Zero as default (falsy value)."""
    print("\n=== Test 8: Zero Default ===")
    c = Config()
    result = c.get('missing', 'key', default=0)
    assert result == 0, f"Expected 0, got {result}"
    print("  PASS: Zero default works correctly")
    return True


def test_false_default():
    """Test 9: False as default (falsy value)."""
    print("\n=== Test 9: False Default ===")
    c = Config()
    result = c.get('missing', 'key', default=False)
    assert result is False, f"Expected False, got {result}"
    print("  PASS: False default works correctly")
    return True


def test_config_persistence():
    """Test 10: Config save/load with defaults."""
    print("\n=== Test 10: Config Persistence ===")
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        # Create config with custom path
        c = Config(config_path=temp_path)
        
        # Set some values
        c.set('general', 'theme', 'light')
        c.set('ai', 'model', 'gpt-4')
        c.save()
        
        # Load new config instance
        c2 = Config(config_path=temp_path)
        
        # Verify values persist
        assert c2.get('general', 'theme') == 'light', "Theme should persist"
        assert c2.get('ai', 'model') == 'gpt-4', "Model should persist"
        
        # Verify defaults still work for unset values
        result = c2.get('missing', 'key', default={'test': 'value'})
        assert result == {'test': 'value'}, "Default should work for unset values"
        
        print("  PASS: Config persistence works correctly")
        return True
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_malformed_config_recovery():
    """Test 11: Recovery from malformed config file."""
    print("\n=== Test 11: Malformed Config Recovery ===")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
        f.write('{ invalid json }')
    
    try:
        # Should fall back to defaults without crashing
        c = Config(config_path=temp_path)
        
        # Should have default values
        assert c.get('ai', 'provider') == 'openai', "Should have default provider"
        
        # get() with default should still work
        result = c.get('missing', 'key', default='fallback')
        assert result == 'fallback', "Default should work after recovery"
        
        print("  PASS: Malformed config recovery works correctly")
        return True
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_backward_compatibility():
    """Test 12: Backward compatibility - existing code should not break."""
    print("\n=== Test 12: Backward Compatibility ===")
    c = Config()
    
    # Old-style calls without default parameter should work
    result = c.get('ai', 'provider')
    assert result == 'openai', "Existing key should work"
    
    result = c.get('ai', 'nonexistent')
    assert result is None, "Missing key should return None"
    
    result = c.get('general')
    assert isinstance(result, dict), "Section access should work"
    
    print("  PASS: Backward compatibility maintained")
    return True


def test_deeply_nested_access():
    """Test 13: Deeply nested key access."""
    print("\n=== Test 13: Deeply Nested Access ===")
    c = Config()
    
    # Test deep traversal that exists
    # Note: Our default config doesn't have deeply nested values,
    # so we test that it handles missing deep paths gracefully
    result = c.get('level1', 'level2', 'level3', 'level4', default='deep_default')
    assert result == 'deep_default', f"Expected 'deep_default', got {result}"
    
    print("  PASS: Deeply nested access works correctly")
    return True


def test_none_as_default():
    """Test 14: Explicit None as default."""
    print("\n=== Test 14: Explicit None Default ===")
    c = Config()
    result = c.get('missing', 'key', default=None)
    assert result is None, f"Expected None, got {result}"
    print("  PASS: Explicit None default works correctly")
    return True


def run_all_tests():
    """Run all config tests."""
    print("=" * 60)
    print("CONFIG.GET() BUG FIX REGRESSION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_scalar_default,
        test_dict_default,
        test_missing_key,
        test_existing_key,
        test_nested_config,
        test_list_default,
        test_empty_string_default,
        test_zero_default,
        test_false_default,
        test_config_persistence,
        test_malformed_config_recovery,
        test_backward_compatibility,
        test_deeply_nested_access,
        test_none_as_default,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
            errors.append((test.__name__, str(e)))
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
            errors.append((test.__name__, str(e)))
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if errors:
        print("\nFailed tests:")
        for name, error in errors:
            print(f"  - {name}: {error}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
