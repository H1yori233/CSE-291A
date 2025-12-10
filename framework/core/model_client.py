"""Qwen VL client with optimization features."""

from __future__ import annotations

import base64
import hashlib
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False


class ModelClient(ABC):
    """Abstract chat completion interface."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 512,
        image: Optional[Any] = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError


class ImageOptimizer:
    """Handles image compression and deduplication."""

    MAX_SIZE: int = 768
    JPEG_QUALITY: int = 85
    PHASH_THRESHOLD: int = 5

    def __init__(self):
        self._prev_hash: Optional[str] = None
        self._prev_result: Optional[str] = None

    def compress(self, image: Any) -> Tuple[bytes, str]:
        """Compresses an image and returns its bytes and a base64 data URL."""
        # Copy to prevent modification of original
        img = image.copy()
        
        # Resize while maintaining aspect ratio
        width, height = img.size
        if width > self.MAX_SIZE or height > self.MAX_SIZE:
            img.thumbnail((self.MAX_SIZE, self.MAX_SIZE))
        
        # Encode as JPEG
        buffer = BytesIO()
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format="JPEG", quality=self.JPEG_QUALITY, optimize=True)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        return img_bytes, f"data:image/jpeg;base64,{img_base64}"

    def compute_hash(self, image: Any) -> str:
        if IMAGEHASH_AVAILABLE:
            return str(imagehash.phash(image))
        else:
            thumb = image.copy()
            thumb.thumbnail((64, 64))
            buffer = BytesIO()
            thumb.save(buffer, format="PNG")
            return hashlib.md5(buffer.getvalue()).hexdigest()

    def is_same_screen(self, image: Any) -> Tuple[bool, Optional[str]]:
        current_hash = self.compute_hash(image)
        
        if self._prev_hash is None:
            self._prev_hash = current_hash
            return False, None
        
        if IMAGEHASH_AVAILABLE:
            prev = imagehash.hex_to_hash(self._prev_hash)
            curr = imagehash.hex_to_hash(current_hash)
            is_same = (prev - curr) < self.PHASH_THRESHOLD
        else:
            is_same = (self._prev_hash == current_hash)
        
        if is_same and self._prev_result is not None:
            return True, self._prev_result
        
        self._prev_hash = current_hash
        return False, None

    def cache_result(self, result: str) -> None:
        self._prev_result = result

    def reset(self) -> None:
        self._prev_hash = None
        self._prev_result = None


class QwenVLClient(ModelClient):
    """Client for the local vLLM endpoint that serves Qwen3-VL."""

    def __init__(
        self,
        model: str = "Qwen/Qwen3-VL-8B-Instruct-FP8",
        base_url: str = "http://127.0.0.1:8000/v1/chat/completions",
        api_key: str = "EMPTY",
        timeout: int = 120,
        enable_screen_cache: bool = False,  # Disabled by default - was causing amnesia
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.enable_screen_cache = enable_screen_cache
        
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })
        
        self._image_optimizer = ImageOptimizer()
        
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
        }

    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 512,
        image: Optional[Any] = None,
    ) -> str:
        self.stats["total_requests"] += 1
        
        if image is not None and self.enable_screen_cache:
            is_same, cached = self._image_optimizer.is_same_screen(image)
            if is_same and cached is not None:
                self.stats["cache_hits"] += 1
                return cached
        
        payload_messages = self._attach_image(messages, image)
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Retry logic for network errors
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    self.base_url,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                try:
                    result = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as exc:
                    raise RuntimeError(f"Unexpected response from Qwen server: {data}") from exc
                
                if image is not None and self.enable_screen_cache:
                    self._image_optimizer.cache_result(result)
                
                return result
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    import time
                    wait_time = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                    import logging
                    logging.getLogger(__name__).warning(
                        "Request failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, max_retries, wait_time, exc
                    )
                    time.sleep(wait_time)
        
        # All retries failed
        raise last_error

    def _attach_image(
        self, messages: List[Dict[str, Any]], image: Optional[Any]
    ) -> List[Dict[str, Any]]:
        if image is None:
            return messages
        
        _, encoded = self._image_optimizer.compress(image)
        
        payload: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") != "user":
                payload.append(msg)
                continue
            payload.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": msg.get("content", "")},
                        {"type": "image_url", "image_url": {"url": encoded}},
                    ],
                }
            )
        return payload

    def get_model_name(self) -> str:
        return f"qwen_vl/{self.model}"

    def reset_cache(self) -> None:
        """Reset same-screen cache (call when starting new task)."""
        self._image_optimizer.reset()

    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        hit_rate = 0.0
        if self.stats["total_requests"] > 0:
            hit_rate = self.stats["cache_hits"] / self.stats["total_requests"]
        return {
            **self.stats,
            "cache_hit_rate": f"{hit_rate:.1%}",
        }

    def close(self) -> None:
        """Close the session."""
        self._session.close()


def create_model_client(name: str = "qwen_vl", **kwargs) -> ModelClient:
    backend = name.lower()
    if backend != "qwen_vl":
        raise ValueError("Only the 'qwen_vl' backend is available in this refactor")
    return QwenVLClient(**kwargs)


__all__ = ["ModelClient", "QwenVLClient", "create_model_client", "ImageOptimizer"]

