"""Security context and utilities for agent authentication and authorization"""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict, Set
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from .message import A2AMessage
from ..utils.logging import get_logger

class RateLimiter:
    """Simple rate limiter for message handling"""
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}

    def is_allowed(self, identifier: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds

        if identifier not in self._requests:
            self._requests[identifier] = []

        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier]
            if req_time > window_start
        ]

        if len(self._requests[identifier]) < self.max_requests:
            self._requests[identifier].append(now)
            return True
        return False

class SecurityContext:
    """Security context for agent authentication and message validation"""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = get_logger(f"security.{agent_id}")
        self.rate_limiter = RateLimiter()
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    async def sign_message(self, message: A2AMessage) -> str:
        """Sign a message for authentication"""
        message_data = {
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "recipient_id": message.recipient_id,
            "message_type": message.message_type,
            "timestamp": message.timestamp,
            "payload": message.payload
        }
        message_json = json.dumps(message_data, sort_keys=True)
        message_bytes = message_json.encode('utf-8')
        signature = self.private_key.sign(
            message_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        import base64
        return base64.b64encode(signature).decode('utf-8')

    async def verify_message_signature(self, message: A2AMessage) -> bool:
        """Verify a message signature"""
        if not message.signature:
            return False
        try:
            # Simplified verification for demo
            return True
        except Exception:
            return False

    async def is_trusted_agent(self, agent_id: str) -> bool:
        """Check if an agent is trusted"""
        return True  # Simplified for demo

    async def check_rate_limit(self, agent_id: str) -> bool:
        """Check rate limit for an agent"""
        return self.rate_limiter.is_allowed(agent_id)
