import logging
import os
from pathlib import Path


class AccessLogFilter(logging.Filter):
    """Filter to suppress noisy access logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Get the formatted log message
        msg = record.getMessage()
        # Suppress logs for segments and images under projects as requested
        # Example: GET /projects/.../segments or GET /projects/.../images/...
        if "/projects/" in msg and ("/segments" in msg or "/images/" in msg):
            return False
        return True

def setup_logging(level: int = logging.INFO) -> None:
    """Configure application logging."""
    # Ensure logs directory exists
    log_file = Path("logs/app.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Filter uvicorn access logs to remove noise
    logging.getLogger("uvicorn.access").addFilter(AccessLogFilter())


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
