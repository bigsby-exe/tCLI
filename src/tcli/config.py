"""Configuration management for tCLI."""

import os
from pathlib import Path
from typing import Optional

import yaml


class Config:
    """Manages configuration from file and environment variables."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config, loading from file and environment variables."""
        self.config_path = config_path or self._get_default_config_path()
        self.base_url: str = ""
        self.api_key: str = ""
        self._load_config()

    def _get_default_config_path(self) -> Path:
        """Get the default config file path based on OS."""
        if os.name == "nt":  # Windows
            config_dir = Path.home() / ".tcli"
        else:  # Linux/Mac
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "tcli"
            else:
                config_dir = Path.home() / ".config" / "tcli"

        return config_dir / "config.yaml"

    def _load_config(self) -> None:
        """Load configuration from file and environment variables."""
        # Load from file if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                    api_config = config_data.get("api", {})
                    self.base_url = api_config.get("base_url", "")
                    self.api_key = api_config.get("api_key", "")
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")

        # Environment variables override config file
        self.base_url = os.environ.get("TAPI_URL", self.base_url)
        self.api_key = os.environ.get("TAPI_KEY", self.api_key)

        # Validate required settings
        if not self.base_url:
            raise ValueError(
                "API base URL not configured. Set TAPI_URL environment variable "
                f"or create config file at {self.config_path}"
            )
        if not self.api_key:
            raise ValueError(
                "API key not configured. Set TAPI_KEY environment variable "
                f"or create config file at {self.config_path}"
            )

    def create_default_config(self, base_url: str, api_key: str) -> None:
        """Create a default config file with the provided values."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {
            "api": {
                "base_url": base_url,
                "api_key": api_key,
            }
        }
        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
        print(f"Configuration saved to {self.config_path}")

