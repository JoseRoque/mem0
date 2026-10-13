"""Small constants shim: replace or adapt to your app's configuration.

Provides get_app_home() used by MemoryStore to resolve the memories dir.
"""
from pathlib import Path
import os

def get_app_home() -> Path:
    """Return a directory for storing app-scoped data. Default: ~/.mem0
    In production adapt to your app's configuration or environment.
    """
    return Path(os.environ.get("MEM0_HOME", Path.home() / ".mem0")).expanduser()
