import os
from loguru import logger

def _resolve_logs_dir() -> str:
    # Prefer explicit env (works for exe too). Fallback: ./logs relative to CWD
    # base = os.getenv("LOG_DIR") or os.path.join(os.getcwd(), "logs")
    base = os.getenv("LOG_DIR") or os.path.join(os.path.dirname(os.getcwd()), "logs")
    os.makedirs(base, exist_ok=True)
    return base

LOG_DIR = _resolve_logs_dir()
APP_LOG = os.path.join(LOG_DIR, "chatbot.log")
ERR_LOG = os.path.join(LOG_DIR, "errors.log")
TOKEN_LOG = os.path.join(LOG_DIR, "tokens.log")
IP_LOG = os.path.join(LOG_DIR, "ip_address.log")
# Remove default sink to avoid duplicate logs in PyInstaller console
logger.remove()

# App flow & chat transcripts
logger.add(APP_LOG, rotation="10 MB", retention="10 days", enqueue=True, level="INFO", backtrace=False, diagnose=False)
# Errors with stacktraces
logger.add(ERR_LOG, rotation="10 MB", retention="30 days", enqueue=True, level="ERROR", backtrace=True, diagnose=False)
logger.add(TOKEN_LOG, rotation="1 day", retention="30 days", format="{time} {message}", level="INFO")
logger.add(IP_LOG,rotation=1,retention="30 days",format="{time}")

# Optional: also echo important info to console when running in dev
if os.getenv("LOG_TO_CONSOLE", "false").lower() == "true":
    logger.add(lambda msg: print(msg, end=""), level="INFO")

__all__ = ["logger", "LOG_DIR", "APP_LOG", "ERR_LOG", "TOKEN_LOG","IP_LOG"]
