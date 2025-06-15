#!/usr/bin/env python3
"""Basic test to verify the system works"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from src.core.agent import Agent, AgentCapability
        from src.core.message import A2AMessage, MessageType
        from src.core.security import SecurityContext
        from src.a2a.client import A2AClient
        from src.mcp.client import MCPClient
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic agent creation"""
    try:
        from src.core.agent import AgentCapability
        from src.core.security import SecurityContext
        
        # Test capability creation
        cap = AgentCapability(
            name="test",
            description="Test capability",
            parameters={"input": {"type": "string"}}
        )
        print(f"✅ Created capability: {cap.name}")
        
        # Test security context
        security = SecurityContext("test-agent")
        print(f"✅ Created security context for: {security.agent_id}")
        
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

async def test_async_functionality():
    """Test async components"""
    try:
        from src.core.message import A2AMessage, MessageType
        from src.core.security import SecurityContext
        
        # Test message creation
        message = A2AMessage(
            message_id="test-123",
            sender_id="test-sender",
            recipient_id="test-recipient",
            message_type=MessageType.TASK_REQUEST,
            payload={"test": "data"}
        )
        print(f"✅ Created message: {message.message_id}")
        
        # Test message signing
        security = SecurityContext("test-agent")
        signature = await security.sign_message(message)
        print(f"✅ Signed message: {signature[:16]}...")
        
        return True
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running basic system tests...")
    print()
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    # Test async functionality
    try:
        if not asyncio.run(test_async_functionality()):
            success = False
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        success = False
    
    print()
    if success:
        print("🎉 All tests passed! The system is ready to use.")
        print()
        print("🚀 Try running: python examples/simple_agent.py --mode demo")
    else:
        print("❌ Some tests failed. Check the error messages above.")
        sys.exit(1)
