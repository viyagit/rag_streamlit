# backend/task_queue.py

import threading
import queue
import traceback
from typing import Any, Dict, List, Callable, Optional, TypedDict
from backend.logger import logger
from backend import settings
from backend.rate_limiter import global_rate_limiter, RATE_LIMIT_MESSAGE

# ----------------- CHANGE 1: REMOVE THIS LINE -----------------
# from backend.azure_client import _call_with_retry_sync  <-- DELETE THIS

# Define a more specific type for the task
class Task(TypedDict):
    messages: List[Dict[str, str]]
    temperature: float
    max_tokens: int
    resolve: Callable[[Any], None]
    reject: Callable[[Exception], None]


class ChatWorker(threading.Thread):
    daemon = True

    def __init__(self, q: "queue.Queue[Task]"):
        super().__init__(name="chat-worker")
        self.q = q

    def run(self):
        # ----------------- FIX THE TYPO HERE -----------------
        # The correct name is _call_with_retry_sync
        from backend.azure_client import _call_with_retry_sync

        while True:
            task: Task = self.q.get()
            try:
                if not global_rate_limiter.allow():
                    logger.warning("Rate limit exceeded; returning friendly message.")
                    task["resolve"](RATE_LIMIT_MESSAGE)
                    continue

                messages = task["messages"]
                temperature = task["temperature"]
                max_tokens = task["max_tokens"]
                
                # --- AND FIX THE FUNCTION CALL HERE ---
                # Use the correct name when calling the function
                reply = _call_with_retry_sync(messages, temperature, max_tokens)
                
                logger.info(
                    "Chat success | prompt={} | response={}", 
                    messages[-1]["content"], 
                    reply[:50] + "..." if len(reply) > 50 else reply
                )
                task["resolve"](reply)
            except Exception as e:
                logger.error("Chat failure: {} \n{}", e, traceback.format_exc())
                task["reject"](e)
            finally:
                self.q.task_done()

class ChatQueue:
    def __init__(self, num_workers: int = 1):
        self.q: "queue.Queue[Task]" = queue.Queue(maxsize=settings.QUEUE_MAXSIZE)
        self.workers = [ChatWorker(self.q) for _ in range(max(num_workers, 1))]
        for w in self.workers:
            w.start()

    def submit(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int, timeout: Optional[float] = None) -> str:
        """
        Synchronous helper: enqueue request and wait for result.
        Now accepts temperature and max_tokens.
        """
        result_holder: Dict[str, Any] = {}
        done = threading.Event()

        def resolve(value: Any):
            result_holder["value"] = value
            done.set()

        def reject(exc: Exception):
            result_holder["error"] = exc
            done.set()

        # Build the task dictionary with all necessary parameters
        task: Task = {
            "messages": messages, 
            "temperature": temperature, 
            "max_tokens": max_tokens, 
            "resolve": resolve, 
            "reject": reject
        }

        self.q.put(task)
        ok = done.wait(timeout or settings.QUEUE_TASK_TIMEOUT)
        
        if not ok:
            # If the request is still in the queue when the timeout hits, 
            # we can't easily remove it, but we can tell the client it failed.
            raise TimeoutError("Request timed out waiting for result from queue worker.")
        
        if "error" in result_holder:
            raise result_holder["error"]
            
        return result_holder.get("value")

# Global singleton
chat_queue = ChatQueue(num_workers=settings.QUEUE_WORKERS)

__all__ = ["chat_queue"]
