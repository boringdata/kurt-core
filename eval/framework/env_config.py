"""Centralized environment configuration and API key management.

This module handles loading of API keys and other environment variables
from .env files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


def load_env_file(env_path: Optional[Path] = None) -> None:
    """Load environment variables from a .env file.

    Args:
        env_path: Path to .env file. If None, searches for .env in standard locations.
    """
    if env_path is None:
        # Search for .env file in common locations
        search_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent / ".env",  # eval/.env
            Path(__file__).parent.parent.parent / ".env",  # project root
        ]
        for path in search_paths:
            if path.exists():
                env_path = path
                break

    if env_path and env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value


def get_api_key(provider: str, required: bool = True) -> Optional[str]:
    """Get API key for a specific provider.

    Args:
        provider: Provider name ('anthropic', 'openai', etc.)
        required: If True, raises exception when key not found

    Returns:
        API key string or None if not found

    Raises:
        ValueError: If required=True and key not found
    """
    # Ensure env file is loaded
    load_env_file()

    # Map provider names to environment variable names
    key_mapping = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",  # Alias
        "gpt": "OPENAI_API_KEY",  # Alias
    }

    env_var = key_mapping.get(provider.lower())
    if not env_var:
        if required:
            raise ValueError(f"Unknown provider: {provider}")
        return None

    api_key = os.environ.get(env_var)

    if required and not api_key:
        raise ValueError(
            f"API key for {provider} not found. "
            f"Please set {env_var} environment variable or add it to .env file"
        )

    return api_key


def get_llm_config(provider: str = "anthropic") -> Dict[str, Any]:
    """Get LLM configuration for a provider.

    Args:
        provider: Provider name ('anthropic', 'openai', etc.)

    Returns:
        Configuration dictionary with model, api_key, and other settings
    """
    api_key = get_api_key(provider)

    configs = {
        "anthropic": {
            "model": "claude-3-5-haiku-20241022",
            "api_key": api_key,
            "max_tokens": 150,
            "temperature": 0.2,
        },
        "openai": {
            "model": "gpt-4o-mini",
            "api_key": api_key,
            "max_tokens": 150,
            "temperature": 0.2,
        },
    }

    config = configs.get(provider.lower())
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    return config


def setup_dspy(provider: str = "anthropic"):
    """Configure DSPy with the specified provider.

    Args:
        provider: Provider name ('anthropic', 'openai', etc.)

    Returns:
        Configured DSPy LM object
    """
    try:
        import dspy
    except ImportError:
        raise ImportError("DSPy not installed. Please install with: pip install dspy-ai")

    config = get_llm_config(provider)

    if provider.lower() == "anthropic":
        return dspy.LM(
            f"anthropic/{config['model']}",
            api_key=config["api_key"],
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )
    elif provider.lower() == "openai":
        return dspy.LM(
            f"openai/{config['model']}",
            api_key=config["api_key"],
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )
    else:
        raise ValueError(f"Unsupported provider for DSPy: {provider}")


# Auto-load env file on import
load_env_file()
