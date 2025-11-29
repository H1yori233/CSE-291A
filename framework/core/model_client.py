"""Minimal OpenAI-compatible client focused on Qwen VL usage."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, Dict, List, Optional

import requests


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


class QwenVLClient(ModelClient):
    """Client for the local vLLM endpoint that serves Qwen3-VL."""

    def __init__(
        self,
        model: str = "Qwen/Qwen3-VL-8B-Instruct",
        base_url: str = "http://127.0.0.1:8000/v1/chat/completions",
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 512,
        image: Optional[Any] = None,
    ) -> str:
        payload_messages = self._attach_image(messages, image)
        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(
            self.base_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:  # pragma: no cover - network error
            raise RuntimeError(f"Unexpected response from Qwen server: {data}") from exc

    def _attach_image(
        self, messages: List[Dict[str, Any]], image: Optional[Any]
    ) -> List[Dict[str, Any]]:
        if image is None:
            return messages
        encoded = self._encode_image(image)
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

    def _encode_image(self, image: Any) -> str:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"

    def get_model_name(self) -> str:
        return f"qwen_vl/{self.model}"


def create_model_client(name: str = "qwen_vl", **kwargs) -> ModelClient:
    backend = name.lower()
    if backend != "qwen_vl":
        raise ValueError("Only the 'qwen_vl' backend is available in this refactor")
    return QwenVLClient(**kwargs)


__all__ = ["ModelClient", "QwenVLClient", "create_model_client"]
