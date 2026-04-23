"""
Configuration management for Claster Forensic Toolkit.
Supports loading from YAML/JSON files, environment variables, and defaults.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field, asdict
from claster.core.logger import get_logger
from claster.core.exceptions import ConfigurationError

logger = get_logger(__name__)

@dataclass
class Config:
    """
    Main configuration container with sensible defaults.
    Can be loaded from a file or environment variables.
    """

    # Case management
    case_name: str = "default_case"
    case_directory: Path = field(default_factory=lambda: Path.cwd() / "cases")
    evidence_directory: Path = field(default_factory=lambda: Path.cwd() / "evidence")
    reports_directory: Path = field(default_factory=lambda: Path.cwd() / "reports")
    temp_directory: Path = field(default_factory=lambda: Path.cwd() / "temp")

    # Hashing
    default_hash_algorithm: str = "sha256"
    verify_copy: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "claster.log"

    # Database
    database_path: Optional[str] = None  # If None, will be derived from case_directory

    # GUI
    theme: str = "dark"
    language: str = "en"

    # PFI (Predictive Forensic Intelligence)
    pfi_model_path: Optional[str] = None
    pfi_threshold: float = 0.75
    pfi_monitoring_interval: int = 5  # seconds

    # Network
    default_interface: Optional[str] = None
    max_packet_sniff: int = 10000

    # Plugin settings
    plugin_directories: list = field(default_factory=lambda: ["./plugins"])

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        data = asdict(self)
        # Convert Path objects to strings for serialization
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary, converting strings to Path where needed."""
        path_keys = ["case_directory", "evidence_directory", "reports_directory", "temp_directory"]
        for key in path_keys:
            if key in data and data[key] is not None:
                data[key] = Path(data[key])
        return cls(**data)

    def save(self, file_path: Union[str, Path]) -> None:
        """
        Save current configuration to a file (YAML or JSON based on extension).

        Args:
            file_path: Path to save configuration.
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        data = self.to_dict()

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if ext in (".yaml", ".yml"):
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            elif ext == ".json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                raise ConfigurationError(f"Unsupported config file format: {ext}")
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}")

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "Config":
        """
        Load configuration from a YAML or JSON file.

        Args:
            file_path: Path to the configuration file.

        Returns:
            Config instance.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"Config file {file_path} not found, using defaults.")
            return cls()

        ext = file_path.suffix.lower()
        try:
            if ext in (".yaml", ".yml"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise ConfigurationError(f"Unsupported config file format: {ext}")

            # Override with environment variables (CLASTER_ prefix)
            for key in data.keys():
                env_var = f"CLASTER_{key.upper()}"
                if env_var in os.environ:
                    data[key] = os.environ[env_var]
                    logger.debug(f"Overriding {key} with env {env_var}={os.environ[env_var]}")

            config = cls.from_dict(data)
            logger.info(f"Configuration loaded from {file_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")

# Global config instance (singleton)
_config_instance: Optional[Config] = None

def get_config(reload: bool = False) -> Config:
    """
    Get the global configuration instance.
    If not yet loaded, creates a default Config.
    Use reload=True to force reload from file.

    Returns:
        Config instance.
    """
    global _config_instance
    if _config_instance is None or reload:
        # Try to load from default location
        default_config_path = Path("config.yaml")
        if default_config_path.exists():
            _config_instance = Config.load(default_config_path)
        else:
            _config_instance = Config()
    return _config_instance