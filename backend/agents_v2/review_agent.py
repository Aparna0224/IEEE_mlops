"""
review_agent.py
---------------
Final quality-review pass.  After Validation has confirmed the paper is
structurally sound, ReviewAgent asks the LLM to:

  1. Check for inconsistencies between sections
  2. Improve language quality (academic tone, clarity, concision)
  3. Verify contribution claims are supported by the results
  4. Return an overall review report + optionally polished sections

This is an OPTIONAL final node — if the LLM call fails or is disabled,
the pipeline simply passes the validated paper through unchanged.
"""

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Prompt helpers
# ──────────────────────────────────────────────────────────────────────────────

_REVIEW_SYSTEM = """
You are a senior IEEE reviewer performing a final quality check on a conference paper.
Be concise, critical, and constructive.
Respond ONLY with valid JSON — no markdown fences, no extra commentary.
"""


def _review_prompt(state: dict) -> str:
    topic = state.get("topic", "")
    abstract = state.get("abstract", "")[:600]
    intro = state.get("introduction", "")[:600]
    conclusion = state.get("conclusion", "")[:400]
    key_findings = json.dumps(state.get("key_findings", []))

    return f"""
Review this IEEE paper draft on: "{topic}"

Abstract (excerpt): {abstract}
Introduction (excerpt): {intro}
Conclusion (excerpt): {conclusion}
Key findings claimed: {key_findings}

Perform a reviewer assessment and return JSON with exactly these keys:
{{
  "overall_quality": "<excellent|good|acceptable|needs_revision>",
  "score": <float 0.0-1.0>,
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "suggestions": ["<specific improvement suggestion>", ...],
  "language_issues": ["<grammar/style issue>", ...],
  "contribution_clarity": "<clear|unclear|missing>",
  "ready_for_submission": <true|false>
}}
"""


def _polish_prompt(section_name: str, content: str, suggestions: list[str]) -> str:
    suggestions_str = "\n".join(f"- {s}" for s in suggestions)
    return f"""
Polish the following IEEE paper section ({section_name.replace('_', ' ').title()}).
Apply the reviewer suggestions below without changing the factual content or adding new claims.

REVIEWER SUGGESTIONS:
{suggestions_str}

SECTION CONTENT:
{content}

Return JSON: {{"{section_name}": "<polished section text>"}}

Rules:
- Fix grammar, clarity, and academic tone
- Remove redundant sentences
- Ensure consistent terminology
- Keep all LaTeX commands (\\cite, \\begin, \\end, etc.) intact
- Do NOT add new results, metrics, or claims
"""


# ──────────────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────────────

class ReviewAgent:
    """
    Final review and optional polish pass.

    Output keys added to PaperState
    ────────────────────────────────
    review_report      : dict    structured reviewer feedback
    review_score       : float
    ready_for_submission: bool
    """

    # Only polish if overall score below this threshold
    POLISH_THRESHOLD: float = 0.75
    # Sections eligible for polishing
    POLISHABLE_SECTIONS = ["abstract", "introduction", "conclusion", "methodology"]
    # Rate-limit delay between LLM calls
    INTER_CALL_DELAY: float = 2.0

    def __init__(self, model_manager=None, enabled: bool = True):
        self.model = model_manager
        self.enabled = enabled

    # ── public ────────────────────────────────────────────────────────────────

    async def run(self, state: dict) -> dict:
        if not self.enabled or not self.model:
            logger.info("[ReviewAgent] Skipped (disabled or no model).")
            return {
                **state,
                "review_report": {"skipped": True},
                "review_score": state.get("validation_score", 1.0),
                "ready_for_submission": state.get("validation_passed", True),
            }

        logger.info("[ReviewAgent] Starting final review.")

        # 1. Get reviewer assessment
        review = await self._get_review(state)

        # 2. Optionally polish weak sections
        current_state = state
        score = review.get("score", 0.75)
        if score < self.POLISH_THRESHOLD and review.get("suggestions"):
            current_state = await self._polish_sections(state, review["suggestions"])
            logger.info("[ReviewAgent] Polish pass completed.")

        logger.info(
            "[ReviewAgent] Review complete. Quality: %s | Score: %.2f | Ready: %s",
            review.get("overall_quality", "N/A"),
            review.get("score", 0.0),
            review.get("ready_for_submission", False),
        )

        return {
            **current_state,
            "review_report": review,
            "review_score": review.get("score", 0.0),
            "ready_for_submission": review.get("ready_for_submission", False),
        }

    # ── private ───────────────────────────────────────────────────────────────

    async def _get_review(self, state: dict) -> dict:
        messages = [
            SystemMessage(content=_REVIEW_SYSTEM),
            HumanMessage(content=_review_prompt(state)),
        ]
        try:
            response = await self.model.ainvoke(messages)
            raw = response.content.strip()
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception as exc:
            logger.error("[ReviewAgent] Review LLM call failed: %s", exc)
            return {
                "overall_quality": "acceptable",
                "score": 0.75,
                "strengths": [],
                "weaknesses": ["Review agent error — manual review recommended."],
                "suggestions": [],
                "language_issues": [],
                "contribution_clarity": "unclear",
                "ready_for_submission": False,
                "error": str(exc),
            }

    async def _polish_sections(self, state: dict, suggestions: list[str]) -> dict:
        """
        Polish each eligible section with the reviewer's suggestions.
        Only touches sections that exist and are non-empty.
        """
        current = dict(state)

        for section in self.POLISHABLE_SECTIONS:
            content = current.get(section, "")
            if not content or len(content.split()) < 50:
                continue

            try:
                await asyncio.sleep(self.INTER_CALL_DELAY)
                polished = await self._polish_one(section, content, suggestions)
                if polished:
                    current[section] = polished
                    logger.info("[ReviewAgent] Polished section: %s", section)
            except Exception as exc:
                logger.warning("[ReviewAgent] Polish failed for '%s': %s", section, exc)

        return current

    async def _polish_one(
        self, section: str, content: str, suggestions: list[str]
    ) -> str:
        """Call LLM to polish a single section."""
        messages = [
            SystemMessage(content=_REVIEW_SYSTEM),
            HumanMessage(content=_polish_prompt(section, content[:1500], suggestions[:5])),
        ]
        response = await self.model.ainvoke(messages)
        raw = response.content.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        try:
            data = json.loads(raw)
            return data.get(section, content)  # fall back to original if key missing
        except Exception:
            return content  # keep original on parse failure

    # ── utility ───────────────────────────────────────────────────────────────

    def get_formatted_report(self, state: dict) -> str:
        """Return a human-readable review report string."""
        rr = state.get("review_report", {})
        if rr.get("skipped"):
            return "Review skipped."

        lines = [
            f"Overall Quality : {rr.get('overall_quality', 'N/A')}",
            f"Score           : {rr.get('score', 0.0):.2f}",
            f"Ready           : {rr.get('ready_for_submission', False)}",
            "",
            "Strengths:",
            *[f"  + {s}" for s in rr.get("strengths", [])],
            "",
            "Weaknesses:",
            *[f"  - {w}" for w in rr.get("weaknesses", [])],
            "",
            "Suggestions:",
            *[f"  * {s}" for s in rr.get("suggestions", [])],
        ]
        return "\n".join(lines)