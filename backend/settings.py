import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

PROXY_IP = os.getenv("PROXY_IP")
PROXY_PORT = os.getenv("PROXY_PORT")

# --- Load control defaults ---
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30"))

# Queue
QUEUE_WORKERS = int(os.getenv("QUEUE_WORKERS", "1"))     # number of worker threads
QUEUE_MAXSIZE = int(os.getenv("QUEUE_MAXSIZE", "100"))   # max pending requests
QUEUE_TASK_TIMEOUT = float(os.getenv("QUEUE_TASK_TIMEOUT", "90"))  # seconds

# HTTP call behavior
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))

# Retry policy (tenacity)
RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
RETRY_MIN_SECONDS = float(os.getenv("RETRY_MIN_SECONDS", "1"))
RETRY_MAX_SECONDS = float(os.getenv("RETRY_MAX_SECONDS", "8"))

# Circuit breaker
CB_FAIL_THRESHOLD = int(os.getenv("CB_FAIL_THRESHOLD", "5"))   # failures in window
CB_WINDOW_SEC = int(os.getenv("CB_WINDOW_SEC", "60"))          # seconds window
CB_COOLDOWN_SEC = int(os.getenv("CB_COOLDOWN_SEC", "30"))      # seconds open

# Fallback text when service is busy/unavailable
FALLBACK_MESSAGE = os.getenv(
    "FALLBACK_MESSAGE",
    "The service is busy right now. Please try again in a few moments."
)