#!/usr/bin/env python3
"""
File Processing Agent - Handles file operations and data analysis
"""

import asyncio
import csv
import json
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.agent import Agent, AgentCapability
from src.core.message import A2AMessage


class FileProcessorAgent(Agent):
    """
    Agent that can read files, process CSV data, and analyze text
    """
    
    def __init__(self, agent_id: str):
        capabilities = [
            AgentCapability(
                name="read_file",
                description="Read contents of a text file",
                parameters={
                    "file_path": {"type": "string", "description": "Path to the file to read"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
                }
            ),
            AgentCapability(
                name="write_file",
                description="Write content to a file",
                parameters={
                    "file_path": {"type": "string", "description": "Path where to write the file"},
                    "content": {"type": "string", "description": "Content to write"},
                    "encoding": {"type": "string", "description": "File encoding (default: utf-8)"}
                }
            ),
            AgentCapability(
                name="analyze_csv",
                description="Analyze CSV data and return statistics",
                parameters={
                    "csv_content": {"type": "string", "description": "CSV content as string"},
                    "delimiter": {"type": "string", "description": "CSV delimiter (default: ,)"}
                }
            ),
            AgentCapability(
                name="list_directory",
                description="List files in a directory",
                parameters={
                    "directory_path": {"type": "string", "description": "Path to directory"},
                    "pattern": {"type": "string", "description": "File pattern filter (optional)"}
                }
            ),
            AgentCapability(
                name="count_words",
                description="Count words in text content",
                parameters={
                    "text": {"type": "string", "description": "Text to analyze"}
                }
            )
        ]
        
        super().__init__(
            agent_id=agent_id,
            name="FileProcessor",
            capabilities=capabilities,
            config={
                "max_concurrent_tasks": 8,
                "allowed_directories": ["/tmp", "./data", "./uploads"],  # Security: limit file access
                "max_file_size": 10 * 1024 * 1024,  # 10MB limit
                "mcp": {
                    "server_url": os.getenv("MCP_SERVER_URL", "http://localhost:8080")
                }
            }
        )
    
    async def execute_task(self, task_type: str, task_data: Dict[str, Any], message: A2AMessage) -> Any:
        """Execute file processing tasks"""
        
        self.logger.info(f"Executing {task_type} with data: {task_data}")
        
        try:
            if task_type == "read_file":
                return await self._read_file(task_data)
            elif task_type == "write_file":
                return await self._write_file(task_data)
            elif task_type == "analyze_csv":
                return await self._analyze_csv(task_data)
            elif task_type == "list_directory":
                return await self._list_directory(task_data)
            elif task_type == "count_words":
                return await self._count_words(task_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            self.logger.error(f"Task {task_type} failed: {e}")
            raise
    
    async def _read_file(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file and return its contents"""
        file_path = task_data.get("file_path")
        encoding = task_data.get("encoding", "utf-8")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        # Security check
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access to {file_path} is not allowed")
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File {file_path} not found")
        
        # Check file size
        if path.stat().st_size > self.config.get("max_file_size", 10 * 1024 * 1024):
            raise ValueError("File too large")
        
        content = path.read_text(encoding=encoding)
        
        result = {
            "file_path": str(path),
            "content": content,
            "size_bytes": path.stat().st_size,
            "line_count": len(content.splitlines()),
            "encoding": encoding
        }
        
        # Store in memory
        self.memory.store(f"file_read_{message.message_id}", result)
        
        return result
    
    async def _write_file(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file"""
        file_path = task_data.get("file_path")
        content = task_data.get("content", "")
        encoding = task_data.get("encoding", "utf-8")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        # Security check
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"Access to {file_path} is not allowed")
        
        path = Path(file_path)
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        path.write_text(content, encoding=encoding)
        
        result = {
            "file_path": str(path),
            "bytes_written": len(content.encode(encoding)),
            "line_count": len(content.splitlines()),
            "success": True
        }
        
        self.memory.store(f"file_write_{message.message_id}", result)
        
        return result
    
    async def _analyze_csv(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CSV data and return statistics"""
        csv_content = task_data.get("csv_content")
        delimiter = task_data.get("delimiter", ",")
        
        if not csv_content:
            raise ValueError("csv_content is required")
        
        # Parse CSV
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        rows = list(reader)
        if not rows:
            return {"error": "No data found in CSV"}
        
        columns = list(rows[0].keys())
        row_count = len(rows)
        
        # Analyze each column
        column_stats = {}
        for col in columns:
            values = [row[col] for row in rows if row[col]]
            
            # Try to convert to numbers for numeric analysis
            numeric_values = []
            for val in values:
                try:
                    numeric_values.append(float(val))
                except (ValueError, TypeError):
                    pass
            
            stats = {
                "total_values": len(values),
                "empty_values": row_count - len(values),
                "unique_values": len(set(values)),
                "is_numeric": len(numeric_values) > 0
            }
            
            if numeric_values:
                stats.update({
                    "numeric_count": len(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "average": sum(numeric_values) / len(numeric_values),
                    "sum": sum(numeric_values)
                })
            
            column_stats[col] = stats
        
        result = {
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns,
            "column_statistics": column_stats,
            "sample_rows": rows[:3]  # First 3 rows as sample
        }
        
        self.memory.store(f"csv_analysis_{message.message_id}", result)
        
        return result
    
    async def _list_directory(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """List files in a directory"""
        directory_path = task_data.get("directory_path")
        pattern = task_data.get("pattern", "*")
        
        if not directory_path:
            raise ValueError("directory_path is required")
        
        # Security check
        if not self._is_path_allowed(directory_path):
            raise PermissionError(f"Access to {directory_path} is not allowed")
        
        path = Path(directory_path)
        if not path.exists():
            raise FileNotFoundError(f"Directory {directory_path} not found")
        
        if not path.is_dir():
            raise ValueError(f"{directory_path} is not a directory")
        
        # List files matching pattern
        files = []
        for file_path in path.glob(pattern):
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size_bytes": stat.st_size,
                "is_directory": file_path.is_dir(),
                "modified_time": stat.st_mtime
            })
        
        result = {
            "directory_path": str(path),
            "pattern": pattern,
            "file_count": len(files),
            "files": sorted(files, key=lambda x: x["name"])
        }
        
        return result
    
    async def _count_words(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Count words in text content"""
        text = task_data.get("text", "")
        
        if not text:
            return {"word_count": 0, "character_count": 0, "line_count": 0}
        
        lines = text.splitlines()
        words = text.split()
        characters = len(text)
        characters_no_spaces = len(text.replace(" ", ""))
        
        # Word frequency analysis
        word_freq = {}
        for word in words:
            cleaned_word = word.lower().strip(".,!?;:")
            word_freq[cleaned_word] = word_freq.get(cleaned_word, 0) + 1
        
        # Get top 10 most common words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        result = {
            "word_count": len(words),
            "character_count": characters,
            "character_count_no_spaces": characters_no_spaces,
            "line_count": len(lines),
            "unique_words": len(word_freq),
            "average_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "top_words": top_words
        }
        
        self.memory.store(f"word_count_{message.message_id}", result)
        
        return result
    
    def _is_path_allowed(self, path: str) -> bool:
        """Check if file path is in allowed directories"""
        allowed_dirs = self.config.get("allowed_directories", [])
        path_obj = Path(path).resolve()
        
        for allowed_dir in allowed_dirs:
            try:
                allowed_path = Path(allowed_dir).resolve()
                if str(path_obj).startswith(str(allowed_path)):
                    return True
            except Exception:
                continue
        
        return False


async def run_file_processor_agent():
    """Run the file processor agent"""
    agent = FileProcessorAgent("file-processor-001")
    
    try:
        await agent.initialize()
        print(f"File processor agent {agent.agent_id} started")
        
        # Keep the agent running
        while agent._running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down file processor agent...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(run_file_processor_agent())
