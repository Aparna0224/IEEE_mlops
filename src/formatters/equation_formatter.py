"""
EquationFormatter – Markdown-math → IEEE-compliant LaTeX converter
──────────────────────────────────────────────────────────────────
Detects mathematical expressions written in Markdown / raw-TeX notation
and converts them into proper IEEE-ready LaTeX:

  \\[ … \\]          →  \\begin{equation} … \\label{eq:auto_N} \\end{equation}
  \\( … \\)          →  $…$
  $$ … $$            →  \\begin{equation} … \\label{eq:auto_N} \\end{equation}
  Bare $ … $         →  preserved (already valid inline math)

Additionally:
  • Auto-numbers every display equation with sequential labels.
  • Escapes %, _, &, # **outside** math zones so equations stay intact.
  • Strips residual Markdown artefacts (bold **, italic __, etc.) from
    non-math text while preserving them inside math.
  • Provides a reference map  {label → equation_number}  for \\ref{} use.

Usage::

    from src.formatters.equation_formatter import EquationFormatter

    fmt = EquationFormatter()
    result = fmt.format(raw_content)

    result.content          # cleaned LaTeX-safe text
    result.equation_count   # total display equations found
    result.label_map        # {"eq:auto_1": 1, …}
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ────────────────────────────────────────────────────────────────────────────
# Result container
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class EquationFormatResult:
    """Output of the EquationFormatter."""
    content: str = ""
    equation_count: int = 0
    inline_count: int = 0
    label_map: dict[str, int] = field(default_factory=dict)


# ────────────────────────────────────────────────────────────────────────────
# Regex patterns
# ────────────────────────────────────────────────────────────────────────────

# Block display math  \[ … \]  (may span multiple lines)
_BLOCK_BRACKET_RE = re.compile(
    r"\\\[\s*\n?(.*?)\n?\s*\\\]",
    re.DOTALL,
)

# Block display math  $$ … $$  (may span multiple lines)
_BLOCK_DOLLAR_RE = re.compile(
    r"\$\$\s*\n?(.*?)\n?\s*\$\$",
    re.DOTALL,
)

# Inline math  \( … \)
_INLINE_PAREN_RE = re.compile(
    r"\\\(\s*(.*?)\s*\\\)",
    re.DOTALL,
)

# Already-valid inline math  $ … $  (single dollar, NOT double)
# We leave these untouched — they're already good LaTeX.
_INLINE_DOLLAR_RE = re.compile(
    r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)",
)

# Markdown bold / italic artefacts that should NOT appear in LaTeX text
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MD_UNDERLINE_BOLD_RE = re.compile(r"__(.+?)__")
_MD_UNDERLINE_ITALIC_RE = re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")

# LaTeX special chars that must be escaped in prose (NOT inside math)
_PROSE_SPECIALS: dict[str, str] = {
    "%": r"\%",
    "&": r"\&",
    "#": r"\#",
    # _ is only escaped outside math; inside math it's a subscript operator
}

# Pattern for the specials above
_PROSE_SPECIAL_RE = re.compile(r"[%&#]")

# Underscore outside math (negative look-behind/ahead for $)
_PROSE_UNDERSCORE_RE = re.compile(r"_")


# ────────────────────────────────────────────────────────────────────────────
# Sentinel used to protect math zones during prose-escaping
# ────────────────────────────────────────────────────────────────────────────

_MATH_PLACEHOLDER = "\x00MATHBLOCK{}\x00"
_MATH_PH_RE = re.compile(r"\x00MATHBLOCK(\d+)\x00")


# ────────────────────────────────────────────────────────────────────────────
# Core class
# ────────────────────────────────────────────────────────────────────────────

class EquationFormatter:
    """
    Convert Markdown / raw-TeX math into IEEE-compliant LaTeX equations.

    Thread-safe: each call to :meth:`format` uses its own counter state.
    """

    # ── public API ────────────────────────────────────────────────────────

    def format(self, raw_content: str) -> EquationFormatResult:
        """
        Process *raw_content* and return cleaned, LaTeX-safe text with
        all equations converted to IEEE format **and** prose characters escaped.

        Use this for standalone usage (e.g. previewing content).
        """
        if not raw_content:
            return EquationFormatResult()

        result = EquationFormatResult()
        text = raw_content

        # ── Step 1: extract & protect existing equation environments ──
        # (so we don't double-process them)
        text, existing_envs = self._protect_existing_environments(text)

        # ── Step 2: convert block equations  \[ … \]  →  equation env ──
        text = self._convert_block_brackets(text, result)

        # ── Step 3: convert block equations  $$ … $$  →  equation env ──
        text = self._convert_block_dollars(text, result)

        # ── Step 4: convert inline  \( … \)  →  $ … $ ────────────────
        text = self._convert_inline_parens(text, result)

        # ── Step 5: protect ALL math zones before prose-escaping ──────
        text, math_zones = self._extract_math_zones(text)

        # ── Step 6: strip leftover Markdown formatting from prose ─────
        text = self._strip_markdown(text)

        # ── Step 7: escape special characters in prose ────────────────
        text = self._escape_prose_specials(text)

        # ── Step 8: restore math zones ────────────────────────────────
        text = self._restore_math_zones(text, math_zones)

        # ── Step 9: restore pre-existing equation environments ────────
        text = self._restore_existing_environments(text, existing_envs)

        result.content = text
        return result

    def convert_math(self, raw_content: str) -> EquationFormatResult:
        """
        Convert Markdown math to IEEE LaTeX format **without** escaping prose.

        Use this when the caller will handle special-char escaping separately
        (e.g. when integrated into IEEEFormattingEngine whose ``_sanitise``
        is already math-aware).
        """
        if not raw_content:
            return EquationFormatResult()

        result = EquationFormatResult()
        text = raw_content

        # Protect existing equation environments
        text, existing_envs = self._protect_existing_environments(text)

        # Convert block equations  \[ … \] → equation env
        text = self._convert_block_brackets(text, result)

        # Convert block equations  $$ … $$ → equation env
        text = self._convert_block_dollars(text, result)

        # Convert inline  \( … \) → $ … $
        text = self._convert_inline_parens(text, result)

        # Strip leftover Markdown formatting
        text, math_zones = self._extract_math_zones(text)
        text = self._strip_markdown(text)
        text = self._restore_math_zones(text, math_zones)

        # Restore pre-existing equation environments
        text = self._restore_existing_environments(text, existing_envs)

        result.content = text
        return result

    # ── Block equation converters ─────────────────────────────────────────

    def _convert_block_brackets(
        self, text: str, result: EquationFormatResult
    ) -> str:
        r"""Convert  \[ … \]  into  \begin{equation}…\end{equation}."""

        def _repl(m: re.Match) -> str:
            result.equation_count += 1
            n = result.equation_count
            label = f"eq:auto_{n}"
            result.label_map[label] = n
            body = m.group(1).strip()
            return (
                f"\\begin{{equation}}\n"
                f"{body}\n"
                f"\\label{{{label}}}\n"
                f"\\end{{equation}}"
            )

        return _BLOCK_BRACKET_RE.sub(_repl, text)

    def _convert_block_dollars(
        self, text: str, result: EquationFormatResult
    ) -> str:
        r"""Convert  $$ … $$  into  \begin{equation}…\end{equation}."""

        def _repl(m: re.Match) -> str:
            result.equation_count += 1
            n = result.equation_count
            label = f"eq:auto_{n}"
            result.label_map[label] = n
            body = m.group(1).strip()
            return (
                f"\\begin{{equation}}\n"
                f"{body}\n"
                f"\\label{{{label}}}\n"
                f"\\end{{equation}}"
            )

        return _BLOCK_DOLLAR_RE.sub(_repl, text)

    # ── Inline equation converter ─────────────────────────────────────────

    @staticmethod
    def _convert_inline_parens(
        text: str, result: EquationFormatResult
    ) -> str:
        r"""Convert  \( … \)  into  $…$."""

        def _repl(m: re.Match) -> str:
            result.inline_count += 1
            body = m.group(1).strip()
            return f"${body}$"

        return _INLINE_PAREN_RE.sub(_repl, text)

    # ── Math-zone protector ───────────────────────────────────────────────

    @staticmethod
    def _extract_math_zones(text: str) -> tuple[str, list[str]]:
        """
        Replace every math span with a placeholder so prose-escaping
        doesn't touch equation internals.

        Math zones detected (in order of greediness):
          1. \\begin{equation} … \\end{equation}
          2. \\begin{align}    … \\end{align}
          3. \\begin{gather}   … \\end{gather}
          4. \\begin{multline} … \\end{multline}
          5. \\begin{eqnarray} … \\end{eqnarray}
          6. $…$  (inline)
        """
        zones: list[str] = []

        # Display environments
        env_re = re.compile(
            r"(\\begin\{(?:equation|align|gather|multline|eqnarray)\*?\}.*?"
            r"\\end\{(?:equation|align|gather|multline|eqnarray)\*?\})",
            re.DOTALL,
        )

        def _stash_env(m: re.Match) -> str:
            zones.append(m.group(0))
            return _MATH_PLACEHOLDER.format(len(zones) - 1)

        text = env_re.sub(_stash_env, text)

        # Inline $…$
        def _stash_inline(m: re.Match) -> str:
            zones.append(m.group(0))
            return _MATH_PLACEHOLDER.format(len(zones) - 1)

        text = _INLINE_DOLLAR_RE.sub(_stash_inline, text)

        return text, zones

    @staticmethod
    def _restore_math_zones(text: str, zones: list[str]) -> str:
        """Put the real math back in place of placeholders."""

        def _repl(m: re.Match) -> str:
            idx = int(m.group(1))
            if 0 <= idx < len(zones):
                return zones[idx]
            return m.group(0)  # safety fallback

        return _MATH_PH_RE.sub(_repl, text)

    # ── Existing environment protector ────────────────────────────────────
    # Prevents double-processing of already-correct \begin{equation} blocks
    # that may appear in the raw content produced by the LLM.

    _EXISTING_ENV_PH = "\x01EXISTINGENV{}\x01"
    _EXISTING_ENV_PH_RE = re.compile(r"\x01EXISTINGENV(\d+)\x01")
    _EXISTING_ENV_RE = re.compile(
        r"(\\begin\{(?:equation|align|gather|multline|eqnarray)\*?\}"
        r".*?"
        r"\\end\{(?:equation|align|gather|multline|eqnarray)\*?\})",
        re.DOTALL,
    )

    @classmethod
    def _protect_existing_environments(
        cls, text: str
    ) -> tuple[str, list[str]]:
        envs: list[str] = []

        def _stash(m: re.Match) -> str:
            envs.append(m.group(0))
            return cls._EXISTING_ENV_PH.format(len(envs) - 1)

        text = cls._EXISTING_ENV_RE.sub(_stash, text)
        return text, envs

    @classmethod
    def _restore_existing_environments(
        cls, text: str, envs: list[str]
    ) -> str:
        def _repl(m: re.Match) -> str:
            idx = int(m.group(1))
            if 0 <= idx < len(envs):
                return envs[idx]
            return m.group(0)

        return cls._EXISTING_ENV_PH_RE.sub(_repl, text)

    # ── Markdown stripper ─────────────────────────────────────────────────

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove Markdown bold / italic markers from prose."""
        text = _MD_BOLD_RE.sub(r"\1", text)
        text = _MD_UNDERLINE_BOLD_RE.sub(r"\1", text)
        text = _MD_ITALIC_RE.sub(r"\1", text)
        # Don't strip single _ here — it'll be escaped as \_
        return text

    # ── Prose special-char escaper ────────────────────────────────────────

    @staticmethod
    def _escape_prose_specials(text: str) -> str:
        """Escape %, &, #, _ in non-math text (placeholders protect math)."""
        # Escape % & #
        text = _PROSE_SPECIAL_RE.sub(
            lambda m: _PROSE_SPECIALS[m.group()], text
        )
        # Escape bare underscores (outside math, which is placeholder'd)
        text = _PROSE_UNDERSCORE_RE.sub(r"\_", text)
        return text
