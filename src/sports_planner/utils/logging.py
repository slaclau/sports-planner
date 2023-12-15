import logging
import time
from functools import wraps

DEBUG_TIME = False


def logtime(start, action):
    if DEBUG_TIME:
        print(f"{action} took {time.time() - start} seconds")


def info_time(func):
    logger = logging.getLogger("timing." + func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"Function {func.__name__}{args} {kwargs} took {elapsed} seconds")
        return result
    return wrapper

def debug_time(func):
    logger = logging.getLogger("timing." + func.__module__)
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"Function {func.__name__}{args} {kwargs} took {elapsed} seconds")
        return result
    return wrapper
