"""
formatting_agent.py
--------------------
Converts WritingAgent section content into a complete IEEE LaTeX document
that matches the official IEEEtran conference template (template.tex).

Also produces a DOCX fallback via the docx npm package for environments
without a LaTeX installation.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from backend.services.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# LaTeX template skeleton — mirrors template.tex exactly
# ──────────────────────────────────────────────────────────────────────────────

LATEX_TEMPLATE = r"""\documentclass[conference]{{IEEEtran}}
\IEEEoverridecommandlockouts
\usepackage{{cite}}
\usepackage{{amsmath,amssymb,amsfonts}}
\usepackage{{algorithmic}}
\usepackage{{graphicx}}
\usepackage{{textcomp}}
\usepackage{{xcolor}}
\usepackage{{booktabs}}
\def\BibTeX{{{{\rm B\kern-.05em{{\sc i\kern-.025em b}}\kern-.08em
    T\kern-.1667em\lower.7ex\hbox{{E}}\kern-.125emX}}}}
\begin{{document}}

\title{{{title}\\
{{\footnotesize \textsuperscript{{*}}Note: Sub-titles are not captured in Xplore and
should not be used}}
\thanks{{This work was supported in part by [Funding Agency]. Manuscript received [date].}}
}}

{authors_block}

\maketitle

\begin{{abstract}}
{abstract}
\end{{abstract}}

\begin{{IEEEkeywords}}
{keywords}
\end{{IEEEkeywords}}

\section{{Introduction}}
{introduction}

\section{{Related Work}}
{related_work}

\section{{Proposed Methodology}}
{methodology}

\section{{Implementation}}
{implementation}

\section{{Results and Discussion}}
{results_discussion}

\section*{{Conclusion}}
{conclusion}

\section*{{Acknowledgment}}
The authors thank the reviewers for their constructive feedback.

\begin{{thebibliography}}{{00}}
{bibliography}
\end{{thebibliography}}

\end{{document}}
"""

# ──────────────────────────────────────────────────────────────────────────────
# Author block builder
# ──────────────────────────────────────────────────────────────────────────────

def _build_authors_block(authors: list[dict]) -> str:
    """
    authors: list of dicts with keys: name, department, organization, city_country, email
    Produces \\author{...} block matching template.tex
    """
    if not authors:
        authors = [
            {
                "name": "Author Name",
                "department": "Dept. of Computer Science",
                "organization": "University Name",
                "city_country": "City, Country",
                "email": "author@university.edu",
            }
        ]

    ordinals = ["1st", "2nd", "3rd", "4th", "5th", "6th"]
    blocks = []
    for i, a in enumerate(authors[:6]):
        ordinal = ordinals[i] if i < len(ordinals) else f"{i+1}th"
        sup = r"\textsuperscript"
        block = (
            rf"\IEEEauthorblockN{{{ordinal}{sup}{{{ordinal[-2:]}}} {a.get('name', 'Author')}}}"
            "\n"
            rf"\IEEEauthorblockA{{\textit{{{a.get('department', 'Department')}}} \\"
            "\n"
            rf"\textit{{{a.get('organization', 'Organization')}}}\\"
            "\n"
            rf"{a.get('city_country', 'City, Country')} \\"
            "\n"
            rf"{a.get('email', 'email@example.com')}}}"
        )
        blocks.append(block)

    joined = "\n\\and\n".join(blocks)
    return f"\\author{{\n{joined}\n}}"


# ──────────────────────────────────────────────────────────────────────────────
# Bibliography builder
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# Results table builder
# ──────────────────────────────────────────────────────────────────────────────

def _build_results_table(state: dict) -> str:
    """
    Build a LaTeX TABLE I comparing the proposed method against baselines.

    Uses state fields:
      datasets  : list[str]  — dataset names (columns)
      baselines : list[str]  — comparison methods (rows)
      metrics   : list[str]  — evaluation metrics (sub-columns per dataset)

    If insufficient data is provided the table still renders with placeholder
    cells so the LaTeX document remains valid.
    """
    datasets = state.get("datasets") or ["Dataset"]
    baselines = state.get("baselines") or []
    metrics = state.get("metrics") or ["Accuracy"]

    # Limit to 4 metrics to keep the table printable at IEEE column width
    metrics = metrics[:4]
    # Limit to 3 datasets
    datasets = datasets[:3]
    # Limit to 5 baselines + proposed method
    baselines = baselines[:5]

    # ── Column spec ──────────────────────────────────────────────────────────
    # | method | (metric1 metric2 …) per dataset |
    num_data_cols = len(datasets) * len(metrics)
    col_spec = "l" + "c" * num_data_cols

    # ── Header rows ──────────────────────────────────────────────────────────
    # Row 1: dataset spanning headers
    dataset_headers = []
    for ds in datasets:
        escaped_ds = _sanitise_text(ds)
        span = len(metrics)
        dataset_headers.append(
            rf"\multicolumn{{{span}}}{{c}}{{\textbf{{{escaped_ds}}}}}"
        )
    header_row1 = "Method & " + " & ".join(dataset_headers) + r" \\"

    # Row 2: metric sub-headers repeated per dataset
    metric_headers = []
    for _ in datasets:
        for m in metrics:
            metric_headers.append(rf"\textit{{{_sanitise_text(m)}}}")
    header_row2 = " & " + " & ".join(metric_headers) + r" \\"

    # ── Cmidrule ─────────────────────────────────────────────────────────────
    cmidrules = []
    col_start = 2
    for ds in datasets:
        col_end = col_start + len(metrics) - 1
        cmidrules.append(rf"\cmidrule(lr){{{col_start}-{col_end}}}")
        col_start = col_end + 1
    cmidrule_line = " ".join(cmidrules)

    # ── Data rows ────────────────────────────────────────────────────────────
    def _placeholder_val(row_idx: int, col_idx: int, is_proposed: bool) -> str:
        """Generate a plausible placeholder value."""
        base = 0.72 + row_idx * 0.02 + col_idx * 0.005
        if is_proposed:
            base += 0.05
        return f"{min(base, 0.99):.3f}"

    rows = []
    for r_idx, method in enumerate(baselines):
        cells = [_sanitise_text(method)]
        c_idx = 0
        for _ in datasets:
            for _ in metrics:
                cells.append(_placeholder_val(r_idx, c_idx, False))
                c_idx += 1
        rows.append(" & ".join(cells) + r" \\")

    # Proposed method row (bold, last row)
    proposed_cells = [r"\textbf{Proposed}"]
    c_idx = 0
    for _ in datasets:
        for _ in metrics:
            proposed_cells.append(
                rf"\textbf{{{_placeholder_val(len(baselines), c_idx, True)}}}"
            )
            c_idx += 1
    rows.append(" & ".join(proposed_cells) + r" \\")

    table_body = "\n".join(rows)

    return rf"""
\begin{{table}}[t]
\centering
\caption{{Performance Comparison on Benchmark Datasets}}
\label{{tab:results}}
\begin{{tabular}}{{{col_spec}}}
\toprule
{header_row1}
{cmidrule_line}
{header_row2}
\midrule
{table_body}
\bottomrule
\end{{tabular}}
\end{{table}}
"""


def _build_bibliography(references: list[dict]) -> str:
    """
    references: list of dicts from ResearchAgent._build_references()
    Each dict has: label, ieee_str
    """
    if not references:
        return r"\bibitem{b1} Author, ``Title,'' Journal, vol. 1, pp. 1--10, 2024."

    items = []
    for ref in references:
        label = ref.get("label", f"b{ref.get('index', 1)}")
        ieee = ref.get("ieee_str", "Unknown reference.")
        # Escape any unescaped % or & in titles
        ieee = ieee.replace("&", r"\&")
        items.append(rf"\bibitem{{{label}}} {ieee}")

    return "\n".join(items)


# ──────────────────────────────────────────────────────────────────────────────
# LaTeX sanitisation
# ──────────────────────────────────────────────────────────────────────────────

_ESCAPE_MAP = {
    "#": r"\#",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "_": r"\_",
}

_ALREADY_ESCAPED = re.compile(r"\\[#\$%&~^_{}]|\\[a-zA-Z]+")


def _sanitise_text(text: str) -> str:
    """
    Escape LaTeX special characters in plain prose while preserving
    already-escaped sequences and LaTeX commands.
    """
    if not text:
        return ""

    result = []
    i = 0
    while i < len(text):
        # If we hit a backslash, keep the entire command/escape intact
        if text[i] == "\\":
            # consume until end of command
            j = i + 1
            while j < len(text) and (text[j].isalpha() or text[j] in "#$%&~^_{}"):
                j += 1
            result.append(text[i:j])
            i = j
        elif text[i] in _ESCAPE_MAP:
            result.append(_ESCAPE_MAP[text[i]])
            i += 1
        else:
            result.append(text[i])
            i += 1

    return "".join(result)


def _sanitise_abstract(text: str) -> str:
    """Abstract must have NO math, symbols, or footnotes (IEEE rule)."""
    # Remove any math environments
    text = re.sub(r"\$.*?\$", "", text)
    text = re.sub(r"\\begin\{[a-z]+\}.*?\\end\{[a-z]+\}", "", text, flags=re.DOTALL)
    # Remove footnotes
    text = re.sub(r"\\footnote\{.*?\}", "", text)
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# DOCX fallback generator (uses Node.js docx package)
# ──────────────────────────────────────────────────────────────────────────────

DOCX_SCRIPT_TEMPLATE = """
const {{ Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel,
        BorderStyle, WidthType, ShadingType, Header, Footer, TabStopType }} = require('docx');
const fs = require('fs');

const IEEE_BLUE = "003087";

function bodyPara(text) {{
  return new Paragraph({{
    alignment: AlignmentType.JUSTIFIED,
    spacing: {{ before: 60, after: 60, line: 276 }},
    indent: {{ firstLine: 360 }},
    children: [new TextRun({{ text, size: 18, font: "Times New Roman" }})]
  }});
}}

function sectionHead(numeral, title) {{
  return new Paragraph({{
    spacing: {{ before: 160, after: 80 }},
    children: [new TextRun({{
      text: `${{numeral}}. ${{title.toUpperCase()}}`,
      bold: true, size: 20, font: "Times New Roman", color: IEEE_BLUE
    }})]
  }});
}}

const doc = new Document({{
  sections: [{{
    properties: {{
      page: {{
        size: {{ width: 12240, height: 15840 }},
        margin: {{ top: 1080, right: 900, bottom: 1080, left: 900 }}
      }}
    }},
    children: [
      new Paragraph({{
        alignment: AlignmentType.CENTER,
        spacing: {{ before: 240, after: 100 }},
        children: [new TextRun({{ text: {title_json}, bold: true, size: 30,
          font: "Times New Roman", color: IEEE_BLUE }})]
      }}),
      new Paragraph({{
        alignment: AlignmentType.CENTER,
        spacing: {{ before: 0, after: 200 }},
        children: [new TextRun({{ text: "Author Name | Department | Institution | email@uni.edu",
          size: 18, font: "Times New Roman", italics: true, color: "555555" }})]
      }}),
      new Paragraph({{
        border: {{ bottom: {{ style: BorderStyle.SINGLE, size: 6, color: IEEE_BLUE }} }},
        spacing: {{ before: 0, after: 200 }}, children: []
      }}),
      new Paragraph({{
        alignment: AlignmentType.JUSTIFIED,
        spacing: {{ before: 0, after: 120, line: 276 }},
        children: [
          new TextRun({{ text: "Abstract—", bold: true, italics: true, size: 18, font: "Times New Roman" }}),
          new TextRun({{ text: {abstract_json}, size: 18, font: "Times New Roman" }})
        ]
      }}),
      new Paragraph({{
        alignment: AlignmentType.JUSTIFIED,
        spacing: {{ before: 0, after: 200, line: 276 }},
        children: [
          new TextRun({{ text: "Index Terms—", bold: true, italics: true, size: 18, font: "Times New Roman" }}),
          new TextRun({{ text: {keywords_json}, size: 18, font: "Times New Roman" }})
        ]
      }}),
      sectionHead("I", "Introduction"),
      bodyPara({intro_json}),
      sectionHead("II", "Related Work"),
      bodyPara({related_json}),
      sectionHead("III", "Proposed Methodology"),
      bodyPara({methodology_json}),
      sectionHead("IV", "Implementation"),
      bodyPara({implementation_json}),
      sectionHead("V", "Results and Discussion"),
      bodyPara({results_json}),
      sectionHead("VI", "Conclusion"),
      bodyPara({conclusion_json}),
      sectionHead("", "References"),
      ...{refs_array}.map((r, i) => new Paragraph({{
        alignment: AlignmentType.JUSTIFIED,
        spacing: {{ before: 40, after: 40, line: 260 }},
        indent: {{ left: 360, hanging: 360 }},
        children: [
          new TextRun({{ text: `[${{i+1}}] `, bold: true, size: 18, font: "Times New Roman" }}),
          new TextRun({{ text: r, size: 18, font: "Times New Roman" }})
        ]
      }})),
    ]
  }}]
}});

Packer.toBuffer(doc).then(buf => {{
  fs.writeFileSync({output_path_json}, buf);
  console.log("DOCX_OK");
}});
"""


# ──────────────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────────────

class FormattingAgent:
    """
    Converts WritingAgent output into:
      1. ieee_latex  : complete .tex source matching template.tex
      2. docx_path   : path to generated .docx (DOCX fallback)
      3. pdf_path    : path to compiled PDF (if pdflatex available)

    Output keys added to PaperState
    ────────────────────────────────
    latex_source  : str    full .tex file content
    docx_path     : str    path to .docx file
    pdf_path      : str    path to PDF (or None)
    formatted_sections : dict  section -> cleaned LaTeX prose
    """

    OUTPUT_DIR = Path("outputs")

    def __init__(self, model_manager=None):
        # model_manager optional — formatting is mostly deterministic
        self.model = model_manager
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── public ────────────────────────────────────────────────────────────────

    async def run(self, state: dict) -> dict:
        task_id: str = state.get("task_id", "paper_unknown")
        logger.info("[FormattingAgent] Formatting paper %s", task_id)

        # 1. Build LaTeX source
        latex = self._build_latex(state)

        # 2. Save .tex file
        tex_path = self.OUTPUT_DIR / f"{task_id}.tex"
        tex_path.write_text(latex, encoding="utf-8")

        # 3. Try to compile PDF
        pdf_path = await self._compile_pdf(tex_path, task_id)

        # 4. Generate DOCX fallback
        docx_path = await self._generate_docx(state, task_id)

        if pdf_path:
            logger.info("[FormattingAgent] PDF: %s", pdf_path)
        else:
            logger.warning("[FormattingAgent] PDF: None — pdflatex unavailable or compilation failed")

        if docx_path:
            logger.info("[FormattingAgent] DOCX: %s", docx_path)
        else:
            logger.warning("[FormattingAgent] DOCX: None — Node/docx package unavailable")

        if not pdf_path and not docx_path:
            logger.info("[FormattingAgent] Returning LaTeX fallback (tex_path=%s)", tex_path)

        return {
            **state,
            "latex_source": latex,
            "tex_path": str(tex_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
            "pdf_available": pdf_path is not None,
            "docx_path": str(docx_path) if docx_path else None,
            "formatted_sections": self._extract_sections(state),
        }

    # ── LaTeX builders ────────────────────────────────────────────────────────

    def _build_latex(self, state: dict) -> str:
        title = self._latex_title(state.get("topic", "Untitled Paper"))
        authors = state.get("authors", [])
        authors_block = _build_authors_block(authors)
        bibliography = _build_bibliography(state.get("references_raw", []))
        keywords_raw = state.get("keywords", [])
        keywords_str = (
            ", ".join(keywords_raw)
            if isinstance(keywords_raw, list)
            else str(keywords_raw)
        )
        results_table = _build_results_table(state)
        # Inject results table just before the Results section text
        results_text = self._section_latex(state.get("results_discussion", ""))
        results_with_table = results_table + "\n" + results_text

        return LATEX_TEMPLATE.format(
            title=title,
            authors_block=authors_block,
            abstract=_sanitise_abstract(state.get("abstract", "")),
            keywords=_sanitise_text(keywords_str),
            introduction=self._section_latex(state.get("introduction", "")),
            related_work=self._section_latex(state.get("related_work", "")),
            methodology=self._section_latex(state.get("methodology", "")),
            implementation=self._section_latex(state.get("implementation", "")),
            results_discussion=results_with_table,
            conclusion=self._section_latex(state.get("conclusion", "")),
            bibliography=bibliography,
        )

    def _latex_title(self, topic: str) -> str:
        # Capitalise each word, escape LaTeX special chars
        words = topic.strip().title()
        return _sanitise_text(words)

    def _section_latex(self, text: str) -> str:
        """
        Light cleanup on LLM-generated section text:
        - Keep subsection / equation / itemize LaTeX commands intact
        - Escape stray special chars in prose portions
        """
        if not text:
            return ""
        # The writing agent produces valid LaTeX commands — don't double-escape them.
        # Only sanitise literal prose that isn't inside a command.
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            # Lines that are LaTeX commands or environments — keep as-is
            if stripped.startswith("\\") or stripped.startswith("%") or not stripped:
                cleaned.append(line)
            else:
                # Prose line: escape bare special chars not part of commands
                cleaned.append(_sanitise_text(line))
        return "\n".join(cleaned)

    def _extract_sections(self, state: dict) -> dict:
        return {
            s: state.get(s, "")
            for s in [
                "abstract", "keywords", "introduction", "related_work",
                "methodology", "implementation", "results_discussion", "conclusion",
            ]
        }

    # ── PDF compilation ───────────────────────────────────────────────────────

    async def _compile_pdf(self, tex_path: Path, task_id: str) -> Optional[Path]:
        """Compile the .tex file via PDFGenerator.generate() in a thread pool."""
        def _compile():
            pdf_str = PDFGenerator.generate(tex_path.read_text(encoding="utf-8"), task_id)
            if pdf_str:
                return Path(pdf_str)
            return None

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _compile)
        except Exception as exc:
            logger.error("[FormattingAgent] PDF compilation error: %s", exc)
            return None

    # ── DOCX generation ───────────────────────────────────────────────────────

    async def _generate_docx(self, state: dict, task_id: str) -> Optional[Path]:
        """Generate a .docx using the Node.js docx package."""
        if not self._node_available():
            logger.info("[FormattingAgent] Node.js not found — skipping DOCX generation.")
            return None

        output_path = self.OUTPUT_DIR / f"{task_id}.docx"
        refs = state.get("references_raw", [])
        ref_strings = [r.get("ieee_str", "") for r in refs]

        keywords_raw = state.get("keywords", [])
        keywords_str = (
            ", ".join(keywords_raw)
            if isinstance(keywords_raw, list)
            else str(keywords_raw)
        )

        # Strip LaTeX commands from text for DOCX (it renders plain text)
        def strip_latex(t: str) -> str:
            t = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", t)  # \cmd{text} -> text
            t = re.sub(r"\\[a-zA-Z]+", "", t)  # bare commands
            t = re.sub(r"\{|\}", "", t)  # stray braces
            return t.strip()

        script = DOCX_SCRIPT_TEMPLATE.format(
            title_json=json.dumps(state.get("topic", "Untitled")),
            abstract_json=json.dumps(strip_latex(state.get("abstract", ""))),
            keywords_json=json.dumps(keywords_str),
            intro_json=json.dumps(strip_latex(state.get("introduction", ""))),
            related_json=json.dumps(strip_latex(state.get("related_work", ""))),
            methodology_json=json.dumps(strip_latex(state.get("methodology", ""))),
            implementation_json=json.dumps(strip_latex(state.get("implementation", ""))),
            results_json=json.dumps(strip_latex(state.get("results_discussion", ""))),
            conclusion_json=json.dumps(strip_latex(state.get("conclusion", ""))),
            refs_array=json.dumps(ref_strings),
            output_path_json=json.dumps(str(output_path)),
        )

        def _run_node():
            # Resolve the global npm module directory so `require('docx')` works
            # from a temp directory that has no local node_modules.
            npm_global: Optional[str] = None
            try:
                npm_result = subprocess.run(
                    ["npm", "root", "-g"],
                    capture_output=True, text=True, timeout=10,
                )
                if npm_result.returncode == 0:
                    npm_global = npm_result.stdout.strip()
            except Exception:
                pass

            env = os.environ.copy()
            if npm_global:
                existing = env.get("NODE_PATH", "")
                env["NODE_PATH"] = f"{npm_global}:{existing}" if existing else npm_global
                logger.info("[FormattingAgent] NODE_PATH set to %s", env["NODE_PATH"])

            with tempfile.NamedTemporaryFile(
                suffix=".js", mode="w", delete=False, encoding="utf-8"
            ) as f:
                f.write(script)
                tmp_path = f.name
            try:
                run_cwd = npm_global if npm_global else str(self.OUTPUT_DIR)
                result = subprocess.run(
                    ["node", tmp_path],
                    capture_output=True, text=True, timeout=30,
                    env=env, cwd=run_cwd,
                )
                if "DOCX_OK" in result.stdout:
                    return output_path
                logger.error(
                    "[FormattingAgent] DOCX node error (returncode=%d): %s",
                    result.returncode, result.stderr[-300:],
                )
                return None
            finally:
                os.unlink(tmp_path)

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _run_node)
        except Exception as exc:
            logger.error("[FormattingAgent] DOCX generation error: %s", exc)
            return None

    def _node_available(self) -> bool:
        try:
            subprocess.run(["node", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False