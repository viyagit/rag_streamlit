import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import List, Dict, Union, Any
from urllib.parse import urljoin

# IMPORTANT: Import core components for queue submission
from backend.task_queue import chat_queue 
from backend.rate_limiter import RATE_LIMIT_MESSAGE # Essential for handling the queue's response
from backend.logger import logger

# NOTE: Assuming these exist in your environment
from backend import settings 
from backend.proxy_config import get_proxy_session 

# --- Internal synchronous retry function (called ONLY by ChatWorker) ---

def _build_azure_url() -> str:
    """Constructs the full Azure OpenAI API endpoint URL."""
    base_url = urljoin(
        settings.AZURE_OPENAI_ENDPOINT,
        f"openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT}/chat/completions"
    )
    return f"{base_url}?api-version={settings.AZURE_OPENAI_API_VERSION}"

def _format_messages(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Formats messages for the specific Azure API payload structure."""
    # Assuming the API expects content wrapped in a 'type: text' object
    return [
        {"role": m["role"], "content": [{"type": "text", "text": m["content"]}]}
        for m in messages
    ]

def _do_azure_call(session: requests.Session, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
    """Performs the actual synchronous HTTP call to the Azure API."""
    url = _build_azure_url()
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_KEY
    }

    payload = {
        "messages": _format_messages(messages),
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    resp = session.post(url, headers=headers, json=payload, timeout=settings.REQUEST_TIMEOUT)

    if resp.status_code == 200:
        data = resp.json()
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        logger.info(
            "TOKENS | prompt={} | completion={} | total={}",
            prompt_tokens, completion_tokens, total_tokens
        )
        
        # Extract the assistant's reply
        return data["choices"][0]["message"]["content"]
    else:
        # Raise HTTPError, allowing tenacity to catch it and retry
        raise requests.HTTPError(f"Azure error {resp.status_code}: {resp.text}")

@retry(
    reraise=True,
    stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=settings.RETRY_MIN_SECONDS, max=settings.RETRY_MAX_SECONDS),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError, requests.HTTPError)) 
)
def _call_with_retry_sync(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
    """
    Synchronous API call with tenacity retry logic. 
    This is called exclusively by the ChatWorker thread.
    """
    session = get_proxy_session()
    return _do_azure_call(session, messages, temperature, max_tokens)


# --- Public interface (called by app.py) ---

def chat_with_azure(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
    """
    Submits a chat request to the global thread-safe queue and waits synchronously for the result.
    The execution, rate limiting, and retries happen in the background worker thread.
    """
    logger.debug(f"Submitting chat request to queue. Message: {messages[-1]['content'][:30]}...")
    
    # The submission blocks until the worker completes the task or the timeout is hit
    response = chat_queue.submit(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    # The response can be the chat reply (str) or RATE_LIMIT_MESSAGE (str)
    return response

__all__ = ["chat_with_azure", "_call_with_retry_sync", "RATE_LIMIT_MESSAGE"]
