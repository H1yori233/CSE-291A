from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any, Dict

import requests


def load_image_as_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    mime = "image/png"
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def build_payload(image_data_url: str) -> Dict[str, Any]:
    return {
        "model": "Qwen/Qwen3-VL-8B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请描述这张图片的关键信息。"},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        "max_tokens": 512,
        "temperature": 0.2,
    }


def main() -> None:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/test.png")
    server_url = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "http://127.0.0.1:8000/v1/chat/completions"
    )

    image_data_url = load_image_as_data_url(image_path)
    payload = build_payload(image_data_url)

    print(f"Sending request to {server_url} with image {image_path}")
    response = requests.post(
        server_url,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )

    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
