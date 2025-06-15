"""Message types and structures for Agent-to-Agent communication"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    """Enumeration of A2A message types"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    CAPABILITY_ANNOUNCEMENT = "capability_announcement"
    CAPABILITY_QUERY = "capability_query"
    CAPABILITY_RESPONSE = "capability_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"

class A2AMessage(BaseModel):
    """Base message structure for Agent-to-Agent communication"""
    message_id: str = Field(..., description="Unique message identifier")
    sender_id: str = Field(..., description="Sender agent ID")
    recipient_id: str = Field(..., description="Recipient agent ID")
    message_type: MessageType = Field(..., description="Type of message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
    requires_response: bool = Field(default=False)
    signature: Optional[str] = Field(None, description="Message signature")

    class Config:
        use_enum_values = True
