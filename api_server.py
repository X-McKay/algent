#!/usr/bin/env python3
"""
REST API Server for Agentic System
Provides HTTP endpoints to interact with agents
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.core.agent import Agent, AgentCapability
from src.core.message import A2AMessage, MessageType
from examples.simple_agent import SimpleCalculatorAgent, SimpleEchoAgent
from src.agents.file_processor import FileProcessorAgent


# Pydantic models for API
class TaskRequest(BaseModel):
    agent_id: str
    task_type: str
    task_data: Dict[str, Any]
    timeout: float = 30.0


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    status: str
    capabilities: List[str]
    active_tasks: int


class AgentCreateRequest(BaseModel):
    agent_type: str
    agent_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


# FastAPI app
app = FastAPI(
    title="Agentic System API",
    description="REST API for managing and interacting with AI agents",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent registry
active_agents: Dict[str, Agent] = {}
task_results: Dict[str, TaskResponse] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize default agents on startup"""
    print("🚀 Starting API server and initializing default agents...")
    
    # Create default agents
    default_agents = [
        SimpleCalculatorAgent("api-calculator-001"),
        SimpleEchoAgent("api-echo-001"),
        FileProcessorAgent("api-fileprocessor-001")
    ]
    
    for agent in default_agents:
        try:
            await agent.initialize()
            active_agents[agent.agent_id] = agent
            print(f"✅ Initialized agent: {agent.agent_id}")
        except Exception as e:
            print(f"❌ Failed to initialize agent {agent.agent_id}: {e}")
    
    print(f"🎉 API server ready with {len(active_agents)} active agents")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup agents on shutdown"""
    print("🛑 Shutting down agents...")
    
    for agent in active_agents.values():
        try:
            await agent.shutdown()
        except Exception as e:
            print(f"Error shutting down agent {agent.agent_id}: {e}")
    
    active_agents.clear()
    print("✅ All agents shut down")


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Agentic System API",
        "version": "1.0.0",
        "active_agents": len(active_agents),
        "endpoints": {
            "agents": "/agents",
            "tasks": "/tasks",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    agent_health = {}
    for agent_id, agent in active_agents.items():
        try:
            if hasattr(agent, 'a2a_client') and agent.a2a_client:
                health = await agent.a2a_client.health_check()
                agent_health[agent_id] = health
            else:
                agent_health[agent_id] = {"status": "no_a2a_client"}
        except Exception as e:
            agent_health[agent_id] = {"status": "error", "error": str(e)}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_agents": len(active_agents),
        "agent_health": agent_health
    }


@app.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all active agents"""
    agents_info = []
    
    for agent in active_agents.values():
        info = AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            status="active" if agent._running else "inactive",
            capabilities=list(agent.capabilities.keys()),
            active_tasks=len(agent._tasks)
        )
        agents_info.append(info)
    
    return agents_info


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get detailed information about a specific agent"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = active_agents[agent_id]
    
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "status": "active" if agent._running else "inactive",
        "capabilities": [cap.dict() for cap in agent.capabilities.values()],
        "active_tasks": len(agent._tasks),
        "memory_size": len(agent.memory._memory),
        "conversation_history": len(agent.memory._conversation_history),
        "config": agent.config
    }


@app.post("/agents", response_model=AgentInfo)
async def create_agent(request: AgentCreateRequest):
    """Create a new agent"""
    agent_id = request.agent_id or f"{request.agent_type}-{uuid.uuid4().hex[:8]}"
    
    if agent_id in active_agents:
        raise HTTPException(status_code=400, detail="Agent ID already exists")
    
    # Create agent based on type
    try:
        if request.agent_type == "calculator":
            agent = SimpleCalculatorAgent(agent_id)
        elif request.agent_type == "echo":
            agent = SimpleEchoAgent(agent_id)
        elif request.agent_type == "file_processor":
            agent = FileProcessorAgent(agent_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {request.agent_type}")
        
        # Apply custom config if provided
        if request.config:
            agent.config.update(request.config)
        
        # Initialize agent
        await agent.initialize()
        active_agents[agent_id] = agent
        
        return AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            status="active",
            capabilities=list(agent.capabilities.keys()),
            active_tasks=0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = active_agents[agent_id]
    
    try:
        await agent.shutdown()
        del active_agents[agent_id]
        return {"message": f"Agent {agent_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Submit a task to an agent"""
    if request.agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = active_agents[request.agent_id]
    
    # Check if agent has the required capability
    if request.task_type not in agent.capabilities:
        raise HTTPException(
            status_code=400, 
            detail=f"Agent {request.agent_id} does not support task type '{request.task_type}'"
        )
    
    task_id = str(uuid.uuid4())
    
    # Execute task in background
    background_tasks.add_task(
        execute_task_async, 
        task_id, 
        agent, 
        request.task_type, 
        request.task_data, 
        request.timeout
    )
    
    # Return immediate response
    response = TaskResponse(
        task_id=task_id,
        status="pending",
        timestamp=datetime.utcnow().isoformat()
    )
    
    task_results[task_id] = response
    return response


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_result(task_id: str):
    """Get the result of a task"""
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_results[task_id]


@app.get("/tasks")
async def list_tasks(limit: int = 50):
    """List recent tasks"""
    recent_tasks = list(task_results.values())[-limit:]
    return {"tasks": recent_tasks, "total": len(task_results)}


async def execute_task_async(task_id: str, agent: Agent, task_type: str, task_data: Dict[str, Any], timeout: float):
    """Execute a task asynchronously and store the result"""
    try:
        # Create a fake message for the task execution
        message = A2AMessage(
            message_id=task_id,
            sender_id="api-server",
            recipient_id=agent.agent_id,
            message_type=MessageType.TASK_REQUEST,
            payload={"task_id": task_id, "task_type": task_type, "data": task_data}
        )
        
        # Execute the task
        result = await asyncio.wait_for(
            agent.execute_task(task_type, task_data, message),
            timeout=timeout
        )
        
        # Update task result
        task_results[task_id] = TaskResponse(
            task_id=task_id,
            status="completed",
            result=result,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except asyncio.TimeoutError:
        task_results[task_id] = TaskResponse(
            task_id=task_id,
            status="timeout",
            error=f"Task timed out after {timeout} seconds",
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        task_results[task_id] = TaskResponse(
            task_id=task_id,
            status="failed",
            error=str(e),
            timestamp=datetime.utcnow().isoformat()
        )


if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
