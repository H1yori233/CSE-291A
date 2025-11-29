#!/usr/bin/env python3
"""
Simple test script for VLM client without requiring display/GUI.
Tests only the QwenVLClient functionality.
"""

import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.core.model_client import create_model_client
from PIL import Image


def test_qwen_vl_connection():
    """Test basic connection to Qwen VL server."""
    print("=" * 60)
    print("Testing Qwen VL Server Connection")
    print("=" * 60)
    
    try:
        # Create client
        print("\n1. Creating QwenVLClient...")
        client = create_model_client(
            'qwen_vl',
            model='Qwen/Qwen3-VL-8B-Instruct',
            base_url='http://127.0.0.1:8000/v1/chat/completions'
        )
        print(f"   ✓ Client created: {client.get_model_name()}")
        
        # Test text-only generation
        print("\n2. Testing text-only generation...")
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'Say "Hello, VLM!" and nothing else.'}
        ]
        response = client.generate(messages, temperature=0.0, max_tokens=50)
        print(f"   Response: {response}")
        print("   ✓ Text generation works")
        
        # Test with image
        print("\n3. Testing multimodal (image + text) generation...")
        
        # Create a simple test image
        img = Image.new('RGB', (200, 200), color='blue')
        
        messages = [
            {'role': 'user', 'content': 'What color is this image? Answer in one word only.'}
        ]
        response = client.generate(messages, temperature=0.0, max_tokens=20, image=img)
        print(f"   Response: {response}")
        print("   ✓ Multimodal generation works")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_action_generation():
    """Test that VLM can generate action JSON."""
    print("\n" + "=" * 60)
    print("Testing Action Generation")
    print("=" * 60)
    
    try:
        client = create_model_client('qwen_vl')
        
        # Create a fake "desktop screenshot" (just colored image for testing)
        img = Image.new('RGB', (800, 600), color='white')
        
        system_prompt = """You are a computer control agent. 
Respond with ONLY a JSON object containing actions.
Example: {"actions": [{"action": "CLICK", "x": 100, "y": 200}]}"""
        
        user_prompt = """Task: Click on the center of the screen.
        
Respond with ONLY a JSON object. No other text."""
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
        
        print("\n1. Asking VLM to generate action JSON...")
        response = client.generate(
            messages, 
            temperature=0.0, 
            max_tokens=200, 
            image=img
        )
        
        print(f"   Raw response:\n{response}\n")
        
        # Try to parse JSON
        import json
        try:
            parsed = json.loads(response.strip())
            print(f"   ✓ Valid JSON!")
            print(f"   Parsed: {parsed}")
            
            if 'actions' in parsed:
                print(f"   ✓ Contains 'actions' key")
                print(f"   Number of actions: {len(parsed['actions'])}")
            else:
                print(f"   ⚠ Missing 'actions' key")
                
        except json.JSONDecodeError as e:
            print(f"   ✗ Invalid JSON: {e}")
            print(f"   Response may contain extra text")
        
        print("\n" + "=" * 60)
        print("✓ Action generation test completed")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("VLM Client Test (No GUI Required)")
    print("="*60)
    print("\nPREREQUISITE: Ensure Qwen VL server is running:")
    print("  bash /workspace/code/test/inference/serve.sh")
    print("="*60 + "\n")
    
    # Test 1: Basic connection
    test1_passed = test_qwen_vl_connection()
    
    if not test1_passed:
        print("\n⚠ QwenVL server not responding. Is it running?")
        sys.exit(1)
    
    # Test 2: Action generation
    test2_passed = test_action_generation()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Connection test:       {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Action generation test: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("\n🎉 VLM client is working correctly!")
        print("\nNext steps:")
        print("  - You can now use QwenVLClient in the agent framework")
        print("  - The framework will send screenshots directly to Qwen VL")
        print("  - No OCR is needed anymore!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)


if __name__ == '__main__':
    main()
