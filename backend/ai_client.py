"""
AI Engineering Study Assistant - OpenAI-Compatible AI Client
Supports OpenAI, Anthropic, Ollama, and any OpenAI-compatible API endpoint.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator, Callable
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from functools import wraps
import time

from config import get_ai_config, AIConfig

logger = logging.getLogger(__name__)


# ============================================
# RETRY DECORATOR
# ============================================

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry API calls on transient errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (exponential backoff)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_error = e
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                except APIConnectionError as e:
                    last_error = e
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"Connection error, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                except APIError as e:
                    # Don't retry on other API errors (e.g., invalid model, auth errors)
                    raise
            raise last_error
        return wrapper
    return decorator


# ============================================
# AI CLIENT
# ============================================

class AIClient:
    """
    OpenAI-compatible AI client.
    
    Supports:
    - OpenAI (GPT-4, GPT-3.5-turbo)
    - Anthropic via OpenAI-compatible proxy
    - Ollama (local LLMs like Llama 3)
    - Any OpenAI-compatible API endpoint
    
    Usage:
        client = AIClient()  # Uses config from .env
        response = client.chat([{"role": "user", "content": "Hello!"}])
        
        # With custom config
        client = AIClient(base_url="http://localhost:11434/v1", model="llama3")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[AIConfig] = None
    ):
        """
        Initialize the AI client.
        
        Args:
            base_url: API base URL (overrides config)
            api_key: API key (overrides config)
            model: Model name (overrides config)
            config: Full AIConfig instance (overrides defaults)
        """
        cfg = config or get_ai_config()
        
        self.base_url = base_url or cfg.api_base_url
        self.api_key = api_key or cfg.api_key
        self.model = model or cfg.model_name
        self.default_temperature = cfg.temperature
        self.default_max_tokens = cfg.max_tokens
        
        # Initialize OpenAI client
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "dummy-key"  # Some local LLMs don't require keys
        )
        
        logger.info(f"AIClient initialized: base_url={self.base_url}, model={self.model}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with role/content
            tools: Optional list of tool definitions for function calling
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum response tokens
            tool_choice: How to select tools ("auto", "none", or specific tool)
            
        Returns:
            Response dict with:
                - content: Text content of response
                - tool_calls: List of tool calls (if any)
                - finish_reason: Why generation stopped
                - usage: Token usage stats
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise
        
        message = response.choices[0].message
        
        result = {
            "content": message.content,
            "tool_calls": [],
            "finish_reason": response.choices[0].finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }
        }
        
        # Parse tool calls if present
        if message.tool_calls:
            for tc in message.tool_calls:
                result["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
        
        return result
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        tool_handlers: Dict[str, Callable],
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Chat with automatic tool execution loop.
        
        Args:
            messages: Initial conversation messages
            tools: Tool definitions
            tool_handlers: Dict mapping tool names to handler functions
            max_iterations: Maximum number of tool call iterations
            
        Returns:
            Final response after all tool calls are processed
        """
        current_messages = messages.copy()
        
        for iteration in range(max_iterations):
            response = self.chat(current_messages, tools=tools)
            
            if not response["tool_calls"]:
                # No more tool calls, return final response
                return response
            
            # Add assistant message with tool calls
            current_messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response["tool_calls"]
            })
            
            # Execute each tool call
            for tool_call in response["tool_calls"]:
                func_name = tool_call["function"]["name"]
                
                try:
                    func_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}
                
                if func_name in tool_handlers:
                    try:
                        result = tool_handlers[func_name](**func_args)
                        result_str = json.dumps(result) if not isinstance(result, str) else result
                    except Exception as e:
                        logger.error(f"Tool execution failed: {func_name} - {e}")
                        result_str = json.dumps({"error": str(e)})
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {func_name}"})
                
                # Add tool result message
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result_str
                })
        
        # Max iterations reached
        logger.warning(f"Max tool iterations ({max_iterations}) reached")
        return self.chat(current_messages)
    
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat completion responses.
        
        Args:
            messages: List of message dicts
            tools: Optional tool definitions
            temperature: Sampling temperature
            
        Yields:
            Chunks with:
                - type: "content" or "tool_call"
                - content: Text chunk for content
                - tool_call: Partial tool call for tool_call
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.default_temperature,
            "stream": True,
        }
        
        if tools:
            kwargs["tools"] = tools
        
        try:
            stream = self._client.chat.completions.create(**kwargs)
            
            for chunk in stream:
                delta = chunk.choices[0].delta
                
                if delta.content:
                    yield {
                        "type": "content",
                        "content": delta.content
                    }
                
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        yield {
                            "type": "tool_call",
                            "tool_call": {
                                "index": tc.index,
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name if tc.function else None,
                                    "arguments": tc.function.arguments if tc.function else None
                                }
                            }
                        }
                        
        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            yield {"type": "error", "error": str(e)}
    
    def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Get embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model (defaults to text-embedding-ada-002)
            
        Returns:
            List of embedding vectors
        """
        embed_model = model or "text-embedding-ada-002"
        
        try:
            response = self._client.embeddings.create(
                model=embed_model,
                input=texts
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if the AI service is available."""
        try:
            # Try a minimal request
            self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"AI service unavailable: {e}")
            return False


# ============================================
# SINGLETON INSTANCE
# ============================================

_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get or create the AI client singleton instance."""
    global _client
    if _client is None:
        _client = AIClient()
    return _client


def reset_ai_client():
    """Reset the AI client singleton (useful for config changes)."""
    global _client
    _client = None


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def quick_chat(
    prompt: str,
    system_prompt: Optional[str] = None
) -> str:
    """
    Quick single-turn chat.
    
    Args:
        prompt: User message
        system_prompt: Optional system prompt
        
    Returns:
        AI response text
    """
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    client = get_ai_client()
    response = client.chat(messages)
    
    return response["content"] or ""


def classify_intent(
    user_message: str,
    categories: List[str]
) -> str:
    """
    Classify user message intent into one of the given categories.
    
    Args:
        user_message: The user's message
        categories: List of possible intent categories
        
    Returns:
        The classified intent category
    """
    system_prompt = f"""You are an intent classifier. Classify the user's message into exactly one of these categories:
{', '.join(categories)}

Respond with ONLY the category name, nothing else."""

    result = quick_chat(user_message, system_prompt)
    
    # Clean and validate result
    result = result.strip().lower()
    
    for category in categories:
        if category.lower() in result or result in category.lower():
            return category
    
    # Default to first category if no match
    return categories[0]
