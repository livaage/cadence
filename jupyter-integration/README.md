# Cadence — Jupyter integration

This integration allows students to submit solutions directly from Jupyter notebooks and teachers to create problem templates with embedded submission capabilities.

## 🚀 Quick Start

### For Students

1. **Install the Extension**:
   ```bash
   pip install cadence-edu
   
   ```

2. **Load a Problem Notebook**:
   - Teacher provides a `.ipynb` file with problem description
   - Open in Jupyter Lab or Jupyter Notebook

3. **Write Your Solution**:
   ```python
   # This cell will be submitted as your solution
   def solve_problem(input_data):
       # Your solution here
       return result
   ```

4. **Submit Solution**:
   - Click the "Submit Solution" button in the toolbar
   - Or use the cell magic: `%%submit_solution`

### For Teachers

1. **Create Problem Notebooks**:
   ```python
   # Use the problem template
   from cadence import create_problem_notebook
   
   notebook = create_problem_notebook(
       problem_id="hello-world-001",
       title="Hello World Problem",
       description="Print 'Hello, World!'",
       difficulty="Easy"
   )
   notebook.save("hello_world_problem.ipynb")
   ```

2. **Distribute to Students**:
   - Share the `.ipynb` file
   - Students can work in their preferred environment
   - Solutions are automatically submitted to the platform

## 📊 Live Lesson Progress

A lightweight checkpoint system for tracking how students progress through a notebook in real time. Teachers register expected answers; students call `check("id", value)` in any cell; a teacher dashboard shows per-checkpoint solve counts, an attempts-to-first-correct histogram, and the most common wrong answers.

See the main [README — Live Lesson Progress](../README.md#-live-lesson-progress) for the end-to-end walkthrough. The reference below documents the magics and helpers themselves.

### Magic reference

**`%load_ext cadence`** — load the extension. Required before any of the magics below.

#### Teacher magics

**`%cadence_create_lesson "<name>" [--code <join-code>]`** — creates a new lesson on the backend and saves the returned `teacher_token` / `join_code` to `~/.cadence/lessons.yaml`. Prints a clickable dashboard URL. Join code is auto-generated (e.g. `soup-river-42`) unless `--code` is supplied.

**`%cadence_lesson "<name>"`** — activates a previously-created lesson for this kernel. Reads the cached `teacher_token` and verifies it against the backend. Use at the top of every teacher notebook.

**`%cadence_register <checkpoint_id> --comparator <type> --expected <json> [--hint <str>] [--order <int>]`** — registers (or updates) the expected answer for a checkpoint in the active lesson. Idempotent — re-running with the same `<checkpoint_id>` replaces the existing record.

Comparators and their `--expected` formats:

| Comparator | `--expected` shape | Match rule |
|---|---|---|
| `exact` | `'"hello"'` or `'{"value": "hello"}'` | `str(submitted).strip() == str(value).strip()` |
| `numeric` | `'{"value": 55}'` or `'{"value": 3.14, "tolerance": 0.001}'` | `abs(submitted - value) <= tolerance` |
| `set` | `'{"value": [1, 2, 3]}'` | `set(submitted) == set(value)` (order-independent) |
| `regex` | `'{"pattern": "^[A-Z].*"}'` | `re.match(pattern, str(submitted))` |

Submitted values from `check()` are JSON-encoded before transport, so lists, dicts, numbers, and strings all round-trip correctly.

**`%cadence_self_test`** — submits every registered checkpoint's own `expected_payload` back to the server and prints a pass/fail table. Run this after `%cadence_register` calls to verify the answers evaluate as you expect. Regex checkpoints are skipped (can't auto-synthesize a matching string).

**`%cadence_create_course "<name>" [--code <join-code>]`** — creates a **course** (a named group of notebooks) on the backend and caches its teacher_token / join_code under `courses/<name>` in `~/.cadence/lessons.yaml`. Prints a clickable course-overview dashboard URL.

**`%cadence_course "<name>"`** — activates a previously-created course for this kernel.

**`%cadence_add_notebook "<name>" [--code <join-code>] [--order <int>]`** — creates a new notebook **inside the active course** and attaches it. Equivalent to `%cadence_create_lesson` + an attach-to-course step. The new notebook is also activated for subsequent `%cadence_register` calls.

**`%cadence_rotate_token [--course] [--also-join-code]`** — mint a fresh `teacher_token` for the currently active lesson (or course with `--course`). The old token is revoked server-side and the local `~/.cadence/lessons.yaml` is updated in place. By default the `join_code` is preserved so existing student notebooks keep working; pass `--also-join-code` for a hard revocation that re-issues the join code too.

### Managing cached credentials from the shell

```bash
cadence-cli lessons list                              # every cached lesson + course, tokens masked
cadence-cli lessons forget "Week 3: Fibonacci"        # drop a stale row when the server-side lesson is gone
cadence-cli lessons rotate "Week 3: Fibonacci"        # mint a new teacher_token, keep the join_code
cadence-cli lessons rotate "Spring 2026" --also-join-code   # full revocation incl. join code
```

`forget` only touches the local YAML file; nothing is sent over the network. `rotate` calls the backend and updates the cache in place. Both are scoped to a single entry; pass `--yes` to `forget` to skip the confirmation prompt.

#### Student magics

**`%cadence_session <join_code> "<display name>"`** — joins either a **standalone notebook** or a **course** as a student. The server looks up the code on both sides and dispatches accordingly.

```python
%cadence_session soup-river-42 "Alice Smith"
```

If the code belonged to a course, the magic prints the list of notebooks and reminds the student to pick one with `%cadence_notebook`.

**`%cadence_notebook "<notebook name>"`** — student-side, course enrollments only. Signals which notebook inside the course the student is currently working on. This drives the "students on each notebook" breakdown in the course dashboard. It does **not** restrict which `check(...)` calls work — attempts are always recorded under the notebook that owns the checkpoint, regardless of which notebook the student last switched to.

**`%%cadence_time <checkpoint_id>`** — cell magic that executes the cell, measures wall-clock time, and submits the value of the last expression as the answer. The elapsed time is recorded on the attempt and contributes to the teacher's timing histogram. Example:

```python
%%cadence_time fib-10
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
fib(10)
```

If the cell raises, nothing is submitted and the exception is re-raised for normal Jupyter debugging. If the cell produces no expression value on the final line (all statements), a warning is shown and nothing is submitted. Only the **first correct** attempt's time contributes to the dashboard histogram, so re-running a known-good cell doesn't pollute the stats.

### Python helpers

```python
from cadence import check, current_session, CheckResult
```

**`check(checkpoint_id: str, value) -> CheckResult`** — submits `value` for the named checkpoint in the currently active session. Returns a `CheckResult` with:

- `.is_correct: bool` (also truthy/falsy — `if check(...):` works)
- `.attempt_num: int` (1, 2, 3, … — counted server-side)
- `.hint: Optional[str]` (the teacher's hint, only on incorrect answers)

In a notebook cell, `CheckResult` renders as a colored ✅/❌ message with the attempt number.

**`current_session() -> Optional[dict]`** — returns `{"session_id", "lesson_id", "display_name", "api"}` if `%cadence_session` has been run, else `None`. Useful for debugging.

### Typical notebook layout

**Teacher setup notebook** (kept private — run once when preparing the lesson):

```python
%load_ext cadence

%cadence_create_lesson "Week 3: Fibonacci"
# prints the join code (e.g. soup-river-42) and dashboard URL

%cadence_register warm-up --order 1 \
    --comparator exact --expected '"hello"'
%cadence_register fib-10 --order 2 \
    --comparator numeric --expected '{"value": 55}'
%cadence_register sorted --order 3 \
    --comparator set --expected '{"value": [1,2,3,4,5]}' \
    --hint "Order does not matter."

%cadence_self_test   # verify every checkpoint evaluates correctly
```

Later, to reopen the lesson (or add more checkpoints):

```python
%load_ext cadence
%cadence_lesson "Week 3: Fibonacci"
```

**Student notebook** (distributed to the class — reusable every term):

```python
%load_ext cadence
%cadence_session soup-river-42 "Your Name"

from cadence import check
```

…then later in the notebook:

```python
check("warm-up", greeting)
check("fib-10", fib(10))
check("sorted", sorted_unique(values))
```

## 📋 Features

### Student Features
- ✅ **Cell-based Submission**: Mark specific cells as solutions
- ✅ **Inline Testing**: Test your code before submission
- ✅ **Real-time Feedback**: See results immediately
- ✅ **Multiple Languages**: Python, C++, and more
- ✅ **Offline Work**: Work without internet, submit when ready

### Teacher Features
- ✅ **Problem Templates**: Create standardized problem notebooks
- ✅ **Embedded Metadata**: Store problem info in notebook
- ✅ **Auto-grading**: Automatic evaluation of submissions
- ✅ **Progress Tracking**: Monitor student progress
- ✅ **Batch Operations**: Grade multiple submissions

## 🔧 Installation

### Option 1: Pip Installation
```bash
pip install cadence-edu

```

### Option 2: Development Installation
```bash
git clone <repository-url>
cd jupyter-integration
pip install -e .


```

## 📖 Usage Examples

### Student Workflow

#### 1. Basic Submission
```python
# This cell will be submitted
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test your solution
print(fibonacci(10))  # Should print 55
```

#### 2. Using Cell Magic
```python
%%submit_solution
# This entire cell will be submitted
def solve_problem():
    n = int(input())
    return n * 2
```

#### 3. Multiple Solutions
```python
# Solution 1: Iterative approach
def iterative_fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

# Solution 2: Recursive approach  
def recursive_fibonacci(n):
    if n <= 1:
        return n
    return recursive_fibonacci(n-1) + recursive_fibonacci(n-2)
```

### Teacher Workflow

#### 1. Create Problem Template
```python
from cadence import ProblemNotebook

notebook = ProblemNotebook(
    problem_id="fibonacci-001",
    title="Fibonacci Sequence",
    description="""
    Write a function that returns the nth Fibonacci number.
    
    Input: An integer n (0 ≤ n ≤ 45)
    Output: The nth Fibonacci number
    
    Example:
    Input: 10
    Output: 55
    """,
    difficulty="Medium",
    time_limit=30,
    memory_limit=512,
    test_cases=[
        {"input": "0", "output": "0", "points": 1},
        {"input": "1", "output": "1", "points": 1},
        {"input": "10", "output": "55", "points": 2},
        {"input": "20", "output": "6765", "points": 3},
    ]
)

notebook.save("fibonacci_problem.ipynb")
```

#### 2. Add Custom Test Cases
```python
# Add hidden test cases
notebook.add_test_case(
    input_data="45",
    expected_output="1134903170",
    is_hidden=True,
    points=5
)
```

## 🔌 API Integration

### Direct API Calls
```python
from cadence import CadenceAPI

api = CadenceAPI(
    base_url="http://localhost:8000",
    student_name="John Doe",
    student_email="john@example.com"
)

# Submit solution
response = api.submit_solution(
    problem_id="fibonacci-001",
    source_code="def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
    language="python"
)

print(f"Score: {response.total_score}/{response.total_points}")
```

### Batch Submission
```python
# Submit multiple solutions
solutions = [
    ("fibonacci-001", "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)"),
    ("hello-world-001", "print('Hello, World!')"),
]

for problem_id, code in solutions:
    result = api.submit_solution(problem_id, code, "python")
    print(f"{problem_id}: {result.total_score}/{result.total_points}")
```

## 🎨 Customization

### Custom Cell Markers
```python
# Use custom markers for solution cells
%%solution fibonacci-001
def fibonacci(n):
    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)
```

### Custom Submission Hooks
```python
# Pre-submission validation
def validate_solution(code):
    if "import os" in code:
        raise ValueError("OS module not allowed")
    return True

# Register validation
api.register_validation_hook(validate_solution)
```

## 🔒 Security Features

- **Code Validation**: Prevent dangerous imports
- **Resource Limits**: Enforce time and memory limits
- **Sandboxed Execution**: Run code in isolated containers
- **Input Sanitization**: Validate all inputs

## 📊 Analytics

### Student Analytics
- Submission history
- Performance trends
- Problem completion rates
- Time spent on problems

### Teacher Analytics
- Class performance overview
- Problem difficulty analysis
- Common error patterns
- Student progress tracking

## 🛠️ Configuration

### Environment Variables
```bash
export CADENCE_API_URL="http://localhost:8000"
export CADENCE_STUDENT_NAME="John Doe"
export CADENCE_STUDENT_EMAIL="john@example.com"
```

### Configuration File
```yaml
# ~/.cadence/config.yaml
api:
  base_url: "http://localhost:8000"
  timeout: 30

student:
  name: "John Doe"
  email: "john@example.com"

submission:
  auto_submit: false
  validate_before_submit: true
  max_retries: 3
```

## 🐛 Troubleshooting

### Common Issues

1. **Extension Not Loading**:
   ```bash
   jupyter nbextension list
   
   ```

2. **API Connection Issues**:
   ```python
   # Check API status
   from cadence import CadenceAPI
   api = CadenceAPI()
   print(api.status())
   ```

3. **Submission Failures**:
   ```python
   # Enable debug mode
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## 📚 Advanced Usage

### Custom Problem Types
```python
class CustomProblem(ProblemNotebook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_validator = self.validate_custom
    
    def validate_custom(self, code):
        # Custom validation logic
        pass
```

### Integration with Other Tools
```python
# Integration with nbgrader
from nbgrader import Gradebook
from cadence import CadenceAPI

# Sync grades
api = CadenceAPI()
gradebook = Gradebook("sqlite:///gradebook.db")

for assignment in gradebook.assignments:
    for submission in assignment.submissions:
        api.sync_grade(assignment.name, submission.student_id, submission.score)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]
- **Email**: support@cadence.example 