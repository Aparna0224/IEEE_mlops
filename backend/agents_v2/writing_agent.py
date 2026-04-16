"""
writing_agent.py
----------------
Uses the research context from ResearchAgent to generate rich, section-level
content for every part of the IEEE paper.  Each section is generated with a
focused prompt so the LLM produces deep, domain-specific prose rather than
generic placeholders.
"""

import asyncio
import json
import logging
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Section definitions – order matches IEEE conference template
# ──────────────────────────────────────────────────────────────────────────────

SECTIONS = [
    "abstract",
    "keywords",
    "introduction",
    "related_work",
    "methodology",
    "implementation",
    "results_discussion",
    "conclusion",
]

# Sections that use the two-step outline → full generation approach
OUTLINE_SECTIONS = frozenset([
    "introduction",
    "related_work",
    "methodology",
    "implementation",
    "results_discussion",
    "conclusion",
])

# Token budget per section — keeps Groq responses inside context window
SECTION_MAX_TOKENS: dict[str, int] = {
    "abstract":            600,
    "keywords":            100,
    "introduction":       1500,
    "related_work":       1500,
    "methodology":        2000,
    "implementation":     1200,
    "results_discussion": 1800,
    "conclusion":          800,
}


# ──────────────────────────────────────────────────────────────────────────────
# Per-section prompt factories
# ──────────────────────────────────────────────────────────────────────────────

def _system_prompt() -> str:
    return "Expert IEEE author. Respond ONLY with JSON — no markdown, no commentary."


def _abstract_prompt(ctx: dict) -> str:
    problem = ctx.get("problem_statement", "")
    solution = ctx.get("proposed_solution", "")
    contribs = ctx.get("key_contributions", [])
    metrics = ctx.get("metrics", [])
    results_summary = ctx.get("results_summary", "")
    contrib_hint = f"\nKey contributions: {json.dumps(contribs)}" if contribs else ""
    metrics_hint = f"\nEvaluation metrics used: {', '.join(metrics)}" if metrics else ""
    results_hint = f"\nResults summary: {results_summary}" if results_summary else ""
    problem_hint = f"\nProblem: {problem}" if problem else ""
    solution_hint = f"\nProposed approach: {solution}" if solution else ""
    return f"""
Topic: {ctx['topic']}
Research summary: {ctx['research_summary'][:300]}
Key findings: {json.dumps(ctx['key_findings'][:5])}

Write the abstract for an IEEE conference paper on this topic.
Return JSON: {{"abstract": "<text>"}}

Requirements:
- 150-250 words, NO symbols, special characters, footnotes, or math (IEEE rule)
- Paragraph 1 (2-3 sentences): problem motivation and real-world significance with quantitative evidence
- Paragraph 2 (2-3 sentences): proposed approach — what it does and how it is novel
- Paragraph 3 (2-3 sentences): key results with concrete numbers from the metrics list; significance
- Do NOT start with "This paper" — vary the opening
- Do NOT use bullet points — continuous prose only
"""


def _keywords_prompt(ctx: dict) -> str:
    datasets = ctx.get("datasets", [])
    metrics = ctx.get("metrics", [])
    dataset_hint = f"\nDatasets: {', '.join(datasets)}" if datasets else ""
    metrics_hint = f"\nMetrics: {', '.join(metrics)}" if metrics else ""
    return f"""
Topic: {ctx['topic']}
Abstract: {ctx.get('abstract','')[:200]}
Research summary: {ctx['research_summary'][:300]}{dataset_hint}{metrics_hint}

Generate IEEE keywords for this paper.
Return JSON: {{"keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"]}}

Requirements:
- 4-6 keywords, lowercase except proper nouns
- Ordered from general to specific
- Include task-specific technical terms (do not just restate the title)
"""


def _introduction_prompt(ctx: dict) -> str:
    problem = ctx.get("problem_statement", "")
    solution = ctx.get("proposed_solution", "")
    contribs = ctx.get("key_contributions", [])
    citation_map = ctx.get("citation_map", {})
    cite_refs = "\n".join(f"  {k} → {v}" for k, v in list(citation_map.items())[:10]) if citation_map else "None"
    contrib_block = (
        "\n".join(f"  {i+1}. {c}" for i, c in enumerate(contribs))
        if contribs else "(derive from topic and research summary)"
    )
    problem_hint = f"\nProblem statement: {problem}" if problem else ""
    solution_hint = f"\nProposed solution: {solution}" if solution else ""
    return f"""
Topic: {ctx['topic']}
Research summary: {ctx['research_summary'][:300]}
Key findings: {json.dumps(ctx['key_findings'][:5])}{problem_hint}{solution_hint}
Key contributions to highlight:
{contrib_block}
Available citations (\\cite{{key}} → title):
{cite_refs}
Abstract: {ctx.get('abstract','')[:200]}

Write a complete Introduction section for this IEEE paper.
Return JSON: {{"introduction": "<full section text>"}}

Requirements:
- 400-600 words total
- Paragraph 1 (~100 words): Problem motivation with real-world impact and quantitative evidence
- Paragraph 2 (~100 words): Critical review of existing approaches — what they do and their concrete limitations
- Paragraph 3 (~80 words): How the proposed approach addresses these gaps; brief overview of the solution
- Paragraph 4 (~100 words): Numbered list of at least 3 explicit contributions starting with "The contributions of this work are:"
- Paragraph 5 (~60 words): Paper organisation sentence ("The remainder of this paper is structured as follows...")
- Use \\cite{{bN}} placeholders matching the available citations list above
- Precise academic language — no vague phrases like "is an important research direction"
"""


def _related_work_prompt(ctx: dict) -> str:
    papers_str = json.dumps(
        [{"title": p["title"], "year": p["year"], "abstract": p["abstract"][:200]}
         for p in ctx.get("research_papers", [])[:8]],
        indent=2,
    )
    citation_map = ctx.get("citation_map", {})
    cite_refs = "\n".join(f"  {k} → {v}" for k, v in list(citation_map.items())[:10]) if citation_map else "None"
    datasets = ctx.get("datasets", [])
    dataset_hint = f"\nDatasets in scope: {', '.join(datasets)}" if datasets else ""
    return f"""
Topic: {ctx['topic']}
Research summary: {ctx['research_summary'][:300]}
Available papers: {papers_str}{dataset_hint}
Available citations (\\cite{{key}} → title):
{cite_refs}

Write a complete Related Work section.
Return JSON: {{"related_work": "<full section text>"}}

Requirements:
- 400-600 words total
- Organise into 3-4 labelled subsections using \\subsection{{...}}, each ~100-150 words
  covering distinct research threads (e.g. traditional methods, deep learning approaches, domain-specific methods, benchmarks)
- Each subsection: describe what papers do, their metrics, then their specific shortcomings
- Final subsection or closing paragraph: position THIS paper relative to the surveyed work
- Use \\cite{{bN}} placeholders from the citations list above; assign labels in order to the provided papers
- Synthesise and contrast — do not just list papers sequentially
"""


def _methodology_prompt(ctx: dict) -> str:
    problem = ctx.get("problem_statement", "")
    solution = ctx.get("proposed_solution", "")
    contribs = ctx.get("key_contributions", [])
    equations = ctx.get("equations", [])  # [{label, latex, description}]
    datasets = ctx.get("datasets", [])
    metrics = ctx.get("metrics", [])
    problem_hint = f"\nProblem statement: {problem}" if problem else ""
    solution_hint = f"\nProposed solution: {solution}" if solution else ""
    contribs_hint = f"\nKey contributions: {json.dumps(contribs)}" if contribs else ""
    eqs_hint = (
        "\nUser-specified equations:\n" +
        "\n".join(f"  [{e.get('label','')}]: {e.get('latex','')} — {e.get('description','')}" for e in equations)
    ) if equations else ""
    datasets_hint = f"\nDatasets: {', '.join(datasets)}" if datasets else ""
    metrics_hint = f"\nEvaluation metrics: {', '.join(metrics)}" if metrics else ""
    return f"""
Topic: {ctx['topic']}
Research summary: {ctx['research_summary'][:300]}
Key findings: {json.dumps(ctx['key_findings'][:5])}
User notes: {str(ctx.get('user_notes', 'None'))[:200]}{problem_hint}{solution_hint}{contribs_hint}{eqs_hint}{datasets_hint}{metrics_hint}

Write a complete Proposed Methodology section.
Return JSON: {{"methodology": "<full section text>"}}

Requirements:
- 500-700 words total
- \\subsection{{Problem Formulation}} (~100 words): formal definition with mathematical notation; include the primary objective function or optimisation criterion using a LaTeX equation (align environment)
- \\subsection{{System Architecture}} (~150 words): describe the end-to-end pipeline, modules, and data flow; reference any user-specified equations above
- \\subsection{{Algorithm Design}} (~150 words): detail the core algorithm or model; specify layer types, activation functions, loss functions, or decision logic
- \\subsection{{Training and Optimisation Strategy}} (~100 words): describe optimiser, learning rate schedule, regularisation, and hyperparameters
- Embed user-specified equations verbatim where appropriate (use the provided LaTeX)
- Mention the datasets listed above for experimental validation
- Justify every design choice with a brief rationale — do not just describe without explanation
"""


def _implementation_prompt(ctx: dict) -> str:
    datasets = ctx.get("datasets", [])
    metrics = ctx.get("metrics", [])
    datasets_hint = f"\nDatasets: {', '.join(datasets)}" if datasets else ""
    metrics_hint = f"\nMetrics used: {', '.join(metrics)}" if metrics else ""
    return f"""
Topic: {ctx['topic']}
Methodology summary: {ctx.get('methodology','')[:500]}{datasets_hint}{metrics_hint}

Write a complete Implementation section.
Return JSON: {{"implementation": "<full section text>"}}

Requirements:
- 300-450 words total
- Paragraph 1 (~100 words): software stack (frameworks, libraries, versions), hardware environment (GPU model, RAM, OS)
- Paragraph 2 (~100 words): dataset details — sizes, train/val/test splits, preprocessing steps applied to datasets listed above
- Paragraph 3 (~100 words): training pipeline — number of epochs, batch size, learning rate, early stopping, checkpointing
- Paragraph 4 (~80 words): evaluation protocol — metrics listed above, cross-validation or held-out test set, statistical significance testing
- Include a LaTeX comment placeholder exactly as: % TABLE I - Results comparison goes here
- Mention specific library versions (e.g. PyTorch 2.1, scikit-learn 1.3) and reproducibility steps
"""


def _results_prompt(ctx: dict) -> str:
    datasets = ctx.get("datasets", [])
    baselines = ctx.get("baselines", [])
    metrics = ctx.get("metrics", [])
    results_summary = ctx.get("results_summary", "")
    datasets_hint = f"\nDatasets evaluated on: {', '.join(datasets)}" if datasets else ""
    baselines_hint = f"\nBaseline methods to compare against: {', '.join(baselines)}" if baselines else ""
    metrics_hint = f"\nMetrics: {', '.join(metrics)}" if metrics else ""
    results_hint = f"\nUser-provided results context: {results_summary}" if results_summary else ""
    baselines_table_hint = (
        f"\n\nFor the comparison table (TABLE I), include columns: Method, " +
        ", ".join(metrics[:4]) +
        f". Rows: {', '.join(baselines[:5])}, and the proposed method." if baselines and metrics else ""
    )
    return f"""
Topic: {ctx['topic']}
Key findings: {json.dumps(ctx['key_findings'][:5])}
Methodology: {ctx.get('methodology','')[:500]}{datasets_hint}{baselines_hint}{metrics_hint}{results_hint}{baselines_table_hint}

Write a complete Results and Discussion section.
Return JSON: {{"results_discussion": "<full section text>"}}

Requirements:
- 500-700 words total
- \\subsection{{Quantitative Results}} (~150 words): main performance numbers on all datasets using the metrics listed; reference TABLE I (performance table) inserted by the formatter
- \\subsection{{Comparison with Baselines}} (~150 words): side-by-side comparison against each baseline listed; explain WHY the proposed method outperforms — architectural advantages, training strategy, etc.
- \\subsection{{Ablation Study}} (~100 words): remove / disable key components one at a time and report degraded performance; confirms each component's contribution
- \\subsection{{Discussion}} (~100 words): interpret findings, acknowledge failure cases and limitations, note statistical significance
- Use realistic and internally consistent numbers — if results_summary is provided, honour those numbers
- Reference TABLE II for ablation results
"""


def _conclusion_prompt(ctx: dict) -> str:
    contribs = ctx.get("key_contributions", [])
    metrics = ctx.get("metrics", [])
    results_summary = ctx.get("results_summary", "")
    contrib_hint = f"\nKey contributions: {json.dumps(contribs)}" if contribs else ""
    metrics_hint = f"\nMetrics achieved: {', '.join(metrics)}" if metrics else ""
    results_hint = f"\nResults context: {results_summary}" if results_summary else ""
    return f"""
Topic: {ctx['topic']}
Abstract: {ctx.get('abstract','')[:200]}
Key findings: {json.dumps(ctx['key_findings'][:5])}{contrib_hint}{metrics_hint}{results_hint}

Write a complete Conclusion section.
Return JSON: {{"conclusion": "<full section text>"}}

Requirements:
- 200-300 words total
- Paragraph 1 (~100 words): Summarise contributions (reference the key_contributions list) and highlight the best metric improvements — no new results
- Paragraph 2 (~100 words): Future work — 3-4 specific, actionable directions (e.g. "extend to multi-modal inputs", "deploy on edge hardware", "benchmark on X dataset") — NOT generic statements
- Do NOT start with "In conclusion" or "In summary" — vary the opening verb
- Do NOT introduce any new experimental results or claims not supported by earlier sections
"""


PROMPT_FACTORIES = {
    "abstract": _abstract_prompt,
    "keywords": _keywords_prompt,
    "introduction": _introduction_prompt,
    "related_work": _related_work_prompt,
    "methodology": _methodology_prompt,
    "implementation": _implementation_prompt,
    "results_discussion": _results_prompt,
    "conclusion": _conclusion_prompt,
}


# ──────────────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────────────

class WritingAgent:
    """
    Generates all IEEE paper sections sequentially.
    Each section is generated with a focused prompt and accumulated into ctx
    so later sections can reference earlier ones (e.g. conclusion sees abstract).

    Output keys added to PaperState
    ────────────────────────────────
    abstract          : str
    keywords          : list[str]
    introduction      : str
    related_work      : str
    methodology       : str
    implementation    : str
    results_discussion: str
    conclusion        : str
    sections_raw      : dict   (all sections keyed by name)
    """

    # Delay between LLM calls to avoid rate-limit 429s
    INTER_CALL_DELAY: float = 2.0

    def __init__(self, model_manager):
        self.model = model_manager

    # ── public ────────────────────────────────────────────────────────────────

    async def run(self, state: dict) -> dict:
        logger.info("[WritingAgent] Starting section generation.")

        # Build a mutable context that grows as sections are written
        ctx: dict[str, Any] = {
            "topic": state.get("topic", ""),
            "user_notes": state.get("user_notes", ""),
            "research_summary": state.get("research_summary", ""),
            "key_findings": state.get("key_findings", []),
            "research_papers": state.get("research_papers", []),
            # Extended fields from new input schema
            "problem_statement": state.get("problem_statement", ""),
            "proposed_solution": state.get("proposed_solution", ""),
            "key_contributions": state.get("key_contributions", []),
            "equations": state.get("equations", []),
            "datasets": state.get("datasets", []),
            "baselines": state.get("baselines", []),
            "metrics": state.get("metrics", []),
            "results_summary": state.get("results_summary", ""),
            "citation_map": state.get("citation_map", {}),
        }

        # Validate that critical research context is present before writing
        if not ctx.get("research_summary"):
            raise ValueError(
                "[WritingAgent] research_summary is missing from state. "
                "ResearchAgent must run successfully before WritingAgent."
            )
        if not ctx.get("key_findings"):
            raise ValueError(
                "[WritingAgent] key_findings is missing from state. "
                "ResearchAgent must run successfully before WritingAgent."
            )

        sections_raw: dict[str, Any] = {}

        for section in SECTIONS:
            logger.info("[WritingAgent] Generating section: %s", section)
            try:
                content = await self._generate_section(section, ctx)
                sections_raw[section] = content
                # Accumulate so later prompts can reference earlier content
                ctx[section] = content if isinstance(content, str) else json.dumps(content)
                await asyncio.sleep(self.INTER_CALL_DELAY)
            except Exception as exc:
                logger.error("[WritingAgent] Failed to generate '%s': %s", section, exc)
                sections_raw[section] = f"[Generation failed for {section}: {exc}]"
                ctx[section] = sections_raw[section]

        logger.info("[WritingAgent] All sections generated.")

        return {
            **state,
            "abstract": sections_raw.get("abstract", ""),
            "keywords": sections_raw.get("keywords", []),
            "introduction": sections_raw.get("introduction", ""),
            "related_work": sections_raw.get("related_work", ""),
            "methodology": sections_raw.get("methodology", ""),
            "implementation": sections_raw.get("implementation", ""),
            "results_discussion": sections_raw.get("results_discussion", ""),
            "conclusion": sections_raw.get("conclusion", ""),
            "sections_raw": sections_raw,
        }

    # ── private ───────────────────────────────────────────────────────────────

    async def _generate_section(self, section: str, ctx: dict) -> Any:
        """
        Generate a single IEEE section.

        For major sections uses a two-step approach:
          Step 1 — Generate a structured outline (5 bullet points)
          Step 2 — Generate the full section guided by that outline

        All LLM calls use the larger writing model via invoke_for("writing").
        """
        print("=================================================")
        print(f"[DEBUG] GENERATING SECTION: {section}")
        print("[DEBUG] Context keys with values:")
        print([k for k, v in ctx.items() if v])

        prompt_fn = PROMPT_FACTORIES[section]

        # ── Step 1: outline (major sections only) ────────────────────────────
        outline_text = ""
        if section in OUTLINE_SECTIONS:
            outline = await self._generate_outline(section, ctx)
            if outline:
                outline_text = "\n".join(f"  {i+1}. {pt}" for i, pt in enumerate(outline))
                print(f"[DEBUG] OUTLINE for {section}:")
                print(outline_text)

        # ── Step 2: full section ──────────────────────────────────────────────
        user_prompt = prompt_fn(ctx)
        if outline_text:
            user_prompt += f"\n\nSection outline to follow:\n{outline_text}"

        print("[DEBUG] Prompt preview:")
        print(user_prompt[:500])

        return await self._invoke_with_retry(section, user_prompt, max_tokens=SECTION_MAX_TOKENS.get(section, 1500))

    async def _generate_outline(self, section: str, ctx: dict) -> list[str]:
        """
        Step 1 of two-step generation.
        Asks the model for 5 bullet points the given section should cover.
        Returns [] on failure (does not block section generation).
        """
        section_label = section.replace("_", " ").title()
        outline_prompt = f"""
Topic: {ctx.get('topic', '')}
Research summary: {ctx.get('research_summary', '')[:300]}
Key findings: {json.dumps(ctx.get('key_findings', [])[:5])}

List 5 bullet points that the {section_label} section of this IEEE paper should cover.
Return ONLY valid JSON: {{"outline": ["point1", "point2", "point3", "point4", "point5"]}}
No markdown, no extra keys, no commentary.
"""
        messages = [
            SystemMessage(content="You are an IEEE paper outline generator. Return only JSON."),
            HumanMessage(content=outline_prompt),
        ]
        try:
            response = await self.model.invoke_for("writing", messages, max_tokens=300)
            raw = response.content.strip()
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            return data.get("outline", [])
        except Exception as exc:
            logger.warning("[WritingAgent] Outline generation failed for '%s': %s", section, exc)
            return []

    async def _invoke_with_retry(self, section: str, user_prompt: str, max_tokens: Optional[int] = None) -> Any:
        """
        Call the writing LLM, parse JSON using 4-strategy recovery, and retry once
        with a strict system message if JSON parsing fails on the first attempt.
        Raises ValueError if both attempts fail.
        """
        async def _attempt(strict: bool):
            system = (
                "Return only JSON. No markdown. No commentary."
                if strict
                else _system_prompt()
            )
            messages = [
                SystemMessage(content=system),
                HumanMessage(content=user_prompt),
            ]
            response = await self.model.invoke_for("writing", messages, max_tokens=max_tokens)
            raw = response.content.strip()
            print("[DEBUG] RAW MODEL RESPONSE:")
            print(raw[:500])
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

            data = None

            # Strategy 1: standard JSON parse
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                pass

            # Strategy 2: extract first {...} block via regex
            if data is None:
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group())
                    except json.JSONDecodeError:
                        pass

            # Strategy 3: repair truncated JSON by appending closing suffix
            if data is None:
                for suffix in ('"}', '"}}', '"}}}'):
                    try:
                        data = json.loads(raw + suffix)
                        break
                    except json.JSONDecodeError:
                        pass

            # Strategy 4: extract any sufficiently long quoted string (raw text fallback)
            if data is None:
                val_m = re.search(r'"([^"]{50,})"', raw, re.DOTALL)
                if val_m:
                    return val_m.group(1), None
                return None, raw

            if section in data:
                result = data[section]
                if isinstance(result, str):
                    print("[DEBUG] PARSED SECTION RESULT:")
                    print(result[:200])
                return result, None
            if len(data) == 1:
                return next(iter(data.values())), None
            return data, None

        # First attempt
        result, last_raw = await _attempt(strict=False)
        if result is not None:
            return result

        # Second attempt — strict JSON-only system message
        print(f"[DEBUG] JSON PARSE FAILED — retrying '{section}' with strict prompt")
        if last_raw:
            print(last_raw[:300])
        result, last_raw2 = await _attempt(strict=True)
        if result is not None:
            return result

        raise ValueError(
            f"[WritingAgent] JSON parsing failed for section '{section}' after 2 attempts. "
            f"Last response: {(last_raw2 or '')[:200]}"
        )

    async def regenerate_section(self, section: str, state: dict, feedback: str = "") -> dict:
        """
        Regenerate a single weak section (called by ValidationAgent).
        feedback: optional string with specific improvement instructions.
        """
        logger.info("[WritingAgent] Regenerating section '%s' with feedback: %s", section, feedback)

        ctx: dict[str, Any] = {
            "topic": state.get("topic", ""),
            "user_notes": state.get("user_notes", ""),
            "research_summary": state.get("research_summary", ""),
            "key_findings": state.get("key_findings", []),
            "research_papers": state.get("research_papers", []),
            "problem_statement": state.get("problem_statement", ""),
            "proposed_solution": state.get("proposed_solution", ""),
            "key_contributions": state.get("key_contributions", []),
            "equations": state.get("equations", []),
            "datasets": state.get("datasets", []),
            "baselines": state.get("baselines", []),
            "metrics": state.get("metrics", []),
            "results_summary": state.get("results_summary", ""),
            "citation_map": state.get("citation_map", {}),
            **{s: state.get(s, "") for s in SECTIONS},
        }

        if feedback:
            original = PROMPT_FACTORIES[section]
            def patched_prompt(c):
                base = original(c)
                return base + f"\n\nPREVIOUS ATTEMPT WAS REJECTED. Feedback: {feedback}\nPlease fix all issues."
            prompt_fn = patched_prompt
        else:
            prompt_fn = PROMPT_FACTORIES[section]

        content = await self._generate_section_with_prompt(section, ctx, prompt_fn)

        return {**state, section: content}

    async def _generate_section_with_prompt(self, section: str, ctx: dict, prompt_fn) -> Any:
        """Build user prompt from prompt_fn and delegate to _invoke_with_retry."""
        user_prompt = prompt_fn(ctx)
        return await self._invoke_with_retry(section, user_prompt, max_tokens=SECTION_MAX_TOKENS.get(section, 1500))