"""Formatters module – LaTeX-based IEEE paper formatting"""

from .ieee_formatter import IEEEFormattingEngine
from .equation_formatter import EquationFormatter, EquationFormatResult

__all__ = ["IEEEFormattingEngine", "EquationFormatter", "EquationFormatResult"]
