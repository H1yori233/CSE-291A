"""
LLM Model Client with support for multiple backends
Designed for easy swapping between OpenAI API and local LLMs
"""

import os
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod


class ModelClient(ABC):
    """
    Abstract base class for LLM clients.
    Allows easy swapping between different model backends.
    """
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response from the model.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name/identifier of the model being used"""
        pass


class OpenAIClient(ModelClient):
    """
    Client for OpenAI API (GPT-4, GPT-3.5, etc.)
    """
    
    def __init__(
        self, 
        model: str = "gpt-4o",
        api_key: Optional[str] = None
    ):
        """
        Initialize OpenAI client.
        
        Args:
            model: Model name (e.g., "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo")
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "OpenAI package not installed. Install with: pip install openai"
            )
        
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response using OpenAI API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI parameters
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")
    
    def get_model_name(self) -> str:
        """Get the model name"""
        return f"openai/{self.model}"


class OllamaClient(ModelClient):
    """
    Client for Ollama (local LLM server)
    """
    
    def __init__(
        self,
        model: str = "llama3.1:8b-instruct",
        base_url: str = "http://localhost:11434"
    ):
        """
        Initialize Ollama client.
        
        Args:
            model: Model name (e.g., "llama3.1:8b-instruct", "mistral")
            base_url: Ollama server URL
        """
        try:
            import ollama
        except ImportError:
            raise RuntimeError(
                "Ollama package not installed.\n"
                "Install with: pip install ollama\n"
                "Or use OpenAI backend for now: create_model_client('openai')"
            )
        
        self.model = model
        self.base_url = base_url
        self.client = ollama
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response using Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama parameters
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            )
            
            return response['message']['content']
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {str(e)}")
    
    def get_model_name(self) -> str:
        """Get the model name"""
        return f"ollama/{self.model}"


class LlamaCppClient(ModelClient):
    """
    Client for llama.cpp (local CPU/GPU inference)
    """
    
    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0
    ):
        """
        Initialize llama.cpp client.
        
        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python not installed.\n"
                "This package requires compilation. Install with:\n"
                "  macOS: CMAKE_ARGS=\"-DLLAMA_METAL=on\" pip install llama-cpp-python\n"
                "  Linux: CMAKE_ARGS=\"-DLLAMA_CUDA=on\" pip install llama-cpp-python\n"
                "  CPU-only: pip install llama-cpp-python\n"
                "Or use OpenAI/Ollama backend instead."
            )
        
        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response using llama.cpp.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional llama.cpp parameters
            
        Returns:
            Generated text response
        """
        try:
            response = self.llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response['choices'][0]['message']['content']
        except Exception as e:
            raise RuntimeError(f"llama.cpp generation failed: {str(e)}")
    
    def get_model_name(self) -> str:
        """Get the model name"""
        return f"llamacpp/{os.path.basename(self.model_path)}"


class AnthropicClient(ModelClient):
    """
    Client for Anthropic API (Claude models)
    """
    
    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None
    ):
        """
        Initialize Anthropic client.
        
        Args:
            model: Model name (e.g., "claude-3-sonnet-20240229")
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise RuntimeError(
                "Anthropic package not installed.\n"
                "Install with: pip install anthropic\n"
                "Or use OpenAI backend for now: create_model_client('openai')"
            )
        
        self.model = model
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment "
                "variable or pass api_key parameter."
            )
        
        self.client = Anthropic(api_key=self.api_key)
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response using Anthropic API.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic parameters
            
        Returns:
            Generated text response
        """
        try:
            # Extract system message if present
            system_msg = None
            chat_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    chat_messages.append(msg)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg if system_msg else "",
                messages=chat_messages,
                **kwargs
            )
            
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {str(e)}")
    
    def get_model_name(self) -> str:
        """Get the model name"""
        return f"anthropic/{self.model}"


def create_model_client(
    backend: str = "openai",
    **kwargs
) -> ModelClient:
    """
    Factory function to create a model client.
    
    Args:
        backend: Backend type ('openai', 'ollama', 'llamacpp', 'anthropic')
        **kwargs: Backend-specific parameters
        
    Returns:
        ModelClient instance
        
    Example:
        # OpenAI
        client = create_model_client('openai', model='gpt-4o')
        
        # Ollama
        client = create_model_client('ollama', model='llama3.1:8b-instruct')
        
        # llama.cpp
        client = create_model_client('llamacpp', model_path='models/llama.gguf')
    """
    backend = backend.lower()
    
    if backend == "openai":
        return OpenAIClient(**kwargs)
    elif backend == "ollama":
        return OllamaClient(**kwargs)
    elif backend == "llamacpp":
        return LlamaCppClient(**kwargs)
    elif backend == "anthropic":
        return AnthropicClient(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {backend}. "
            f"Supported: openai, ollama, llamacpp, anthropic"
        )

