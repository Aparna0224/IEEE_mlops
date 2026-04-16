"""
Diagram Processor Service
────────────────────────

Handles diagram upload, storage, and LaTeX figure insertion.
Converts diagram metadata into IEEE-compliant LaTeX figures.

Supported formats: PNG, JPG, SVG
"""

import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import base64


@dataclass
class DiagramInfo:
    """Metadata for a diagram"""
    diagram_id: str
    filename: str
    caption: str
    label: str
    file_path: str
    width: float = 0.9  # LaTeX width as fraction of linewidth
    position: str = "h"  # h, t, b, p (here, top, bottom, page)


@dataclass
class DiagramProcessResult:
    """Result of diagram processing"""
    diagrams: list[DiagramInfo]
    latex_figures: list[str]  # LaTeX figure code
    labels_map: dict[str, str]  # label → diagram_id mapping


class DiagramProcessor:
    """
    Manages diagram upload, storage, and LaTeX integration.
    
    Usage::
       
        processor = DiagramProcessor()
        result = processor.process_diagrams(
            diagrams=[{"base64": "...", "caption": "...", "label": "fig:architecture"}],
            output_dir="generated_assets"
        )
    """
    
    SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "svg"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    
    def __init__(self, output_dir: str = "generated_assets"):
        """
        Initialize diagram processor.
        
        Args:
            output_dir: Directory to store uploaded diagrams
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.diagrams: list[DiagramInfo] = []
    
    def save_diagram_from_base64(
        self,
        base64_data: str,
        caption: str,
        label: Optional[str] = None,
        width: float = 0.9,
    ) -> DiagramInfo:
        """
        Save a diagram from base64-encoded data.
        
        Args:
            base64_data: Base64 string of image data
            caption: Figure caption
            label: LaTeX label (auto-generated if not provided)
            width: Width as fraction of linewidth (0.0-1.0)
            
        Returns:
            DiagramInfo with saved diagram metadata
        """
        # Extract MIME type and decode
        try:
            if "," in base64_data:
                mime_header, b64 = base64_data.split(",", 1)
                # Extract extension from mime type
                if "png" in mime_header:
                    ext = "png"
                elif "svg" in mime_header:
                    ext = "svg"
                else:
                    ext = "jpg"
            else:
                b64 = base64_data
                ext = "png"  # default
            
            image_data = base64.b64decode(b64)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 image: {e}")
        
        # Validate file size
        if len(image_data) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {len(image_data)} > {self.MAX_FILE_SIZE}")
        
        # Generate unique filename
        diagram_id = str(uuid.uuid4())[:8]
        filename = f"diagram_{diagram_id}.{ext}"
        file_path = self.output_dir / filename
        
        # Save file
        file_path.write_bytes(image_data)
        
        # Create DiagramInfo
        if not label:
            label = f"fig:diagram_{diagram_id}"
        
        diagram_info = DiagramInfo(
            diagram_id=diagram_id,
            filename=filename,
            caption=caption,
            label=label,
            file_path=str(file_path),
            width=width,
        )
        
        self.diagrams.append(diagram_info)
        return diagram_info
    
    def save_diagram_from_file(
        self,
        file_path: str,
        caption: str,
        label: Optional[str] = None,
        width: float = 0.9,
    ) -> DiagramInfo:
        """
        Save diagram from file path.
        
        Args:
            file_path: Path to diagram file
            caption: Figure caption
            label: LaTeX label
            width: Width fraction
            
        Returns:
            DiagramInfo
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Diagram file not found: {file_path}")
        
        ext = file_path.suffix.lstrip(".").lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}")
        
        # Copy to output directory
        diagram_id = str(uuid.uuid4())[:8]
        new_filename = f"diagram_{diagram_id}.{ext}"
        new_path = self.output_dir / new_filename
        
        import shutil
        shutil.copy(str(file_path), str(new_path))
        
        if not label:
            label = f"fig:diagram_{diagram_id}"
        
        diagram_info = DiagramInfo(
            diagram_id=diagram_id,
            filename=new_filename,
            caption=caption,
            label=label,
            file_path=str(new_path),
            width=width,
        )
        
        self.diagrams.append(diagram_info)
        return diagram_info
    
    def generate_latex_figure(
        self,
        diagram_info: DiagramInfo,
        relative_path: Optional[str] = None,
    ) -> str:
        """
        Generate LaTeX figure code for a diagram.
        
        Args:
            diagram_info: Diagram metadata
            relative_path: Relative path to diagram from LaTeX file
            
        Returns:
            LaTeX figure code
        """
        # Use relative or absolute path
        img_path = relative_path or diagram_info.filename
        
        # Escape special characters in caption
        caption = diagram_info.caption.replace("_", "\\_").replace("&", "\\&")
        
        latex_code = f"""
\\begin{{figure}}[{diagram_info.position}]
\\centering
\\includegraphics[width={diagram_info.width:.2f}\\linewidth]{{{img_path}}}
\\caption{{{caption}}}
\\label{{{diagram_info.label}}}
\\end{{figure}}
"""
        return latex_code.strip()
    
    def process_diagrams(
        self,
        diagrams: list[Dict[str, Any]],
        output_dir: Optional[str] = None,
    ) -> DiagramProcessResult:
        """
        Process a batch of diagrams.
        
        Expected diagram format:
        {
            "base64": "data:image/png;base64,..." | "...",
            "caption": "Figure caption",
            "label": "fig:name",  # optional
            "width": 0.9,  # optional, default 0.9
        }
        
        Args:
            diagrams: List of diagram dictionaries
            output_dir: Override output directory
            
        Returns:
            DiagramProcessResult with processed diagrams
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.diagrams.clear()
        latex_figures = []
        labels_map = {}
        
        for diagram_dict in diagrams:
            try:
                base64_data = diagram_dict.get("base64", "")
                caption = diagram_dict.get("caption", "Figure")
                label = diagram_dict.get("label")
                width = diagram_dict.get("width", 0.9)
                
                diagram_info = self.save_diagram_from_base64(
                    base64_data=base64_data,
                    caption=caption,
                    label=label,
                    width=width,
                )
                
                latex_fig = self.generate_latex_figure(diagram_info)
                latex_figures.append(latex_fig)
                labels_map[diagram_info.label] = diagram_info.diagram_id
                
            except Exception as e:
                print(f"[WARNING] Failed to process diagram: {e}")
                continue
        
        return DiagramProcessResult(
            diagrams=self.diagrams,
            latex_figures=latex_figures,
            labels_map=labels_map,
        )
    
    def insert_diagrams_into_content(
        self,
        content: str,
        diagrams: list[DiagramInfo],
    ) -> str:
        """
        Insert diagram references into paper content.
        
        Looks for markers like [DIAGRAM: fig:architecture] in content
        and replaces with LaTeX figure code.
        
        Args:
            content: Paper content
            diagrams: List of DiagramInfo objects
            
        Returns:
            Content with diagrams integrated
        """
        import re
        
        # Create lookup by label
        diagrams_by_label = {d.label: d for d in diagrams}
        
        # Find and replace [DIAGRAM: label] markers
        def replace_diagram(match):
            label = match.group(1)
            if label in diagrams_by_label:
                diagram_info = diagrams_by_label[label]
                return self.generate_latex_figure(diagram_info)
            return match.group(0)  # Return original if not found
        
        # Pattern: [DIAGRAM: fig:label]
        pattern = r"\[DIAGRAM:\s*([^\]]+)\]"
        result = re.sub(pattern, replace_diagram, content)
        
        return result
    
    def get_diagram_reference_text(self, label: str) -> str:
        """
        Generate reference text for a diagram.
        
        Args:
            label: Diagram label
            
        Returns:
            Reference text like "Fig. 1"
        """
        diagram = next((d for d in self.diagrams if d.label == label), None)
        if not diagram:
            return label
        
        # Extract figure number from label if possible
        fig_num = len([d for d in self.diagrams if self.diagrams.index(d) <= self.diagrams.index(diagram)])
        return f"Fig. {fig_num}"
