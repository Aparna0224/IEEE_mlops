"""
FastAPI Backend for IEEE Paper Generator
REST API endpoints for LangGraph-based paper generation
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import project modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from backend import langgraph_routes

# Load environment variables
load_dotenv()

# Ensure internal pipeline steps are visible in terminal logs.
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
else:
    logging.getLogger().setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="IEEE Paper Generator API",
    description="AI-Powered Research Paper Generator using LangGraph",
    version="2.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include LangGraph paper generation routes
app.include_router(langgraph_routes.router)

# In-memory storage for generation status
generation_status = {}


# Request/Response Models
class AuthorInfo(BaseModel):
    """Author details for the paper"""
    name: str = Field(default="", max_length=100, description="Author name")
    affiliation: str = Field(default="", max_length=200, description="Institution / organization")
    location: str = Field(default="", max_length=100, description="City, Country")
    email: str = Field(default="", max_length=100, description="Contact email")


class GenerationRequest(BaseModel):
    """Request model for paper generation"""
    topic: str = Field(..., min_length=3, max_length=200, description="Research topic")
    max_results: int = Field(default=3, ge=1, le=10, description="Number of papers to fetch")
    model_name: str = Field(default="llama3", description="Ollama model to use")
    authors: list[AuthorInfo] = Field(default_factory=lambda: [AuthorInfo()], description="Authors (1-6)", min_length=1, max_length=6)


class GenerationStatus(BaseModel):
    """Status model for generation progress"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    pdf_path: Optional[str] = None
    latex_pdf_path: Optional[str] = None  # LaTeX-based IEEE PDF path
    topic: Optional[str] = None
    paper_content: Optional[str] = None
    authors: list[AuthorInfo] = Field(default_factory=list)
    references: list[dict] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)  # Paper keywords
    validation_result: Optional[dict] = None
    ieee_report: Optional[dict] = None
    enhancement_scores: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class GenerationResponse(BaseModel):
    """Response model for paper generation"""
    task_id: str
    status: str
    message: str


# Helper function to generate task ID
def generate_task_id() -> str:
    """Generate unique task ID"""
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


# Background task for paper generation
async def generate_paper_task(task_id: str, topic: str, max_results: int, model_name: str, authors: list[dict]):
    """Background task to generate paper using RobustPaperPipeline."""
    try:
        # Update status: processing
        generation_status[task_id].update({
            "status": "processing",
            "progress": 10,
            "message": "Initializing model with fallback chain...",
            "updated_at": datetime.now().isoformat()
        })

        # Progress callback that updates the shared status dict
        def _progress(stage: str, detail: str):
            pct_map = {
                "PIPELINE START": 10, "GENERATING": 30,
                "VALIDATING": 60, "BOOSTING": 65,
                "IEEE CLEANUP": 70,
                "ENHANCEMENT": 72,
                "ENHANCEMENT 1/5": 74,
                "ENHANCEMENT 2/5": 78,
                "ENHANCEMENT 3/5": 82,
                "ENHANCEMENT 4/5": 86,
                "ENHANCEMENT 5/5": 90,
                "ENHANCEMENT COMPLETE": 93,
                "COMPLETE": 95,
            }
            pct = pct_map.get(stage, 50)
            generation_status[task_id].update({
                "progress": pct,
                "message": f"{stage}: {detail}",
                "updated_at": datetime.now().isoformat()
            })

        # Search arXiv for references
        generation_status[task_id].update({
            "progress": 15,
            "message": "Searching arXiv for references...",
            "updated_at": datetime.now().isoformat()
        })
        papers = search_arxiv(topic, max_results=max_results)

        # Store references for later export use
        generation_status[task_id]["references"] = papers or []

        # Run the robust pipeline
        pipeline = RobustPaperPipeline(
            primary_model=model_name,
            progress_callback=_progress,
        )
        result = pipeline.generate(
            topic=topic,
            references=papers or [],
        )

        # Use Pydantic validation result from pipeline (already validated + boosted)
        validation_result = result.get("validation_result")
        ieee_report = result.get("ieee_report")
        enhancement_result = result.get("enhancement_result")

        # Generate IEEE PDF with LaTeX-based formatter (primary method)
        generation_status[task_id].update({
            "progress": 96,
            "message": "Generating IEEE-formatted PDF with LaTeX...",
            "updated_at": datetime.now().isoformat()
        })
        
        # Extract proper keywords from content using IEEEFormattingEngine
        # Get abstract from the content for keyword extraction
        abstract_match = None
        full_content = result["full_text"]
        abstract_keywords = []
        
        # Simple abstract extraction (look for "Abstract" section)
        import re as regex_module
        abstract_section = regex_module.search(r'(?:^|\n)\s*Abstract\s*\n(.*?)(?:\n\s*(?:Introduction|Related|Methodology)|$)', 
                                               full_content, regex_module.IGNORECASE | regex_module.DOTALL)
        if abstract_section:
            abstract_text = abstract_section.group(1)[:500]  # First 500 chars for keyword extraction
        else:
            abstract_text = full_content[:500]
        
        # Use the new keyword extraction method
        abstract_keywords = IEEEFormattingEngine._guess_keywords(topic, abstract_text)
        
        pdf_path = None
        latex_pdf_path = None
        
        try:
            # Primary: LaTeX-based IEEE formatter
            engine = IEEEFormattingEngine(output_dir="outputs")
            latex_result = engine.format(
                title=topic,
                authors=authors,
                raw_content=result["full_text"],
                references=papers or [],
                keywords=abstract_keywords,  # Pass extracted keywords
                topic_slug=task_id,
            )
            if latex_result.pdf_path:
                latex_pdf_path = latex_result.pdf_path
                pdf_path = latex_result.pdf_path
                print(f"[SUCCESS] LaTeX-based IEEE PDF generated: {latex_pdf_path}")
            else:
                # Fallback: ReportLab if LaTeX failed
                print(f"[WARNING] LaTeX generation returned no PDF path. Falling back to ReportLab...")
                pdf_path = generate_ieee_paper(topic, papers or [], result["full_text"], authors=authors)
        except Exception as latex_err:
            # Fallback: ReportLab if LaTeX failed completely
            print(f"[WARNING] LaTeX-based PDF generation failed: {latex_err}")
            print(f"[INFO] Falling back to ReportLab formatter...")
            try:
                pdf_path = generate_ieee_paper(topic, papers or [], result["full_text"], authors=authors)
                print(f"[SUCCESS] ReportLab fallback PDF generated: {pdf_path}")
            except Exception as reportlab_err:
                print(f"[ERROR] ReportLab fallback also failed: {reportlab_err}")

        # Build enhancement scores dict
        enhancement_scores = None
        if enhancement_result:
            enhancement_scores = {
                "novelty_score": enhancement_result.novelty_score,
                "ieee_compliance_score": enhancement_result.ieee_compliance_score,
                "reviewer_score": enhancement_result.reviewer_score,
                "overall_quality_score": enhancement_result.overall_quality_score,
                "enhancement_time_seconds": enhancement_result.enhancement_time_seconds,
                "stages_completed": enhancement_result.stages_completed,
                "total_actions": enhancement_result.total_actions,
            }
            # Include detailed agent reports
            if enhancement_result.novelty_analysis:
                enhancement_scores["novelty_analysis"] = enhancement_result.novelty_analysis.model_dump()
            if enhancement_result.quality_report:
                enhancement_scores["quality_report"] = enhancement_result.quality_report.model_dump()
            if enhancement_result.citation_report:
                enhancement_scores["citation_report"] = enhancement_result.citation_report.model_dump()
            if enhancement_result.review_report:
                enhancement_scores["review_report"] = enhancement_result.review_report.model_dump()
            if enhancement_result.post_processor_report:
                enhancement_scores["post_processor_report"] = enhancement_result.post_processor_report.model_dump()

        # Done
        generation_status[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Paper generation completed!",
            "pdf_path": pdf_path,
            "latex_pdf_path": latex_pdf_path,
            "paper_content": result["full_text"],
            "authors": authors,
            "keywords": abstract_keywords,  # Include extracted keywords
            "validation_result": validation_result.model_dump() if validation_result else None,
            "ieee_report": ieee_report.model_dump() if ieee_report else None,
            "enhancement_scores": enhancement_scores,
            "updated_at": datetime.now().isoformat()
        })

    except AllModelsFailed as e:
        generation_status[task_id].update({
            "status": "failed",
            "progress": 0,
            "message": "Model invocation failed. Check Ollama service and model availability.",
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        })

    except Exception as e:
        generation_status[task_id].update({
            "status": "failed",
            "progress": 0,
            "message": "Paper generation failed",
            "error": str(e),
            "updated_at": datetime.now().isoformat()
        })


# API Endpoints

@app.get("/")
async def root():
    """API root — frontend served separately via Next.js"""
    return {"service": "MCP Research Paper Generator API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_provider": os.getenv("MODEL_PROVIDER", "ollama"),
        "default_model": os.getenv("OLLAMA_MODEL", "llama3"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    }


@app.post("/api/generate", response_model=GenerationResponse)
async def generate_paper(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Start paper generation process
    Returns task ID for status tracking
    """
    try:
        # Validate request using Pydantic
        validated_request = PaperGenerationRequest(
            topic=request.topic,
            max_results=request.max_results,
            model_name=request.model_name
        )
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Initialize status
        authors_list = [a.model_dump() for a in request.authors]

        generation_status[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Task created, waiting to start...",
            "pdf_path": None,
            "topic": request.topic,
            "authors": authors_list,
            "references": [],
            "validation_result": None,
            "ieee_report": None,
            "enhancement_scores": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add background task
        background_tasks.add_task(
            generate_paper_task,
            task_id,
            validated_request.topic,
            validated_request.max_results,
            validated_request.model_name,
            authors_list
        )
        
        return GenerationResponse(
            task_id=task_id,
            status="pending",
            message="Paper generation started"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/status/{task_id}", response_model=GenerationStatus)
async def get_generation_status(task_id: str):
    """
    Get status of paper generation task
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return GenerationStatus(**generation_status[task_id])


@app.get("/api/download/{task_id}")
async def download_paper(task_id: str):
    """
    Download generated PDF paper
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = generation_status[task_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready yet")
    
    pdf_path = status.get("pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path)
    )


@app.get("/api/validation/{task_id}")
async def get_validation_metrics(task_id: str):
    """
    Get validation metrics for generated paper
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = generation_status[task_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready yet")
    
    validation_result = status.get("validation_result")
    if not validation_result:
        raise HTTPException(status_code=404, detail="Validation metrics not found")
    
    # Include IEEE report alongside validation metrics
    ieee_report = status.get("ieee_report")
    enhancement_scores = status.get("enhancement_scores")
    response = {**validation_result}
    if ieee_report:
        response["ieee_report"] = ieee_report
    if enhancement_scores:
        response["enhancement_scores"] = enhancement_scores
    
    return JSONResponse(content=response)


@app.get("/api/tasks")
async def list_tasks():
    """
    List all generation tasks
    """
    return {
        "tasks": list(generation_status.values()),
        "total": len(generation_status)
    }


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a generation task
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete PDF file if exists
    status = generation_status[task_id]
    pdf_path = status.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception as e:
            print(f"Error deleting PDF: {e}")
    
    # Remove from status
    del generation_status[task_id]
    
    return {"message": "Task deleted successfully"}


# ── IEEE LaTeX Export Endpoints ──────────────────────────────────────────────

@app.post("/export/ieee-pdf")
async def export_ieee_pdf(task_id: str):
    """
    Generate a proper IEEE-conference-ready PDF using the LaTeX
    formatting engine (IEEEtran document class + pdflatex).
    Falls back to ReportLab if pdflatex is unavailable.
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status = generation_status[task_id]
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready yet")

    paper_content = status.get("paper_content")
    if not paper_content:
        raise HTTPException(status_code=400, detail="No paper content available")

    # Collect metadata
    title = status.get("topic", "Research Paper")
    authors_raw = status.get("authors", [])
    references = status.get("references", [])

    # Use the LaTeX engine
    engine = IEEEFormattingEngine(output_dir="outputs")
    result = engine.format(
        title=title,
        authors=authors_raw,
        raw_content=paper_content,
        references=references,
        topic_slug=task_id,
    )

    if result.pdf_path and os.path.exists(result.pdf_path):
        return FileResponse(
            result.pdf_path,
            media_type="application/pdf",
            filename=os.path.basename(result.pdf_path),
            headers={
                "X-IEEE-Compliant": str(result.ieee_compliant).lower(),
                "X-Fallback-Used": str(result.fallback_used).lower(),
            },
        )

    raise HTTPException(
        status_code=500,
        detail=f"PDF generation failed: {result.error or 'Unknown error'}",
    )


@app.post("/export/ieee-latex")
async def export_ieee_latex(task_id: str):
    """
    Return the raw LaTeX source for the IEEE-formatted paper
    (useful for manual editing in Overleaf / local TeX editors).
    """
    if task_id not in generation_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status = generation_status[task_id]
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Paper not ready yet")

    paper_content = status.get("paper_content")
    if not paper_content:
        raise HTTPException(status_code=400, detail="No paper content available")

    title = status.get("topic", "Research Paper")
    authors_raw = status.get("authors", [])
    references = status.get("references", [])

    engine = IEEEFormattingEngine(output_dir="outputs")

    from src.formatters.ieee_formatter import parse_sections, _extract_abstract, _extract_references_section, AuthorInfo as FmtAuthor

    norm_authors = engine._normalise_authors(authors_raw)
    sections = parse_sections(paper_content)
    abstract, sections = _extract_abstract(sections)
    refs_text, sections = _extract_references_section(sections)
    ref_objs = engine._build_references(references, refs_text)
    kw = engine._guess_keywords(title, abstract)

    latex_src = engine._build_latex(
        title=title,
        authors=norm_authors,
        abstract=abstract,
        keywords=kw,
        sections=sections,
        references=ref_objs,
    )

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=latex_src,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{task_id}_ieee.tex"'},
    )


if __name__ == "__main__":
    import uvicorn
    # Use reload_excludes to prevent watchfiles from restarting the server when output files change
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["outputs/*", "logs/*"])
