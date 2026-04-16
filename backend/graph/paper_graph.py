"""
LangGraph Orchestration - Coordinates the 5-agent paper generation pipeline.
research → writing → formatting → validation → review → END
"""

import logging
from langgraph.graph import StateGraph, END

from backend.graph.paper_state import PaperState
from backend.agents_v2.research_agent import ResearchAgent
from backend.agents_v2.writing_agent import WritingAgent
from backend.agents_v2.formatting_agent import FormattingAgent
from backend.agents_v2.validation_agent import ValidationAgent
from backend.agents_v2.review_agent import ReviewAgent


logger = logging.getLogger(__name__)


class PaperGenerationGraph:
    """
    LangGraph-based orchestration for paper generation.

    Workflow:
    ResearchAgent → WritingAgent → FormattingAgent → ValidationAgent → ReviewAgent → END
    """

    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.graph = self._build()

    def _build(self):
        # Instantiate agents
        research_agent   = ResearchAgent(self.model_manager)
        writing_agent    = WritingAgent(self.model_manager)
        formatting_agent = FormattingAgent(self.model_manager)
        validation_agent = ValidationAgent(
            model_manager=self.model_manager,
            writing_agent=writing_agent,
        )
        review_agent = ReviewAgent(
            model_manager=self.model_manager,
            enabled=True,
        )

        # Build graph
        builder = StateGraph(PaperState)

        builder.add_node("research",   research_agent.run)
        builder.add_node("writing",    writing_agent.run)
        builder.add_node("formatting", formatting_agent.run)
        builder.add_node("validation", validation_agent.run)
        builder.add_node("review",     review_agent.run)

        # Linear pipeline
        builder.set_entry_point("research")
        builder.add_edge("research",   "writing")
        builder.add_edge("writing",    "formatting")
        builder.add_edge("formatting", "validation")
        builder.add_edge("validation", "review")
        builder.add_edge("review",     END)

        return builder.compile()

    async def invoke(self, initial_state: PaperState) -> PaperState:
        return await self.graph.ainvoke(initial_state)

    def get_graph_structure(self) -> dict:
        return {
            "nodes": ["research", "writing", "formatting", "validation", "review"],
            "edges": [
                ("research",   "writing"),
                ("writing",    "formatting"),
                ("formatting", "validation"),
                ("validation", "review"),
                ("review",     "END"),
            ],
            "entry_point": "research",
        }
