"""
Simple Persistence Layer - SQLite-based storage for agent data
"""

import asyncio
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logging import get_logger


class SimplePersistence:
    """
    Simple persistence layer using SQLite for storing agent data
    """
    
    def __init__(self, db_path: str = "data/agentic_system.db"):
        self.db_path = Path(db_path)
        self.logger = get_logger("persistence")
        self._lock = threading.Lock()
        
        # Create data directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- Agents table
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    agent_type TEXT,
                    status TEXT DEFAULT 'active',
                    capabilities TEXT,  -- JSON array
                    config TEXT,        -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Task results table
                CREATE TABLE IF NOT EXISTS task_results (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT,
                    task_type TEXT,
                    task_data TEXT,     -- JSON object
                    result TEXT,        -- JSON object
                    status TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
                );
                
                -- Messages table for audit trail
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    sender_id TEXT,
                    recipient_id TEXT,
                    message_type TEXT,
                    payload TEXT,       -- JSON object
                    signature TEXT,
                    timestamp TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Agent memory/state table
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    memory_key TEXT,
                    memory_value TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, memory_key)
                );
                
                -- Conversation history
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    context_id TEXT,
                    message TEXT,       -- JSON object
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_task_results_agent_id ON task_results(agent_id);
                CREATE INDEX IF NOT EXISTS idx_task_results_status ON task_results(status);
                CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
                CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);
                CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON agent_memory(agent_id);
                CREATE INDEX IF NOT EXISTS idx_conversation_context ON conversation_history(context_id);
            ''')
        
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def save_agent(self, agent_id: str, name: str, agent_type: str, capabilities: List[str], config: Dict[str, Any]):
        """Save agent information"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO agents 
                    (agent_id, name, agent_type, capabilities, config, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    agent_id,
                    name,
                    agent_type,
                    json.dumps(capabilities),
                    json.dumps(config),
                    datetime.utcnow().isoformat()
                ))
        
        self.logger.debug(f"Saved agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM agents WHERE agent_id = ?',
                (agent_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "agent_id": row["agent_id"],
                    "name": row["name"],
                    "agent_type": row["agent_type"],
                    "status": row["status"],
                    "capabilities": json.loads(row["capabilities"]) if row["capabilities"] else [],
                    "config": json.loads(row["config"]) if row["config"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
        
        return None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM agents ORDER BY created_at DESC')
            
            agents = []
            for row in cursor.fetchall():
                agents.append({
                    "agent_id": row["agent_id"],
                    "name": row["name"],
                    "agent_type": row["agent_type"],
                    "status": row["status"],
                    "capabilities": json.loads(row["capabilities"]) if row["capabilities"] else [],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return agents
    
    def save_task_result(self, task_id: str, agent_id: str, task_type: str, task_data: Dict[str, Any], 
                        result: Any = None, status: str = "pending", error_message: str = None):
        """Save task result"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                completed_at = datetime.utcnow().isoformat() if status in ["completed", "failed"] else None
                
                conn.execute('''
                    INSERT OR REPLACE INTO task_results 
                    (task_id, agent_id, task_type, task_data, result, status, error_message, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    agent_id,
                    task_type,
                    json.dumps(task_data),
                    json.dumps(result) if result is not None else None,
                    status,
                    error_message,
                    completed_at
                ))
        
        self.logger.debug(f"Saved task result: {task_id}")
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM task_results WHERE task_id = ?',
                (task_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "task_id": row["task_id"],
                    "agent_id": row["agent_id"],
                    "task_type": row["task_type"],
                    "task_data": json.loads(row["task_data"]) if row["task_data"] else {},
                    "result": json.loads(row["result"]) if row["result"] else None,
                    "status": row["status"],
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"]
                }
        
        return None
    
    def list_task_results(self, agent_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List task results, optionally filtered by agent_id"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if agent_id:
                cursor = conn.execute(
                    'SELECT * FROM task_results WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?',
                    (agent_id, limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT * FROM task_results ORDER BY created_at DESC LIMIT ?',
                    (limit,)
                )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "task_id": row["task_id"],
                    "agent_id": row["agent_id"],
                    "task_type": row["task_type"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"]
                })
            
            return results
    
    def save_message(self, message_id: str, sender_id: str, recipient_id: str, 
                    message_type: str, payload: Dict[str, Any], signature: str = None):
        """Save message for audit trail"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO messages 
                    (message_id, sender_id, recipient_id, message_type, payload, signature, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_id,
                    sender_id,
                    recipient_id,
                    message_type,
                    json.dumps(payload),
                    signature,
                    datetime.utcnow().isoformat()
                ))
    
    def save_agent_memory(self, agent_id: str, memory_key: str, memory_value: Any):
        """Save agent memory/state"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO agent_memory 
                    (agent_id, memory_key, memory_value, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    agent_id,
                    memory_key,
                    json.dumps(memory_value),
                    datetime.utcnow().isoformat()
                ))
    
    def get_agent_memory(self, agent_id: str, memory_key: str = None) -> Any:
        """Get agent memory/state"""
        with sqlite3.connect(self.db_path) as conn:
            if memory_key:
                cursor = conn.execute(
                    'SELECT memory_value FROM agent_memory WHERE agent_id = ? AND memory_key = ?',
                    (agent_id, memory_key)
                )
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None
            else:
                cursor = conn.execute(
                    'SELECT memory_key, memory_value FROM agent_memory WHERE agent_id = ?',
                    (agent_id,)
                )
                return {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    
    def add_conversation_history(self, agent_id: str, context_id: str, message: Dict[str, Any]):
        """Add to conversation history"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO conversation_history 
                    (agent_id, context_id, message)
                    VALUES (?, ?, ?)
                ''', (
                    agent_id,
                    context_id,
                    json.dumps(message)
                ))
    
    def get_conversation_history(self, context_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversation history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM conversation_history 
                WHERE context_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (context_id, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "agent_id": row["agent_id"],
                    "context_id": row["context_id"],
                    "message": json.loads(row["message"]),
                    "timestamp": row["timestamp"]
                })
            
            return list(reversed(history))  # Return in chronological order
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Count agents
            cursor = conn.execute('SELECT COUNT(*) FROM agents')
            stats['total_agents'] = cursor.fetchone()[0]
            
            # Count tasks
            cursor = conn.execute('SELECT COUNT(*) FROM task_results')
            stats['total_tasks'] = cursor.fetchone()[0]
            
            # Count messages
            cursor = conn.execute('SELECT COUNT(*) FROM messages')
            stats['total_messages'] = cursor.fetchone()[0]
            
            # Task status breakdown
            cursor = conn.execute('''
                SELECT status, COUNT(*) 
                FROM task_results 
                GROUP BY status
            ''')
            stats['task_status_breakdown'] = dict(cursor.fetchall())
            
            # Recent activity
            cursor = conn.execute('''
                SELECT COUNT(*) 
                FROM task_results 
                WHERE created_at > datetime('now', '-24 hours')
            ''')
            stats['tasks_last_24h'] = cursor.fetchone()[0]
            
            return stats


# Global persistence instance
persistence = SimplePersistence()
