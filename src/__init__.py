"""
MCP-PROJECT: AI-Powered Research Paper Generator
Full-stack application for generating IEEE-formatted research papers

Now uses LangGraph for the core pipeline (see backend/langgraph_routes.py)
"""

__version__ = "2.0.0"
__author__ = "JAashmi"

# Legacy agents/modules are integrated into LangGraph pipeline
# For direct access to specific components, import from their respective modules
# E.g.: from src.agents.novelty_agent import NoveltyAgent
#       from src.validators.pydantic_models import PaperGenerationRequest

__all__ = [
    "PaperGeneratorAgent",
    "search_arxiv",
    "PydanticContentValidator",
    "ValidationResult",
    "PaperGenerationRequest",
    "PaperGenerationResponse",
    "generate_ieee_paper",
    "IEEEFormattingEngine",
]
