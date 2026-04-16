"""
Shared state model for LangGraph paper generation pipeline.
Uses TypedDict so LangGraph can merge partial dicts returned by each agent.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class PaperState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────
    task_id:              str
    topic:                str
    user_notes:           str
    model_name:           str
    authors:              list[dict]   # for FormattingAgent author block
    # Extended input schema (session 5)
    paper_type:           str          # e.g. "conference", "journal"
    target_venue:         str          # e.g. "IEEE CVPR", "ACM MM"
    page_limit:           int          # max pages (e.g. 8)
    problem_statement:    str          # clear problem description from user
    proposed_solution:    str          # high-level solution approach
    key_contributions:    list[str]    # explicit list of contributions
    equations:            list[dict]   # user-specified equations [{label, latex, description}]
    datasets:             list[str]    # dataset names e.g. ["CIFAR-10", "ImageNet"]
    baselines:            list[str]    # comparison methods e.g. ["ResNet-50", "ViT-B/16"]
    metrics:              list[str]    # evaluation metrics e.g. ["accuracy", "F1", "mAP"]
    results_summary:      str          # user-provided expected/actual results summary
    num_arxiv_papers:     int          # number of arXiv papers to retrieve (default 10)

    # ── ResearchAgent outputs ─────────────────────────────────
    research_papers:  list[dict]
    research_summary: str
    key_findings:     list[str]
    references_raw:   list[dict]   # IEEE-formatted citation objects
    citation_map:     dict         # {"\cite{b1}": "Paper Title", ...}

    # ── WritingAgent outputs ──────────────────────────────────
    abstract:              str
    keywords:              list[str]
    introduction:          str
    related_work:          str
    methodology:           str
    implementation:        str
    results_discussion:    str
    conclusion:            str
    sections_raw:          dict    # all sections keyed by name

    # ── FormattingAgent outputs ───────────────────────────────
    latex_source:          str     # full .tex file content
    tex_path:              str     # path to saved .tex file
    pdf_path:              Optional[str]
    docx_path:             Optional[str]
    formatted_sections:    dict    # cleaned sections dict

    # ── ValidationAgent outputs ───────────────────────────────
    validation_report:     dict    # full structured report
    validation_passed:     bool
    validation_score:      float

    # ── ReviewAgent outputs ───────────────────────────────────
    review_report:         dict
    review_score:          float
    ready_for_submission:  bool

    # ── Pipeline metadata ─────────────────────────────────────
    error:            Optional[str]
    status:           str
