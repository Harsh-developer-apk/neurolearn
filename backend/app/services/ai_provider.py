import json
import logging
import os
import time
import base64
from io import BytesIO
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


def _nvidia_ocr_data_url(data: bytes, content_type: str) -> str:
    """Keep the NVIDIA OCR data URL within its documented request size."""
    encoded = base64.b64encode(data).decode("ascii")
    if len(encoded) < 165_000:
        return f"data:{content_type};base64,{encoded}"

    from PIL import Image, ImageOps

    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        for scale in (1.0, 0.85, 0.7, 0.55):
            width = max(1, round(image.width * scale))
            height = max(1, round(image.height * scale))
            resized = image.resize((width, height), Image.Resampling.LANCZOS) if scale != 1.0 else image
            for quality in (90, 84, 78, 72):
                output = BytesIO()
                resized.save(output, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(output.getvalue()).decode("ascii")
                if len(encoded) < 165_000:
                    return f"data:image/jpeg;base64,{encoded}"
        raise RuntimeError("The image is too detailed for the NVIDIA OCR fallback. Use a smaller image or paste the syllabus text.")


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


def generate_json(system_prompt: str, user_prompt: str, max_tokens: int = 2200, task: str = "generation",
                  providers: list[str] | None = None, model_overrides: dict[str, str] | None = None,
                  native_gemini: bool = False) -> tuple[str, str, str]:
    errors = []
    provider_order = providers if providers is not None else configured_provider_order()
    for provider in provider_order:
        config = PROVIDER_CONFIG[provider]
        api_key = os.getenv(config["key"])
        model = (model_overrides or {}).get(provider, config["model"])
        if not api_key:
            errors.append(f"{provider} key is not configured")
            logger.warning("ai_request task=%s provider=%s model=%s outcome=missing_key", task, provider, model)
            continue
        token_budget = max_tokens
        for attempt in range(2):
            started = time.perf_counter()
            try:
                use_native_gemini = provider == "gemini" and native_gemini
                if use_native_gemini:
                    request_body = {
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": 0.25,
                            "maxOutputTokens": token_budget,
                            "responseMimeType": "application/json",
                        },
                    }
                    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    headers = {"x-goog-api-key": api_key}
                else:
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
                    endpoint = config["base_url"].rstrip("/") + "/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key}"}
                if provider == "nvidia":
                    # Reserve the output budget for lesson JSON rather than a long reasoning trace.
                    request_body["chat_template_kwargs"] = {"enable_thinking": False}
                if os.getenv("AI_LOG_PROMPTS", "false").strip().lower() in {"1", "true", "yes", "on"}:
                    logger.info("ai_prompt task=%s provider=%s model=%s attempt=%s system=%s user=%s",
                                task, provider, model, attempt + 1, system_prompt, user_prompt)
                response = httpx.post(
                    endpoint,
                    headers=headers,
                    json=request_body,
                    timeout=75.0,
                )
                duration_ms = round((time.perf_counter() - started) * 1000)
                if response.status_code >= 400:
                    logger.warning("ai_request task=%s provider=%s model=%s attempt=%s status=%s duration_ms=%s outcome=http_error",
                                   task, provider, model, attempt + 1, response.status_code, duration_ms)
                response.raise_for_status()
                body = response.json()
                if use_native_gemini:
                    candidate = body.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    content = "\n".join(part.get("text", "") for part in parts if isinstance(part.get("text"), str))
                    finish_reason = "length" if candidate.get("finishReason") == "MAX_TOKENS" else candidate.get("finishReason", "unknown")
                    metadata = body.get("usageMetadata", {})
                    usage = {"prompt_tokens": metadata.get("promptTokenCount"), "completion_tokens": metadata.get("candidatesTokenCount")}
                else:
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


def extract_syllabus_image(data: bytes, content_type: str) -> tuple[str, str, str]:
    """Read image text with retries, Gemini model fallback, then NVIDIA OCR."""
    encoded = base64.b64encode(data).decode("ascii")
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
    last_issue = "provider unavailable"

    # Retry transient Gemini overloads, then try its low-latency fallback model.
    gemini_key = os.getenv(PROVIDER_CONFIG["gemini"]["key"])
    if gemini_key:
        gemini_models = list(dict.fromkeys((
            PROVIDER_CONFIG["gemini"]["model"],
            os.getenv("GEMINI_OCR_FALLBACK_MODEL", "gemini-3.5-flash-lite"),
        )))
        prompt = (
            "Transcribe the readable syllabus text from this image faithfully. Preserve headings, unit names, "
            "topic names, and bullet structure. Do not add or infer missing syllabus topics. Return only the transcribed text."
        )
        request_body = {
            "contents": [{"role": "user", "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": content_type, "data": encoded}},
            ]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 5000},
        }
        for model_index, model in enumerate(gemini_models):
            attempts = 2 if model_index == 0 else 1
            for attempt in range(attempts):
                started = time.perf_counter()
                try:
                    response = httpx.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                        headers={"x-goog-api-key": gemini_key},
                        json=request_body,
                        timeout=90.0,
                    )
                    duration_ms = round((time.perf_counter() - started) * 1000)
                    if response.status_code >= 400:
                        last_issue = f"Gemini HTTP {response.status_code}"
                        logger.warning("ai_request task=syllabus-image-ocr provider=gemini model=%s attempt=%s status=%s duration_ms=%s outcome=http_error",
                                       model, attempt + 1, response.status_code, duration_ms)
                        if response.status_code in retryable_statuses and attempt + 1 < attempts:
                            time.sleep(0.6)
                            continue
                        break
                    body = response.json()
                    parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = "\n".join(part.get("text", "") for part in parts if isinstance(part.get("text"), str))
                    if text.strip():
                        logger.info("ai_request task=syllabus-image-ocr provider=gemini model=%s attempt=%s status=%s duration_ms=%s",
                                    model, attempt + 1, response.status_code, duration_ms)
                        return text.strip(), "gemini", model
                    last_issue = "Gemini returned no readable text"
                    logger.warning("ai_request task=syllabus-image-ocr provider=gemini model=%s attempt=%s outcome=empty_text", model, attempt + 1)
                    break
                except httpx.RequestError as exc:
                    last_issue = f"Gemini connection error ({type(exc).__name__})"
                    logger.warning("ai_request task=syllabus-image-ocr provider=gemini model=%s attempt=%s duration_ms=%s outcome=connection_error exception_type=%s",
                                   model, attempt + 1, round((time.perf_counter() - started) * 1000), type(exc).__name__)
                    if attempt + 1 < attempts:
                        time.sleep(0.6)
                        continue
                    break
    else:
        last_issue = "Gemini key is not configured"
        logger.warning("ai_request task=syllabus-image-ocr provider=gemini outcome=missing_key")

    # Nemotron OCR is a separate NVIDIA vision endpoint; the configured
    # Nemotron Lightning chat model is text-only, so don't send it image data.
    nvidia_key = os.getenv(PROVIDER_CONFIG["nvidia"]["key"])
    if nvidia_key:
        nvidia_data_url = _nvidia_ocr_data_url(data, content_type)
        request_body = {"input": [{"type": "image_url", "url": nvidia_data_url}], "merge_levels": ["paragraph"]}
        for attempt in range(2):
            started = time.perf_counter()
            try:
                response = httpx.post(
                    "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2",
                    headers={"Authorization": f"Bearer {nvidia_key}", "Accept": "application/json"},
                    json=request_body,
                    timeout=90.0,
                )
                duration_ms = round((time.perf_counter() - started) * 1000)
                if response.status_code >= 400:
                    last_issue = f"NVIDIA OCR HTTP {response.status_code}"
                    logger.warning("ai_request task=syllabus-image-ocr provider=nvidia model=nvidia/nemotron-ocr-v2 attempt=%s status=%s duration_ms=%s outcome=http_error",
                                   attempt + 1, response.status_code, duration_ms)
                    if response.status_code in retryable_statuses and attempt == 0:
                        time.sleep(0.7)
                        continue
                    break
                body = response.json()
                detections = [
                    detection.get("text_prediction", {}).get("text", "")
                    for image in body.get("data", [])
                    for detection in image.get("text_detections", [])
                    if isinstance(detection.get("text_prediction", {}).get("text"), str)
                ]
                text = "\n".join(value.strip() for value in detections if value.strip())
                if text:
                    logger.info("ai_request task=syllabus-image-ocr provider=nvidia model=nvidia/nemotron-ocr-v2 attempt=%s status=%s duration_ms=%s",
                                attempt + 1, response.status_code, duration_ms)
                    return text, "nvidia", "nvidia/nemotron-ocr-v2"
                last_issue = "NVIDIA OCR returned no readable text"
                logger.warning("ai_request task=syllabus-image-ocr provider=nvidia model=nvidia/nemotron-ocr-v2 attempt=%s outcome=empty_text", attempt + 1)
                break
            except httpx.RequestError as exc:
                last_issue = f"NVIDIA OCR connection error ({type(exc).__name__})"
                logger.warning("ai_request task=syllabus-image-ocr provider=nvidia model=nvidia/nemotron-ocr-v2 attempt=%s duration_ms=%s outcome=connection_error exception_type=%s",
                               attempt + 1, round((time.perf_counter() - started) * 1000), type(exc).__name__)
                if attempt == 0:
                    time.sleep(0.7)
                    continue
                break
    else:
        logger.warning("ai_request task=syllabus-image-ocr provider=nvidia outcome=missing_key")

    raise RuntimeError(
        "Image text reading is temporarily unavailable. We tried Gemini and NVIDIA OCR. "
        "Please retry, use a text based PDF or DOCX, or paste the syllabus text."
    )
