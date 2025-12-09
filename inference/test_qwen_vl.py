"""Benchmark script for Qwen VL client."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from PIL import Image

# Import our optimized client
sys.path.insert(0, str(Path(__file__).parent.parent))
from framework.core.model_client import QwenVLClient, ImageOptimizer


def load_image(image_path: Path) -> Image.Image:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return Image.open(image_path)


def format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def run_benchmark(
    client: QwenVLClient,
    image: Image.Image,
    prompt: str,
    num_requests: int = 5,
) -> None:
    print(f"Running benchmark with {num_requests} requests...")
    
    optimizer = ImageOptimizer()
    original_size = image.size
    compressed_bytes, _ = optimizer.compress(image.copy())
    
    print(f"Image compression: {original_size} -> {optimizer.MAX_SIZE}x{optimizer.MAX_SIZE} (JPEG)")
    print(f"Compressed size: {format_size(len(compressed_bytes))}")
    
    messages = [{"role": "user", "content": prompt}]
    latencies = []
    
    for i in range(num_requests):
        start_time = time.time()
        try:
            response = client.generate(
                messages=messages,
                image=image,
                max_tokens=256,
                temperature=0.2,
            )
            latency = time.time() - start_time
            latencies.append(latency)
            
            stats = client.get_stats()
            is_hit = stats["cache_hits"] == i + 1
            status = "HIT " if is_hit else "MISS"
            
            print(f"Req {i+1}/{num_requests}: {status} | {latency:.4f}s")
            
        except Exception as e:
            print(f"Req {i+1}/{num_requests}: ERROR {e}")
    
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"\nResults:")
        print(f"Average Latency: {avg:.4f}s")
        print(f"Min Latency:     {min(latencies):.4f}s")
        print(f"Max Latency:     {max(latencies):.4f}s")
    
    stats = client.get_stats()
    print(f"Cache Hit Rate:  {stats.get('cache_hit_rate', '0%')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test Qwen VL with P0 optimizations"
    )
    parser.add_argument(
        "image",
        type=Path,
        nargs="?",
        default=Path("./data/logo.png"),
        help="Path to test image",
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
        help="vLLM server URL",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-VL-8B-Instruct-FP8",
        help="Model name",
    )
    parser.add_argument(
        "--prompt",
        default="请描述这张图片的关键信息。",
        help="Prompt to send",
    )
    parser.add_argument(
        "-n", "--num-requests",
        type=int,
        default=5,
        help="Number of requests to send (default: 5)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable same-screen cache",
    )
    
    args = parser.parse_args()
    
    # Load image
    print(f"📷 Loading image: {args.image}")
    image = load_image(args.image)
    
    # Create optimized client
    print(f"🔌 Connecting to: {args.server_url}")
    client = QwenVLClient(
        model=args.model,
        base_url=args.server_url,
        enable_screen_cache=not args.no_cache,
    )
    
    try:
        run_benchmark(
            client=client,
            image=image,
            prompt=args.prompt,
            num_requests=args.num_requests,
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Benchmark stopped by user")
    finally:
        client.close()
        print("\n✅ Done")


if __name__ == "__main__":
    main()