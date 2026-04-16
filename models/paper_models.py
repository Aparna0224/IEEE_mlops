"""Compatibility shim for strict paper models."""

from backend.models.paper_models import (
    PaperSection,
    Equation,
    Figure,
    Reference,
    ResearchPaper,
)

__all__ = [
    "PaperSection",
    "Equation",
    "Figure",
    "Reference",
    "ResearchPaper",
]
