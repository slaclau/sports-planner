import logging
import time
import typing
from functools import wraps
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def log_debug_time(start: float, action: str) -> float:
    end = time.time()
    logger.debug(f"{action} took {end - start} seconds")
    return end

F = typing.TypeVar("F", bound=typing.Callable[..., typing.Any])  # type: ignore


def info_time(func: F) -> F:  # type: ignore
    logger = logging.getLogger("timing." + func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"Function {func.__name__}{args} {kwargs} took {elapsed} seconds")
        return result

    return typing.cast(F, wrapper)  # type: ignore


def debug_time(func: F) -> F:  # type: ignore
    logger = logging.getLogger("timing." + func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.debug(f"Function {func.__name__}{args} {kwargs} took {elapsed} seconds")
        return result

    return typing.cast(F, wrapper)  # type: ignore
