"""
Centralized error handling for Spatelier.

This module provides consistent error handling patterns
across all services and modules.
"""

import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from spatelier.core.base import ProcessingResult
from spatelier.core.logger import get_logger


class ErrorHandler:
    """Centralized error handler for consistent error management."""

    def __init__(self, logger_name: str = "ErrorHandler", verbose: bool = False):
        """
        Initialize error handler.

        Args:
            logger_name: Name for logger
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.logger = get_logger(logger_name, verbose=verbose)
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default error handlers."""
        self.error_handlers[FileNotFoundError] = self._handle_file_not_found
        self.error_handlers[PermissionError] = self._handle_permission_error
        self.error_handlers[OSError] = self._handle_os_error
        self.error_handlers[ValueError] = self._handle_value_error
        self.error_handlers[KeyError] = self._handle_key_error
        self.error_handlers[ImportError] = self._handle_import_error

    def handle_error(
        self, error: Exception, context: str = "", return_result: bool = True, **kwargs
    ) -> Optional[ProcessingResult]:
        """
        Handle an error with appropriate response.

        Args:
            error: Exception to handle
            context: Context where error occurred
            return_result: Whether to return ProcessingResult
            **kwargs: Additional context for error handling

        Returns:
            ProcessingResult if return_result=True, None otherwise
        """
        error_type = type(error)

        # Log the error
        self.logger.error(f"Error in {context}: {error}")
        if self.verbose:
            self.logger.debug(f"Error traceback: {traceback.format_exc()}")

        # Get specific handler or use generic handler
        handler = self.error_handlers.get(error_type, self._handle_generic_error)
        result = handler(error, context, **kwargs)

        if return_result:
            return result
        return None

    def _handle_file_not_found(
        self, error: FileNotFoundError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle FileNotFoundError."""
        file_path = getattr(error, "filename", "unknown file")
        return ProcessingResult.error_result(
            message=f"File not found: {file_path}",
            errors=[f"FileNotFoundError in {context}: {str(error)}"],
        )

    def _handle_permission_error(
        self, error: PermissionError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle PermissionError."""
        return ProcessingResult.error_result(
            message="Permission denied",
            errors=[f"PermissionError in {context}: {str(error)}"],
        )

    def _handle_os_error(
        self, error: OSError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle OSError."""
        return ProcessingResult.error_result(
            message=f"System error: {error.strerror}",
            errors=[f"OSError in {context}: {str(error)}"],
        )

    def _handle_value_error(
        self, error: ValueError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle ValueError."""
        return ProcessingResult.error_result(
            message=f"Invalid value: {str(error)}",
            errors=[f"ValueError in {context}: {str(error)}"],
        )

    def _handle_key_error(
        self, error: KeyError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle KeyError."""
        key = str(error).strip("'\"")
        return ProcessingResult.error_result(
            message=f"Missing key: {key}",
            errors=[f"KeyError in {context}: Missing key '{key}'"],
        )

    def _handle_import_error(
        self, error: ImportError, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle ImportError."""
        module = getattr(error, "name", "unknown module")
        return ProcessingResult.error_result(
            message=f"Import error: {module}",
            errors=[f"ImportError in {context}: Cannot import {module}"],
        )

    def _handle_generic_error(
        self, error: Exception, context: str, **kwargs
    ) -> ProcessingResult:
        """Handle generic errors."""
        return ProcessingResult.error_result(
            message=f"Unexpected error: {type(error).__name__}",
            errors=[f"{type(error).__name__} in {context}: {str(error)}"],
        )

    def register_handler(
        self, exception_type: Type[Exception], handler: Callable[..., ProcessingResult]
    ) -> None:
        """Register a custom error handler."""
        self.error_handlers[exception_type] = handler

    def safe_execute(
        self,
        func: Callable[..., Any],
        context: str = "",
        default_result: Optional[ProcessingResult] = None,
        *args: Any,
        **kwargs: Any,
    ) -> ProcessingResult:
        """
        Safely execute a function with error handling.

        Args:
            func: Function to execute
            context: Context for error reporting
            default_result: Default result if function fails
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            ProcessingResult from function or error result
        """
        try:
            result = func(*args, **kwargs)
            if isinstance(result, ProcessingResult):
                return result
            else:
                return ProcessingResult.success_result(
                    message="Operation completed successfully",
                    metadata={"result": result},
                )
        except Exception as e:
            error_result = self.handle_error(e, context, return_result=True)
            if default_result:
                return default_result
            return error_result or ProcessingResult.error_result(
                message="Operation failed", errors=[f"Unexpected error in {context}"]
            )


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler(verbose: bool = False) -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(verbose=verbose)
    return _error_handler


def handle_error(
    error: Exception, context: str = "", verbose: bool = False, **kwargs
) -> ProcessingResult:
    """Convenience function for handling errors."""
    handler = get_error_handler(verbose=verbose)
    return handler.handle_error(error, context, **kwargs)


def safe_execute(
    func: Callable[..., Any],
    context: str = "",
    verbose: bool = False,
    default_result: Optional[ProcessingResult] = None,
    *args: Any,
    **kwargs: Any,
) -> ProcessingResult:
    """Convenience function for safe execution."""
    handler = get_error_handler(verbose=verbose)
    return handler.safe_execute(func, context, default_result, *args, **kwargs)
