import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
):
    """
    Configure root logging once for the whole app.
    Shows: timestamp, level, process, module:function:line, message
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    fmt = (
        "%(asctime)s | %(levelname)s | pid=%(process)d | "
        "%(name)s.%(funcName)s:%(lineno)d | %(message)s"
    )
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = []

    # Console handler (stdout)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(console)

    # Optional rotating file handler
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
        handlers.append(file_handler)

    # Reset root handlers (avoid duplicate logs on re-run)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)
    for h in handlers:
        root.addHandler(h)

    # Optional: quieter third-party libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
