"""
validation_agent.py
--------------------
Validates the generated IEEE paper against:
  1. Structural completeness  (all required sections present and non-empty)
  2. Content quality          (word counts, no placeholder text, citations present)
  3. IEEE formatting rules    (abstract has no math/symbols, keywords format, etc.)
  4. Regeneration trigger     (requests WritingAgent to redo any failing section)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────────────────────────────────────

MIN_WORD_COUNTS = {
    "abstract": 120,
    "introduction": 300,
    "related_work": 300,
    "methodology": 400,
    "implementation": 200,
    "results_discussion": 400,
    "conclusion": 150,
}

MAX_WORD_COUNTS = {
    "abstract": 300,
}

# Phrases that indicate the LLM returned a placeholder instead of real content
PLACEHOLDER_PATTERNS = [
    r"is an important research direction",
    r"prior studies provide strong baselines",
    r"this section positions the present work",
    r"the methodology formalizes the problem setting",
    r"implementation follows a modular pipeline",
    r"results summarize observed trends",
    r"this paper presents a structured treatment",
    r"\[generation failed",
    r"placeholder",
    r"todo",
    r"\[insert\]",
]

REQUIRED_SECTIONS = [
    "abstract",
    "keywords",
    "introduction",
    "related_work",
    "methodology",
    "implementation",
    "results_discussion",
    "conclusion",
]


# ──────────────────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SectionResult:
    name: str
    passed: bool
    score: float          # 0.0 – 1.0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    overall_passed: bool
    overall_score: float  # 0.0 – 1.0
    sections: dict[str, SectionResult] = field(default_factory=dict)
    ieee_issues: list[str] = field(default_factory=list)
    sections_to_regenerate: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_passed": self.overall_passed,
            "overall_score": round(self.overall_score, 3),
            "sections": {
                k: {
                    "passed": v.passed,
                    "score": round(v.score, 3),
                    "issues": v.issues,
                    "warnings": v.warnings,
                }
                for k, v in self.sections.items()
            },
            "ieee_issues": self.ieee_issues,
            "sections_to_regenerate": self.sections_to_regenerate,
            "summary": self.summary,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────────────

class ValidationAgent:
    """
    Validates paper state and optionally triggers regeneration of weak sections.

    Output keys added to PaperState
    ────────────────────────────────
    validation_report   : dict       full ValidationReport.to_dict()
    validation_passed   : bool
    validation_score    : float
    """

    # Sections scoring below this threshold get regenerated
    REGENERATE_THRESHOLD: float = 0.5
    # Max regeneration attempts per section
    MAX_REGEN_ATTEMPTS: int = 2

    def __init__(self, model_manager=None, writing_agent=None):
        self.model = model_manager
        self.writing_agent = writing_agent  # injected for regeneration

    # ── public ────────────────────────────────────────────────────────────────

    async def run(self, state: dict) -> dict:
        logger.info("[ValidationAgent] Starting validation.")

        report = self._validate(state)
        logger.info(
            "[ValidationAgent] Score: %.2f | Passed: %s | To regenerate: %s",
            report.overall_score,
            report.overall_passed,
            report.sections_to_regenerate,
        )

        # Attempt to regenerate failing sections
        current_state = state
        if report.sections_to_regenerate and self.writing_agent:
            current_state = await self._regen_loop(state, report)
            # Re-validate after regeneration
            report = self._validate(current_state)
            logger.info(
                "[ValidationAgent] Post-regen score: %.2f | Passed: %s",
                report.overall_score, report.overall_passed
            )

        return {
            **current_state,
            "validation_report": report.to_dict(),
            "validation_passed": report.overall_passed,
            "validation_score": report.overall_score,
        }

    # ── private: validation ───────────────────────────────────────────────────

    def _validate(self, state: dict) -> ValidationReport:
        section_results: dict[str, SectionResult] = {}
        ieee_issues: list[str] = []

        for section in REQUIRED_SECTIONS:
            result = self._validate_section(section, state.get(section, ""))
            section_results[section] = result

        # IEEE-specific global checks
        ieee_issues.extend(self._check_ieee_rules(state))

        # Determine sections to regenerate
        to_regen = [
            name
            for name, res in section_results.items()
            if res.score < self.REGENERATE_THRESHOLD
        ]

        # Overall score = mean of section scores, penalised by IEEE issues
        scores = [r.score for r in section_results.values()]
        base_score = sum(scores) / len(scores) if scores else 0.0
        penalty = min(len(ieee_issues) * 0.03, 0.15)
        overall_score = max(0.0, base_score - penalty)
        overall_passed = overall_score >= 0.70 and not to_regen

        # Build summary
        failed_sections = [n for n, r in section_results.items() if not r.passed]
        if overall_passed:
            summary = f"Validation passed with score {overall_score:.2f}."
        else:
            summary = (
                f"Validation failed (score {overall_score:.2f}). "
                f"Problem sections: {', '.join(failed_sections)}. "
                f"IEEE issues: {len(ieee_issues)}."
            )

        return ValidationReport(
            overall_passed=overall_passed,
            overall_score=overall_score,
            sections=section_results,
            ieee_issues=ieee_issues,
            sections_to_regenerate=to_regen,
            summary=summary,
        )

    def _validate_section(self, section: str, text: Any) -> SectionResult:
        issues: list[str] = []
        warnings: list[str] = []
        score = 1.0

        # ── 1. Presence check ─────────────────────────────────────────────────
        if not text:
            return SectionResult(
                name=section, passed=False, score=0.0,
                issues=[f"Section '{section}' is missing or empty."]
            )

        # keywords is a list — convert for text checks
        if isinstance(text, list):
            text_str = ", ".join(str(t) for t in text)
        else:
            text_str = str(text)

        word_count = len(text_str.split())

        # ── 2. Placeholder detection ──────────────────────────────────────────
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text_str, re.IGNORECASE):
                issues.append(f"Placeholder text detected: '{pattern}'")
                score -= 0.40
                break  # one deduction per section

        # ── 3. Word count ─────────────────────────────────────────────────────
        min_wc = MIN_WORD_COUNTS.get(section, 0)
        max_wc = MAX_WORD_COUNTS.get(section, 99999)

        if word_count < min_wc:
            shortfall = min_wc - word_count
            issues.append(
                f"Too short: {word_count} words (minimum {min_wc}, shortfall {shortfall})."
            )
            score -= min(0.30, 0.30 * (shortfall / min_wc))

        if word_count > max_wc:
            excess = word_count - max_wc
            warnings.append(
                f"Too long: {word_count} words (maximum {max_wc}, excess {excess})."
            )
            score -= 0.05

        # ── 4. Section-specific checks ────────────────────────────────────────
        if section == "abstract":
            if re.search(r"\$.*?\$|\\begin\{", text_str):
                issues.append("Abstract must not contain math environments (IEEE rule).")
                score -= 0.15

        if section == "keywords":
            kw_list = text if isinstance(text, list) else [text]
            if len(kw_list) < 3:
                issues.append(f"Too few keywords: {len(kw_list)} (minimum 3).")
                score -= 0.20

        if section in ("introduction", "related_work", "methodology", "results_discussion"):
            if not re.search(r"\\cite\{|\\cite\[", text_str):
                warnings.append("No \\cite{} commands found — citations recommended.")
                score -= 0.05

        if section == "methodology":
            if not re.search(r"\\begin\{(align|equation|IEEEeqnarray)", text_str):
                warnings.append("No equation environment found — consider adding one.")
                score -= 0.05

        if section == "results_discussion":
            # Should mention at least one numeric metric
            if not re.search(r"\d+\.?\d*\s*(%|percent|f1|accuracy|precision|recall|auc)", text_str, re.IGNORECASE):
                issues.append("No quantitative metrics found in Results section.")
                score -= 0.20

        # ── 5. Clamp score ────────────────────────────────────────────────────
        score = max(0.0, min(1.0, score))
        passed = score >= 0.60 and not any("Placeholder" in i for i in issues)

        return SectionResult(
            name=section, passed=passed, score=score,
            issues=issues, warnings=warnings
        )

    def _check_ieee_rules(self, state: dict) -> list[str]:
        issues: list[str] = []

        # Title should not start with "A ", "An ", "The " (weak openers for IEEE)
        title = state.get("topic", "")
        if re.match(r"^(A |An |The )", title, re.IGNORECASE):
            issues.append(
                f"Title starts with article '{title.split()[0]}' — IEEE discourages this."
            )

        # Abstract must not have footnotes
        abstract = state.get("abstract", "")
        if "\\footnote" in abstract:
            issues.append("Abstract contains \\footnote — not allowed by IEEE.")

        # References must exist
        refs = state.get("references_raw", [])
        if len(refs) < 5:
            issues.append(
                f"Only {len(refs)} references found — IEEE papers typically cite 10+."
            )

        # Check that LaTeX source was generated
        if not state.get("latex_source"):
            issues.append("No LaTeX source generated by FormattingAgent.")

        return issues

    # ── private: regeneration ─────────────────────────────────────────────────

    async def _regen_loop(self, state: dict, report: ValidationReport) -> dict:
        """Re-generate each failing section up to MAX_REGEN_ATTEMPTS times."""
        current = state
        for section in report.sections_to_regenerate:
            sec_result = report.sections[section]
            feedback = "; ".join(sec_result.issues + sec_result.warnings)
            logger.info(
                "[ValidationAgent] Regenerating '%s'. Feedback: %s", section, feedback
            )
            for attempt in range(self.MAX_REGEN_ATTEMPTS):
                try:
                    current = await self.writing_agent.regenerate_section(
                        section, current, feedback=feedback
                    )
                    # Quick check — if placeholder gone, break
                    new_text = current.get(section, "")
                    quick = self._validate_section(section, new_text)
                    if quick.score >= self.REGENERATE_THRESHOLD:
                        logger.info(
                            "[ValidationAgent] '%s' passed after attempt %d (score %.2f).",
                            section, attempt + 1, quick.score
                        )
                        break
                except Exception as exc:
                    logger.error(
                        "[ValidationAgent] Regen attempt %d failed for '%s': %s",
                        attempt + 1, section, exc
                    )
        return current