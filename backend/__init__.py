"""
Backend API for MCP Research Paper Generator
FastAPI-based REST API with async support and background tasks
"""

__version__ = "1.0.0"

from .api import app

__all__ = ["app"]

