# src/logger_config.py
import logging
from logging.handlers import RotatingFileHandler
import sys
from src.config import LOGS_DIR

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO

# --- Handlers ---
# A handler for streaming logs to the console
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(LOG_LEVEL)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

def setup_logger(name: str, log_file: str):
    """
    Sets up a logger that logs to both a file and the console.
    The file handler will rotate, keeping the log files from growing indefinitely.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Prevent adding handlers multiple times in interactive environments
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- File Handler (with rotation) ---
    # This handler writes to a file, creating a new file when the
    # current one reaches a certain size.
    log_path = LOGS_DIR / log_file
    
    # maxBytes=1048576 (1MB), backupCount=3 -> keeps main log + 3 backups
    file_handler = RotatingFileHandler(
        log_path, maxBytes=1 * 1024 * 1024, backupCount=3, mode='w' # mode='w' ensures it starts fresh on each run
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

# --- Create and provide loggers for each major component ---
# Other modules will import these specific loggers.
api_logger = setup_logger("api_server", "api.log")
worker_logger = setup_logger("main_worker", "worker.log")
watcher_logger = setup_logger("query_watcher", "watcher.log")