"""
IEEE LaTeX Formatting Engine
─────────────────────────────
Converts structured paper data into a proper IEEE-conference-ready PDF
using the IEEEtran LaTeX document class and pdflatex compilation.

Workflow:
  1. Accept paper JSON (title, authors, abstract, keywords, sections, references)
  2. Sanitise all text for LaTeX special characters
  3. Build a complete .tex source using IEEEtran two-column format
  4. Write .tex to a temp directory
  5. Run pdflatex (twice for cross-refs)
  6. Return {pdf_path, latex_source, ieee_compliant}
  7. On failure: sanitise → retry once → fall back to ReportLab
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .equation_formatter import EquationFormatter


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class AuthorInfo:
    name: str = "Author"
    affiliation: str = ""
    location: str = ""
    email: str = ""


@dataclass
class PaperSection:
    heading: str = ""
    content: str = ""


@dataclass
class Reference:
    index: int = 0
    authors: str = ""
    title: str = ""
    venue: str = ""
    year: str = ""
    link: str = ""


@dataclass
class FormattingResult:
    pdf_path: str | None = None
    latex_source: str = ""
    ieee_compliant: bool = False
    fallback_used: bool = False
    error: str | None = None
    compile_log: str = ""


# ── LaTeX special-character sanitiser ─────────────────────────────────────────

_LATEX_SPECIAL = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Regex that matches any of the special chars (but NOT the backslash)
_SPECIAL_RE = re.compile("|".join(re.escape(k) for k in _LATEX_SPECIAL))

# Backslash must be handled first (before we inject more backslashes)
_BACKSLASH_RE = re.compile(r"\\(?![&%$#_{}~^])")


# Sentinel to protect math zones during sanitisation
_MATH_SAFE_PH = "\x02MATHSAFE{}\x02"
_MATH_SAFE_PH_RE = re.compile(r"\x02MATHSAFE(\d+)\x02")

# Patterns that identify math zones we must NOT sanitise
_MATH_ENV_RE = re.compile(
    r"(\\begin\{(?:equation|align|gather|multline|eqnarray)\*?\}"
    r".*?"
    r"\\end\{(?:equation|align|gather|multline|eqnarray)\*?\})",
    re.DOTALL,
)
_INLINE_MATH_RE = re.compile(r"((?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$))", re.DOTALL)


def _sanitise(text: str) -> str:
    """Escape LaTeX special characters in *user-supplied* text,
    while preserving math zones (equation environments and inline $…$)."""
    if not text:
        return ""

    # 1. Stash all math zones so they're untouched by escaping
    zones: list[str] = []

    def _stash(m: re.Match) -> str:
        zones.append(m.group(0))
        return _MATH_SAFE_PH.format(len(zones) - 1)

    text = _MATH_ENV_RE.sub(_stash, text)
    text = _INLINE_MATH_RE.sub(_stash, text)

    # 2. Escape stray backslashes in prose
    text = _BACKSLASH_RE.sub(r"\\textbackslash{}", text)
    # 3. Escape special chars in prose
    text = _SPECIAL_RE.sub(lambda m: _LATEX_SPECIAL[m.group()], text)

    # 4. Restore math zones
    def _restore(m: re.Match) -> str:
        idx = int(m.group(1))
        return zones[idx] if 0 <= idx < len(zones) else m.group(0)

    text = _MATH_SAFE_PH_RE.sub(_restore, text)
    return text


def _sanitise_url(url: str) -> str:
    """URLs go inside \\url{} so only escape braces."""
    return url.replace("{", r"\{").replace("}", r"\}")


# ── Section parser ────────────────────────────────────────────────────────────

# Typical IEEE headings emitted by the LLM pipeline
_HEADING_PATTERNS = [
    r"^#{1,3}\s+(.+)",               # Markdown headings
    r"^(?:I{1,3}V?|VI{0,3}|IX|X)\.\s+(.+)",  # Roman numeral headings
    r"^(\d+)\.\s+(.+)",              # Numeric headings
    r"^(ABSTRACT|INTRODUCTION|RELATED WORK|METHODOLOGY|PROPOSED .+|"
    r"EXPERIMENTAL .+|RESULTS|DISCUSSION|CONCLUSION|REFERENCES|"
    r"ACKNOWLEDGMENT|FUTURE WORK)[:.]?\s*$",
]
_HEADING_RE = re.compile("|".join(_HEADING_PATTERNS), re.IGNORECASE | re.MULTILINE)


def parse_sections(raw_content: str) -> list[PaperSection]:
    """
    Split raw paper text into ``PaperSection`` objects.

    Handles Markdown headings, Roman numeral headings, and bare
    UPPER-CASE section titles commonly produced by the generation pipeline.
    """
    sections: list[PaperSection] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in raw_content.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m:
            # Flush previous section
            if current_heading or current_lines:
                sections.append(PaperSection(
                    heading=current_heading.strip(),
                    content="\n".join(current_lines).strip(),
                ))
            # Grab the first non-None group as the heading text
            groups = [g for g in m.groups() if g is not None]
            current_heading = groups[-1] if groups else line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Flush last section
    if current_heading or current_lines:
        sections.append(PaperSection(
            heading=current_heading.strip(),
            content="\n".join(current_lines).strip(),
        ))

    return sections


def _extract_abstract(sections: list[PaperSection]) -> tuple[str, list[PaperSection]]:
    """Pop and return the abstract section if present."""
    for i, sec in enumerate(sections):
        if sec.heading.upper().startswith("ABSTRACT"):
            abstract = sec.content
            remaining = sections[:i] + sections[i + 1:]
            return abstract, remaining
    # No explicit abstract – use first 900 chars of content
    all_text = " ".join(s.content for s in sections)
    return all_text[:900], sections


def _extract_references_section(sections: list[PaperSection]) -> tuple[str, list[PaperSection]]:
    """Pop and return the references section text if present."""
    for i, sec in enumerate(sections):
        if sec.heading.upper().startswith("REFERENCE"):
            refs_text = sec.content
            remaining = sections[:i] + sections[i + 1:]
            return refs_text, remaining
    return "", sections


# ── Core engine ───────────────────────────────────────────────────────────────

class IEEEFormattingEngine:
    """
    Full IEEE-conference LaTeX formatter.

    Usage::

        engine = IEEEFormattingEngine()
        result = engine.format(
            title="My Paper",
            authors=[AuthorInfo(name="Alice", affiliation="MIT")],
            raw_content="# ABSTRACT\\n...",
            references=[{"title": "...", "link": "..."}],
            keywords=["AI", "ML"],
        )
        if result.pdf_path:
            print("PDF at", result.pdf_path)
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._eq_formatter = EquationFormatter()

    # ── public API ────────────────────────────────────────────────────────

    def format(
        self,
        title: str,
        authors: list[AuthorInfo | dict],
        raw_content: str,
        references: list[dict[str, Any]] | None = None,
        keywords: list[str] | None = None,
        topic_slug: str | None = None,
    ) -> FormattingResult:
        """
        End-to-end: generate LaTeX → compile → return result.

        Falls back to the existing ReportLab writer when pdflatex is
        unavailable or compilation fails after retry.
        """
        # Normalise author dicts → dataclass
        norm_authors = self._normalise_authors(authors)

        # Parse sections from raw content
        sections = parse_sections(raw_content)
        abstract, sections = _extract_abstract(sections)
        refs_text, sections = _extract_references_section(sections)

        # Build reference objects
        ref_objs = self._build_references(references or [], refs_text)

        # ── Run EquationFormatter on abstract + every section ──
        # Use convert_math() (not format()) so prose escaping is left
        # to _sanitise which is math-zone-aware.
        eq_result = self._eq_formatter.convert_math(abstract)
        abstract = eq_result.content
        total_equations = eq_result.equation_count
        total_inline = eq_result.inline_count

        for sec in sections:
            sec_eq = self._eq_formatter.convert_math(sec.content)
            sec.content = sec_eq.content
            total_equations += sec_eq.equation_count
            total_inline += sec_eq.inline_count

        # Keyword list
        kw = keywords or self._guess_keywords(title, abstract)

        # Generate LaTeX source
        latex_src = self._build_latex(
            title=title,
            authors=norm_authors,
            abstract=abstract,
            keywords=kw,
            sections=sections,
            references=ref_objs,
        )

        # Generate slug for filenames
        slug = topic_slug or re.sub(r"\W+", "_", title)[:60]

        # Try compilation
        result = self._compile(latex_src, slug)

        if result.pdf_path:
            result.ieee_compliant = True
            return result

        # Retry once after extra sanitisation
        latex_src_clean = self._aggressive_sanitise(latex_src)
        result = self._compile(latex_src_clean, slug, attempt=2)

        if result.pdf_path:
            result.ieee_compliant = True
            result.latex_source = latex_src_clean
            return result

        # Fallback to ReportLab
        result = self._fallback_reportlab(
            title, authors, raw_content, references or [], slug
        )
        return result

    # ── LaTeX generation ──────────────────────────────────────────────────

    def _build_latex(
        self,
        title: str,
        authors: list[AuthorInfo],
        abstract: str,
        keywords: list[str],
        sections: list[PaperSection],
        references: list[Reference],
    ) -> str:
        """Assemble a complete IEEEtran .tex document."""
        parts: list[str] = []

        # Preamble
        parts.append(textwrap.dedent(r"""
            \documentclass[conference]{IEEEtran}
            \usepackage[utf8]{inputenc}
            \usepackage[T1]{fontenc}
            \usepackage{amsmath,amssymb,amsfonts}
            \usepackage{graphicx}
            \usepackage{textcomp}
            \usepackage{xcolor}
            \usepackage{hyperref}
            \usepackage{cite}
            \usepackage{algorithmic}
            \usepackage{balance}

            \hypersetup{
                colorlinks=true,
                linkcolor=black,
                citecolor=black,
                urlcolor=blue,
            }
        """).strip())

        # Title
        parts.append(f"\n\\title{{{_sanitise(title)}}}")

        # Authors — IEEEtran \author block
        author_block = self._format_authors_latex(authors)
        parts.append(f"\n{author_block}")

        # Begin document
        parts.append("\n\\begin{document}")
        parts.append("\\maketitle")

        # Abstract
        parts.append("\n\\begin{abstract}")
        parts.append(_sanitise(abstract))
        parts.append("\\end{abstract}")

        # Keywords
        if keywords:
            kw_str = ", ".join(_sanitise(k) for k in keywords)
            parts.append(f"\n\\begin{{IEEEkeywords}}\n{kw_str}\n\\end{{IEEEkeywords}}")

        # Sections
        for sec in sections:
            heading = sec.heading
            if not heading:
                continue
            parts.append(f"\n\\section{{{_sanitise(heading)}}}")

            # Split content into paragraphs
            paragraphs = sec.content.split("\n\n")
            for para in paragraphs:
                cleaned = _sanitise(para.strip())
                if cleaned:
                    parts.append(f"{cleaned}\n")

        # References
        if references:
            parts.append("\n\\begin{thebibliography}{00}")
            for ref in references:
                entry = self._format_bibitem(ref)
                parts.append(entry)
            parts.append("\\end{thebibliography}")

        # Balance columns on last page
        parts.append("\n\\balance")
        parts.append("\\end{document}")

        return "\n".join(parts)

    def _format_authors_latex(self, authors: list[AuthorInfo]) -> str:
        """Build the IEEEtran \\author{\\IEEEauthorblockN{...}} block."""
        if not authors:
            return "\\author{\\IEEEauthorblockN{Author}}"

        blocks: list[str] = []
        for a in authors:
            name_line = f"\\IEEEauthorblockN{{{_sanitise(a.name)}}}"
            aff_parts: list[str] = []
            if a.affiliation:
                aff_parts.append(_sanitise(a.affiliation))
            if a.location:
                aff_parts.append(_sanitise(a.location))
            if a.email:
                aff_parts.append(f"Email: {_sanitise(a.email)}")

            if aff_parts:
                aff_line = f"\\IEEEauthorblockA{{{chr(10).join(aff_parts)}}}"
                blocks.append(f"{name_line}\n{aff_line}")
            else:
                blocks.append(name_line)

        inner = " \\and\n".join(blocks)
        return f"\\author{{{inner}}}"

    def _format_bibitem(self, ref: Reference) -> str:
        """Format a single \\bibitem entry."""
        label = f"b{ref.index}"
        parts = []
        if ref.authors:
            parts.append(_sanitise(ref.authors))
        if ref.title:
            parts.append(f"``{_sanitise(ref.title)},''")
        if ref.venue:
            parts.append(f"\\textit{{{_sanitise(ref.venue)}}}")
        if ref.year:
            parts.append(_sanitise(ref.year))
        if ref.link:
            parts.append(f"\\url{{{_sanitise_url(ref.link)}}}")

        body = " ".join(parts) if parts else _sanitise(ref.title or "Reference")
        return f"\\bibitem{{{label}}} {body}."

    # ── Compilation ───────────────────────────────────────────────────────

    def _compile(
        self, latex_src: str, slug: str, attempt: int = 1
    ) -> FormattingResult:
        """
        Write .tex to a temp dir and run pdflatex twice.
        Copy resulting PDF to self.output_dir.
        """
        result = FormattingResult(latex_source=latex_src)

        # Check pdflatex availability
        if not shutil.which("pdflatex"):
            result.error = "pdflatex not found on PATH"
            result.compile_log = "pdflatex binary not available"
            return result

        tmpdir = tempfile.mkdtemp(prefix="ieee_latex_")
        tex_path = os.path.join(tmpdir, "paper.tex")

        try:
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_src)

            # Run pdflatex twice (for cross-references & bibliography)
            for pass_num in (1, 2):
                proc = subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-output-directory", tmpdir,
                        tex_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )
                if proc.returncode != 0 and pass_num == 2:
                    result.error = f"pdflatex failed (attempt {attempt}, pass {pass_num})"
                    result.compile_log = (proc.stdout + "\n" + proc.stderr)[-3000:]
                    return result

            # Copy PDF to output dir
            src_pdf = os.path.join(tmpdir, "paper.pdf")
            if os.path.exists(src_pdf):
                dest = str(self.output_dir / f"{slug}_IEEE_LaTeX.pdf")
                shutil.copy2(src_pdf, dest)
                result.pdf_path = dest
                result.compile_log = "Compilation successful"
            else:
                result.error = "PDF not produced despite pdflatex exit 0"

        except subprocess.TimeoutExpired:
            result.error = f"pdflatex timed out (attempt {attempt})"
        except Exception as exc:
            result.error = f"Compilation error: {exc}"
        finally:
            # Cleanup temp dir
            shutil.rmtree(tmpdir, ignore_errors=True)

        return result

    # ── Aggressive sanitiser for retry ────────────────────────────────────

    @staticmethod
    def _aggressive_sanitise(latex_src: str) -> str:
        """
        Second-pass sanitisation: strip problematic Unicode, collapse
        bad control sequences, remove orphan braces.
        """
        # Remove non-ASCII that isn't common accented chars
        cleaned = re.sub(r"[^\x00-\x7F\u00C0-\u00FF]", " ", latex_src)
        # Fix orphan braces (odd counts)
        for ch, esc in [("{", r"\{"), ("}", r"\}")]:
            # Only fix braces NOT preceded by backslash and outside commands
            pass  # keep simple – just remove stray Unicode
        return cleaned

    # ── ReportLab fallback ────────────────────────────────────────────────

    def _fallback_reportlab(
        self,
        title: str,
        authors: list[AuthorInfo | dict],
        raw_content: str,
        references: list[dict],
        slug: str,
    ) -> FormattingResult:
        """Use the existing ReportLab writer as a fallback."""
        try:
            from src.writers.paper_writer import generate_ieee_paper

            author_dicts = []
            for a in authors:
                if isinstance(a, AuthorInfo):
                    author_dicts.append({
                        "name": a.name,
                        "affiliation": a.affiliation,
                        "location": a.location,
                        "email": a.email,
                    })
                else:
                    author_dicts.append(a)

            pdf_path = generate_ieee_paper(
                topic=title,
                papers=references,
                content=raw_content,
                authors=author_dicts,
            )

            return FormattingResult(
                pdf_path=pdf_path,
                latex_source="",
                ieee_compliant=False,
                fallback_used=True,
                error=None,
                compile_log="Used ReportLab fallback (pdflatex unavailable or failed)",
            )
        except Exception as exc:
            return FormattingResult(
                error=f"Both LaTeX and ReportLab fallback failed: {exc}",
                fallback_used=True,
            )

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_authors(authors: list[AuthorInfo | dict]) -> list[AuthorInfo]:
        """Convert author dicts to AuthorInfo dataclass instances."""
        result = []
        for a in authors:
            if isinstance(a, AuthorInfo):
                result.append(a)
            elif isinstance(a, dict):
                result.append(AuthorInfo(
                    name=a.get("name", "Author"),
                    affiliation=a.get("affiliation", ""),
                    location=a.get("location", ""),
                    email=a.get("email", ""),
                ))
            else:
                result.append(AuthorInfo(name=str(a)))
        return result if result else [AuthorInfo()]

    @staticmethod
    def _build_references(
        paper_refs: list[dict[str, Any]], refs_text: str
    ) -> list[Reference]:
        """Build Reference objects from arXiv paper dicts + any inline refs."""
        refs: list[Reference] = []

        # From arXiv paper metadata
        for i, p in enumerate(paper_refs, start=1):
            authors_str = ", ".join(p.get("authors", [])) if isinstance(p.get("authors"), list) else p.get("authors", "")
            refs.append(Reference(
                index=i,
                authors=authors_str,
                title=p.get("title", ""),
                venue=p.get("journal", p.get("venue", "")),
                year=p.get("year", p.get("published", "")[:4] if p.get("published") else ""),
                link=p.get("link", p.get("url", "")),
            ))

        # Parse additional refs from section text if no structured refs given
        if not refs and refs_text:
            for i, line in enumerate(refs_text.strip().splitlines(), start=1):
                line = line.strip()
                if line and not line.startswith("["):
                    refs.append(Reference(index=i, title=line))
                elif line:
                    # Strip "[N] " prefix
                    cleaned = re.sub(r"^\[\d+\]\s*", "", line)
                    refs.append(Reference(index=i, title=cleaned))

        return refs

    @staticmethod
    def _guess_keywords(title: str, abstract: str) -> list[str]:
        """
        Extract dynamic keywords from title and abstract.
        
        Strategy:
        1. Extract noun phrases from title and abstract
        2. Filter by relevance and uniqueness
        3. Return top 5-6 keywords
        """
        import re
        from collections import Counter
        
        # Combine title and abstract for analysis
        full_text = f"{title}. {abstract}"
        
        # Extract capitalized phrases (likely important terms)
        # Match capitalized words and their sequences
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', full_text)
        
        # Common stop words to filter out
        stop_words = {
            'The', 'A', 'An', 'Is', 'Are', 'Was', 'Were', 'Be', 'Being',
            'Been', 'Have', 'Has', 'Had', 'Do', 'Does', 'Did', 'Should',
            'Would', 'Could', 'Can', 'May', 'Might', 'Must', 'And', 'Or',
            'But', 'In', 'On', 'At', 'To', 'For', 'Of', 'With', 'By', 'From',
            'About', 'As', 'Into', 'Through', 'During', 'This', 'That', 'These',
            'Those', 'Which', 'Who', 'What', 'When', 'Where', 'Why', 'How',
            'All', 'Each', 'Every', 'Both', 'Few', 'More', 'Most', 'Other',
            'Some', 'Such', 'No', 'Nor', 'Not', 'Only', 'Same', 'So', 'Than',
            'Too', 'Very', 'Up', 'Down', 'Out', 'Over', 'Under', 'Again',
            'Further', 'Then', 'Once', 'Here', 'There', 'Abstract', 'Introduction',
            'Conclusion', 'Paper', 'System', 'Method', 'Approach', 'Based',
            'Proposed', 'Novel', 'New', 'Research', 'Study', 'Analysis',
        }
        
        # Filter out stop words and phrases that are too short or too long
        keywords = []
        seen = set()
        
        for phrase in capitalized_phrases:
            if phrase not in stop_words and phrase not in seen and len(phrase) > 1:
                keywords.append(phrase)
                seen.add(phrase)
        
        # If we have title keywords, prioritize those
        title_words = title.split()
        title_keywords = []
        for word in title_words:
            if len(word) > 3 and word not in stop_words and word not in seen:
                title_keywords.append(word)
                seen.add(word)
        
        # Combine: title keywords first, then abstract keywords
        result_keywords = title_keywords + keywords
        
        # If still not enough, add the full title if not too long
        if len(result_keywords) < 4 and len(title) < 80:
            result_keywords.insert(0, title)
        
        # Look for topic-specific technical terms in abstract
        technical_terms = [
            "Machine Learning", "Deep Learning", "Neural Network",
            "Artificial Intelligence", "Natural Language Processing",
            "Computer Vision", "Reinforcement Learning", "Transformer",
            "Cybersecurity", "Blockchain", "IoT", "Cloud Computing",
            "Zero Trust", "Quantum", "Anomaly Detection", "Detection System",
            "Security", "Network", "Data Analysis", "Optimization", "Algorithm",
            "Framework", "Architecture", "Classification", "Recognition",
            "Prediction", "Clustering", "Segmentation", "Vision",
        ]
        
        for term in technical_terms:
            if term.lower() in abstract.lower() and term not in result_keywords:
                result_keywords.append(term)
        
        # Remove duplicates while preserving order
        final_keywords = []
        final_seen = set()
        for kw in result_keywords:
            kw_lower = kw.lower()
            if kw_lower not in final_seen:
                final_keywords.append(kw)
                final_seen.add(kw_lower)
        
        # Return top 4-6 keywords (IEEE standard)
        return final_keywords[:6] if final_keywords else ["Research", "Analysis", "System"]
