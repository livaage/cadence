"""
Notebook management for Code Cadence

This module provides tools for creating and managing problem notebooks
with embedded metadata for the competition platform.
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

@dataclass
class TestCase:
    """Test case for a problem"""
    input_data: str
    expected_output: str
    is_hidden: bool = False
    points: int = 1

@dataclass
class ProblemMetadata:
    """Metadata for a problem notebook"""
    problem_id: str
    title: str
    description: str
    difficulty: str
    time_limit: int = 30
    memory_limit: int = 512
    test_cases: List[TestCase] = None
    tags: List[str] = None
    created_by: str = ""
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.test_cases is None:
            self.test_cases = []
        if self.tags is None:
            self.tags = []

class ProblemNotebook:
    """A Jupyter notebook with embedded problem metadata"""
    
    def __init__(
        self,
        problem_id: str,
        title: str,
        description: str,
        difficulty: str = "Easy",
        time_limit: int = 30,
        memory_limit: int = 512,
        test_cases: Optional[List[Dict]] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Initialize a problem notebook
        
        Args:
            problem_id: Unique identifier for the problem
            title: Problem title
            description: Problem description
            difficulty: Problem difficulty (Easy, Medium, Hard)
            time_limit: Time limit in seconds
            memory_limit: Memory limit in MB
            test_cases: List of test case dictionaries
            tags: List of tags for the problem
        """
        self.metadata = ProblemMetadata(
            problem_id=problem_id,
            title=title,
            description=description,
            difficulty=difficulty,
            time_limit=time_limit,
            memory_limit=memory_limit,
            tags=tags or []
        )
        
        # Convert test cases
        if test_cases:
            for tc in test_cases:
                self.add_test_case(**tc)
        
        # Create the notebook
        self.notebook = self._create_notebook()
    
    def _create_notebook(self) -> nbf.NotebookNode:
        """Create the initial notebook structure"""
        nb = new_notebook()
        
        # Add metadata
        nb.metadata.cadence = asdict(self.metadata)
        
        # Add title cell
        title_cell = new_markdown_cell(f"# {self.metadata.title}\n\n**Difficulty:** {self.metadata.difficulty}")
        nb.cells.append(title_cell)
        
        # Add description cell
        desc_cell = new_markdown_cell(self.metadata.description)
        nb.cells.append(desc_cell)
        
        # Add problem info cell
        info_text = f"""
## Problem Information

- **Time Limit:** {self.metadata.time_limit} seconds
- **Memory Limit:** {self.metadata.memory_limit} MB
- **Problem ID:** `{self.metadata.problem_id}`

## Instructions

Write your solution in the code cell below. Your code should:
1. Read input from `input()`
2. Process the input according to the problem requirements
3. Print the result using `print()`

## Example

```python
# Read input
n = int(input())

# Your solution here
result = n * 2

# Print output
print(result)
```
"""
        info_cell = new_markdown_cell(info_text)
        nb.cells.append(info_cell)
        
        # Add solution template cell
        solution_cell = new_code_cell("# Write your solution here\n\n# Read input\n# n = int(input())\n\n# Your solution here\n# result = ...\n\n# Print output\n# print(result)")
        solution_cell.metadata.cadence = {
            "is_solution": True,
            "problem_id": self.metadata.problem_id
        }
        nb.cells.append(solution_cell)
        
        # Add test cases cell
        if self.metadata.test_cases:
            test_cases_text = "## Test Cases\n\n"
            for i, tc in enumerate(self.metadata.test_cases, 1):
                visibility = "Hidden" if tc.is_hidden else "Visible"
                test_cases_text += f"**Test Case {i}** ({visibility}, {tc.points} points)\n"
                test_cases_text += f"- Input: `{tc.input_data}`\n"
                if not tc.is_hidden:
                    test_cases_text += f"- Expected Output: `{tc.expected_output}`\n"
                test_cases_text += "\n"
            
            test_cell = new_markdown_cell(test_cases_text)
            nb.cells.append(test_cell)
        
        # Add submission cell
        submission_text = """
## Submit Your Solution

Run the cell below to submit your solution for evaluation.
"""
        submission_cell = new_markdown_cell(submission_text)
        nb.cells.append(submission_cell)
        
        submit_code = f"""
# Submit your solution
from cadence import CadenceAPI

# Initialize API (configure with your details)
api = CadenceAPI(
    student_name="Your Name",
    student_email="your.email@example.com"
)

# Submit the solution
response = api.submit_notebook_cell(
    problem_id="{self.metadata.problem_id}",
    cell_source=In[-2],  # Get the solution cell
    language="python"
)

print(f"Submission Status: {{response.status}}")
print(f"Message: {{response.message}}")

if response.status == "pending":
    # Wait for completion
    completed = api.wait_for_submission(response.submission_id)
    print(f"\\nFinal Results:")
    print(f"Score: {{completed.total_score}}/{{completed.total_points}}")
    print(f"Execution Time: {{completed.execution_time_ms}}ms")
    print(f"Memory Usage: {{completed.memory_usage_mb}}MB")
    if completed.error_message:
        print(f"Error: {{completed.error_message}}")
"""
        submit_cell = new_code_cell(submit_code)
        nb.cells.append(submit_cell)
        
        return nb
    
    def add_test_case(
        self,
        input_data: str,
        expected_output: str,
        is_hidden: bool = False,
        points: int = 1
    ):
        """Add a test case to the problem"""
        test_case = TestCase(
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            points=points
        )
        self.metadata.test_cases.append(test_case)
        
        # Update notebook metadata
        self.notebook.metadata.cadence = asdict(self.metadata)
    
    def add_solution_template(self, template_code: str):
        """Add a solution template to the notebook"""
        # Find the solution cell and update it
        for cell in self.notebook.cells:
            if (hasattr(cell, 'metadata') and 
                hasattr(cell.metadata, 'cadence') and
                cell.metadata.cadence.get('is_solution')):
                cell.source = template_code
                break
    
    def add_custom_cell(self, cell_type: str, content: str, metadata: Optional[Dict] = None):
        """Add a custom cell to the notebook"""
        if cell_type == "markdown":
            cell = new_markdown_cell(content)
        elif cell_type == "code":
            cell = new_code_cell(content)
        else:
            raise ValueError(f"Unknown cell type: {cell_type}")
        
        if metadata:
            cell.metadata.cadence = metadata
        
        self.notebook.cells.append(cell)
    
    def save(self, filename: str):
        """Save the notebook to a file"""
        nbf.write(self.notebook, filename)
    
    def get_solution_cells(self) -> List[nbf.NotebookNode]:
        """Get all solution cells from the notebook"""
        solution_cells = []
        for cell in self.notebook.cells:
            if (hasattr(cell, 'metadata') and 
                hasattr(cell.metadata, 'cadence') and
                cell.metadata.cadence.get('is_solution')):
                solution_cells.append(cell)
        return solution_cells
    
    def extract_solutions(self) -> List[str]:
        """Extract all solution code from the notebook"""
        solutions = []
        for cell in self.get_solution_cells():
            if hasattr(cell, 'source'):
                solutions.append(cell.source)
        return solutions
    
    @classmethod
    def load(cls, filename: str) -> 'ProblemNotebook':
        """Load a problem notebook from a file"""
        nb = nbf.read(filename, as_version=4)
        
        # Extract metadata
        if hasattr(nb.metadata, 'cadence'):
            metadata = nb.metadata.cadence
            problem = cls(
                problem_id=metadata['problem_id'],
                title=metadata['title'],
                description=metadata['description'],
                difficulty=metadata['difficulty'],
                time_limit=metadata['time_limit'],
                memory_limit=metadata['memory_limit'],
                tags=metadata.get('tags', [])
            )
            
            # Add test cases
            for tc_data in metadata.get('test_cases', []):
                problem.add_test_case(**tc_data)
            
            # Set the notebook
            problem.notebook = nb
            return problem
        else:
            raise ValueError("Not a valid problem notebook (missing metadata)")
    
    def validate(self) -> List[str]:
        """Validate the problem notebook"""
        errors = []
        
        # Check required fields
        if not self.metadata.problem_id:
            errors.append("Problem ID is required")
        if not self.metadata.title:
            errors.append("Title is required")
        if not self.metadata.description:
            errors.append("Description is required")
        
        # Check test cases
        if not self.metadata.test_cases:
            errors.append("At least one test case is required")
        
        # Check solution cells
        solution_cells = self.get_solution_cells()
        if not solution_cells:
            errors.append("At least one solution cell is required")
        
        return errors

def create_problem_notebook(
    problem_id: str,
    title: str,
    description: str,
    difficulty: str = "Easy",
    time_limit: int = 30,
    memory_limit: int = 512,
    test_cases: Optional[List[Dict]] = None,
    tags: Optional[List[str]] = None
) -> ProblemNotebook:
    """
    Create a new problem notebook
    
    Args:
        problem_id: Unique identifier for the problem
        title: Problem title
        description: Problem description
        difficulty: Problem difficulty
        time_limit: Time limit in seconds
        memory_limit: Memory limit in MB
        test_cases: List of test case dictionaries
        tags: List of tags for the problem
        
    Returns:
        ProblemNotebook instance
    """
    return ProblemNotebook(
        problem_id=problem_id,
        title=title,
        description=description,
        difficulty=difficulty,
        time_limit=time_limit,
        memory_limit=memory_limit,
        test_cases=test_cases,
        tags=tags
    )

def create_sample_problems() -> List[ProblemNotebook]:
    """Create sample problem notebooks"""
    problems = []
    
    # Hello World Problem
    hello_world = create_problem_notebook(
        problem_id="hello-world-001",
        title="Hello World",
        description="""
Write a program that prints "Hello, World!" to the console.

This is a simple introduction to programming.
""",
        difficulty="Easy",
        test_cases=[
            {"input_data": "", "expected_output": "Hello, World!", "points": 1}
        ]
    )
    problems.append(hello_world)
    
    # Fibonacci Problem
    fibonacci = create_problem_notebook(
        problem_id="fibonacci-001",
        title="Fibonacci Sequence",
        description="""
Write a function that returns the nth Fibonacci number.

The Fibonacci sequence is defined as:
- F(0) = 0
- F(1) = 1
- F(n) = F(n-1) + F(n-2) for n > 1

Input: An integer n (0 ≤ n ≤ 45)
Output: The nth Fibonacci number

Example:
Input: 10
Output: 55
""",
        difficulty="Medium",
        test_cases=[
            {"input_data": "0", "expected_output": "0", "points": 1},
            {"input_data": "1", "expected_output": "1", "points": 1},
            {"input_data": "10", "expected_output": "55", "points": 2},
            {"input_data": "20", "expected_output": "6765", "points": 3},
            {"input_data": "45", "expected_output": "1134903170", "is_hidden": True, "points": 5}
        ]
    )
    problems.append(fibonacci)
    
    # Sum of Two Numbers
    sum_problem = create_problem_notebook(
        problem_id="sum-numbers-001",
        title="Sum of Two Numbers",
        description="""
Write a program that reads two integers and prints their sum.

Input: Two integers on separate lines
Output: The sum of the two integers

Example:
Input:
5
3
Output:
8
""",
        difficulty="Easy",
        test_cases=[
            {"input_data": "5\n3", "expected_output": "8", "points": 1},
            {"input_data": "0\n0", "expected_output": "0", "points": 1},
            {"input_data": "-5\n10", "expected_output": "5", "points": 2}
        ]
    )
    problems.append(sum_problem)
    
    return problems 