#!/usr/bin/env python3
"""
Simple Agent Example
Demonstrates basic agent functionality with A2A and MCP integration.
"""

import asyncio
import os
import sys
from typing import Any, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.agent import Agent, AgentCapability
from src.core.message import A2AMessage


class SimpleCalculatorAgent(Agent):
    """
    A simple calculator agent that can perform basic math operations
    """
    
    def __init__(self, agent_id: str):
        capabilities = [
            AgentCapability(
                name="add",
                description="Add two numbers",
                parameters={
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                }
            ),
            AgentCapability(
                name="subtract",
                description="Subtract two numbers",
                parameters={
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                }
            ),
            AgentCapability(
                name="multiply",
                description="Multiply two numbers",
                parameters={
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                }
            ),
            AgentCapability(
                name="divide",
                description="Divide two numbers",
                parameters={
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                }
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="SimpleCalculator",
            capabilities=capabilities,
            config={
                "max_concurrent_tasks": 5,
                "mcp": {
                    "server_url": os.getenv("MCP_SERVER_URL", "http://localhost:8080")
                }
            }
        )
    
    async def execute_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        message: A2AMessage
    ) -> Any:
        """Execute a calculation task"""
        
        self.logger.info(f"Executing {task_type} with data: {task_data}")
        
        # Extract parameters
        a = task_data.get("a")
        b = task_data.get("b")
        
        if a is None or b is None:
            raise ValueError("Both 'a' and 'b' parameters are required")
        
        # Convert to numbers
        try:
            a = float(a)
            b = float(b)
        except (ValueError, TypeError):
            raise ValueError("Parameters 'a' and 'b' must be numbers")
        
        # Perform calculation
        if task_type == "add":
            result = a + b
        elif task_type == "subtract":
            result = a - b
        elif task_type == "multiply":
            result = a * b
        elif task_type == "divide":
            if b == 0:
                raise ValueError("Division by zero is not allowed")
            result = a / b
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Store calculation in memory
        calculation_record = {
            "operation": task_type,
            "inputs": {"a": a, "b": b},
            "result": result,
            "requester": message.sender_id
        }
        
        self.memory.store(f"calculation_{message.message_id}", calculation_record)
        self.memory.add_to_history({
            "type": "calculation",
            "operation": task_type,
            "result": result
        })
        
        self.logger.info(f"Calculation result: {a} {task_type} {b} = {result}")
        
        return {
            "result": result,
            "operation": task_type,
            "inputs": {"a": a, "b": b}
        }
    
    async def on_task_response(
        self,
        task_id: str,
        success: bool,
        result: Any,
        error: str = None
    ) -> None:
        """Handle responses from tasks we sent to other agents"""
        if success:
            self.logger.info(f"Task {task_id} completed successfully: {result}")
        else:
            self.logger.error(f"Task {task_id} failed: {error}")


class SimpleEchoAgent(Agent):
    """
    A simple echo agent that repeats messages
    """
    
    def __init__(self, agent_id: str):
        capabilities = [
            AgentCapability(
                name="echo",
                description="Echo back a message",
                parameters={
                    "message": {"type": "string", "description": "Message to echo"}
                }
            ),
            AgentCapability(
                name="uppercase",
                description="Convert message to uppercase",
                parameters={
                    "message": {"type": "string", "description": "Message to convert"}
                }
            ),
            AgentCapability(
                name="reverse",
                description="Reverse a message",
                parameters={
                    "message": {"type": "string", "description": "Message to reverse"}
                }
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="SimpleEcho",
            capabilities=capabilities,
            config={
                "max_concurrent_tasks": 10,
                "mcp": {
                    "server_url": os.getenv("MCP_SERVER_URL", "http://localhost:8080")
                }
            }
        )
    
    async def execute_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        message: A2AMessage
    ) -> Any:
        """Execute a text processing task"""
        
        self.logger.info(f"Executing {task_type} with data: {task_data}")
        
        # Extract message
        text = task_data.get("message", "")
        if not isinstance(text, str):
            raise ValueError("Parameter 'message' must be a string")
        
        # Process text
        if task_type == "echo":
            result = text
        elif task_type == "uppercase":
            result = text.upper()
        elif task_type == "reverse":
            result = text[::-1]
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Store in memory
        self.memory.store(f"text_processing_{message.message_id}", {
            "operation": task_type,
            "input": text,
            "output": result,
            "requester": message.sender_id
        })
        
        self.memory.add_to_history({
            "type": "text_processing",
            "operation": task_type,
            "input_length": len(text),
            "output_length": len(result)
        })
        
        return {
            "result": result,
            "operation": task_type,
            "original": text
        }


async def run_calculator_agent():
    """Run the calculator agent"""
    agent = SimpleCalculatorAgent("calc-001")
    
    try:
        await agent.initialize()
        print(f"Calculator agent {agent.agent_id} started")
        
        # Keep the agent running
        while agent._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down calculator agent...")
    finally:
        await agent.shutdown()


async def run_echo_agent():
    """Run the echo agent"""
    agent = SimpleEchoAgent("echo-001")
    
    try:
        await agent.initialize()
        print(f"Echo agent {agent.agent_id} started")
        
        # Keep the agent running
        while agent._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down echo agent...")
    finally:
        await agent.shutdown()


async def run_demo():
    """Run a demo with both agents communicating"""
    print("Starting agent demo...")
    
    # Create agents
    calc_agent = SimpleCalculatorAgent("calc-demo")
    echo_agent = SimpleEchoAgent("echo-demo")
    
    try:
        # Initialize agents
        await calc_agent.initialize()
        await echo_agent.initialize()
        
        print("Both agents initialized, waiting for startup...")
        await asyncio.sleep(2)
        
        # Demo: Calculator agent sends task to echo agent
        print("\n=== Demo: Sending echo task ===")
        echo_result = await calc_agent.send_task_to_agent(
            recipient_id="echo-demo",
            task_type="uppercase",
            task_data={"message": "Hello from calculator agent!"}
        )
        print(f"Echo result: {echo_result}")
        
        # Demo: Echo agent sends task to calculator agent
        print("\n=== Demo: Sending calculation task ===")
        calc_result = await echo_agent.send_task_to_agent(
            recipient_id="calc-demo",
            task_type="multiply",
            task_data={"a": 7, "b": 6}
        )
        print(f"Calculation result: {calc_result}")
        
        # Demo: Discover available agents
        print("\n=== Demo: Agent discovery ===")
        discovered = await calc_agent.a2a_client.discover_agents(timeout=3.0)
        print(f"Discovered agents: {discovered}")
        
        print("\nDemo completed successfully!")
        
        # Keep running for manual testing
        print("Agents are running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down demo...")
    except Exception as e:
        print(f"Demo error: {e}")
    finally:
        await calc_agent.shutdown()
        await echo_agent.shutdown()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Agent Example")
    parser.add_argument(
        "--mode",
        choices=["calculator", "echo", "demo"],
        default="demo",
        help="Mode to run: calculator agent, echo agent, or demo"
    )
    
    args = parser.parse_args()
    
    if args.mode == "calculator":
        asyncio.run(run_calculator_agent())
    elif args.mode == "echo":
        asyncio.run(run_echo_agent())
    elif args.mode == "demo":
        asyncio.run(run_demo())