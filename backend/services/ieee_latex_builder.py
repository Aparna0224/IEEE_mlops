r"""
IEEE LaTeX Document Builder
────────────────────────────

Assembles paper content into official IEEE conference LaTeX format.

Uses \documentclass[conference]{IEEEtran} with:
- Two-column layout
- Times New Roman font
- IEEE author block formatting
- Equation/Figure/Table numbering
- IEEE citation style (numbered [1], [2], etc.)

Example usage:
    builder = IEEELatexBuilder(
        title="Deep Learning Architecture",
        authors=[{"name": "John Doe", "affiliation": "MIT", "location": "Cambridge, MA", "email": "john@mit.edu"}]
    )
    builder.add_abstract("This paper presents...")
    builder.add_keywords(["deep learning", "neural networks"])
    builder.add_section("1. Introduction", "The motivation...")
    builder.add_equation("x = y + z", label="eq:simple")
    builder.add_figure("image.png", "System Architecture", label="fig:arch")
    latex_doc = builder.build()
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import os


@dataclass
class EquationData:
    """Equation information."""
    latex: str
    label: str
    number: int


@dataclass
class FigureData:
    """Figure/diagram information."""
    filepath: str
    caption: str
    label: str
    number: int
    width: str = r"\linewidth"


@dataclass
class TableData:
    """Table information."""
    content: str  # LaTeX table code
    caption: str
    label: str
    number: int


@dataclass
class AuthorInfo:
    """Author information."""
    name: str
    affiliation: str
    location: str
    email: str


class IEEELatexBuilder:
    """
    Builds IEEE-compliant LaTeX documents with proper formatting,
    equation/figure numbering, and citation handling.
    """

    # IEEE LaTeX preamble with conference settings
    PREAMBLE = r"""\documentclass[conference]{IEEEtran}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{times}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{url}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{array}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{balance}

% IEEE paper margins are automatically set by \documentclass[conference]{IEEEtran}
\setcounter{secnumdepth}{2}
\setcounter{tocdepth}{2}

% Figure and table caption formatting (IEEE style)
\captionsetup{font=small,labelsep=period}

\begin{document}

"""

    CLOSING = r"""
\end{document}
"""

    def __init__(
        self,
        title: str,
        authors: List[Dict[str, str]],
        keywords: List[str] = None,
    ):
        """
        Initialize IEEE LaTeX builder.

        Args:
            title: Paper title
            authors: List of author dicts with keys: name, affiliation, location, email
            keywords: List of keywords (optional)
        """
        self.title = title
        self.authors = [AuthorInfo(**a) for a in authors] if authors else []
        self.keywords = keywords or []

        # Content sections
        self.abstract = ""
        self.sections: List[Tuple[str, str, bool]] = []  # (heading, content, raw_latex)
        self.equations: List[EquationData] = []
        self.figures: List[FigureData] = []
        self.tables: List[TableData] = []
        self.references: List[str] = []

        # Counters
        self.eq_counter = 0
        self.fig_counter = 0
        self.tbl_counter = 0
        self.ref_counter = 0

    def add_abstract(self, text: str) -> None:
        """Add abstract text."""
        self.abstract = text.strip()

    def add_keywords(self, keywords: List[str]) -> None:
        """Add keywords."""
        self.keywords = keywords

    def add_section(self, title: str, content: str, raw_latex: bool = False) -> None:
        """
        Add a paper section.

        Args:
            title: Section title (e.g., "1. Introduction")
            content: Section content
        """
        self.sections.append((title, content.strip(), raw_latex))

    def add_equation(
        self, latex: str, label: str = "", caption: str = ""
    ) -> int:
        """
        Add an equation to the paper.

        Args:
            latex: LaTeX equation code (without \\begin{equation}...\\end)
            label: Reference label (e.g., "eq:sentiment")
            caption: Optional equation description

        Returns:
            Equation number for referencing
        """
        self.eq_counter += 1
        eq_label = label or f"eq:{self.eq_counter}"

        # Clean up LaTeX if it has inline math delimiters
        latex = latex.strip()
        if latex.startswith("$"):
            latex = latex.strip("$")

        eq_data = EquationData(
            latex=latex,
            label=eq_label,
            number=self.eq_counter,
        )
        self.equations.append(eq_data)
        return self.eq_counter

    def add_figure(
        self,
        filepath: str,
        caption: str,
        label: str = "",
        width: str = r"\linewidth",
    ) -> int:
        """
        Add a figure/diagram to the paper.

        Args:
            filepath: Path to image file (relative to LaTeX compile directory)
            caption: Figure caption
            label: Reference label (e.g., "fig:architecture")
            width: LaTeX width (default: full column width)

        Returns:
            Figure number for referencing
        """
        self.fig_counter += 1
        fig_label = label or f"fig:{self.fig_counter}"

        fig_data = FigureData(
            filepath=filepath,
            caption=caption.strip(),
            label=fig_label,
            number=self.fig_counter,
            width=width,
        )
        self.figures.append(fig_data)
        return self.fig_counter

    def add_table(
        self,
        content: str,
        caption: str,
        label: str = "",
    ) -> int:
        """
        Add a table to the paper.

        Args:
            content: LaTeX table code (tabular environment)
            caption: Table caption
            label: Reference label (e.g., "tbl:results")

        Returns:
            Table number for referencing
        """
        self.tbl_counter += 1
        tbl_label = label or f"tbl:{self.tbl_counter}"

        tbl_data = TableData(
            content=content.strip(),
            caption=caption.strip(),
            label=tbl_label,
            number=self.tbl_counter,
        )
        self.tables.append(tbl_data)
        return self.tbl_counter

    def add_reference(self, citation: str) -> int:
        """
        Add a reference/citation.

        Args:
            citation: Citation in any format (will be formatted as IEEE [#])

        Returns:
            Reference number [#]
        """
        self.ref_counter += 1
        self.references.append(citation.strip())
        return self.ref_counter

    def _build_title_author_block(self) -> str:
        """Build IEEE-formatted title and author block."""
        latex = f"\\title{{{self._escape_latex(self.title)}}}\n\n"

        if self.authors:
            latex += r"\author{" + "\n"

            for author in self.authors:
                latex += (
                    f"\\IEEEauthorblockN{{{self._escape_latex(author.name)}}}\n"
                )
                latex += r"\IEEEauthorblockA{" + "\n"
                latex += (
                    f"{self._escape_latex(author.affiliation)} \\\\\n"
                )
                latex += f"{self._escape_latex(author.location)} \\\\\n"
                latex += f"\\texttt{{{author.email}}}\n"
                latex += r"}" + "\n"

            latex += r"}" + "\n\n"

        return latex

    def _build_abstract_keywords(self) -> str:
        """Build abstract and keywords."""
        latex = r"\begin{abstract}" + "\n"
        latex += f"{self._escape_latex(self.abstract)}\n"
        latex += r"\end{abstract}" + "\n\n"

        keywords_text = ", ".join(self.keywords) if self.keywords else "IEEE, research paper, methodology, evaluation"
        latex += r"\begin{IEEEkeywords}" + "\n"
        latex += f"{self._escape_latex(keywords_text)}\n"
        latex += r"\end{IEEEkeywords}" + "\n\n"

        latex += r"\IEEEpeerreviewmaketitle" + "\n\n"
        return latex

    def _build_sections(self) -> str:
        """Build paper sections with proper numbering."""
        latex = ""
        for title, content, raw_latex in self.sections:
            # Format section heading
            section_cmd = f"\\section{{{title}}}"

            latex += section_cmd + "\n"
            latex += f"{content if raw_latex else self._escape_latex(content)}\n\n"

        return latex

    def _build_floats(self) -> str:
        """Build equations, figures, and tables into the document."""
        latex = ""

        # Equations are referenced as (1), (2), etc.
        for eq in self.equations:
            latex += f"\\begin{{equation}}\\label{{{eq.label}}}\n"
            latex += f"{eq.latex}\n"
            latex += "\\end{equation}\n\n"

        for fig in self.figures:
            caption = self._escape_latex(fig.caption)
            latex += "\\begin{figure}[h]\n"
            latex += "\\centering\n"
            latex += f"\\includegraphics[width={fig.width}]{{{fig.filepath}}}\n"
            latex += f"\\caption{{{caption}}}\n"
            latex += f"\\label{{{fig.label}}}\n"
            latex += "\\end{figure}\n\n"

        for tbl in self.tables:
            caption = self._escape_latex(tbl.caption)
            latex += "\\begin{table}[h]\n"
            latex += "\\centering\n"
            latex += f"\\caption{{{caption}}}\n"
            latex += f"\\label{{{tbl.label}}}\n"
            latex += f"{tbl.content}\n"
            latex += "\\end{table}\n\n"

        return latex

    def _build_references(self) -> str:
        """Build references section in IEEE format."""
        latex = r"\begin{thebibliography}{99}" + "\n\n"

        if not self.references:
            latex += r"\bibitem{1} References unavailable." + "\n\n"
            latex += r"\end{thebibliography}" + "\n"
            return latex

        for i, ref in enumerate(self.references, 1):
            latex += f"\\bibitem{{{i}}}\n"
            latex += f"{self._escape_latex(ref)}\n\n"

        latex += r"\end{thebibliography}" + "\n"
        return latex

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Escape special LaTeX characters in text."""
        replacements = {
            "\\": r"\textbackslash{}",
            "{": r"\{",
            "}": r"\}",
            "_": r"\_",
            "$": r"\$",
            "&": r"\&",
            "%": r"\%",
            "#": r"\#",
            "^": r"\^{}",
            "~": r"\textasciitilde{}",
        }

        text = str(text)
        # Process backslash first to avoid double-escaping
        text = text.replace("\\", r"\textbackslash{}")

        for char, escaped in replacements.items():
            if char != "\\":  # Skip backslash since we already handled it
                text = text.replace(char, escaped)

        return text

    def build(self) -> str:
        """
        Build the complete IEEE LaTeX document.

        Returns:
            Complete LaTeX code as a string
        """
        latex = self.PREAMBLE

        # Title and authors
        latex += self._build_title_author_block()

        # Abstract and keywords
        latex += self._build_abstract_keywords()

        # Main content sections
        latex += self._build_sections()

        # Equations, figures, tables
        latex += self._build_floats()

        # Balance final page columns for conference layout.
        latex += "\\balance\n"

        # References
        latex += self._build_references()

        # Closing
        latex += self.CLOSING

        return latex

    def save(self, filepath: str) -> None:
        """
        Save LaTeX document to file.

        Args:
            filepath: Output file path (should end in .tex)
        """
        latex_content = self.build()

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(latex_content)

        print(f"[INFO] LaTeX document saved to {filepath}")


def build_ieee_paper(
    title: str,
    authors: List[Dict[str, str]],
    abstract: str,
    keywords: List[str],
    sections: Dict[str, str],
    equations: List[Dict[str, str]] = None,
    figures: List[Dict[str, str]] = None,
    references: List[str] = None,
) -> str:
    """
    Convenience function to build an IEEE paper from structured data.

    Args:
        title: Paper title
        authors: List of author dicts
        abstract: Abstract text
        keywords: List of keywords
        sections: Dict mapping section titles to content
        equations: List of equation dicts with keys: latex, label
        figures: List of figure dicts with keys: filepath, caption, label
        references: List of reference strings

    Returns:
        Complete LaTeX document code
    """
    builder = IEEELatexBuilder(title, authors, keywords)

    builder.add_abstract(abstract)

    # Add sections in order
    section_order = [
        "Introduction",
        "Related Work",
        "Methodology",
        "Implementation",
        "Results",
        "Discussion",
        "Conclusion",
    ]

    section_num = 1
    for section_key in section_order:
        # Find matching section (case-insensitive)
        for key, content in sections.items():
            if key.lower().startswith(section_key.lower()):
                title_str = f"{section_num}. {section_key}"
                builder.add_section(title_str, content)
                section_num += 1
                break

    # Add equations
    if equations:
        for eq in equations:
            builder.add_equation(eq.get("latex", ""), eq.get("label", ""))

    # Add figures
    if figures:
        for fig in figures:
            builder.add_figure(
                fig.get("filepath", ""),
                fig.get("caption", ""),
                fig.get("label", ""),
            )

    # Add references
    if references:
        for ref in references:
            builder.add_reference(ref)

    return builder.build()
