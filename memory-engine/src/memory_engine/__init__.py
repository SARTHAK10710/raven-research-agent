"""Raven Memory Engine.

Owns two separate logical knowledge domains: Personal Memory and Document
Intelligence. Phase 8.1 provides only the foundation: configuration, error
hierarchy, structured logging and the domain-layer boundary.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("raven-memory-engine")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0"

__all__ = ["__version__"]
