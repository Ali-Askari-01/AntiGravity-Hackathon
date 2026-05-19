import os
import json
import logging
from pathlib import Path
from typing import Optional, List

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENROUTER_MODELS = [
    os.getenv("OPENROUTER_MODEL", ""),
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct:free",
]
OPENROUTER_MODELS = [m for m in OPENROUTER_MODELS if m]

_gemini_client = None
_gemini_available = bool(GEMINI_API_KEY)
_openrouter_available = bool(OPENROUTER_API_KEY)


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("LLM Client: Gemini initialized successfully")
        return _gemini_client
    except Exception as e:
        logger.warning(f"LLM Client: Gemini init failed: {e}")
        return None


def _call_openrouter(prompt: str, model: Optional[str] = None) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return None
    import requests
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://xidmat.ai",
        "X-Title": "XIDMAT.AI",
    }

    models_to_try = [model] if model else OPENROUTER_MODELS

    for m in models_to_try:
        if not m:
            continue
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                logger.warning(f"LLM Client: OpenRouter model {m} rate-limited, trying next...")
                continue
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "").strip()
                if text:
                    logger.info(f"LLM Client: OpenRouter call succeeded with model {m}")
                    return text
            logger.warning(f"LLM Client: OpenRouter model {m} returned empty response")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"LLM Client: OpenRouter model {m} HTTP error: {e}")
            continue
        except Exception as e:
            logger.warning(f"LLM Client: OpenRouter model {m} failed: {e}")
            continue
    return None


def _call_gemini(prompt: str, model: Optional[str] = None) -> Optional[str]:
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        response = client.models.generate_content(
            model=model or GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        if text:
            logger.info("LLM Client: Gemini call succeeded")
            return text
        return None
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            logger.warning("LLM Client: Gemini quota exhausted, will fallback to OpenRouter")
        else:
            logger.warning(f"LLM Client: Gemini call failed: {e}")
        return None


def call_llm(prompt: str, model: Optional[str] = None, prefer: str = "auto") -> Optional[str]:
    if prefer == "openrouter":
        result = _call_openrouter(prompt, model)
        if result:
            return result
        result = _call_gemini(prompt, model)
        if result:
            return result
    elif prefer == "gemini":
        result = _call_gemini(prompt, model)
        if result:
            return result
        result = _call_openrouter(prompt, model)
        if result:
            return result
    else:
        result = _call_gemini(prompt, model)
        if result:
            return result
        result = _call_openrouter(prompt, model)
        if result:
            return result
    logger.error("LLM Client: All LLM providers failed")
    return None


def call_llm_json(prompt: str, model: Optional[str] = None, prefer: str = "auto") -> Optional[dict]:
    raw = call_llm(prompt, model=model, prefer=prefer)
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"LLM Client: JSON parse failed: {e}\nRaw: {text[:200]}")
        return None