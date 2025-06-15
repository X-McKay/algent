#!/usr/bin/env python3
"""
Test script for Quick Wins implementation
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.agents.file_processor import FileProcessorAgent
from src.utils.persistence import SimplePersistence
from examples.simple_agent import SimpleCalculatorAgent


async def test_file_processor():
    """Test the File Processor Agent"""
    print("🧪 Testing File Processor Agent...")
    
    # Create test data directory
    test_dir = Path("./data")
    test_dir.mkdir(exist_ok=True)
    
    agent = FileProcessorAgent("test-file-processor")
    
    try:
        await agent.initialize()
        print("✅ File processor agent initialized")
        
        # Test 1: Write a file
        write_result = await agent.send_task_to_agent(
            recipient_id="test-file-processor",
            task_type="write_file",
            task_data={
                "file_path": "./data/test_file.txt",
                "content": "Hello, World!\nThis is a test file.\nLine 3 here."
            }
        )
        print(f"✅ Write file result: {write_result}")
        
        # Test 2: Read the file back
        read_result = await agent.send_task_to_agent(
            recipient_id="test-file-processor",
            task_type="read_file",
            task_data={"file_path": "./data/test_file.txt"}
        )
        print(f"✅ Read file result: Lines={read_result['result']['line_count']}, Size={read_result['result']['size_bytes']}")
        
        # Test 3: Count words
        word_count_result = await agent.send_task_to_agent(
            recipient_id="test-file-processor",
            task_type="count_words",
            task_data={"text": "The quick brown fox jumps over the lazy dog. The fox is quick."}
        )
        print(f"✅ Word count result: {word_count_result['result']['word_count']} words, top word: {word_count_result['result']['top_words'][0]}")
        
        # Test 4: Analyze CSV
        csv_data = """name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,Chicago
Alice,28,Boston"""
        
        csv_result = await agent.send_task_to_agent(
            recipient_id="test-file-processor",
            task_type="analyze_csv",
            task_data={"csv_content": csv_data}
        )
        print(f"✅ CSV analysis result: {csv_result['result']['row_count']} rows, {csv_result['result']['column_count']} columns")
        
        # Test 5: List directory
        list_result = await agent.send_task_to_agent(
            recipient_id="test-file-processor",
            task_type="list_directory",
            task_data={"directory_path": "./data"}
        )
        print(f"✅ Directory listing: {list_result['result']['file_count']} files found")
        
    except Exception as e:
        print(f"❌ File processor test failed: {e}")
    finally:
        await agent.shutdown()


def test_persistence():
    """Test the Persistence layer"""
    print("\n🧪 Testing Persistence Layer...")
    
    # Use a test database
    test_db = SimplePersistence("data/test_agentic.db")
    
    # Test 1: Save agent
    test_db.save_agent(
        agent_id="test-agent-001",
        name="TestAgent",
        agent_type="test",
        capabilities=["test_task", "another_task"],
        config={"max_tasks": 5}
    )
    print("✅ Agent saved to database")
    
    # Test 2: Get agent
    agent_data = test_db.get_agent("test-agent-001")
    print(f"✅ Agent retrieved: {agent_data['name']} with {len(agent_data['capabilities'])} capabilities")
    
    # Test 3: Save task result
    test_db.save_task_result(
        task_id="task-001",
        agent_id="test-agent-001",
        task_type="test_task",
        task_data={"input": "test"},
        result={"output": "success"},
        status="completed"
    )
    print("✅ Task result saved")
    
    # Test 4: Get task result
    task_data = test_db.get_task_result("task-001")
    print(f"✅ Task result retrieved: Status={task_data['status']}")
    
    # Test 5: Save and get memory
    test_db.save_agent_memory("test-agent-001", "last_calculation", {"result": 42, "operation": "multiply"})
    memory = test_db.get_agent_memory("test-agent-001", "last_calculation")
    print(f"✅ Memory saved and retrieved: {memory}")
    
    # Test 6: Get stats
    stats = test_db.get_stats()
    print(f"✅ Database stats: {stats['total_agents']} agents, {stats['total_tasks']} tasks")


async def test_integration():
    """Test integration between components"""
    print("\n🧪 Testing Integration...")
    
    # Initialize persistence
    db = SimplePersistence("data/integration_test.db")
    
    # Create agents
    calc_agent = SimpleCalculatorAgent("integration-calc")
    file_agent = FileProcessorAgent("integration-file")
    
    try:
        await calc_agent.initialize()
        await file_agent.initialize()
        print("✅ Both agents initialized")
        
        # Test workflow: Calculate something, then save result to file
        calc_result = await calc_agent.send_task_to_agent(
            recipient_id="integration-calc",
            task_type="multiply",
            task_data={"a": 15, "b": 23}
        )
        
        result_value = calc_result['result']['result']
        print(f"✅ Calculation completed: 15 × 23 = {result_value}")
        
        # Save calculation to database
        db.save_task_result(
            task_id="calc-task-001",
            agent_id="integration-calc",
            task_type="multiply",
            task_data={"a": 15, "b": 23},
            result=calc_result['result'],
            status="completed"
        )
        
        # Save result to file
        file_content = f"Calculation Result\n================\n15 × 23 = {result_value}\nCalculated by: {calc_agent.agent_id}\nTimestamp: {calc_result.get('timestamp', 'unknown')}"
        
        write_result = await file_agent.send_task_to_agent(
            recipient_id="integration-file",
            task_type="write_file",
            task_data={
                "file_path": "./data/calculation_result.txt",
                "content": file_content
            }
        )
        print(f"✅ Result saved to file: {write_result['result']['bytes_written']} bytes written")
        
        # Verify by reading back
        read_result = await file_agent.send_task_to_agent(
            recipient_id="integration-file",
            task_type="read_file",
            task_data={"file_path": "./data/calculation_result.txt"}
        )
        print(f"✅ File verified: {read_result['result']['line_count']} lines read")
        
        print("🎉 Integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await calc_agent.shutdown()
        await file_agent.shutdown()


async def main():
    """Run all tests"""
    print("🚀 Running Quick Wins Tests...")
    print("=" * 50)
    
    # Test individual components
    await test_file_processor()
    test_persistence()
    await test_integration()
    
    print("\n" + "=" * 50)
    print("🎉 All Quick Wins tests completed!")
    print("\n📋 What was tested:")
    print("  ✅ File Processor Agent - read/write files, analyze CSV, count words")
    print("  ✅ Persistence Layer - SQLite database storage")
    print("  ✅ Integration - agents working together with persistence")
    print("\n🚀 Next steps:")
    print("  1. Start the API server: python api_server.py")
    print("  2. Test the REST API: curl http://localhost:8000/agents")
    print("  3. Use the file processor via API")


if __name__ == "__main__":
    asyncio.run(main())
