import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger("neurolearn.ai")
logger.setLevel(logging.INFO)
log_directory = Path(__file__).resolve().parents[2] / "logs"
log_directory.mkdir(exist_ok=True)
log_file = log_directory / "neurolearn-ai.log"
if not any(getattr(handler, "baseFilename", None) == str(log_file) for handler in logger.handlers):
    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)

PROVIDER_CONFIG = {
    "nvidia": {
        "key": "NVIDIA_API_KEY",
        "model": os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"),
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    "gemini": {
        "key": "GEMINI_API_KEY",
        "model": os.getenv("GEMINI_MODEL", "gemini-4-hydrogen"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
}


def configured_provider_order() -> list[str]:
    primary = os.getenv("AI_PRIMARY_PROVIDER", "nvidia").strip().lower()
    fallback = os.getenv("AI_FALLBACK_PROVIDER", "gemini").strip().lower()
    order = [provider for provider in (primary, fallback) if provider in PROVIDER_CONFIG]
    return list(dict.fromkeys(order))


def configured_models() -> list[dict]:
    return [
        {"provider": provider, "model": PROVIDER_CONFIG[provider]["model"], "key_configured": bool(os.getenv(PROVIDER_CONFIG[provider]["key"]))}
        for provider in configured_provider_order()
    ]


def generate_json(system_prompt: str, user_prompt: str, max_tokens: int = 2200, task: str = "generation") -> tuple[str, str, str]:
    errors = []
    for provider in configured_provider_order():
        config = PROVIDER_CONFIG[provider]
        api_key = os.getenv(config["key"])
        model = config["model"]
        if not api_key:
            errors.append(f"{provider} key is not configured")
            logger.warning("ai_request task=%s provider=%s model=%s outcome=missing_key", task, provider, model)
            continue
        token_budget = max_tokens
        for attempt in range(2):
            started = time.perf_counter()
            try:
                request_body = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.35,
                    "max_tokens": token_budget,
                    "response_format": {"type": "json_object"},
                }
                if provider == "nvidia":
                    # Reserve the output budget for lesson JSON rather than a long reasoning trace.
                    request_body["chat_template_kwargs"] = {"enable_thinking": False}
                if os.getenv("AI_LOG_PROMPTS", "false").strip().lower() in {"1", "true", "yes", "on"}:
                    logger.info("ai_prompt task=%s provider=%s model=%s attempt=%s system=%s user=%s",
                                task, provider, model, attempt + 1, system_prompt, user_prompt)
                response = httpx.post(
                    config["base_url"].rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=request_body,
                    timeout=75.0,
                )
                duration_ms = round((time.perf_counter() - started) * 1000)
                if response.status_code >= 400:
                    logger.warning("ai_request task=%s provider=%s model=%s attempt=%s status=%s duration_ms=%s outcome=http_error",
                                   task, provider, model, attempt + 1, response.status_code, duration_ms)
                response.raise_for_status()
                body = response.json()
                choice = body.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content")
                finish_reason = choice.get("finish_reason", "unknown")
                usage = body.get("usage", {})
                logger.info("ai_request task=%s provider=%s model=%s attempt=%s status=%s duration_ms=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s",
                            task, provider, model, attempt + 1, response.status_code, duration_ms, finish_reason,
                            usage.get("prompt_tokens", "unknown"), usage.get("completion_tokens", "unknown"))
                if finish_reason == "length" and attempt == 0:
                    token_budget = min(max(token_budget * 2, 5200), 8192)
                    logger.warning("ai_output_truncated task=%s provider=%s model=%s retry_max_tokens=%s", task, provider, model, token_budget)
                    continue
                if content:
                    return content, provider, model
                errors.append(f"{provider} returned an empty response")
                break
            except Exception as exc:
                # Never expose the exception text; provider errors can include request details.
                errors.append(f"{provider} request failed ({type(exc).__name__})")
                cause = exc.__cause__
                target_host = urlparse(config["base_url"]).hostname
                cause_errno = getattr(cause, "errno", None)
                proxy_configured = any(os.getenv(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"))
                logger.warning("ai_request task=%s provider=%s model=%s attempt=%s duration_ms=%s outcome=exception exception_type=%s target_host=%s cause_type=%s cause_errno=%s proxy_configured=%s",
                               task, provider, model, attempt + 1, round((time.perf_counter() - started) * 1000),
                               type(exc).__name__, target_host, type(cause).__name__ if cause else "unknown",
                               cause_errno if cause_errno is not None else "unknown", proxy_configured)
                if attempt == 0 and isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
                    time.sleep(0.5)
                    continue
                break
    raise RuntimeError("AI providers unavailable: " + "; ".join(errors))
