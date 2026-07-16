#!/usr/bin/env python3
"""Send one small LLM request without starting the FastAPI server."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.llm import LLM_CLIENT  # noqa: E402


def main() -> int:
    status = LLM_CLIENT.status()
    print("Agent Town LLM connection check")
    print("===============================")
    print(f"Provider: {status['provider']}")
    print(f"Model: {status['model']}")
    print(f"Enabled: {status['enabled']}")
    print(f"Configured: {status['configured']}")

    if not status["enabled"]:
        print("[FAIL] Set ENABLE_LLM=true in backend/.env.")
        return 1
    if status["provider"] == "mock":
        print("[FAIL] Select a real provider in backend/.env.")
        return 1
    if not status["configured"]:
        print("[FAIL] Add your API key to LLM_API_KEY in backend/.env.")
        return 1

    result = LLM_CLIENT.generate_json_text(
        system_prompt=(
            "你是 Agent Town 的连接测试助手。"
            "只返回 JSON 对象，格式为 {\"text\": \"连接成功后的简短中文问候\"}。"
        ),
        context={"task": "connection_check", "language": "zh-CN"},
        fallback_text="连接测试未获得有效的 LLM 响应。",
    )
    if not result.used_llm:
        print(f"[FAIL] {result.fallback_reason}")
        return 1

    print(f"[OK] {status['provider']} returned: {result.text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
