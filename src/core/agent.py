"""Core Agent Implementation"""
import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
from pydantic import BaseModel, Field
from .message import A2AMessage, MessageType
from .security import SecurityContext
from ..a2a.client import A2AClient
from ..mcp.client import MCPClient
from ..utils.logging import get_logger

class AgentCapability(BaseModel):
    """Represents an agent capability"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"

class AgentMemory:
    """Simple in-memory storage for agent state"""
    def __init__(self):
        self._memory: Dict[str, Any] = {}
        self._conversation_history: List[Dict] = []

    def store(self, key: str, value: Any) -> None:
        self._memory[key] = value

    def retrieve(self, key: str) -> Optional[Any]:
        return self._memory.get(key)

    def add_to_history(self, message: Dict) -> None:
        self._conversation_history.append({
            **message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_history(self, limit: int = 100) -> List[Dict]:
        return self._conversation_history[-limit:]

class Agent(ABC):
    """Base Agent class implementing core functionality"""

    def __init__(self, agent_id: str, name: str, capabilities: List[AgentCapability], config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.name = name
        self.capabilities = {cap.name: cap for cap in capabilities}
        self.config = config or {}

        self.logger = get_logger(f"agent.{self.name}")
        self.memory = AgentMemory()
        self.security_context = SecurityContext(agent_id)

        self.a2a_client: Optional[A2AClient] = None
        self.mcp_client: Optional[MCPClient] = None

        self._running = False
        self._tasks: Set[str] = set()

    async def initialize(self) -> None:
        """Initialize the agent and its clients"""
        try:
            # Get Redis URL from environment, with password if set
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_password = os.getenv("REDIS_PASSWORD")
            
            # If password is set, include it in the URL
            if redis_password and "redis://" in redis_url and "@" not in redis_url:
                # Convert redis://host:port to redis://:password@host:port
                redis_url = redis_url.replace("redis://", f"redis://:{redis_password}@")
            
            self.a2a_client = A2AClient(
                agent_id=self.agent_id, 
                security_context=self.security_context,
                redis_url=redis_url
            )
            await self.a2a_client.initialize()

            self.mcp_client = MCPClient(agent_id=self.agent_id, config=self.config.get("mcp", {}))
            await self.mcp_client.initialize()

            await self._register_message_handlers()
            await self._announce_capabilities()

            self._running = True
            self.logger.info(f"Agent {self.name} successfully initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.name}: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the agent gracefully"""
        self._running = False
        if self.a2a_client:
            await self.a2a_client.shutdown()
        if self.mcp_client:
            await self.mcp_client.shutdown()
        self.logger.info(f"Agent {self.name} shut down")

    async def _register_message_handlers(self) -> None:
        """Register A2A message handlers"""
        if not self.a2a_client:
            return

        handlers = {
            MessageType.TASK_REQUEST: self._handle_task_request,
            MessageType.TASK_RESPONSE: self._handle_task_response,
            MessageType.CAPABILITY_QUERY: self._handle_capability_query,
        }

        for message_type, handler in handlers.items():
            await self.a2a_client.register_handler(message_type, handler)

    async def _announce_capabilities(self) -> None:
        """Announce agent capabilities to the network"""
        if not self.a2a_client:
            return

        announcement = A2AMessage(
            message_id=str(uuid4()),
            sender_id=self.agent_id,
            recipient_id="*",
            message_type=MessageType.CAPABILITY_ANNOUNCEMENT,
            payload={
                "agent_name": self.name,
                "capabilities": [cap.dict() for cap in self.capabilities.values()],
                "status": "active"
            },
            requires_response=False
        )

        await self.a2a_client.broadcast_message(announcement)

    async def _handle_task_request(self, message: A2AMessage) -> None:
        """Handle incoming task requests"""
        try:
            task_id = message.payload.get("task_id", str(uuid4()))
            task_type = message.payload.get("task_type")
            task_data = message.payload.get("data", {})

            if task_type not in self.capabilities:
                await self._send_task_response(message.sender_id, task_id, False, error=f"Capability '{task_type}' not supported")
                return

            self._tasks.add(task_id)
            try:
                result = await self.execute_task(task_type, task_data, message)
                await self._send_task_response(message.sender_id, task_id, True, result=result)
            except Exception as e:
                await self._send_task_response(message.sender_id, task_id, False, error=str(e))
            finally:
                self._tasks.discard(task_id)
        except Exception as e:
            self.logger.error(f"Error handling task request: {e}")

    async def _send_task_response(self, recipient_id: str, task_id: str, success: bool, result: Any = None, error: str = None) -> None:
        """Send a task response message"""
        if not self.a2a_client:
            return

        response = A2AMessage(
            message_id=str(uuid4()),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=MessageType.TASK_RESPONSE,
            payload={"task_id": task_id, "success": success, "result": result, "error": error},
            requires_response=False
        )

        await self.a2a_client.send_message(response)

    async def _handle_task_response(self, message: A2AMessage) -> None:
        """Handle task responses from other agents"""
        task_id = message.payload.get("task_id")
        self.memory.store(f"task_response_{task_id}", message.payload)

    async def _handle_capability_query(self, message: A2AMessage) -> None:
        """Handle capability queries from other agents"""
        response = A2AMessage(
            message_id=str(uuid4()),
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type=MessageType.CAPABILITY_RESPONSE,
            payload={"capabilities": [cap.dict() for cap in self.capabilities.values()]},
            requires_response=False
        )
        await self.a2a_client.send_message(response)

    async def send_task_to_agent(self, recipient_id: str, task_type: str, task_data: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        """Send a task to another agent and wait for response"""
        if not self.a2a_client:
            raise RuntimeError("A2A client not initialized")

        task_id = str(uuid4())
        message = A2AMessage(
            message_id=str(uuid4()),
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=MessageType.TASK_REQUEST,
            payload={"task_id": task_id, "task_type": task_type, "data": task_data},
            requires_response=True
        )

        await self.a2a_client.send_message(message)

        # Wait for response
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            response = self.memory.retrieve(f"task_response_{task_id}")
            if response:
                return response
            await asyncio.sleep(0.1)

        raise TimeoutError(f"No response received for task {task_id} within {timeout}s")

    @abstractmethod
    async def execute_task(self, task_type: str, task_data: Dict[str, Any], message: A2AMessage) -> Any:
        """Execute a specific task - to be implemented by subclasses"""
        pass
