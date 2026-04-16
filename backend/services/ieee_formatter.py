r"""
Enhanced IEEE Paper Formatter
──────────────────────────────

Integrates paper content with IEEE LaTeX builder to produce
properly formatted conference papers.

This bridges the LangGraph pipeline with IEEE formatting.
"""

from typing import Dict, List, Any, Optional
from backend.services.ieee_latex_builder import IEEELatexBuilder
from backend.services.pdf_generator import PDFGenerator
import re


class IEEEPaperFormatter:
    """
    Formats paper content using IEEE LaTeX standards.

    Takes paper data from the LangGraph pipeline and produces:
    - Properly formatted LaTeX source
    - Final PDF output
    """

    def __init__(self):
        """Initialize IEEE formatter."""
        self.pdf_gen = PDFGenerator()

    def format_paper(
        self,
        title: str,
        authors: List[Dict[str, str]],
        abstract: str,
        keywords: List[str],
        sections: Dict[str, str],
        equations: List[Dict[str, Any]] = None,
        diagrams: List[Dict[str, Any]] = None,
        references: List[Dict[str, Any]] = None,
        tables: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format paper sections into IEEE LaTeX document.

        Args:
            title: Paper title
            authors: List of author dicts with keys: name, affiliation, location, email
            abstract: Abstract text
            keywords: List of keywords
            sections: Dict mapping section titles to content
            equations: List of equation dicts with keys: latex, label, description
            diagrams: List of diagram dicts with keys: filepath, caption, label
            references: List of reference strings

        Returns:
            Dict with keys:
                - latex_source: Complete LaTeX code
                - sections_count: Number of sections
                - equations_count: Number of equations
                - diagrams_count: Number of diagrams
                - references_count: Number of references
        """
        # Create builder
        builder = IEEELatexBuilder(title, authors, keywords)

        # Add abstract
        builder.add_abstract(abstract)

        # Add sections in logical IEEE order
        self._add_sections_ordered(builder, sections)

        # Add equations
        equations_count = 0
        if equations:
            for eq in equations:
                builder.add_equation(
                    eq.get("latex") or eq.get("input") or eq.get("notation") or "",
                    label=eq.get("label", ""),
                )
                equations_count += 1

        # Add diagrams as figures
        diagrams_count = 0
        if diagrams:
            for diagram in diagrams:
                builder.add_figure(
                    diagram.get("filepath") or diagram.get("file_path") or diagram.get("file") or "",
                    diagram.get("caption", "Figure"),
                    label=diagram.get("label", ""),
                )
                diagrams_count += 1

        # Add tables
        tables_count = 0
        if tables:
            for tbl in tables:
                table_latex = self._build_table_latex(tbl)
                builder.add_table(
                    content=table_latex,
                    caption=tbl.get("caption", "Results Table"),
                    label=tbl.get("label", ""),
                )
                tables_count += 1

        # Add references
        references_count = 0
        if references:
            for idx, ref in enumerate(references, 1):
                builder.add_reference(self._format_reference(ref, idx))
                references_count += 1

        # Build LaTeX
        latex_source = builder.build()

        return {
            "latex_source": latex_source,
            "sections_count": len(builder.sections),
            "equations_count": equations_count,
            "diagrams_count": diagrams_count,
            "tables_count": tables_count,
            "references_count": references_count,
        }

    def compile_to_pdf(
        self,
        latex_source: str,
        output_name: str = "paper.pdf",
        image_files: List[tuple] = None,
    ) -> Optional[str]:
        """
        Compile LaTeX source to PDF.

        Args:
            latex_source: Complete LaTeX document code
            output_name: Output PDF filename
            image_files: List of (source_path, dest_filename) tuples

        Returns:
            Path to generated PDF, or None if compilation failed
        """
        return self.pdf_gen.compile_latex(latex_source, output_name, image_files)

    @staticmethod
    def _add_sections_ordered(
        builder: IEEELatexBuilder, sections: Dict[str, str]
    ) -> None:
        """
        Add sections to builder in logical IEEE order.

        Section order:
        1. Introduction
        2. Related Work
        3. Proposed Methodology / Approach
        4. Implementation / Method
        5. Results and Discussion
        6. Conclusion

        Args:
            builder: IEEELatexBuilder instance
            sections: Dict mapping section titles to content
        """
        # Define expected section order
        section_order = [
            ("introduction", "I. Introduction"),
            ("related", "II. Related Work"),
            ("methodology", "III. Proposed Methodology"),
            ("approach", "III. Proposed Methodology"),
            ("implementation", "IV. Implementation"),
            ("results", "V. Results and Discussion"),
            ("discussion", "V. Results and Discussion"),
            ("conclusion", "VI. Conclusion"),
        ]

        added_sections = set()

        # Add sections in defined order
        for pattern, numbered_title in section_order:
            for key, content in sections.items():
                # Match section by keyword
                if (
                    key.lower() not in added_sections
                    and pattern in key.lower()
                ):
                    builder.add_section(numbered_title, content)
                    added_sections.add(key.lower())
                    break

    @staticmethod
    def _build_table_latex(table_data: Dict[str, Any]) -> str:
        """Build IEEE-compatible tabular block from table payload."""
        headers = table_data.get("headers", []) or []
        rows = table_data.get("rows", []) or []
        col_count = max(len(headers), max((len(r) for r in rows), default=0), 1)
        col_spec = "|" + "|".join(["c"] * col_count) + "|"

        lines = [f"\\begin{{tabular}}{{{col_spec}}}", "\\hline"]
        if headers:
            safe_headers = [str(h).replace("%", "\\%") for h in headers]
            lines.append(" & ".join(safe_headers) + r" \\")
            lines.append("\\hline")

        for row in rows:
            padded = [str(v).replace("%", "\\%") for v in row] + [""] * (col_count - len(row))
            lines.append(" & ".join(padded[:col_count]) + r" \\")
            lines.append("\\hline")

        lines.append("\\end{tabular}")
        return "\n".join(lines)

    @staticmethod
    def _format_reference(ref: Dict[str, Any], index: int) -> str:
        """Format references into compact IEEE style."""
        if isinstance(ref, str):
            return f"[{index}] {ref}"

        title = ref.get("title", "Untitled")
        authors = ref.get("authors") or ref.get("author") or "Unknown"
        if isinstance(authors, list):
            authors = ", ".join([str(a) for a in authors[:3]])
        venue = ref.get("venue") or ref.get("source") or "arXiv"
        year = ref.get("year") or "n.d."
        return f"[{index}] {authors}, \"{title},\" {venue}, {year}."

    @staticmethod
    def extract_citations(text: str) -> List[str]:
        """
        Extract citation references from text.

        Looks for patterns like:
        - [citation]
        - cite{author, year}
        - (Author, year)

        Args:
            text: Text containing citations

        Returns:
            List of extracted citations
        """
        citations = []

        # Pattern 1: [citation]
        citations.extend(re.findall(r"\[([^\]]+)\]", text))

        # Pattern 2: cite{...}
        citations.extend(re.findall(r"cite\{([^}]+)\}", text))

        # Pattern 3: (Author, year)
        citations.extend(re.findall(r"\(([A-Z][a-z]+(?:\s+et\s+al\.?|,\s+\d{4})[^)]*)\)", text))

        return list(set(citations))  # Remove duplicates

    @staticmethod
    def format_ieee_reference(citation: str, index: int) -> str:
        """
        Format a single reference in IEEE style.

        IEEE format: [1] Author(s), "Title," Journal/Conference, year.

        Args:
            citation: Citation string
            index: Reference number

        Returns:
            Formatted reference
        """
        # If already formatted, return as-is
        if citation.startswith(f"[{index}]"):
            return citation

        # Try to parse citation components
        # Format: Author(s), Title, Year, Venue
        parts = [p.strip() for p in citation.split(",")]

        if len(parts) >= 3:
            authors = parts[0]
            title = parts[1] if len(parts) > 1 else "Untitled"
            year = parts[-1]
            venue = ", ".join(parts[2:-1]) if len(parts) > 3 else ""

            formatted = f"[{index}] {authors}, \"{title},\" {venue}, {year}."
            return formatted.replace('""', '"')

        # Fallback: use as-is with numbering
        return f"[{index}] {citation}"

    @staticmethod
    def validate_latex(latex_source: str) -> Dict[str, Any]:
        """
        Validate LaTeX source for common issues.

        Args:
            latex_source: LaTeX code to validate

        Returns:
            Dict with validation results:
                - is_valid: bool
                - has_title: bool
                - has_author: bool
                - has_abstract: bool
                - section_count: int
                - equation_count: int
                - figure_count: int
                - errors: List of issues found
        """
        errors = []
        latex_lower = latex_source.lower()

        # Check for required elements
        has_title = r"\title{" in latex_source
        has_author = r"\author{" in latex_source
        has_abstract = r"\begin{abstract}" in latex_lower

        if not has_title:
            errors.append("Missing title")
        if not has_author:
            errors.append("Missing author block")
        if not has_abstract:
            errors.append("Missing abstract")

        # Count sections, equations, figures
        section_count = len(re.findall(r"\\section\{", latex_source))
        equation_count = len(re.findall(r"\\begin\{equation\}", latex_source))
        figure_count = len(re.findall(r"\\begin\{figure\}", latex_source))

        # Check for unmatched braces
        open_braces = latex_source.count("{")
        close_braces = latex_source.count("}")
        if open_braces != close_braces:
            errors.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

        # Check for unmatched environments
        begin_matches = len(re.findall(r"\\begin\{", latex_source))
        end_matches = len(re.findall(r"\\end\{", latex_source))
        if begin_matches != end_matches:
            errors.append(f"Unmatched environments: {begin_matches} begin, {end_matches} end")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "has_title": has_title,
            "has_author": has_author,
            "has_abstract": has_abstract,
            "section_count": section_count,
            "equation_count": equation_count,
            "figure_count": figure_count,
            "errors": errors,
        }
