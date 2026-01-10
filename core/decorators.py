"""
Decorators for Spatelier modules.

This module provides decorators for common patterns like
error handling, timing, and validation.
"""

import time
import functools
from typing import Callable, Any, Optional, Union
from pathlib import Path

from core.base import ProcessingResult
from core.error_handler import get_error_handler


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"


def handle_errors(
    context: str = "",
    return_result: bool = True,
    verbose: bool = False
):
    """
    Decorator for automatic error handling.
    
    Args:
        context: Context for error reporting
        return_result: Whether to return ProcessingResult on error
        verbose: Enable verbose logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[Any, ProcessingResult]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler(verbose=verbose)
                error_result = handler.handle_error(e, context, return_result=return_result)
                if return_result:
                    return error_result
                raise
        return wrapper
    return decorator


def time_operation(verbose: bool = False):
    """
    Decorator for timing operations.
    
    Args:
        verbose: Enable verbose logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if verbose:
                    print(f"{func.__name__} completed in {format_duration(duration)}")
                
                # Add timing to result if it's a ProcessingResult
                if isinstance(result, ProcessingResult):
                    result.duration_seconds = duration
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                if verbose:
                    print(f"{func.__name__} failed after {format_duration(duration)}: {e}")
                raise
        return wrapper
    return decorator


def validate_input(
    input_validator: Optional[Callable] = None,
    output_validator: Optional[Callable] = None
):
    """
    Decorator for input/output validation.
    
    Args:
        input_validator: Function to validate inputs
        output_validator: Function to validate outputs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Validate inputs
            if input_validator:
                try:
                    input_validator(*args, **kwargs)
                except Exception as e:
                    raise ValueError(f"Input validation failed: {e}")
            
            result = func(*args, **kwargs)
            
            # Validate outputs
            if output_validator:
                try:
                    output_validator(result)
                except Exception as e:
                    raise ValueError(f"Output validation failed: {e}")
            
            return result
        return wrapper
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying operations on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        raise last_exception
            
            return None  # Should never reach here
        return wrapper
    return decorator


def log_operation(
    level: str = "INFO",
    include_args: bool = False,
    include_result: bool = False
):
    """
    Decorator for logging operations.
    
    Args:
        level: Log level
        include_args: Whether to include function arguments in log
        include_result: Whether to include result in log
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from core.logger import get_logger
            logger = get_logger(func.__module__)
            
            # Log function start
            log_msg = f"Starting {func.__name__}"
            if include_args:
                log_msg += f" with args={args}, kwargs={kwargs}"
            
            if level.upper() == "DEBUG":
                logger.debug(log_msg)
            elif level.upper() == "INFO":
                logger.info(log_msg)
            elif level.upper() == "WARNING":
                logger.warning(log_msg)
            elif level.upper() == "ERROR":
                logger.error(log_msg)
            
            try:
                result = func(*args, **kwargs)
                
                # Log function completion
                log_msg = f"Completed {func.__name__}"
                if include_result:
                    log_msg += f" with result={result}"
                
                if level.upper() == "DEBUG":
                    logger.debug(log_msg)
                elif level.upper() == "INFO":
                    logger.info(log_msg)
                elif level.upper() == "WARNING":
                    logger.warning(log_msg)
                elif level.upper() == "ERROR":
                    logger.error(log_msg)
                
                return result
            except Exception as e:
                logger.error(f"Failed {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


def ensure_path_exists(path_arg: str = "path"):
    """
    Decorator to ensure a path argument exists.
    
    Args:
        path_arg: Name of the path argument to validate
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get the path argument
            if path_arg in kwargs:
                path = kwargs[path_arg]
            else:
                # Try to get from positional args (this is a simplified approach)
                path = args[0] if args else None
            
            if path:
                path_obj = Path(path)
                if not path_obj.exists():
                    raise FileNotFoundError(f"Path does not exist: {path}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
