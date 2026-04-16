r"""
Equation Service
────────────────

Handles user equation input, LaTeX conversion, and equation numbering.

Converts various equation formats into IEEE-compliant LaTeX:
- Simple symbolic math: S_i = (1/N) * sum(w_j * s_j)
- LaTeX style: S_i = \frac{1}{N} \sum_{j=1}^{N} w_j s_j
- Plain text descriptions

Automatically numbers equations and creates reference labels.
"""

import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class EquationInfo:
    """Metadata for a processed equation"""
    equation_id: str
    original_input: str
    latex_equation: str
    label: str
    equation_number: int
    explanation: str = ""
    variables: dict[str, str] = field(default_factory=dict)  # var_name → description


@dataclass
class EquationProcessResult:
    """Result of equation processing"""
    equations: list[EquationInfo]
    latex_code: list[str]  # Full LaTeX equation environments
    labels_map: dict[str, int]  # label → equation_number mapping


class EquationService:
    r"""
    Manages user equation input, LaTeX conversion, and numbering.
    
    Usage::
    
        eq_service = EquationService()
        result = eq_service.process_equations(
            equations=[
                {
                    "input": "S_i = (1/N) * sum(w_j * s_j)",
                    "label": "eq:sentiment",
                    "explanation": "Where N is the number of samples"
                }
            ]
        )
    """
    
    # Simple replacements for common math operations
    MATH_REPLACEMENTS = {
        r"\bsum\b": r"\sum",
        r"\bproduct\b": r"\prod",
        r"\bint\b": r"\int",
        r"\bfrac": r"\frac",
        r"\bsqrt": r"\sqrt",
        r"\b(\d+)/(\d+)\b": lambda m: f"\\frac{{{m.group(1)}}}{{{m.group(2)}}}",
    }
    
    def __init__(self):
        """Initialize equation service."""
        self.equations: list[EquationInfo] = []
        self.equation_counter = 0
    
    def convert_simple_to_latex(self, equation_str: str) -> str:
        r"""
        Convert simple equation notation to LaTeX.
        
        Examples:
            "1/N" → "\frac{1}{N}"
            "sum(x_i)" → "\sum x_i"
            "sqrt(x)" → "\sqrt{x}"
        
        Args:
            equation_str: Equation in simple notation
            
        Returns:
            LaTeX equation
        """
        latex = equation_str.strip()
        
        # Handle fractions: a/b → \frac{a}{b}
        # Simple cases like: 1/N, (1+N)/2
        latex = re.sub(r'\(([^)]+)\)/(\w+)', r'\\frac{\1}{\2}', latex)
        latex = re.sub(r'(\w+)/(\w+)', r'\\frac{\1}{\2}', latex)
        
        # Handle sum notation: sum(...) or Σ
        latex = latex.replace("sum(", "\\sum ")
        latex = latex.replace("Sum(", "\\sum ")
        latex = latex.replace("Σ", "\\sum ")
        
        # Handle product
        latex = latex.replace("product(", "\\prod ")
        latex = latex.replace("Product(", "\\prod ")
        latex = latex.replace("Π", "\\prod ")
        
        # Handle sqrt
        latex = re.sub(r'sqrt\(([^)]+)\)', r'\\sqrt{\1}', latex)
        
        # Handle subscripts and superscripts
        # x_i → x_{i}, x^2 → x^{2}
        latex = re.sub(r'([a-zA-Z])(_{)([^}]+)(})', r'\1_{\3}', latex)
        latex = re.sub(r'([a-zA-Z])_(\w)(?![{])', r'\1_{\2}', latex)
        latex = re.sub(r'(\}|\d|\))(\^)(\w)(?![{])', r'\1^\3', latex)
        
        return latex
    
    def extract_variables(self, equation_str: str) -> dict[str, str]:
        """
        Extract variable names from equation.
        
        Args:
            equation_str: Equation string
            
        Returns:
            Dictionary of variable names found
        """
        variables = {}
        
        # Find subscripted variables: x_i, w_j, S_i
        subscripted = re.findall(r'([a-zA-Z])_([a-zA-Z0-9]+)', equation_str)
        for var, sub in subscripted:
            var_name = f"{var}_{sub}"
            variables[var_name] = f"{var} with index {sub}"
        
        # Find simple variables: N, w, s
        simple_vars = re.findall(r'\b([A-Z])\b', equation_str)
        for var in set(simple_vars):
            if var not in variables:
                variables[var] = f"Variable {var}"
        
        return variables
    
    def create_latex_equation(
        self,
        latex_equation: str,
        label: str,
        equation_number: int,
        explanation: str = "",
    ) -> str:
        """
        Generate complete LaTeX equation environment.
        
        Args:
            latex_equation: LaTeX equation content
            label: Equation label for referencing
            equation_number: Sequential equation number
            explanation: Optional explanation text
            
        Returns:
            Complete LaTeX equation code
        """
        # Sanitize label
        label = label.replace(" ", "_").lower()
        if not label.startswith("eq:"):
            label = f"eq:{label}"
        
        latex_code = f"""
\\begin{{equation}}
{latex_equation}
\\label{{{label}}}
\\end{{equation}}
"""
        
        if explanation:
            # Escape underscores in explanation
            explanation = explanation.replace("_", "\\_")
            latex_code += f"\n\\noindent\\textit{{Note: {explanation}}}\n"
        
        return latex_code.strip()
    
    def process_equations(
        self,
        equations: list[Dict[str, str]],
        start_number: int = 1,
    ) -> EquationProcessResult:
        """
        Process a batch of equations.
        
        Expected equation format:
        {
            "input": "S_i = (1/N) * sum(w_j * s_j)",  # or already LaTeX
            "label": "eq:sentiment",  # optional
            "explanation": "Text explaining the equation"  # optional
        }
        
        Args:
            equations: List of equation dictionaries
            start_number: Starting equation number
            
        Returns:
            EquationProcessResult with processed equations
        """
        self.equations.clear()
        self.equation_counter = start_number - 1
        latex_codes = []
        labels_map = {}
        
        for eq_dict in equations:
            try:
                equation_input = eq_dict.get("input", "").strip()
                if not equation_input:
                    continue
                
                label = eq_dict.get("label", f"eq:unknown_{self.equation_counter + 1}")
                explanation = eq_dict.get("explanation", "")
                
                # Detect if already LaTeX or needs conversion
                if "\\" in equation_input or "$" in equation_input:
                    # Likely already LaTeX
                    latex_equation = equation_input.replace("$", "").strip()
                else:
                    # Convert from simple notation
                    latex_equation = self.convert_simple_to_latex(equation_input)
                
                # Extract variables
                variables = self.extract_variables(equation_input)
                
                # Increment counter
                self.equation_counter += 1
                
                # Create equation info
                eq_info = EquationInfo(
                    equation_id=f"eq_{self.equation_counter}",
                    original_input=equation_input,
                    latex_equation=latex_equation,
                    label=label,
                    equation_number=self.equation_counter,
                    explanation=explanation,
                    variables=variables,
                )
                
                self.equations.append(eq_info)
                
                # Generate LaTeX code
                latex_code = self.create_latex_equation(
                    latex_equation=latex_equation,
                    label=label,
                    equation_number=self.equation_counter,
                    explanation=explanation,
                )
                
                latex_codes.append(latex_code)
                labels_map[label] = self.equation_counter
                
            except Exception as e:
                print(f"[WARNING] Failed to process equation: {e}")
                continue
        
        return EquationProcessResult(
            equations=self.equations,
            latex_code=latex_codes,
            labels_map=labels_map,
        )
    
    def insert_equations_into_content(
        self,
        content: str,
        equations: list[EquationInfo],
    ) -> str:
        """
        Insert equation references into paper content.
        
        Looks for markers like [EQUATION: eq:sentiment] and replaces 
        with LaTeX equation code.
        
        Args:
            content: Paper content
            equations: List of processed equations
            
        Returns:
            Content with equations integrated
        """
        equations_by_label = {eq.label: eq for eq in equations}
        
        def replace_equation(match):
            label = match.group(1)
            if label in equations_by_label:
                eq = equations_by_label[label]
                return self.create_latex_equation(
                    latex_equation=eq.latex_equation,
                    label=eq.label,
                    equation_number=eq.equation_number,
                    explanation=eq.explanation,
                )
            return match.group(0)
        
        # Pattern: [EQUATION: eq:label]
        pattern = r"\[EQUATION:\s*([^\]]+)\]"
        result = re.sub(pattern, replace_equation, content)
        
        return result
    
    def generate_equation_reference(self, label: str) -> str:
        """
        Generate reference text for an equation.
        
        Args:
            label: Equation label
            
        Returns:
            Reference text like (1), (2), etc.
        """
        eq = next((e for e in self.equations if e.label == label), None)
        if not eq:
            return label
        
        return f"({eq.equation_number})"
    
    def get_all_variables_documentation(self) -> str:
        """
        Generate documentation for all variables in equations.
        
        Returns:
            Formatted text documenting all variables
        """
        doc_lines = []
        all_variables = {}
        
        for eq in self.equations:
            for var_name, var_desc in eq.variables.items():
                if var_name not in all_variables:
                    all_variables[var_name] = var_desc
        
        if all_variables:
            doc_lines.append("\\subsection*{Variables}")
            doc_lines.append("\\begin{itemize}")
            for var_name, var_desc in sorted(all_variables.items()):
                doc_lines.append(f"\\item $\\mathbf{{{var_name}}}$: {var_desc}")
            doc_lines.append("\\end{itemize}")
        
        return "\n".join(doc_lines)
