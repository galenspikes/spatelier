"""
Base classes for Spatelier modules.

This module provides base classes that all processing modules should inherit from.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from core.config import Config
from core.logger import get_logger


class ProcessingResult(BaseModel):
    """Base class for processing results with enhanced error handling."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message about the operation")
    output_path: Optional[Path] = Field(default=None, description="Path to output file")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of warnings encountered"
    )
    temp_dir: Optional[Path] = Field(
        default=None, description="Temporary directory used for processing"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Processing duration in seconds"
    )

    @classmethod
    def success_result(
        cls,
        message: str,
        output_path: Optional[Union[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "ProcessingResult":
        """Create a successful processing result."""
        return cls(
            success=True,
            message=message,
            output_path=Path(output_path) if output_path else None,
            metadata=metadata or {},
            warnings=warnings or [],
        )

    @classmethod
    def error_result(
        cls,
        message: str,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> "ProcessingResult":
        """Create an error processing result."""
        return cls(
            success=False, message=message, errors=errors or [], warnings=warnings or []
        )

    @classmethod
    def warning_result(
        cls,
        message: str,
        warnings: List[str],
        output_path: Optional[Union[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ProcessingResult":
        """Create a result with warnings but still successful."""
        return cls(
            success=True,
            message=message,
            output_path=Path(output_path) if output_path else None,
            metadata=metadata or {},
            warnings=warnings,
        )

    def add_error(self, error: str):
        """Add an error to the result."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str):
        """Add a warning to the result."""
        self.warnings.append(warning)

    def add_metadata(self, key: str, value: Any):
        """Add metadata to the result."""
        self.metadata[key] = value

    def has_errors(self) -> bool:
        """Check if result has errors."""
        return bool(self.errors)

    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return bool(self.warnings)

    def is_successful(self) -> bool:
        """Check if result is successful (no errors)."""
        return self.success and not self.has_errors()

    def get_summary(self) -> str:
        """Get a summary of the result."""
        summary = f"Success: {self.success}, Message: {self.message}"
        if self.has_errors():
            summary += f", Errors: {len(self.errors)}"
        if self.has_warnings():
            summary += f", Warnings: {len(self.warnings)}"
        if self.duration_seconds:
            summary += f", Duration: {self.duration_seconds:.2f}s"
        return summary


class BaseProcessor(ABC):
    """
    Base class for all processors.

    This class provides common functionality that all processors should have,
    including configuration management, logging, and error handling.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """
        Initialize the processor.

        Args:
            config: Configuration instance
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.logger = get_logger(self.__class__.__name__, verbose=verbose)

    @abstractmethod
    def process(self, input_path: Union[str, Path], **kwargs) -> ProcessingResult:
        """
        Process the input and return a result.

        Args:
            input_path: Path to input file
            **kwargs: Additional processing options

        Returns:
            ProcessingResult with operation details
        """
        pass

    def validate_input(self, input_path: Union[str, Path]) -> bool:
        """
        Validate that the input file exists and is accessible.

        Args:
            input_path: Path to input file

        Returns:
            True if valid, False otherwise
        """
        path = Path(input_path)

        if not path.exists():
            self.logger.error(f"Input file does not exist: {path}")
            return False

        if not path.is_file():
            self.logger.error(f"Input path is not a file: {path}")
            return False

        return True

    def ensure_output_dir(self, output_path: Union[str, Path]) -> bool:
        """
        Ensure the output directory exists.

        Args:
            output_path: Path to output file

        Returns:
            True if directory exists or was created, False otherwise
        """
        output_dir = Path(output_path).parent

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create output directory {output_dir}: {e}")
            return False


class BaseDownloader(BaseProcessor):
    """
    Base class for download processors.

    Extends BaseProcessor with download-specific functionality.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """Initialize the downloader."""
        super().__init__(config, verbose)
        self.supported_sites = []

    @abstractmethod
    def download(
        self, url: str, output_path: Optional[Union[str, Path]] = None, **kwargs
    ) -> ProcessingResult:
        """
        Download content from URL.

        Args:
            url: URL to download from
            output_path: Optional output path
            **kwargs: Additional download options

        Returns:
            ProcessingResult with download details
        """
        pass

    def process(self, input_data: Any, **kwargs) -> ProcessingResult:
        """Process method implementation for downloaders."""
        if isinstance(input_data, str):
            return self.download(input_data, **kwargs)
        else:
            raise ValueError("Downloaders expect URL strings as input")

    def is_supported(self, url: str) -> bool:
        """
        Check if the URL is supported by this downloader.

        Args:
            url: URL to check

        Returns:
            True if supported, False otherwise
        """
        # Basic implementation - subclasses should override
        return any(site in url.lower() for site in self.supported_sites)


class BaseConverter(BaseProcessor):
    """
    Base class for format converters.

    Extends BaseProcessor with conversion-specific functionality.
    """

    def __init__(self, config: Config, verbose: bool = False):
        """Initialize the converter."""
        super().__init__(config, verbose)
        self.supported_input_formats = []
        self.supported_output_formats = []

    @abstractmethod
    def convert(
        self, input_path: Union[str, Path], output_path: Union[str, Path], **kwargs
    ) -> ProcessingResult:
        """
        Convert file from one format to another.

        Args:
            input_path: Path to input file
            output_path: Path to output file
            **kwargs: Additional conversion options

        Returns:
            ProcessingResult with conversion details
        """
        pass

    def process(self, input_path: Union[str, Path], **kwargs) -> ProcessingResult:
        """Process method implementation for converters."""
        output_path = kwargs.pop("output_path", None)
        if not output_path:
            raise ValueError("Converters require output_path in kwargs")
        return self.convert(input_path, output_path, **kwargs)

    def is_supported_format(
        self, file_path: Union[str, Path], is_input: bool = True
    ) -> bool:
        """
        Check if the file format is supported.

        Args:
            file_path: Path to file
            is_input: Whether this is an input file (True) or output file (False)

        Returns:
            True if format is supported, False otherwise
        """
        suffix = Path(file_path).suffix.lower().lstrip(".")

        if is_input:
            return suffix in self.supported_input_formats
        else:
            return suffix in self.supported_output_formats
