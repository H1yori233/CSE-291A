#!/usr/bin/env python3
"""
Test script for VLM-based agent architecture.
Verifies that QwenVLClient can process screenshots and generate actions.
"""

import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.core.model_client import create_model_client
from framework.core.loop import AgentLoop


def test_qwen_vl_client():
    """Test that QwenVLClient can be instantiated and communicate with the server."""
    print("=" * 60)
    print("Testing QwenVLClient")
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
        
        # Test simple text generation (without image)
        print("\n2. Testing text-only generation...")
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'Say "Hello, VLM!" and nothing else.'}
        ]
        response = client.generate(messages, temperature=0.0, max_tokens=50)
        print(f"   Response: {response[:100]}")
        print("   ✓ Text generation works")
        
        # Test with a dummy image
        print("\n3. Testing image + text generation...")
        from PIL import Image
        import io
        
        # Create a simple test image (100x100 red square)
        img = Image.new('RGB', (100, 100), color='red')
        
        messages = [
            {'role': 'user', 'content': 'What color is this image? Answer in one word.'}
        ]
        response = client.generate(messages, temperature=0.0, max_tokens=50, image=img)
        print(f"   Response: {response[:100]}")
        print("   ✓ Image generation works")
        
        print("\n" + "=" * 60)
        print("✓ All QwenVLClient tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_loop():
    """Test that AgentLoop can run with VLM."""
    print("\n" + "=" * 60)
    print("Testing AgentLoop with VLM")
    print("=" * 60)
    
    try:
        # Create VLM client
        print("\n1. Creating VLM client...")
        client = create_model_client('qwen_vl')
        print(f"   ✓ Client ready: {client.get_model_name()}")
        
        # Create agent loop
        print("\n2. Creating AgentLoop...")
        loop = AgentLoop(
            model_client=client,
            verbose=True,
            run_dir='/tmp/test_vlm_agent',
            action_delay=0.1
        )
        print("   ✓ AgentLoop initialized")
        
        # Run a simple test task (just 1 step to verify)
        print("\n3. Running test task (max 1 step)...")
        print("   Task: 'Describe what you see on the screen'")
        
        result = loop.run_task(
            task_description="Describe what you see on the screen",
            max_steps=1,
            auto_success_check=False
        )
        
        print(f"\n   Result:")
        print(f"   - Steps taken: {result['current_step']}")
        print(f"   - Success: {result['success']}")
        
        print("\n" + "=" * 60)
        print("✓ AgentLoop test completed!")
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
    print("VLM Architecture Integration Test")
    print("="*60)
    print("\nPREREQUISITE: Ensure Qwen VL server is running:")
    print("  bash /workspace/code/test/inference/serve.sh")
    print("="*60 + "\n")
    
    # Test 1: QwenVLClient
    test1_passed = test_qwen_vl_client()
    
    if not test1_passed:
        print("\n⚠ Stopping tests - QwenVLClient test failed")
        print("Make sure the VLM server is running!")
        sys.exit(1)
    
    # Test 2: AgentLoop
    test2_passed = test_agent_loop()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"QwenVLClient test: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"AgentLoop test:    {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print("="*60)
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! VLM architecture is working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
