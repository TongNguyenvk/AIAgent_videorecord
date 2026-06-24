"""
Custom LLM wrapper for 9Router (OpenAI-compatible API).
This allows browser-use to work with 9Router without langchain dependency.
"""

import os
import json
import requests
from typing import Any, Dict, List, Optional


class Router9LLM:
    """
    Custom LLM wrapper for 9Router that mimics langchain's ChatModel interface.
    Compatible with browser-use Agent.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:20128/v1",
        api_key: Optional[str] = None,
        model: str = "kr/claude-sonnet-4.5",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize 9Router LLM client.
        
        Args:
            base_url: 9Router API endpoint
            api_key: API key from 9Router dashboard
            model: Model to use (e.g., kr/claude-sonnet-4.5)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("ROUTER_API_KEY")
        self.model = model
        self.model_name = model  # Required by browser-use Agent
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = "9router"  # Required by browser-use Agent
        
        if not self.api_key:
            raise ValueError("API key required. Set ROUTER_API_KEY in .env or pass api_key parameter")
    
    def _make_request(self, messages: List[Dict[str, Any]], stream: bool = False) -> Dict[str, Any]:
        """Make request to 9Router API."""
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"9Router API error: {response.status_code} - {response.text}")
        
        if stream:
            return response  # Return response object for streaming
        else:
            return response.json()
    
    def invoke(self, prompt: str) -> str:
        """
        Synchronous invoke (for compatibility).
        
        Args:
            prompt: Text prompt
            
        Returns:
            Response text
        """
        messages = [{"role": "user", "content": prompt}]
        result = self._make_request(messages, stream=False)
        
        # Extract content from response
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content
    
    async def ainvoke(self, *args, **kwargs) -> "RouterResponse":
        """
        Async invoke (required by browser-use).
        
        Args:
            *args: Positional arguments (prompt or messages)
            **kwargs: Additional parameters (ignored for compatibility)
            
        Returns:
            RouterResponse object with .content attribute
        """
        # Get prompt from args or kwargs
        if args:
            prompt = args[0]
        elif 'prompt' in kwargs:
            prompt = kwargs['prompt']
        elif 'messages' in kwargs:
            prompt = kwargs['messages']
        else:
            raise ValueError("No prompt provided")
        
        # Handle langchain message objects
        if isinstance(prompt, list):
            messages = []
            for msg in prompt:
                # Handle langchain message objects (SystemMessage, HumanMessage, etc.)
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                    # Langchain message object
                    role = msg.type if msg.type in ['system', 'user', 'assistant'] else 'user'
                    messages.append({"role": role, "content": msg.content})
                elif isinstance(msg, dict):
                    # Already a dict
                    messages.append(msg)
                else:
                    # Convert to string
                    messages.append({"role": "user", "content": str(msg)})
        elif isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            # Try to extract content
            if hasattr(prompt, 'content'):
                messages = [{"role": "user", "content": prompt.content}]
            else:
                messages = [{"role": "user", "content": str(prompt)}]
        
        # Make async request (using sync for now, can be upgraded to aiohttp)
        result = self._make_request(messages, stream=False)
        
        # Extract content
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Return response object
        return RouterResponse(content=content, raw=result)
    
    async def astream(self, messages: List[Dict[str, Any]]):
        """
        Async streaming (for browser-use compatibility).
        
        Args:
            messages: List of message dicts
            
        Yields:
            Response chunks
        """
        response = self._make_request(messages, stream=True)
        
        # Parse SSE stream
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                
                if data == '[DONE]':
                    break
                
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        yield RouterChunk(content=content)
                        
                except json.JSONDecodeError:
                    continue
    
    def __repr__(self):
        return f"Router9LLM(model={self.model}, base_url={self.base_url})"


class RouterResponse:
    """Response object that mimics langchain's AIMessage."""
    
    def __init__(self, content: str, raw: Optional[Dict] = None):
        self.content = content
        self.raw = raw or {}
        # Add usage info for browser-use compatibility
        usage_data = self.raw.get("usage", {})
        self.usage = {
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }
    
    def __str__(self):
        return self.content
    
    def __repr__(self):
        return f"RouterResponse(content={self.content[:50]}...)"


class RouterChunk:
    """Streaming chunk object."""
    
    def __init__(self, content: str):
        self.content = content
    
    def __str__(self):
        return self.content


# Convenience function
def create_9router_llm(
    model: str = "kr/claude-sonnet-4.5",
    api_key: Optional[str] = None,
    base_url: str = "http://localhost:20128/v1",
    temperature: float = 0.7,
) -> Router9LLM:
    """
    Create a 9Router LLM instance.
    
    Args:
        model: Model name (default: kr/claude-sonnet-4.5)
        api_key: API key (default: from ROUTER_API_KEY env var)
        base_url: 9Router endpoint (default: http://localhost:20128/v1)
        temperature: Sampling temperature
        
    Returns:
        Router9LLM instance
    """
    return Router9LLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )


if __name__ == "__main__":
    # Quick test
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test():
        llm = create_9router_llm()
        print(f"Testing {llm}")
        
        response = await llm.ainvoke("Say 'Hello from 9Router!' in Vietnamese")
        print(f"Response: {response.content}")
    
    asyncio.run(test())
