import logging.handlers
from pathlib import Path
import logging
import asyncio
import os
from datetime import datetime
import inspect
from typing import Callable, Any, Optional
import functools
import time


# Get current date
current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d")
# Get the directory of the current script
script_dir = Path(__file__).resolve().parent


def setup_logger_simple():
    # for check in cloud
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger


def setup_logger(module_name=None):
    if module_name is None:
        # Get the calling module's name
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        module_name = module.__name__
        # If it's '__main__', get the filename without extension
        if module_name == '__main__' and hasattr(module, '__file__'):
            module_name = os.path.splitext(os.path.basename(module.__file__))[0]

    # Create logger
    logger = logging.getLogger(module_name)

    # Clear any existing handlers to avoid duplication
    if logger.handlers:
        logger.handlers = []

    # Set log level
    logger.setLevel(logging.DEBUG)

    # Create a formatter that will work well with CloudWatch
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create console handler (this works with CloudWatch in Lambda)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger



