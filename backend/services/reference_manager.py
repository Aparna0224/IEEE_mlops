"""
Reference Manager Service
──────────────────────────

Manages figure, equation, and bibliographic references.
Automatically numbers and cross-references diagrams and equations.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class Reference:
    """A single reference in the paper"""
    ref_id: str  # Unique identifier
    ref_type: str  # "figure", "equation", "citation"
    label: str  # LaTeX label
    number: int  # Sequential number
    title: str  # Title/caption
    page: Optional[int] = None  # Page number (set during PDF generation)


class ReferenceManager:
    """
    Manages all references (figures, equations, citations) in a paper.
    
    Usage::
    
        manager = ReferenceManager()
        manager.add_figure("fig:architecture", "System Architecture")
        manager.add_equation("eq:sentiment", "Sentiment Score")
        
        # Generate reference text
        ref_text = manager.get_reference("fig:architecture")  # "Fig. 1"
        
        # Update content with reference numbers
        content = manager.replace_generic_refs(content)
    """
    
    def __init__(self):
        """Initialize reference manager."""
        self.references: Dict[str, Reference] = {}
        self.figures: List[Reference] = []
        self.equations: List[Reference] = []
        self.citations: List[Reference] = []
    
    def add_figure(self, label: str, title: str) -> Reference:
        """
        Add a figure reference.
        
        Args:
            label: LaTeX label (e.g., "fig:architecture")
            title: Figure title/caption
            
        Returns:
            Reference object
        """
        number = len(self.figures) + 1
        ref = Reference(
            ref_id=label,
            ref_type="figure",
            label=label,
            number=number,
            title=title,
        )
        self.references[label] = ref
        self.figures.append(ref)
        return ref
    
    def add_equation(self, label: str, title: str) -> Reference:
        """
        Add an equation reference.
        
        Args:
            label: LaTeX label (e.g., "eq:sentiment")
            title: Equation title/description
            
        Returns:
            Reference object
        """
        number = len(self.equations) + 1
        ref = Reference(
            ref_id=label,
            ref_type="equation",
            label=label,
            number=number,
            title=title,
        )
        self.references[label] = ref
        self.equations.append(ref)
        return ref
    
    def add_citation(self, label: str, title: str) -> Reference:
        """
        Add a citation reference.
        
        Args:
            label: Citation label
            title: Paper title/author info
            
        Returns:
            Reference object
        """
        number = len(self.citations) + 1
        ref = Reference(
            ref_id=label,
            ref_type="citation",
            label=label,
            number=number,
            title=title,
        )
        self.references[label] = ref
        self.citations.append(ref)
        return ref
    
    def get_reference(self, label: str) -> Optional[str]:
        """
        Get formatted reference text for a label.
        
        Returns:
            Formatted reference like "Fig. 1", "Eq. (2)", "[3]"
        """
        if label not in self.references:
            return None
        
        ref = self.references[label]
        
        if ref.ref_type == "figure":
            return f"Fig. {ref.number}"
        elif ref.ref_type == "equation":
            return f"({ref.number})"
        elif ref.ref_type == "citation":
            return f"[{ref.number}]"
        
        return label
    
    def get_all_figures(self) -> List[Reference]:
        """Get all figure references."""
        return self.figures
    
    def get_all_equations(self) -> List[Reference]:
        """Get all equation references."""
        return self.equations
    
    def get_all_citations(self) -> List[Reference]:
        """Get all citation references."""
        return self.citations
    
    def get_list_of_figures(self) -> str:
        """
        Generate LaTeX 'List of Figures' section.
        
        Returns:
            LaTeX code for list of figures
        """
        if not self.figures:
            return ""
        
        lines = ["\\clearpage", "\\listoffigures"]
        return "\n".join(lines)
    
    def replace_generic_refs(self, content: str) -> str:
        """
        Replace generic reference patterns with formatted references.
        
        Patterns:
            @fig:label → Fig. N
            @eq:label → (N)
            @cite:label → [N]
        
        Args:
            content: Text content with generic refs
            
        Returns:
            Content with replaced references
        """
        def replace_ref(match):
            label = match.group(1)
            ref_text = self.get_reference(label)
            return ref_text if ref_text else match.group(0)
        
        # Pattern: @label
        pattern = r"@([\w:]+)"
        result = re.sub(pattern, replace_ref, content)
        
        return result
    
    def generate_reference_section(self) -> str:
        """
        Generate a reference section summary or TOC.
        
        Returns:
            LaTeX code for reference section
        """
        lines = []
        
        if self.figures:
            lines.append("\\subsubsection*{Figures}")
            for fig in self.figures:
                lines.append(f"\\textbf{{Fig. {fig.number}}}: {fig.title}")
        
        if self.equations:
            lines.append("\\subsubsection*{Equations}")
            for eq in self.equations:
                lines.append(f"\\textbf{{Eq. {eq.number}}}: {eq.title}")
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get reference statistics.
        
        Returns:
            Dictionary with reference counts
        """
        return {
            "total_figures": len(self.figures),
            "total_equations": len(self.equations),
            "total_citations": len(self.citations),
            "total_references": len(self.references),
        }
    
    def generate_appendix_references(self) -> str:
        """
        Generate appendix with all reference information.
        
        Returns:
            LaTeX code for reference appendix
        """
        lines = ["\\appendix", "\\section{References}", ""]
        
        lines.append("\\subsection{Figures}")
        for fig in self.figures:
            lines.append(f"\\textbf{{Fig. {fig.number}}}: {fig.title} (Label: \\texttt{{{fig.label}}})")
        
        lines.append("\n\\subsection{Equations}")
        for eq in self.equations:
            lines.append(f"\\textbf{{Eq. {eq.number}}}: {eq.title} (Label: \\texttt{{{eq.label}}})")
        
        if self.citations:
            lines.append("\n\\subsection{Citations}")
            for cite in self.citations:
                lines.append(f"\\textbf{{[{cite.number}]}}: {cite.title}")
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear all references."""
        self.references.clear()
        self.figures.clear()
        self.equations.clear()
        self.citations.clear()
