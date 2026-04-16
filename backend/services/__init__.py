"""
Backend services for IEEE paper generation.
"""

from .diagram_processor import DiagramProcessor
from .equation_service import EquationService
from .reference_manager import ReferenceManager

__all__ = [
    "DiagramProcessor",
    "EquationService",
    "ReferenceManager",
]
