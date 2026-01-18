"""
Configuration management for Spatelier.

This module handles all configuration loading, validation, and management.
Simplified to reduce unnecessary nesting while maintaining essential structure.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


def _find_repo_root() -> Optional[Path]:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def get_default_data_dir() -> Path:
    env_dir = os.getenv("SPATELIER_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    repo_root = _find_repo_root()
    if repo_root:
        return repo_root / ".data"
    return Path.home() / ".config" / "spatelier"


class VideoConfig(BaseModel):
    """Video processing configuration."""

    default_format: str = "mp4"
    quality: str = "best"
    output_dir: Optional[Path] = None
    temp_dir: Path = Field(
        default_factory=lambda: get_default_data_dir() / "tmp" / "video"
    )

    @field_validator("default_format")
    @classmethod
    def validate_format(cls, v):
        """Validate video format."""
        valid_formats = ["mp4", "mkv", "webm", "avi", "mov", "m4v", "flv"]
        if v.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format '{v}'. Must be one of: {', '.join(valid_formats)}"
            )
        return v.lower()

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v):
        """Validate video quality."""
        valid_qualities = ["best", "worst", "720p", "1080p", "480p", "360p", "240p"]
        if v.lower() not in valid_qualities and not v.isdigit():
            raise ValueError(
                f"Invalid quality '{v}'. Must be one of: {', '.join(valid_qualities)} or a number"
            )
        return v.lower()

    @model_validator(mode="after")
    def ensure_paths_exist(self):
        """Ensure paths exist and are writable."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        return self


class AudioConfig(BaseModel):
    """Audio processing configuration."""

    default_format: str = "mp3"
    bitrate: int = 320
    output_dir: Optional[Path] = None
    temp_dir: Path = Field(
        default_factory=lambda: get_default_data_dir() / "tmp" / "audio"
    )

    @field_validator("default_format")
    @classmethod
    def validate_format(cls, v):
        """Validate audio format."""
        valid_formats = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"]
        if v.lower() not in valid_formats:
            raise ValueError(
                f"Invalid format '{v}'. Must be one of: {', '.join(valid_formats)}"
            )
        return v.lower()

    @field_validator("bitrate")
    @classmethod
    def validate_bitrate(cls, v):
        """Validate bitrate."""
        if not isinstance(v, int) or v < 64 or v > 320:
            raise ValueError(f"Invalid bitrate '{v}'. Must be between 64 and 320")
        return v

    @model_validator(mode="after")
    def ensure_paths_exist(self):
        """Ensure paths exist and are writable."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        return self


class DatabaseConfig(BaseModel):
    """Database configuration."""

    sqlite_path: Path = Field(
        default_factory=lambda: get_default_data_dir() / "spatelier.db"
    )
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "spatelier"
    enable_mongodb: bool = False
    retention_days: int = 365
    enable_analytics: bool = True


class TranscriptionConfig(BaseModel):
    """Transcription configuration."""

    default_model: str = "large"
    default_language: str = "en"
    use_faster_whisper: bool = True
    device: str = "auto"
    compute_type: str = "auto"

    @field_validator("default_model")
    @classmethod
    def validate_model(cls, v):
        """Validate Whisper model."""
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if v.lower() not in valid_models:
            raise ValueError(
                f"Invalid model '{v}'. Must be one of: {', '.join(valid_models)}"
            )
        return v.lower()

    @field_validator("device")
    @classmethod
    def validate_device(cls, v):
        """Validate device."""
        valid_devices = ["auto", "cpu", "cuda", "mps"]
        if v.lower() not in valid_devices:
            raise ValueError(
                f"Invalid device '{v}'. Must be one of: {', '.join(valid_devices)}"
            )
        return v.lower()

    @field_validator("compute_type")
    @classmethod
    def validate_compute_type(cls, v):
        """Validate compute type."""
        valid_types = ["auto", "int8", "int8_float16", "int16", "float16", "float32"]
        if v.lower() not in valid_types:
            raise ValueError(
                f"Invalid compute type '{v}'. Must be one of: {', '.join(valid_types)}"
            )
        return v.lower()


class Config(BaseModel):
    """
    Main configuration class for Spatelier.

    Simplified structure with essential nested configs and flattened simple settings.
    """

    # Essential nested configurations
    video: VideoConfig = Field(default_factory=VideoConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)

    # Flattened simple settings (previously nested)
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # File processing settings (flattened)
    video_extensions: List[str] = Field(
        default_factory=lambda: [
            ".mp4",
            ".webm",
            ".avi",
            ".mov",
            ".mkv",
            ".m4v",
            ".flv",
        ]
    )
    audio_extensions: List[str] = Field(
        default_factory=lambda: [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"]
    )
    max_filename_length: int = 255

    # Fallback settings (flattened)
    fallback_max_files: int = 10
    fallback_timeout_seconds: int = 30

    # Global settings
    verbose: bool = False
    debug: bool = False

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {', '.join(valid_levels)}"
            )
        return v.upper()

    @field_validator("max_filename_length")
    @classmethod
    def validate_filename_length(cls, v):
        """Validate filename length."""
        if not isinstance(v, int) or v < 1 or v > 1000:
            raise ValueError(
                f"Invalid max_filename_length '{v}'. Must be between 1 and 1000"
            )
        return v

    @classmethod
    def load_from_file(cls, config_file: Union[str, Path]) -> "Config":
        """Load configuration from YAML file."""
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            verbose=os.getenv("SPATELIER_VERBOSE", "false").lower() == "true",
            debug=os.getenv("SPATELIER_DEBUG", "false").lower() == "true",
            log_level=os.getenv("SPATELIER_LOG_LEVEL", "INFO"),
        )

    def save_to_file(self, config_file: Union[str, Path]) -> None:
        """Save configuration to YAML file."""
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            config_dict = self.model_dump()

            def convert_paths(obj):
                if isinstance(obj, dict):
                    return {k: convert_paths(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_paths(item) for item in obj]
                elif isinstance(obj, Path):
                    return str(obj)
                else:
                    return obj

            yaml.dump(convert_paths(config_dict), f, default_flow_style=False, indent=2)

    def get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        return get_default_data_dir() / "config.yaml"

    def ensure_default_config(self) -> None:
        """Ensure default configuration file exists."""
        default_path = self.get_default_config_path()

        if not default_path.exists():
            default_path.parent.mkdir(parents=True, exist_ok=True)
            self.save_to_file(default_path)

    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Validate video config
        try:
            if self.video.output_dir and not self.video.output_dir.exists():
                issues.append(
                    f"Video output directory does not exist: {self.video.output_dir}"
                )
        except Exception as e:
            issues.append(f"Video output directory error: {e}")

        # Validate audio config
        try:
            if self.audio.output_dir and not self.audio.output_dir.exists():
                issues.append(
                    f"Audio output directory does not exist: {self.audio.output_dir}"
                )
        except Exception as e:
            issues.append(f"Audio output directory error: {e}")

        # Validate database config
        try:
            if not self.database.sqlite_path.parent.exists():
                issues.append(
                    f"Database directory does not exist: {self.database.sqlite_path.parent}"
                )
        except Exception as e:
            issues.append(f"Database directory error: {e}")

        return issues

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate_config()) == 0
