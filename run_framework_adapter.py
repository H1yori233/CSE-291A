"""
Runner that plugs the framework's Qwen-based agent into OSWorld without
modifying existing benchmark code. Run from the OSWorld directory:

    uv run python run_framework_adapter.py \
        --base-url http://194.68.245.40:22093/v1/chat/completions \
        --model Qwen/Qwen3-VL-8B-Instruct-FP8 \
        --domain onboard
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List

from desktop_env.desktop_env import DesktopEnv
import lib_run_single

# Make the sibling `framework` package importable (need the parent dir of the package)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from framework.core.agent import AgentConfig
from framework.osworld_adapter import build_adapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run OSWorld benchmark with the framework agent")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument("--api-key", type=str, default="EMPTY")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=700)

    parser.add_argument("--provider_name", type=str, default="docker")
    parser.add_argument("--path_to_vm", type=str, default=None)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--sleep_after_execution", type=float, default=1.0)
    parser.add_argument("--max_steps", type=int, default=15)
    parser.add_argument("--action_space", type=str, default="computer_13")
    parser.add_argument("--observation_type", type=str, default="screenshot")
    parser.add_argument("--test_all_meta_path", type=str, default="evaluation_examples/test_all.json")
    parser.add_argument("--result_dir", type=str, default="./results_framework")
    parser.add_argument("--domain", type=str, default="all")
    parser.add_argument("--client_password", type=str, default="")
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    parser.add_argument("--region", type=str, default="us-east-1")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of examples per domain")
    return parser


def load_examples(meta_path: str, domain_filter: str, logger: logging.Logger) -> Dict[str, List[str]]:
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if domain_filter != "all":
        if domain_filter not in meta:
            available = ", ".join(sorted(meta.keys()))
            fallback = sorted(meta.keys())[0] if meta else None
            logger.warning(
                "Domain %s not found in %s. Falling back to %s. Available: %s",
                domain_filter,
                meta_path,
                fallback,
                available,
            )
            if not fallback:
                raise ValueError("No domains found in meta file")
            meta = {fallback: meta[fallback]}
        else:
            meta = {domain_filter: meta[domain_filter]}
    return meta


def build_env(args: argparse.Namespace) -> DesktopEnv:
    require_a11y_tree = args.observation_type in ["a11y_tree", "screenshot_a11y_tree", "som"]
    return DesktopEnv(
        path_to_vm=args.path_to_vm,
        action_space=args.action_space,
        provider_name=args.provider_name,
        region=args.region,
        snapshot_name=None,
        screen_size=(args.screen_width, args.screen_height),
        headless=args.headless,
        os_type="Ubuntu",
        require_a11y_tree=require_a11y_tree,
        enable_proxy=True,
        client_password=args.client_password,
    )


def main():
    args = build_parser().parse_args()

    os.makedirs(args.result_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger("framework.runner")
    logger.info("Using model %s at %s", args.model, args.base_url)

    agent_cfg = AgentConfig(
        max_steps=args.max_steps,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    agent = build_adapter(
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        agent_config=agent_cfg,
    )

    examples = load_examples(args.test_all_meta_path, args.domain, logger)
    env = build_env(args)

    scores: List[float] = []
    try:
        for domain, ids in examples.items():
            if args.limit:
                ids = ids[: args.limit]
            for example_id in ids:
                config_path = os.path.join(
                    args.test_all_meta_path.rsplit("/", 1)[0],
                    "examples",
                    domain,
                    f"{example_id}.json",
                )
                with open(config_path, "r", encoding="utf-8") as f:
                    example = json.load(f)

                example_result_dir = os.path.join(
                    args.result_dir,
                    args.action_space,
                    args.observation_type,
                    args.model,
                    domain,
                    example_id,
                )
                os.makedirs(example_result_dir, exist_ok=True)

                logger.info("Running %s/%s", domain, example_id)
                try:
                    lib_run_single.run_single_example(
                        agent,
                        env,
                        example,
                        args.max_steps,
                        example["instruction"],
                        args,
                        example_result_dir,
                        scores,
                    )
                except Exception as exc:  # keep env alive for next task
                    logger.exception("Failed on %s/%s: %s", domain, example_id, exc)
    finally:
        try:
            env.close()
        except Exception:
            logger.warning("Environment close raised, ignoring.")

    if scores:
        avg = sum(scores) / len(scores)
        logger.info("Average score across %d tasks: %.3f", len(scores), avg)
    else:
        logger.info("No scores recorded.")


if __name__ == "__main__":
    main()

