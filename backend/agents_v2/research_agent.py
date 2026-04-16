"""
research_agent.py
-----------------
Queries arXiv for relevant papers, extracts key findings, and synthesises
a structured research context that downstream agents consume.
"""

import asyncio
import json
import logging
import re
from typing import Any

try:
    import arxiv  # pip install arxiv
except ImportError:
    logger_init = logging.getLogger(__name__)
    logger_init.warning("arxiv package not installed. Install with: pip install arxiv")
    arxiv = None

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Remove newlines / extra whitespace from arXiv abstracts."""
    return re.sub(r"\s+", " ", text).strip()


def _build_queries(topic: str) -> list[str]:
    """Return a small set of arXiv search queries for a given topic."""
    base = topic.strip()
    return [
        base,
        f"{base} deep learning",
        f"{base} survey",
    ]


async def _fetch_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Fetch arXiv papers in a thread so we don't block the event loop."""
    if arxiv is None:
        logger.error("[ResearchAgent] arxiv module not available. Install with: pip install arxiv")
        return []
    
    def _sync():
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        results = []
        for paper in client.results(search):
            results.append(
                {
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors[:4]],
                    "year": paper.published.year if paper.published else "n.d.",
                    "abstract": _clean(paper.summary),
                    "url": paper.entry_id,
                    "arxiv_id": paper.entry_id.split("/")[-1],
                }
            )
        return results

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


# ──────────────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────────────

class ResearchAgent:
    """
    Collects arXiv literature and produces a structured research brief.

    Output keys added to PaperState
    ────────────────────────────────
    research_papers   : list[dict]   raw paper metadata
    research_summary  : str          2-3 paragraph synthesis
    key_findings      : list[str]    bullet-style findings (plain text)
    references_raw    : list[dict]   papers formatted for citation later
    """

    def __init__(self, model_manager):
        self.model = model_manager

    # ── public ────────────────────────────────────────────────────────────────

    async def run(self, state: dict) -> dict:
        topic: str = state.get("topic", "")
        user_notes: str = state.get("user_notes", "")
        num_papers: int = int(state.get("num_arxiv_papers") or 10)
        logger.info("[ResearchAgent] Starting research for topic: %s (max %d papers)", topic, num_papers)

        # 1. Fetch papers from arXiv
        papers = await self._gather_papers(topic, max_total=num_papers)

        # 2. Ask LLM to synthesise findings
        summary, findings = await self._synthesise(topic, user_notes, papers)

        # 3. Build citation-ready reference list
        references = self._build_references(papers)

        # 4. Build citation map for WritingAgent
        citation_map = self._build_citation_map(references)

        logger.info("[ResearchAgent] Found %d papers, synthesis complete.", len(papers))

        return {
            **state,
            "research_papers": papers,
            "research_summary": summary,
            "key_findings": findings,
            "references_raw": references,
            "citation_map": citation_map,
        }

    # ── private ───────────────────────────────────────────────────────────────

    async def _gather_papers(self, topic: str, max_total: int = 10) -> list[dict]:
        queries = _build_queries(topic)
        seen_ids: set[str] = set()
        papers: list[dict] = []

        for q in queries:
            if len(papers) >= max_total:
                break
            try:
                batch = await _fetch_arxiv(q, max_results=5)
                for p in batch:
                    if p["arxiv_id"] not in seen_ids:
                        seen_ids.add(p["arxiv_id"])
                        papers.append(p)
                        if len(papers) >= max_total:
                            break
            except Exception as exc:
                logger.warning("[ResearchAgent] arXiv fetch failed for '%s': %s", q, exc)

        return papers

    async def _synthesise(
        self, topic: str, user_notes: str, papers: list[dict]
    ) -> tuple[str, list[str]]:
        """Ask the LLM to produce a research summary and key findings."""
        paper_snippets = "\n".join(
            f"- [{i+1}] {p['title']} ({p['year']}): {p['abstract'][:300]}..."
            for i, p in enumerate(papers)
        )

        system = (
            "You are an expert research synthesiser for IEEE conference papers. "
            "Respond ONLY with valid JSON — no markdown, no extra keys."
        )

        user_prompt = f"""
Topic: {topic}
User notes: {user_notes or 'None'}

Relevant papers:
{paper_snippets}

Produce a JSON object with exactly these keys:
{{
  "summary": "<2-3 paragraph research context and gap analysis>",
  "key_findings": ["<finding 1>", "<finding 2>", ...]
}}

Requirements:
- summary: discuss state-of-the-art, limitations in existing work, and the motivation for this research
- key_findings: 5-8 concise bullet findings that the writing agent should incorporate
- Do NOT include markdown, code fences, or extra keys
"""

        messages = [SystemMessage(content=system), HumanMessage(content=user_prompt)]

        try:
            response = await self.model.invoke_for("research", messages)
            raw = response.content.strip()
            # Strip accidental code fences
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            summary = data.get("summary", "")
            findings = data.get("key_findings", [])

            # Validate quality — fall back to simpler synthesis if result is insufficient
            if len(summary.split()) < 50:
                raise ValueError("Summary too short — fewer than 50 words returned")
            if len(findings) < 3:
                raise ValueError("Too few key findings — fewer than 3 returned")

            return summary, findings
        except Exception as exc:
            logger.warning(
                "[ResearchAgent] Primary synthesis failed (%s) — retrying with simple prompt", exc
            )
            return await self._synthesise_simple(topic, papers)

    async def _synthesise_simple(self, topic: str, papers: list[dict]) -> tuple[str, list[str]]:
        """
        Fallback synthesis using a simplified prompt.
        Lists paper titles and asks the model for a short summary plus 5 research challenges.
        Called when the primary synthesis produces insufficient output.
        """
        titles = "\n".join(
            f"- [{i+1}] {p['title']} ({p['year']})"
            for i, p in enumerate(papers[:8])
        )

        user_prompt = f"""
Topic: {topic}

Available papers:
{titles}

Return ONLY this JSON — no markdown, no extra keys:
{{
  "summary": "<2-3 sentences describing the research area, current limitations, and motivation>",
  "key_findings": ["challenge 1", "challenge 2", "challenge 3", "challenge 4", "challenge 5"]
}}
"""
        messages = [
            SystemMessage(content="Return only valid JSON. No markdown."),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = await self.model.invoke_for("research", messages)
            raw = response.content.strip()
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            summary = data.get("summary", "")
            findings = data.get("key_findings", [])
            if not summary:
                summary = f"Research on {topic} encompasses several open challenges."
            if not findings:
                findings = [f"Open challenge in {topic}." for _ in range(5)]
            logger.info("[ResearchAgent] Fallback synthesis succeeded.")
            return summary, findings
        except Exception as exc2:
            logger.error("[ResearchAgent] Fallback synthesis also failed: %s", exc2)
            return (
                f"Research on {topic} involves multiple open problems requiring further investigation.",
                [f"Key research challenge in {topic}." for _ in range(5)],
            )

    def _build_references(self, papers: list[dict]) -> list[dict]:
        """Convert raw paper dicts into IEEE-style reference dicts."""
        refs = []
        for i, p in enumerate(papers):
            authors = p.get("authors", ["Unknown"])
            author_str = (
                ", ".join(authors[:3]) + " et al."
                if len(authors) > 3
                else " and ".join(authors)
            )
            refs.append(
                {
                    "index": i + 1,
                    "label": f"b{i+1}",
                    "authors": author_str,
                    "title": p["title"],
                    "year": p["year"],
                    "url": p.get("url", ""),
                    "arxiv_id": p.get("arxiv_id", ""),
                    # formatted IEEE string
                    "ieee_str": (
                        f'{author_str}, "{p["title"]}," arXiv:{p.get("arxiv_id","")}, {p["year"]}.'
                    ),
                }
            )
        return refs

    def _build_citation_map(self, references: list[dict]) -> dict:
        """
        Build a mapping from \\cite{bN} keys to paper titles.
        Used by WritingAgent to resolve citations in prompts.
        Returns: {"\\cite{b1}": "Paper Title", "\\cite{b2}": "...", ...}
        """
        return {
            f"\\cite{{{ref['label']}}}": ref["title"]
            for ref in references
        }