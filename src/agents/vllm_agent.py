"""VLLM Agent for General Language Tasks"""
import asyncio
import logging
import json
import httpx
from typing import Dict, Any, Optional
from src.core.agent import Agent, AgentCapability


class VLLMAgent(Agent):
    """Agent that interfaces with VLLM endpoint for general language tasks"""
    
    def __init__(self, agent_id: str, vllm_endpoint: str = "http://localhost:8001/v1", model_name: str = "gpt-3.5-turbo"):
        super().__init__(agent_id, "VLLMAgent")
        self.vllm_endpoint = vllm_endpoint
        self.model_name = model_name
        self.client = None
        
        # Register capabilities
        self.capabilities = [
            AgentCapability("chat", "General conversation and question answering"),
            AgentCapability("analyze", "Analyze text, data, or problems"),
            AgentCapability("plan", "Create plans and break down complex tasks"),
            AgentCapability("summarize", "Summarize text or information"),
            AgentCapability("generate", "Generate text, code, or creative content"),
            AgentCapability("reason", "Logical reasoning and problem solving")
        ]
    
    async def initialize(self):
        """Initialize the VLLM client"""
        await super().initialize()
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Test connection to VLLM endpoint
        try:
            response = await self.client.get(f"{self.vllm_endpoint}/models")
            if response.status_code == 200:
                self.logger.info(f"Successfully connected to VLLM endpoint: {self.vllm_endpoint}")
            else:
                self.logger.warning(f"VLLM endpoint returned status {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Could not connect to VLLM endpoint: {e}")
    
    async def shutdown(self):
        """Cleanup VLLM client"""
        if self.client:
            await self.client.aclose()
        await super().shutdown()
    
    async def _call_vllm(self, messages: list, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Make a call to the VLLM endpoint"""
        try:
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = await self.client.post(
                f"{self.vllm_endpoint}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"VLLM API error: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                return f"Error: {error_msg}"
                
        except Exception as e:
            error_msg = f"Failed to call VLLM: {str(e)}"
            self.logger.error(error_msg)
            return f"Error: {error_msg}"
    
    async def chat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """General chat/conversation capability"""
        message = data.get("message", "")
        context = data.get("context", "")
        
        if not message:
            return {"error": "No message provided"}
        
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant. Provide clear, accurate, and helpful responses."}
        ]
        
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        
        messages.append({"role": "user", "content": message})
        
        response = await self._call_vllm(messages)
        
        return {
            "response": response,
            "message": message,
            "context": context
        }
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze text, data, or problems"""
        content = data.get("content", "")
        analysis_type = data.get("type", "general")
        
        if not content:
            return {"error": "No content provided for analysis"}
        
        system_prompt = f"""You are an expert analyst. Analyze the following content with focus on {analysis_type} analysis.
Provide a structured analysis including:
1. Key insights
2. Important patterns or trends
3. Potential issues or concerns
4. Recommendations or next steps"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        response = await self._call_vllm(messages, temperature=0.3)
        
        return {
            "analysis": response,
            "content": content,
            "type": analysis_type
        }
    
    async def plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create plans and break down complex tasks"""
        task = data.get("task", "")
        constraints = data.get("constraints", "")
        available_agents = data.get("available_agents", [])
        
        if not task:
            return {"error": "No task provided for planning"}
        
        system_prompt = """You are an expert task planner. Break down complex tasks into clear, actionable steps.
For each step, specify:
1. What needs to be done
2. Which agent/tool should handle it (if applicable)
3. Expected inputs and outputs
4. Dependencies on other steps

Return your plan as a structured JSON array of steps."""
        
        user_content = f"Task: {task}"
        if constraints:
            user_content += f"\nConstraints: {constraints}"
        if available_agents:
            user_content += f"\nAvailable agents: {', '.join(available_agents)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = await self._call_vllm(messages, temperature=0.3)
        
        return {
            "plan": response,
            "task": task,
            "constraints": constraints,
            "available_agents": available_agents
        }
    
    async def summarize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize text or information"""
        content = data.get("content", "")
        length = data.get("length", "medium")  # short, medium, long
        focus = data.get("focus", "")
        
        if not content:
            return {"error": "No content provided for summarization"}
        
        length_instructions = {
            "short": "Provide a brief 1-2 sentence summary",
            "medium": "Provide a concise paragraph summary",
            "long": "Provide a detailed summary with key points"
        }
        
        system_prompt = f"""You are an expert at summarization. {length_instructions.get(length, length_instructions['medium'])}.
{f'Focus particularly on: {focus}' if focus else ''}
Ensure the summary captures the most important information and key insights."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        response = await self._call_vllm(messages, temperature=0.3)
        
        return {
            "summary": response,
            "content": content,
            "length": length,
            "focus": focus
        }
    
    async def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate text, code, or creative content"""
        prompt = data.get("prompt", "")
        content_type = data.get("type", "text")  # text, code, creative, etc.
        style = data.get("style", "")
        
        if not prompt:
            return {"error": "No prompt provided for generation"}
        
        type_instructions = {
            "code": "Generate clean, well-commented code",
            "creative": "Generate creative and engaging content",
            "technical": "Generate precise technical content",
            "text": "Generate clear and informative text"
        }
        
        system_prompt = f"""You are an expert content generator. {type_instructions.get(content_type, type_instructions['text'])}.
{f'Style: {style}' if style else ''}
Ensure the generated content is high-quality, relevant, and well-structured."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._call_vllm(messages, temperature=0.8)
        
        return {
            "generated_content": response,
            "prompt": prompt,
            "type": content_type,
            "style": style
        }
    
    async def reason(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Logical reasoning and problem solving"""
        problem = data.get("problem", "")
        context = data.get("context", "")
        reasoning_type = data.get("type", "logical")  # logical, mathematical, causal, etc.
        
        if not problem:
            return {"error": "No problem provided for reasoning"}
        
        system_prompt = f"""You are an expert at {reasoning_type} reasoning. Approach this problem systematically:
1. Understand the problem clearly
2. Identify key information and constraints
3. Apply appropriate reasoning methods
4. Show your step-by-step thinking
5. Provide a clear conclusion

Be thorough and explain your reasoning process."""
        
        user_content = f"Problem: {problem}"
        if context:
            user_content += f"\nContext: {context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = await self._call_vllm(messages, temperature=0.3)
        
        return {
            "reasoning": response,
            "problem": problem,
            "context": context,
            "type": reasoning_type
        }

