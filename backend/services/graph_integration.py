"""
Graph Integration Service - Bridges LangGraph with FastAPI.
Manages task execution, status tracking, and error handling.
"""

import asyncio
import uuid
import json
import time
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

from backend.graph.paper_state import PaperState
from backend.graph.paper_graph import PaperGenerationGraph
from backend.services.model_manager import ModelManager

# Tasks storage file
TASKS_FILE = Path(__file__).parent.parent.parent / "outputs" / "tasks.json"
COMPLETED_TASK_RETENTION = 3600  # seconds — 1 hour
MAX_TASKS = 50

PIPELINE_STEP_ORDER = [
    "model_selection",
    "research",
    "writing",
    "formatting",
    "validation",
    "review",
    "complete",
]

STEP_PROGRESS = {
    "model_selection": 8,
    "research":        20,
    "writing":         45,
    "formatting":      65,
    "validation":      80,
    "review":          92,
    "complete":        100,
}

STEP_MESSAGES = {
    "model_selection": "Selecting an available LLM",
    "research":        "Fetching arXiv papers...",
    "writing":         "Generating paper sections...",
    "formatting":      "Building IEEE LaTeX & DOCX...",
    "validation":      "Validating IEEE compliance...",
    "review":          "Final quality review...",
    "complete":        "Paper ready!",
}

class GraphIntegrationService:
    """
    Service for integrating LangGraph pipeline with FastAPI.
    
    Manages:
    - Task creation and tracking
    - LLM initialization
    - Pipeline execution
    - Status monitoring
    """

    def __init__(self, model: str = "llama3"):
        """
        Initialize the graph service.
        
        Args:
            model: Preferred Ollama model
        """
        self.model = model
        self.model_manager = ModelManager()
        self.tasks: Dict[str, Dict] = self._load_tasks()  # Load from persistent storage
        self.remove_old_tasks()
        self.cleanup_old_tasks()


    def _load_tasks(self) -> Dict[str, Dict]:
        """Load tasks from persistent storage."""
        if TASKS_FILE.exists():
            try:
                with open(TASKS_FILE, 'r') as f:
                    loaded_tasks = json.load(f)
                    # If server restarted mid-run, those tasks cannot resume.
                    for task in loaded_tasks.values():
                        if task.get("status") == "processing":
                            task["status"] = "failed"
                            task["error"] = "Task interrupted by server restart. Please regenerate."
                            task["completed_at"] = datetime.now().isoformat()
                    print(f"[INFO] Loaded {len(loaded_tasks)} tasks from {TASKS_FILE}")
                    return loaded_tasks
            except Exception as e:
                print(f"[WARNING] Failed to load tasks from {TASKS_FILE}: {e}")
        else:
            print(f"[INFO] No tasks file found at {TASKS_FILE}")
        return {}

    def _save_tasks(self):
        """Save tasks to persistent storage."""
        try:
            TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Convert tasks to JSON-serializable format
            serializable_tasks = {}
            for task_id, task in self.tasks.items():
                serializable_tasks[task_id] = {
                    "state": task["state"].to_dict() if hasattr(task["state"], "to_dict") else task["state"],
                    "model_name": task.get("model_name", self.model),
                    "status": task["status"],
                    "step": task.get("step", "model_selection"),
                    "progress": task.get("progress", 0),
                    "message": task.get("message", "Queued..."),
                    "stages": task.get("stages", {}),
                    "created_at": task["created_at"],
                    "started_at": task["started_at"],
                    "completed_at": task["completed_at"],
                    "error": task["error"],
                }
            with open(TASKS_FILE, 'w') as f:
                json.dump(serializable_tasks, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save tasks to {TASKS_FILE}: {e}")

    def _created_at_to_ts(self, created_at_value) -> float:
        """Convert created_at values (iso string or timestamp) to epoch seconds."""
        if created_at_value is None:
            return 0.0
        if isinstance(created_at_value, (int, float)):
            return float(created_at_value)
        if isinstance(created_at_value, str):
            try:
                return datetime.fromisoformat(created_at_value).timestamp()
            except Exception:
                return 0.0
        return 0.0

    @staticmethod
    def _empty_stage_map() -> Dict[str, str]:
        return {
            "model_selection": "pending",
            "research":        "pending",
            "writing":         "pending",
            "formatting":      "pending",
            "validation":      "pending",
            "review":          "pending",
            "complete":        "pending",
        }

    def _normalize_task_tracking(self, task: Dict) -> None:
        """Backfill tracking fields for older persisted tasks."""
        if "stages" not in task or not isinstance(task.get("stages"), dict):
            task["stages"] = self._empty_stage_map()
        else:
            for key, val in self._empty_stage_map().items():
                task["stages"].setdefault(key, val)

        task.setdefault("step", "model_selection")
        task.setdefault("progress", 0)
        task.setdefault("message", "Queued...")

    def _set_task_step(
        self,
        task: Dict,
        step: str,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        *,
        failed: bool = False,
    ) -> None:
        """Update task step metadata and synchronized stage map."""
        self._normalize_task_tracking(task)

        if step not in PIPELINE_STEP_ORDER:
            step = "model_selection"

        stage_map = self._empty_stage_map()
        current_idx = PIPELINE_STEP_ORDER.index(step)

        for idx, stage in enumerate(PIPELINE_STEP_ORDER):
            if idx < current_idx:
                stage_map[stage] = "completed"
            elif idx == current_idx:
                stage_map[stage] = "failed" if failed else ("completed" if step == "complete" else "in_progress")
            else:
                stage_map[stage] = "pending"

        if failed:
            stage_map["complete"] = "pending"

        task["stages"] = stage_map
        task["step"] = step
        task["progress"] = int(progress if progress is not None else STEP_PROGRESS.get(step, 0))
        task["message"] = message or STEP_MESSAGES.get(step, "Processing...")

    async def cleanup_task(self, task_id: str):
        """Remove completed/failed task after retention delay."""
        await asyncio.sleep(COMPLETED_TASK_RETENTION)
        if task_id in self.tasks and self.tasks[task_id].get("status") in {"completed", "failed"}:
            del self.tasks[task_id]
            self._save_tasks()
            print(f"[CLEANUP] Removed task {task_id}")
            print("[CLEANUP] Task removed from memory")

    def cleanup_old_tasks(self):
        """Trim oldest tasks when task count exceeds MAX_TASKS."""
        if len(self.tasks) <= MAX_TASKS:
            return

        sorted_tasks = sorted(
            self.tasks.items(),
            key=lambda x: x[1].get("created_at", ""),
        )

        while len(sorted_tasks) > MAX_TASKS:
            task_id, _ = sorted_tasks.pop(0)
            if task_id in self.tasks:
                del self.tasks[task_id]
                print(f"[CLEANUP] Removed old task {task_id}")

        self._save_tasks()

    def remove_old_tasks(self):
        """Remove expired tasks older than 1 hour."""
        now = time.time()
        for task_id in list(self.tasks.keys()):
            created_at = self.tasks[task_id].get("created_at")
            created_ts = self._created_at_to_ts(created_at)
            if created_ts and (now - created_ts > 3600):
                del self.tasks[task_id]
                print(f"[CLEANUP] Removed expired task {task_id}")

        self._save_tasks()

    def cache_pdf_path(self, task_id: str, pdf_path: str) -> None:
        """
        Persist a compiled PDF path into the task state so subsequent
        /download requests can serve it directly without recompiling.
        """
        if task_id not in self.tasks:
            return
        state = self.tasks[task_id].get("state")
        if isinstance(state, dict):
            state["pdf_path"] = pdf_path
        self._save_tasks()

    def _to_result_dict(self, state_obj) -> Dict:
        """Convert final pipeline state (TypedDict/dict) to stable API result shape."""
        fs = state_obj if isinstance(state_obj, dict) else {}
        return {
            # Paper content
            "topic":              fs.get("topic", ""),
            "abstract":           fs.get("abstract", ""),
            "keywords":           fs.get("keywords", []),
            "introduction":       fs.get("introduction", ""),
            "related_work":       fs.get("related_work", ""),
            "methodology":        fs.get("methodology", ""),
            "implementation":     fs.get("implementation", ""),
            "results_discussion": fs.get("results_discussion", ""),
            "conclusion":         fs.get("conclusion", ""),
            # Formatting outputs
            "latex_source":       fs.get("latex_source", ""),
            "tex_path":           fs.get("tex_path"),
            "pdf_path":           fs.get("pdf_path"),
            "docx_path":          fs.get("docx_path"),
            # References
            "references_raw":     fs.get("references_raw", []),
            # Validation
            "validation_report":  fs.get("validation_report", {}),
            "validation_passed":  fs.get("validation_passed", False),
            "validation_score":   fs.get("validation_score", 0.0),
            # Review
            "review_report":      fs.get("review_report", {}),
            "review_score":       fs.get("review_score", 0.0),
            "ready_for_submission": fs.get("ready_for_submission", False),
        }

    async def generate_paper(
        self,
        topic: str,
        notes: Optional[str] = None,
        diagrams: list = None,
        equations: list = None,
        tables: list = None,
        authors: list = None,
        max_references: int = 5,
        model_name: str = "llama3",
        research_structure: Optional[Dict] = None,
        paper_type: Optional[str] = None,
        target_venue: Optional[str] = None,
        page_limit: Optional[int] = None,
        problem_statement: Optional[str] = None,
        proposed_solution: Optional[str] = None,
        key_contributions: Optional[List] = None,
        datasets: Optional[List] = None,
        baselines: Optional[List] = None,
        metrics: Optional[List] = None,
        results_summary: Optional[str] = None,
        num_arxiv_papers: int = 10,
    ) -> str:
        """
        Start paper generation task.
        
        Args:
            topic: Research topic
            notes: Optional research notes
            diagrams: Optional list of diagrams
            equations: Optional list of equations
            tables: Optional list of tables
            authors: Optional list of authors
            max_references: Max number of references to retrieve
            model_name: LLM model to use
            research_structure: Optional structured research data (title, problem_statement, methodology, etc.)
            paper_type: "conference" or "journal"
            target_venue: Target publication venue
            page_limit: Maximum page count
            problem_statement: Clear problem description
            proposed_solution: High-level solution approach
            key_contributions: Explicit list of contributions
            datasets: Dataset names for experiments
            baselines: Comparison method names
            metrics: Evaluation metrics
            results_summary: Expected/actual results context
            num_arxiv_papers: Number of arXiv papers to retrieve
            
        Returns:
            task_id for status polling
        """
        # Generate task ID
        task_id = f"paper_{uuid.uuid4().hex[:8]}"

        # Extract diagrams and equations from research_structure if provided
        if research_structure:
            diagrams = diagrams or research_structure.get("diagrams", [])
            equations = equations or research_structure.get("equations", [])
            tables = tables or research_structure.get("tables", [])
            # Promote problem_statement / proposed_solution from structure if not set directly
            if not problem_statement:
                problem_statement = research_structure.get("problem_statement", "")
            if not proposed_solution:
                proposed_solution = research_structure.get("proposed_solution", "")
            # Store full structure in notes for later use
            structure_info = {
                "title": research_structure.get("title", ""),
                "problem_statement": research_structure.get("problem_statement", ""),
                "proposed_solution": research_structure.get("proposed_solution", ""),
                "objective": research_structure.get("objective", ""),
                "methodology": research_structure.get("methodology", ""),
                "dataset": research_structure.get("dataset", ""),
                "experiments": research_structure.get("experiments", ""),
                "keywords": research_structure.get("keywords", []),
                "notes": research_structure.get("notes", ""),
            }
            # Merge into notes
            combined_notes = f"{notes or ''}\n\n[RESEARCH_STRUCTURE]\n{str(structure_info)}"
            notes = combined_notes

        # Create initial state (TypedDict — plain dict)
        state: PaperState = {
            "task_id":             task_id,
            "topic":               topic,
            "user_notes":          notes or "",
            "model_name":          model_name or "",
            "authors":             authors or [],
            "status":              "processing",
            # Extended schema fields
            "paper_type":          paper_type or "",
            "target_venue":        target_venue or "",
            "page_limit":          page_limit or 8,
            "problem_statement":   problem_statement or "",
            "proposed_solution":   proposed_solution or "",
            "key_contributions":   key_contributions or [],
            "equations":           equations or [],
            "datasets":            datasets or [],
            "baselines":           baselines or [],
            "metrics":             metrics or [],
            "results_summary":     results_summary or "",
            "num_arxiv_papers":    num_arxiv_papers,
        }

        # Store task
        self.tasks[task_id] = {
            "state": state,
            "model_name": model_name,
            "status": "queued",
            "step": "model_selection",
            "progress": 0,
            "message": "Queued...",
            "stages": self._empty_stage_map(),
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
        }

        self.cleanup_old_tasks()
        
        # Persist to disk
        self._save_tasks()

        # Launch background task
        asyncio.create_task(self._execute_pipeline(task_id))

        return task_id

    async def _execute_pipeline(self, task_id: str):
        """
        Execute the paper generation pipeline.
        
        Args:
            task_id: Task identifier
        """
        try:
            task = self.tasks[task_id]
            task["status"] = "processing"
            task["started_at"] = datetime.now().isoformat()
            self._set_task_step(task, "model_selection", "Selecting an available LLM using ModelManager", 8)
            self._save_tasks()  # Persist status update

            preferred_model = task.get("model_name") or self.model
            await self.model_manager.get_llm(preferred_model=preferred_model)
            task["model_name"] = self.model_manager.current_model or preferred_model
            self._set_task_step(task, "research", "Fetching arXiv papers...", 20)
            self._save_tasks()

            graph = PaperGenerationGraph(self.model_manager)
            result_state = await asyncio.wait_for(
                graph.invoke(task["state"]),
                timeout=3600,
            )

            # Update task with results
            task["state"] = result_state
            task["status"] = "completed"
            self._set_task_step(task, "complete", "Final IEEE paper generated and ready for download", 100)
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks()  # Persist completion
            asyncio.create_task(self.cleanup_task(task_id))

        except asyncio.TimeoutError:
            task = self.tasks[task_id]
            task["status"] = "failed"
            task["error"] = "Generation timed out after 60 minutes. Please retry with a simpler prompt or fewer references."
            self._set_task_step(task, task.get("step", "model_selection"), "Generation timed out", task.get("progress", 0), failed=True)
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks()
            print(f"Pipeline timeout for {task_id}")
            asyncio.create_task(self.cleanup_task(task_id))

        except Exception as e:
            task = self.tasks[task_id]
            task["status"] = "failed"
            task["error"] = str(e)
            self._set_task_step(task, task.get("step", "model_selection"), str(e), task.get("progress", 0), failed=True)
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks()  # Persist error
            print(f"Pipeline error for {task_id}: {e}")
            asyncio.create_task(self.cleanup_task(task_id))

    def get_status(self, task_id: str) -> Dict:
        """
        Get task status.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Status dictionary
        """
        try:
            if task_id not in self.tasks:
                print(f"[DEBUG] Task {task_id} not in self.tasks. Available: {list(self.tasks.keys())}")
                return {"error": "Task not found"}

            task = self.tasks[task_id]
            self._normalize_task_tracking(task)
            state = task["state"]

            # Determine overall progress
            progress = self._calculate_progress(task)
            
            # Handle both dict and object formats for state
            def get_status_field(s, field):
                if isinstance(s, dict):
                    return s.get(field, "pending")
                return getattr(s, field, "pending")

            return {
                "task_id": task_id,
                "status": task["status"],
                "step": task.get("step", "model_selection"),
                "progress": progress,
                "message": task.get("message") or self._build_status_message(task),
                "created_at": task["created_at"],
                "started_at": task["started_at"],
                "completed_at": task["completed_at"],
                "error": task["error"],
                "stages": task.get("stages") or self._empty_stage_map(),
                # Return results if completed
                "result": self._to_result_dict(state) if task["status"] == "completed" else None,
            }
        except Exception as e:
            print(f"[ERROR] get_status failed for {task_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error retrieving status: {str(e)}"}

    def _calculate_progress(self, task: Dict) -> int:
        """Calculate overall progress percentage."""
        try:
            if task["status"] == "queued":
                return 0
            if task["status"] == "completed":
                return 100
            if task["status"] == "failed":
                return int(task.get("progress", 0))

            if "progress" in task:
                return int(task.get("progress", 0))

            state = task["state"]
            
            # Handle both dict and object formats
            def get_state_field(s, field):
                if isinstance(s, dict):
                    return s.get(field, "pending")
                return getattr(s, field, "pending")
            
            research_status = get_state_field(state, "research_status")
            writing_status = get_state_field(state, "writing_status")
            formatting_status = get_state_field(state, "formatting_status")
            review_status = get_state_field(state, "review_status")
            
            stage_progress = {
                "research": 25 if research_status == "completed" else 10,
                "writing": 50 if writing_status == "completed" else 30,
                "formatting": 75 if formatting_status == "completed" else 60,
                "review": 100 if review_status == "completed" else 90,
            }

            current_stage = None
            if research_status != "completed":
                current_stage = "research"
            elif writing_status != "completed":
                current_stage = "writing"
            elif formatting_status != "completed":
                current_stage = "formatting"
            elif review_status != "completed":
                current_stage = "review"

            if current_stage:
                return stage_progress[current_stage]

            return 0
        except Exception as e:
            print(f"[ERROR] _calculate_progress failed: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _build_status_message(self, task: Dict) -> str:
        """Build user-facing pipeline status text."""
        status = task.get("status")
        if status == "queued":
            return "Queued..."
        if status == "completed":
            return "Completed"
        if status == "failed":
            return task.get("error") or "Generation failed"

        state = task.get("state", {})
        if isinstance(state, dict):
            final_status = state.get("final_status", "")
        else:
            final_status = getattr(state, "final_status", "")

        mapping = {
            "research_in_progress": "Internet Research in progress...",
            "writing_in_progress": "Paper Writing in progress...",
            "formatting_in_progress": "IEEE Formatting in progress...",
            "review_in_progress": "Validation in progress...",
        }
        return mapping.get(final_status, "Initializing...")

    def get_result(self, task_id: str) -> Optional[Dict]:
        """
        Get final result.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Result dictionary if completed, None otherwise
        """
        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        if task["status"] != "completed":
            return None

        state = task["state"]
        return self._to_result_dict(state)

    def list_tasks(self) -> list:
        """Get list of all tasks."""
        return [
            {
                "task_id": task_id,
                "status": task["status"],
                "topic": (
                    task["state"].get("topic", "Untitled")
                    if isinstance(task["state"], dict)
                    else getattr(task["state"], "topic", "Untitled")
                ),
                "created_at": task["created_at"],
            }
            for task_id, task in self.tasks.items()
        ]

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()  # Persist deletion
            return True
        return False

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Return the raw task dict (includes state + metadata), or None."""
        return self.tasks.get(task_id)
