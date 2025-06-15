"""
A2A Client Implementation - Python 3.13 Compatible
Handles communication between agents using Redis as message bus.
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional
import redis.asyncio as redis
from pydantic import ValidationError

from ..core.message import A2AMessage, MessageType
from ..core.security import SecurityContext
from ..utils.logging import get_logger


class A2AClient:
    """
    A2A Client for agent-to-agent communication - Python 3.13 compatible
    """
    
    def __init__(
        self,
        agent_id: str,
        security_context: SecurityContext,
        redis_url: str = "redis://localhost:6379"
    ):
        self.agent_id = agent_id
        self.security_context = security_context
        self.redis_url = redis_url
        self.logger = get_logger(f"a2a.{agent_id}")
        
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        
        # Message handlers
        self.handlers: Dict[MessageType, Callable] = {}
        
        # Connection state
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the A2A client"""
        try:
            # Create Redis connection with Python 3.13 compatible redis library
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Set up pub/sub
            self.pubsub = self.redis_client.pubsub()
            
            # Subscribe to agent-specific channel and broadcast channel
            agent_channel = f"agentic:agent:{self.agent_id}"
            broadcast_channel = "agentic:broadcast"
            
            await self.pubsub.subscribe(agent_channel, broadcast_channel)
            
            # Start listening for messages
            self._running = True
            self._listen_task = asyncio.create_task(self._listen_for_messages())
            
            self.logger.info(f"A2A client initialized for agent {self.agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize A2A client: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the A2A client"""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
        
        if self.redis_client:
            await self.redis_client.aclose()
        
        self.logger.info(f"A2A client shut down for agent {self.agent_id}")
    
    async def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[A2AMessage], None]
    ) -> None:
        """Register a message handler for a specific message type"""
        self.handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
    
    async def send_message(self, message: A2AMessage) -> None:
        """Send a message to a specific agent"""
        if not self.redis_client:
            raise RuntimeError("A2A client not initialized")
        
        # Validate and sign message
        await self._prepare_message(message)
        
        # Determine target channel
        if message.recipient_id == "*":
            channel = "agentic:broadcast"
        else:
            channel = f"agentic:agent:{message.recipient_id}"
        
        # Serialize message
        message_json = message.json()
        
        # Publish message
        await self.redis_client.publish(channel, message_json)
        
        self.logger.debug(f"Sent message {message.message_id} to {message.recipient_id}")
    
    async def broadcast_message(self, message: A2AMessage) -> None:
        """Broadcast a message to all agents"""
        message.recipient_id = "*"
        await self.send_message(message)
    
    async def _prepare_message(self, message: A2AMessage) -> None:
        """Prepare message for sending (validation, signing, etc.)"""
        # Set sender ID if not already set
        if not message.sender_id:
            message.sender_id = self.agent_id
        
        # Set timestamp if not already set
        if not message.timestamp:
            from datetime import datetime
            message.timestamp = datetime.utcnow().isoformat()
        
        # Sign the message
        message.signature = await self.security_context.sign_message(message)
    
    async def _listen_for_messages(self) -> None:
        """Listen for incoming messages"""
        if not self.pubsub:
            return
        
        self.logger.info("Started listening for A2A messages")
        
        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                
                if message["type"] != "message":
                    continue
                
                try:
                    # Parse message
                    a2a_message = A2AMessage.parse_raw(message["data"])
                    
                    # Skip our own messages
                    if a2a_message.sender_id == self.agent_id:
                        continue
                    
                    # Validate message
                    if not await self._validate_message(a2a_message):
                        self.logger.warning(f"Invalid message from {a2a_message.sender_id}")
                        continue
                    
                    # Route to appropriate handler
                    await self._handle_message(a2a_message)
                    
                except ValidationError as e:
                    self.logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
        
        except asyncio.CancelledError:
            self.logger.info("Message listening cancelled")
        except Exception as e:
            self.logger.error(f"Error in message listener: {e}")
    
    async def _validate_message(self, message: A2AMessage) -> bool:
        """Validate an incoming message"""
        try:
            # Verify message signature
            if not await self.security_context.verify_message_signature(message):
                return False
            
            # Check if sender is trusted
            if not await self.security_context.is_trusted_agent(message.sender_id):
                return False
            
            # Apply rate limiting
            if not await self.security_context.check_rate_limit(message.sender_id):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Message validation error: {e}")
            return False
    
    async def _handle_message(self, message: A2AMessage) -> None:
        """Route message to appropriate handler"""
        handler = self.handlers.get(message.message_type)
        
        if handler:
            try:
                await handler(message)
                self.logger.debug(f"Handled message {message.message_id} of type {message.message_type}")
            except Exception as e:
                self.logger.error(f"Handler error for message {message.message_id}: {e}")
        else:
            self.logger.warning(f"No handler for message type: {message.message_type}")
    
    async def discover_agents(self, timeout: float = 5.0) -> list:
        """Discover available agents in the network"""
        # Simplified discovery for demo
        return []
    
    def is_connected(self) -> bool:
        """Check if the client is connected and running"""
        return self._running and self.redis_client is not None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the A2A client"""
        health = {
            "status": "healthy" if self.is_connected() else "unhealthy",
            "agent_id": self.agent_id,
            "redis_connected": False,
            "listening": self._running,
            "handlers_registered": len(self.handlers)
        }
        
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis_connected"] = True
            except Exception as e:
                health["redis_error"] = str(e)
        
        return health