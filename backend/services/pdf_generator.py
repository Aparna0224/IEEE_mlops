r"""
PDF Generation Service — LaTeX-first pipeline
──────────────────────────────────────────────

Compiles LaTeX into a properly formatted IEEE PDF.

Strategy (in priority order):
  1. Local pdflatex  — if installed
  2. latexonline.cc API — online compilation fallback
  3. Return None — caller must surface the .tex file

Public API
----------
PDFGenerator.generate(latex_source, task_id) -> Optional[str]
    Synchronous local-only compilation.
    Returns absolute path to outputs/{task_id}.pdf, or None on failure.

await PDFGenerator.generate_async(latex_source, task_id) -> Optional[str]
    Full pipeline: local pdflatex first, then online fallback.
    Returns absolute path, or None if both strategies fail.

PDFGenerator.pdflatex_version() -> Optional[str]
    Return the pdflatex version string, or None if not installed.
"""

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ordered list of paths searched for IEEEtran.cls
_IEEETRAN_SEARCH_PATHS = [
    Path("IEEEtran.cls"),
    Path("backend/IEEEtran.cls"),
    Path("assets/IEEEtran.cls"),
    Path("/usr/share/texmf/tex/latex/IEEEtran/IEEEtran.cls"),
    Path("/Library/TeX/texmf-local/tex/latex/IEEEtran/IEEEtran.cls"),
]

OUTPUT_DIR = Path("outputs")

# latexonline.cc compilation endpoint
_LATEXONLINE_URL = "https://latexonline.cc/compile"
# Timeout for the online request (seconds)
_ONLINE_TIMEOUT = 120


def _find_ieeetran() -> Optional[Path]:
    """Return the first IEEEtran.cls found in well-known local paths, or None."""
    for p in _IEEETRAN_SEARCH_PATHS:
        if p.exists():
            return p.resolve()
    # Also check texlive/texmf trees via kpsewhich if available
    try:
        result = subprocess.run(
            ["kpsewhich", "IEEEtran.cls"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            path = Path(result.stdout.strip())
            if path.exists():
                return path
    except Exception:
        pass
    logger.warning("[PDFGenerator] IEEEtran.cls not found in any search path")
    return None


def _build_latex_in_tempdir(latex_source: str) -> tuple:
    """
    Write *latex_source* to a fresh temp directory and copy IEEEtran.cls if
    available.

    Returns (build_dir, tex_file) — caller is responsible for cleanup.
    """
    build_dir = Path(tempfile.mkdtemp(prefix="latex_build_"))
    tex_file = build_dir / "paper.tex"
    tex_file.write_text(latex_source, encoding="utf-8")

    cls_path = _find_ieeetran()
    if cls_path:
        shutil.copy(cls_path, build_dir / "IEEEtran.cls")
        logger.info("[PDFGenerator] Using IEEEtran.cls from %s", cls_path)
    else:
        logger.info("[PDFGenerator] IEEEtran.cls not found — relying on system texlive")

    return build_dir, tex_file


class PDFGenerator:
    """Compiles LaTeX to PDF — local pdflatex first, online API fallback."""

    # ── synchronous local compilation ──────────────────────────────────────

    @classmethod
    def generate(cls, latex_source: str, task_id: str) -> Optional[str]:
        """
        Compile *latex_source* locally with pdflatex.

        Runs pdflatex twice to resolve \\cite and \\ref cross-references.
        Saves the result to outputs/{task_id}.pdf.

        Returns the absolute path on success, None on failure.
        """
        if not cls.pdflatex_version():
            logger.warning(
                "[PDFGenerator] pdflatex not found — cannot compile PDF for task %s", task_id
            )
            return None

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        final_pdf = OUTPUT_DIR / f"{task_id}.pdf"

        build_dir, tex_file = _build_latex_in_tempdir(latex_source)
        try:
            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_file),
            ]

            for pass_num in (1, 2):
                logger.info("[PDFGenerator] pdflatex pass %d for task %s", pass_num, task_id)
                proc = subprocess.run(
                    cmd,
                    cwd=str(build_dir),
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if proc.returncode != 0:
                    last_lines = "\n".join(proc.stdout.splitlines()[-30:])
                    logger.error(
                        "[PDFGenerator] pdflatex pass %d failed for task %s.\n%s",
                        pass_num, task_id, last_lines,
                    )
                    return None

            built_pdf = build_dir / "paper.pdf"
            if not built_pdf.exists():
                logger.error(
                    "[PDFGenerator] pdflatex exited 0 but paper.pdf not found (task %s)", task_id
                )
                return None

            shutil.copy(built_pdf, final_pdf)
            logger.info("[PDFGenerator] PDF written to %s", final_pdf)
            return str(final_pdf.resolve())

        except subprocess.TimeoutExpired:
            logger.error("[PDFGenerator] pdflatex timed out for task %s", task_id)
            return None
        except FileNotFoundError:
            logger.error(
                "[PDFGenerator] pdflatex executable not found. "
                "Install: brew install basictex (macOS) or apt install texlive-latex-base (Linux)"
            )
            return None
        except Exception as exc:
            logger.error(
                "[PDFGenerator] Unexpected compilation error for task %s: %s", task_id, exc
            )
            return None
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

    # ── async pipeline: local → online fallback ──────────────────────────────

    @classmethod
    async def generate_async(cls, latex_source: str, task_id: str) -> Optional[str]:
        """
        Full PDF generation pipeline (async).

        1. Try local pdflatex in a thread pool.
        2. If that fails or pdflatex is absent, try the latexonline.cc online API.
        3. Return absolute path to outputs/{task_id}.pdf, or None if both fail.
        """
        loop = asyncio.get_event_loop()
        pdf_path = await loop.run_in_executor(None, cls.generate, latex_source, task_id)
        if pdf_path:
            return pdf_path

        logger.info(
            "[PDFGenerator] Local compilation unavailable — trying latexonline.cc for task %s",
            task_id,
        )
        return await cls._compile_online(latex_source, task_id)

    @classmethod
    async def _compile_online(cls, latex_source: str, task_id: str) -> Optional[str]:
        """
        Compile *latex_source* using the latexonline.cc API.

        Sends the .tex file as a multipart form POST and saves the PDF
        response to outputs/{task_id}.pdf.
        """
        try:
            import aiohttp  # optional dependency
        except ImportError:
            logger.error(
                "[PDFGenerator] aiohttp is not installed — online compilation unavailable. "
                "Run: pip install aiohttp"
            )
            return None

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        final_pdf = OUTPUT_DIR / f"{task_id}.pdf"

        with tempfile.NamedTemporaryFile(
            suffix=".tex", mode="w", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(latex_source)
            tmp_path = Path(tmp.name)

        try:
            timeout = aiohttp.ClientTimeout(total=_ONLINE_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                with open(tmp_path, "rb") as tex_fh:
                    form = aiohttp.FormData()
                    form.add_field(
                        "file",
                        tex_fh,
                        filename="paper.tex",
                        content_type="application/x-tex",
                    )
                    logger.info("[PDFGenerator] Sending to latexonline.cc (task %s)", task_id)
                    async with session.post(_LATEXONLINE_URL, data=form) as resp:
                        if resp.status != 200:
                            logger.error(
                                "[PDFGenerator] latexonline.cc returned HTTP %d for task %s",
                                resp.status, task_id,
                            )
                            return None
                        content_type = resp.headers.get("Content-Type", "")
                        if "pdf" not in content_type.lower():
                            body = await resp.text()
                            logger.error(
                                "[PDFGenerator] latexonline.cc did not return a PDF "
                                "(Content-Type: %s) for task %s. Body: %s",
                                content_type, task_id, body[:300],
                            )
                            return None
                        pdf_bytes = await resp.read()

            final_pdf.write_bytes(pdf_bytes)
            logger.info(
                "[PDFGenerator] Online PDF saved to %s (%d bytes)",
                final_pdf, len(pdf_bytes),
            )
            return str(final_pdf.resolve())

        except asyncio.TimeoutError:
            logger.error("[PDFGenerator] latexonline.cc request timed out for task %s", task_id)
            return None
        except Exception as exc:
            logger.error("[PDFGenerator] latexonline.cc error for task %s: %s", task_id, exc)
            return None
        finally:
            tmp_path.unlink(missing_ok=True)

    # ── utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def pdflatex_version() -> Optional[str]:
        """
        Return the pdflatex version string (e.g. "pdfTeX 3.141592653-2.6-1.40.25 …"),
        or None if pdflatex is not installed or not on PATH.
        """
        try:
            result = subprocess.run(
                ["pdflatex", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.splitlines()[0].strip()
        except Exception:
            pass
        return None

    # ── legacy shims (kept so old call sites continue to work) ───────────────

    @staticmethod
    def check_pdflatex() -> bool:
        """Legacy shim — prefer pdflatex_version() for richer information."""
        return PDFGenerator.pdflatex_version() is not None

    def compile_latex(
        self,
        latex_source: str,
        output_name: str = "paper.pdf",
        image_files: list = None,
    ) -> Optional[str]:
        """Legacy instance-method shim — delegates to PDFGenerator.generate()."""
        task_id = Path(output_name).stem or "paper"
        return PDFGenerator.generate(latex_source, task_id)
