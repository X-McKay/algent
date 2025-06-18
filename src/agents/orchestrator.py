"""Orchestration and Planning System"""
import asyncio
import json
import logging
import uuid
import datetime
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import httpx

from src.core.agent import Agent, AgentCapability


class AgentStepModel(BaseModel):
    """Model for a single step in an execution plan"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    agent: str
    action: str
    input: Dict[str, Any]
    output: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed, skipped
    retries: int = 0
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


class ExecutionPlanModel(BaseModel):
    """Model for a complete execution plan"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_query: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    steps: List[AgentStepModel] = []
    status: str = "created"  # created, running, completed, failed, cancelled
    metadata: Dict[str, Any] = {}


class OrchestratorAgent(Agent):
    """Main orchestrator agent that plans and coordinates other agents"""
    
    def __init__(self, agent_id: str = "orchestrator-001"):
        super().__init__(agent_id, "OrchestratorAgent")
        self.vllm_endpoint = "http://localhost:8001/v1"
        self.model_name = "gpt-3.5-turbo"
        self.client = None
        self.agent_registry = {}
        self.active_plans = {}
        
        # Register capabilities
        self.capabilities = [
            AgentCapability("plan", "Create execution plans for complex tasks"),
            AgentCapability("orchestrate", "Coordinate multiple agents to complete tasks"),
            AgentCapability("route", "Route queries to appropriate agents"),
            AgentCapability("monitor", "Monitor and manage plan execution"),
            AgentCapability("revise", "Revise plans based on execution results")
        ]
    
    async def initialize(self):
        """Initialize the orchestrator"""
        await super().initialize()
        self.client = httpx.AsyncClient(timeout=30.0)
        await self._discover_agents()
    
    async def shutdown(self):
        """Cleanup orchestrator"""
        if self.client:
            await self.client.aclose()
        await super().shutdown()
    
    async def _discover_agents(self):
        """Discover available agents and their capabilities"""
        try:
            # Get agents from the API server
            response = await self.client.get("http://localhost:8000/agents")
            if response.status_code == 200:
                agents_data = response.json()
                for agent in agents_data:
                    agent_id = agent.get("agent_id")
                    capabilities = agent.get("capabilities", [])
                    self.agent_registry[agent_id] = {
                        "name": agent.get("name"),
                        "status": agent.get("status"),
                        "capabilities": capabilities
                    }
                self.logger.info(f"Discovered {len(self.agent_registry)} agents")
            else:
                self.logger.warning("Could not discover agents from API server")
        except Exception as e:
            self.logger.error(f"Failed to discover agents: {e}")
    
    async def _call_vllm(self, messages: list, temperature: float = 0.7) -> str:
        """Make a call to the VLLM endpoint for planning"""
        try:
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature
            }
            
            response = await self.client.post(
                f"{self.vllm_endpoint}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"Error: VLLM API returned {response.status_code}"
                
        except Exception as e:
            return f"Error calling VLLM: {str(e)}"
    
    async def plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution plan for a user query"""
        user_query = data.get("query", "")
        if not user_query:
            return {"error": "No query provided"}
        
        # Create system prompt with available agents
        agent_info = []
        for agent_id, info in self.agent_registry.items():
            capabilities = ", ".join(info.get("capabilities", []))
            agent_info.append(f"- {agent_id} ({info.get('name')}): {capabilities}")
        
        system_prompt = f"""You are an expert task orchestrator. Given a user query, create a detailed execution plan.

Available agents and their capabilities:
{chr(10).join(agent_info)}

Create a plan as a JSON array of steps. Each step should have:
- task: Clear description of what needs to be done
- agent: Which agent should handle this step
- action: The specific action/capability to use
- input: Input parameters for the agent

Consider dependencies between steps and order them logically.
Return ONLY the JSON array, no other text."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a plan for: {user_query}"}
        ]
        
        plan_response = await self._call_vllm(messages, temperature=0.3)
        
        try:
            # Parse the plan
            steps_data = json.loads(plan_response)
            steps = []
            
            for step_data in steps_data:
                step = AgentStepModel(
                    task=step_data.get("task", ""),
                    agent=step_data.get("agent", ""),
                    action=step_data.get("action", ""),
                    input=step_data.get("input", {})
                )
                steps.append(step)
            
            # Create execution plan
            plan = ExecutionPlanModel(
                user_query=user_query,
                steps=steps
            )
            
            # Store the plan
            self.active_plans[plan.id] = plan
            
            return {
                "plan_id": plan.id,
                "user_query": user_query,
                "steps": [step.dict() for step in steps],
                "total_steps": len(steps)
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse plan JSON: {e}")
            return {
                "error": "Failed to create valid plan",
                "raw_response": plan_response
            }
    
    async def orchestrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plan by orchestrating multiple agents"""
        plan_id = data.get("plan_id", "")
        if not plan_id or plan_id not in self.active_plans:
            return {"error": "Invalid or missing plan_id"}
        
        plan = self.active_plans[plan_id]
        plan.status = "running"
        
        results = []
        
        for step in plan.steps:
            step.status = "running"
            
            try:
                # Execute the step
                response = await self.client.post(
                    "http://localhost:8000/tasks",
                    json={
                        "agent_id": step.agent,
                        "action": step.action,
                        "data": step.input
                    }
                )
                
                if response.status_code == 200:
                    task_data = response.json()
                    task_id = task_data.get("task_id")
                    
                    # Wait for task completion
                    await asyncio.sleep(2)  # Give task time to process
                    
                    result_response = await self.client.get(f"http://localhost:8000/tasks/{task_id}")
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        step.output = json.dumps(result_data.get("result", {}))
                        step.status = "completed"
                    else:
                        step.output = f"Failed to get result: {result_response.status_code}"
                        step.status = "failed"
                else:
                    step.output = f"Failed to execute: {response.status_code}"
                    step.status = "failed"
                    
            except Exception as e:
                step.output = f"Error: {str(e)}"
                step.status = "failed"
            
            step.completed_at = datetime.datetime.utcnow().isoformat()
            results.append(step.dict())
        
        plan.status = "completed"
        
        return {
            "plan_id": plan_id,
            "status": plan.status,
            "results": results,
            "total_steps": len(plan.steps),
            "completed_steps": len([s for s in plan.steps if s.status == "completed"])
        }
    
    async def route(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route a simple query to the most appropriate agent"""
        query = data.get("query", "")
        if not query:
            return {"error": "No query provided"}
        
        # Use VLLM to determine the best agent
        agent_info = []
        for agent_id, info in self.agent_registry.items():
            capabilities = ", ".join(info.get("capabilities", []))
            agent_info.append(f"- {agent_id}: {capabilities}")
        
        system_prompt = f"""Given a user query, determine which agent is best suited to handle it.

Available agents:
{chr(10).join(agent_info)}

Return only the agent ID that should handle this query."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        agent_response = await self._call_vllm(messages, temperature=0.1)
        suggested_agent = agent_response.strip()
        
        # Validate the suggested agent
        if suggested_agent in self.agent_registry:
            return {
                "query": query,
                "suggested_agent": suggested_agent,
                "agent_info": self.agent_registry[suggested_agent]
            }
        else:
            return {
                "query": query,
                "error": f"No suitable agent found",
                "suggestion": agent_response
            }
    
    async def monitor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor active plans and their status"""
        plan_id = data.get("plan_id")
        
        if plan_id:
            # Monitor specific plan
            if plan_id in self.active_plans:
                plan = self.active_plans[plan_id]
                return {
                    "plan_id": plan_id,
                    "status": plan.status,
                    "user_query": plan.user_query,
                    "total_steps": len(plan.steps),
                    "completed_steps": len([s for s in plan.steps if s.status == "completed"]),
                    "failed_steps": len([s for s in plan.steps if s.status == "failed"]),
                    "steps": [step.dict() for step in plan.steps]
                }
            else:
                return {"error": f"Plan {plan_id} not found"}
        else:
            # Monitor all active plans
            plans_summary = []
            for pid, plan in self.active_plans.items():
                plans_summary.append({
                    "plan_id": pid,
                    "status": plan.status,
                    "user_query": plan.user_query,
                    "created_at": plan.created_at,
                    "total_steps": len(plan.steps),
                    "completed_steps": len([s for s in plan.steps if s.status == "completed"])
                })
            
            return {
                "active_plans": len(self.active_plans),
                "plans": plans_summary
            }
    
    async def revise(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Revise a plan based on execution results or new requirements"""
        plan_id = data.get("plan_id", "")
        revision_reason = data.get("reason", "")
        
        if not plan_id or plan_id not in self.active_plans:
            return {"error": "Invalid or missing plan_id"}
        
        plan = self.active_plans[plan_id]
        
        # Create revision prompt
        current_steps = [step.dict() for step in plan.steps]
        
        system_prompt = f"""You are revising an execution plan based on current results and feedback.

Original query: {plan.user_query}
Revision reason: {revision_reason}

Current plan steps and their status:
{json.dumps(current_steps, indent=2)}

Create a revised plan as a JSON array of steps. Consider:
1. What steps have already completed successfully
2. What steps failed and need to be redone differently
3. What new steps might be needed
4. The revision reason provided

Return ONLY the JSON array of revised steps."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Revise the plan. Reason: {revision_reason}"}
        ]
        
        revision_response = await self._call_vllm(messages, temperature=0.3)
        
        try:
            # Parse the revised plan
            revised_steps_data = json.loads(revision_response)
            revised_steps = []
            
            for step_data in revised_steps_data:
                step = AgentStepModel(
                    task=step_data.get("task", ""),
                    agent=step_data.get("agent", ""),
                    action=step_data.get("action", ""),
                    input=step_data.get("input", {})
                )
                revised_steps.append(step)
            
            # Update the plan
            plan.steps = revised_steps
            plan.status = "revised"
            
            return {
                "plan_id": plan_id,
                "status": "revised",
                "revision_reason": revision_reason,
                "revised_steps": [step.dict() for step in revised_steps],
                "total_steps": len(revised_steps)
            }
            
        except json.JSONDecodeError as e:
            return {
                "error": "Failed to parse revised plan",
                "raw_response": revision_response
            }

