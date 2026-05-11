"""
IPython magic commands for Code Cadence

This module provides magic commands for submitting solutions
directly from Jupyter notebook cells.
"""

import json
import os
import shlex
import sys
import time
from typing import Optional
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from IPython.display import display, HTML, Markdown

from .api import CadenceAPI
from . import progress as _progress
from . import lesson_store


def _parse_expected(raw: str) -> dict:
    """Parse the --expected argument into an expected_payload dict.

    IPython's magic_arguments tokenizer runs shlex in posix=False mode, which
    leaves outer quote characters in place. That means the user writing
    `--expected '{"value": 55}'` sees the full `'{"value": 55}'` string
    (leading/trailing single quotes included) arrive here. We strip one layer
    of matching outer quotes, then JSON-decode, then wrap bare values in
    `{"value": ...}` so every comparator sees the same shape.
    """
    if raw is None:
        return {}
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        parsed = s
    if not isinstance(parsed, dict):
        parsed = {"value": parsed}
    return parsed

@magics_class
class CadenceMagic(Magics):
    """Magic commands for Code Cadence"""
    
    def __init__(self, shell):
        super().__init__(shell)
        self.api = None
        self._initialize_api()
    
    def _initialize_api(self):
        """Initialize the API client"""
        try:
            self.api = CadenceAPI()
            # Test connection
            status = self.api.status()
            if status.get('status') == 'error':
                self.api = None
        except Exception:
            self.api = None
    
    @magic_arguments()
    @argument('problem_id', help='Problem ID to submit for')
    @argument('-l', '--language', default='python', help='Programming language')
    @argument('-n', '--name', help='Student name')
    @argument('-e', '--email', help='Student email')
    @cell_magic
    def submit_solution(self, line, cell):
        """
        Submit a cell as a solution for a problem
        
        Usage:
            %%submit_solution problem_id [-l language] [-n name] [-e email]
            # Your solution code here
        """
        if not self.api:
            return display(HTML(
                '<div style="color: red;">❌ Cadence API not available. '
                'Please check your connection.</div>'
            ))
        
        args = parse_argstring(self.submit_solution, line)
        
        # Override API settings if provided
        if args.name:
            self.api.student_name = args.name
        if args.email:
            self.api.student_email = args.email
        
        try:
            # Submit the solution
            response = self.api.submit_notebook_cell(
                problem_id=args.problem_id,
                cell_source=cell,
                language=args.language
            )
            
            # Display initial response
            status_color = "green" if response.status == "pending" else "orange"
            display(HTML(f'''
                <div style="color: {status_color};">
                    <strong>Submission Status:</strong> {response.status}<br>
                    <strong>Message:</strong> {response.message}
                </div>
            '''))
            
            # Wait for completion if pending
            if response.status == "pending":
                display(HTML('<div>⏳ Waiting for evaluation...</div>'))
                
                try:
                    completed = self.api.wait_for_submission(response.submission_id)
                    
                    # Display results
                    if completed.status == "completed":
                        score_color = "green" if completed.total_score == completed.total_points else "orange"
                        display(HTML(f'''
                            <div style="border: 1px solid {score_color}; padding: 10px; margin: 10px 0;">
                                <h3>✅ Evaluation Complete</h3>
                                <p><strong>Score:</strong> <span style="color: {score_color};">{completed.total_score}/{completed.total_points}</span></p>
                                <p><strong>Execution Time:</strong> {completed.execution_time_ms}ms</p>
                                <p><strong>Memory Usage:</strong> {completed.memory_usage_mb}MB</p>
                            </div>
                        '''))
                    else:
                        display(HTML(f'''
                            <div style="border: 1px solid red; padding: 10px; margin: 10px 0;">
                                <h3>❌ Evaluation Failed</h3>
                                <p><strong>Error:</strong> {completed.error_message}</p>
                            </div>
                        '''))
                        
                except TimeoutError:
                    display(HTML('<div style="color: orange;">⏰ Evaluation timed out. Check the web interface for results.</div>'))
                    
        except Exception as e:
            display(HTML(f'<div style="color: red;">❌ Submission failed: {str(e)}</div>'))
    
    @line_magic
    def cadence_status(self, line):
        """Check the status of the competition platform"""
        if not self.api:
            return display(HTML('<div style="color: red;">❌ API not available</div>'))
        
        try:
            status = self.api.status()
            if status.get('status') == 'ok':
                display(HTML('<div style="color: green;">✅ Cadence is online</div>'))
            else:
                display(HTML(f'<div style="color: orange;">⚠️ Platform status: {status}</div>'))
        except Exception as e:
            display(HTML(f'<div style="color: red;">❌ Connection failed: {str(e)}</div>'))
    
    @line_magic
    def cadence_problems(self, line):
        """List available problems"""
        if not self.api:
            return display(HTML('<div style="color: red;">❌ API not available</div>'))
        
        try:
            problems = self.api.get_problems()
            
            if not problems:
                display(HTML('<div>No problems available.</div>'))
                return
            
            html = '<div><h3>Available Problems:</h3><ul>'
            for problem in problems:
                html += f'''
                    <li>
                        <strong>{problem.title}</strong> ({problem.difficulty})<br>
                        <small>ID: {problem.id} | Time: {problem.time_limit}s | Memory: {problem.memory_limit}MB</small>
                    </li>
                '''
            html += '</ul></div>'
            
            display(HTML(html))
            
        except Exception as e:
            display(HTML(f'<div style="color: red;">❌ Failed to fetch problems: {str(e)}</div>'))
    
    @magic_arguments()
    @argument('problem_id', help='Problem ID to get details for')
    @line_magic
    def cadence_problem(self, line):
        """Get details for a specific problem"""
        if not self.api:
            return display(HTML('<div style="color: red;">❌ API not available</div>'))
        
        args = parse_argstring(self.cadence_problem, line)
        
        try:
            problem = self.api.get_problem(args.problem_id)
            
            html = f'''
                <div style="border: 1px solid #ccc; padding: 15px; margin: 10px 0;">
                    <h2>{problem.title}</h2>
                    <p><strong>Difficulty:</strong> {problem.difficulty}</p>
                    <p><strong>Time Limit:</strong> {problem.time_limit} seconds</p>
                    <p><strong>Memory Limit:</strong> {problem.memory_limit} MB</p>
                    <p><strong>Problem ID:</strong> <code>{problem.id}</code></p>
                    <hr>
                    <h3>Description:</h3>
                    <div style="white-space: pre-wrap;">{problem.description}</div>
                </div>
            '''
            
            display(HTML(html))
            
        except Exception as e:
            display(HTML(f'<div style="color: red;">❌ Failed to fetch problem: {str(e)}</div>'))
    
    @line_magic
    def cadence_progress(self, line):
        """Show student progress"""
        if not self.api:
            return display(HTML('<div style="color: red;">❌ API not available</div>'))
        
        try:
            progress = self.api.get_student_progress()
            
            if 'error' in progress:
                display(HTML(f'<div style="color: orange;">⚠️ {progress["error"]}</div>'))
                return
            
            html = '<div><h3>Your Progress:</h3>'
            
            if 'submissions' in progress:
                html += '<ul>'
                for submission in progress['submissions']:
                    status_color = "green" if submission['status'] == "completed" else "orange"
                    html += f'''
                        <li>
                            <strong>{submission['problem_title']}</strong> - 
                            <span style="color: {status_color};">{submission['status']}</span>
                            {f" ({submission['total_score']}/{submission['total_points']})" if submission.get('total_score') else ""}
                        </li>
                    '''
                html += '</ul>'
            else:
                html += '<p>No submissions yet.</p>'
            
            html += '</div>'
            display(HTML(html))
            
        except Exception as e:
            display(HTML(f'<div style="color: red;">❌ Failed to fetch progress: {str(e)}</div>'))
    
    @magic_arguments()
    @argument('name', help='Student name')
    @argument('email', help='Student email')
    @line_magic
    def cadence_setup(self, line):
        """Setup student information for submissions"""
        args = parse_argstring(self.cadence_setup, line)
        
        if not self.api:
            self._initialize_api()
        
        if self.api:
            self.api.student_name = args.name
            self.api.student_email = args.email
            
            display(HTML(f'''
                <div style="color: green;">
                    ✅ Student information set:<br>
                    <strong>Name:</strong> {args.name}<br>
                    <strong>Email:</strong> {args.email}
                </div>
            '''))
        else:
            display(HTML('<div style="color: red;">❌ Could not initialize API</div>'))

    # ------------------------------------------------------------------
    # Teacher: create / activate lesson
    # ------------------------------------------------------------------

    def _require_api(self):
        if not self.api:
            self._initialize_api()
        if not self.api:
            display(HTML(
                '<div style="color: red;">❌ Cadence API not reachable at '
                f'<code>{os.getenv("CADENCE_API_URL", "http://localhost:8000")}</code>. '
                'Set <code>CADENCE_API_URL</code> or start the backend.</div>'
            ))
            return False
        return True

    def _dashboard_url(self, teacher_token: str) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "http://localhost:3000"))
        return f"{base.rstrip('/')}/teacher/live?token={teacher_token}"

    def _render_lesson_card(self, lesson: dict, created: bool) -> None:
        title = "Lesson created" if created else "Lesson loaded"
        dash = self._dashboard_url(lesson["teacher_token"])
        display(HTML(f'''
            <div style="border: 1px solid #1976d2; border-radius: 6px;
                        padding: 12px; margin: 8px 0; background: #f4f9ff;">
                <div style="font-weight: 600; color: #1976d2;">✅ {title}: {lesson["name"]}</div>
                <div style="margin-top: 6px;">
                    Share this join code with students:
                    <code style="font-size: 1.1em; background: white; padding: 2px 6px; border-radius: 3px;">
                        {lesson["join_code"]}
                    </code>
                </div>
                <div style="margin-top: 6px;">
                    🔗 <a href="{dash}" target="_blank">Open live dashboard</a>
                    &nbsp;<em style="color: #666;">(bookmark this)</em>
                </div>
                <div style="margin-top: 4px; font-size: 0.85em; color: #666;">
                    Credentials saved to <code>~/.cadence/lessons.yaml</code>
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('name', help='Lesson name (used as the local cache key)', nargs='+')
    @argument('--code', default=None, help='Override the auto-generated join code')
    @line_magic
    def cadence_create_lesson(self, line):
        """Create a new lesson and persist credentials to ~/.cadence/lessons.yaml.

        Usage:
            %cadence_create_lesson "Week 3: Fibonacci" [--code my-code]
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_create_lesson, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        if not name:
            return display(HTML('<div style="color: red;">❌ Provide a lesson name</div>'))

        join_code = args.code or lesson_store.generate_join_code()
        try:
            resp = self.api.create_lesson(name=name, join_code=join_code)
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not create lesson: {e}</div>'))

        lesson_store.put(
            name,
            lesson_id=resp["id"],
            join_code=resp["join_code"],
            teacher_token=resp["teacher_token"],
            api_url=self.api.base_url,
        )
        _progress.set_teacher(
            teacher_token=resp["teacher_token"],
            lesson_id=resp["id"],
            lesson_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_lesson_card(resp, created=True)

    @magic_arguments()
    @argument('name', help='Lesson name (must match the cache key)', nargs='+')
    @line_magic
    def cadence_lesson(self, line):
        """Activate a previously-created lesson for this kernel.

        Reads the teacher_token from ~/.cadence/lessons.yaml so subsequent
        `%cadence_register` calls and `%cadence_self_test` know which
        lesson to use.
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_lesson, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")

        cached = lesson_store.get(name)
        if not cached or not cached.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No cached lesson named <code>{name}</code>. '
                f'Run <code>%cadence_create_lesson "{name}"</code> first.</div>'
            ))

        try:
            resp = self.api.get_lesson_by_token(cached["teacher_token"])
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not reach lesson on server: {e}.<br>'
                'If you recreated the backend database, remove the stale entry with '
                f'<code>cadence-cli lessons forget "{name}"</code> and create the lesson again.</div>'
            ))

        _progress.set_teacher(
            teacher_token=resp["teacher_token"],
            lesson_id=resp["id"],
            lesson_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_lesson_card(resp, created=False)

    # ------------------------------------------------------------------
    # Teacher: create / activate course, add notebooks
    # ------------------------------------------------------------------

    def _course_dashboard_url(self, teacher_token: str) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "http://localhost:3000"))
        return f"{base.rstrip('/')}/teacher/course?token={teacher_token}"

    def _render_course_card(self, course: dict, created: bool) -> None:
        title = "Course created" if created else "Course loaded"
        dash = self._course_dashboard_url(course["teacher_token"])
        display(HTML(f'''
            <div style="border: 1px solid #7b1fa2; border-radius: 6px;
                        padding: 12px; margin: 8px 0; background: #faf5ff;">
                <div style="font-weight: 600; color: #7b1fa2;">📚 {title}: {course["name"]}</div>
                <div style="margin-top: 6px;">
                    Share this course join code with students:
                    <code style="font-size: 1.1em; background: white; padding: 2px 6px; border-radius: 3px;">
                        {course["join_code"]}
                    </code>
                </div>
                <div style="margin-top: 6px;">
                    🔗 <a href="{dash}" target="_blank">Open course dashboard</a>
                </div>
                <div style="margin-top: 4px; font-size: 0.85em; color: #666;">
                    Use <code>%cadence_add_notebook "&lt;name&gt;"</code> to add notebooks to this course.
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('name', help='Course name', nargs='+')
    @argument('--code', default=None, help='Override the auto-generated join code')
    @line_magic
    def cadence_create_course(self, line):
        """Create a course (grouping of notebooks) and persist credentials."""
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_create_course, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        if not name:
            return display(HTML('<div style="color: red;">❌ Provide a course name</div>'))

        join_code = args.code or lesson_store.generate_join_code()
        try:
            resp = self.api.create_course(name=name, join_code=join_code)
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not create course: {e}</div>'))

        lesson_store.put_course(
            name,
            course_id=resp["id"],
            join_code=resp["join_code"],
            teacher_token=resp["teacher_token"],
            api_url=self.api.base_url,
        )
        _progress.set_course_teacher(
            teacher_token=resp["teacher_token"],
            course_id=resp["id"],
            course_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_course_card(resp, created=True)

    @magic_arguments()
    @argument('name', help='Course name (matches local cache key)', nargs='+')
    @line_magic
    def cadence_course(self, line):
        """Activate a previously-created course for this kernel."""
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_course, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")

        cached = lesson_store.get_course(name)
        if not cached or not cached.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No cached course named <code>{name}</code>. '
                f'Run <code>%cadence_create_course "{name}"</code> first.</div>'
            ))
        try:
            resp = self.api.get_course_by_token(cached["teacher_token"])
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not reach course: {e}</div>'))

        _progress.set_course_teacher(
            teacher_token=resp["teacher_token"],
            course_id=resp["id"],
            course_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_course_card(resp, created=False)

    @magic_arguments()
    @argument('name', help='Notebook name', nargs='+')
    @argument('--code', default=None, help='Override the auto-generated notebook join code')
    @argument('--order', type=int, default=0, help='Order inside the course')
    @line_magic
    def cadence_add_notebook(self, line):
        """Create a new notebook inside the active course.

        Equivalent to running `%cadence_create_lesson` + attaching the
        resulting lesson to the active course. Also activates the new notebook
        so subsequent `%cadence_register` calls target it.
        """
        if not self._require_api():
            return
        course = _progress.current_course_teacher()
        if not course:
            return display(HTML(
                '<div style="color: red;">❌ No active course. Run '
                '<code>%cadence_create_course "…"</code> or '
                '<code>%cadence_course "…"</code> first.</div>'
            ))
        args = parse_argstring(self.cadence_add_notebook, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        if not name:
            return display(HTML('<div style="color: red;">❌ Provide a notebook name</div>'))

        join_code = args.code or lesson_store.generate_join_code()
        try:
            lesson = self.api.create_lesson(name=name, join_code=join_code)
            self.api.add_notebook_to_course(
                course_teacher_token=course["teacher_token"],
                lesson_teacher_token=lesson["teacher_token"],
                order_index=args.order,
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not add notebook: {e}</div>'))

        lesson_store.put(
            name,
            lesson_id=lesson["id"],
            join_code=lesson["join_code"],
            teacher_token=lesson["teacher_token"],
            api_url=self.api.base_url,
            course=course["course_name"],
        )
        _progress.set_teacher(
            teacher_token=lesson["teacher_token"],
            lesson_id=lesson["id"],
            lesson_name=lesson["name"],
            join_code=lesson["join_code"],
            api=self.api,
        )
        self._render_lesson_card(lesson, created=True)

    # ------------------------------------------------------------------
    # Student: join a session
    # ------------------------------------------------------------------

    @line_magic
    def cadence_session(self, line):
        """Join a lesson or course as a student.

        Usage:
            %cadence_session <join_code> "<your name>"

        If <join_code> belongs to a course, the student enrolls in the course
        and should then pick a notebook with `%cadence_notebook "<name>"`.
        If it belongs to a standalone lesson, they join that notebook directly.
        """
        if not self._require_api():
            return
        try:
            parts = shlex.split(line)
        except ValueError as e:
            return display(HTML(f'<div style="color: red;">❌ Could not parse arguments: {e}</div>'))
        if len(parts) < 2:
            return display(HTML(
                '<div style="color: red;">❌ Usage: '
                '<code>%cadence_session &lt;join_code&gt; "&lt;display name&gt;"</code></div>'
            ))

        join_code, display_name = parts[0], parts[1]

        # Try lesson first (cheaper, most common path); on 404 try course.
        try:
            resp = self.api.start_session(join_code, display_name)
            _progress.set_session(
                session_id=resp["session_id"],
                join_code=join_code,
                lesson_id=resp["lesson_id"],
                display_name=display_name,
                api=self.api,
            )
            return display(HTML(
                f'<div style="color: green;">✅ Joined notebook as '
                f'<strong>{display_name}</strong> (code <code>{join_code}</code>).</div>'
            ))
        except Exception:
            # Not a lesson code — fall through and try interpreting it as a course code.
            pass

        try:
            resp = self.api.start_course_session(join_code, display_name)
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Failed to join with code <code>{join_code}</code>: {e}</div>'
            ))

        # `lesson_id` in the response carries the course id for course enrollments.
        _progress.set_session(
            session_id=resp["session_id"],
            join_code=join_code,
            lesson_id=None,
            display_name=display_name,
            api=self.api,
        )
        # Fetch course metadata so we can list notebooks for the student.
        try:
            course = self.api.get_course_by_code(join_code)
            notebook_list = ''.join(
                f'<li><code>{nb["name"]}</code></li>' for nb in course.get("notebooks", [])
            ) or '<li><em>(no notebooks added yet)</em></li>'
        except Exception:
            notebook_list = ''

        display(HTML(
            f'<div style="color: green;">✅ Enrolled in course as '
            f'<strong>{display_name}</strong> (code <code>{join_code}</code>).<br>'
            f'Next, tell us which notebook you are on: '
            f'<code>%cadence_notebook "&lt;notebook name&gt;"</code><br>'
            f'<small>Available notebooks:</small>'
            f'<ul>{notebook_list}</ul></div>'
        ))

    @line_magic
    def cadence_notebook(self, line):
        """Student-side: switch to a notebook inside the active course session.

        Usage:
            %cadence_notebook "Week 1 — Variables"
        """
        if not self._require_api():
            return
        session = _progress.current_session()
        if not session:
            return display(HTML(
                '<div style="color: red;">❌ No active session. Run '
                '<code>%cadence_session &lt;join_code&gt; "&lt;name&gt;"</code> first.</div>'
            ))
        try:
            parts = shlex.split(line)
        except ValueError as e:
            return display(HTML(f'<div style="color: red;">❌ Could not parse: {e}</div>'))
        if len(parts) < 1:
            return display(HTML(
                '<div style="color: red;">❌ Usage: '
                '<code>%cadence_notebook "&lt;notebook name&gt;"</code></div>'
            ))
        target = parts[0]

        # Resolve the notebook by name against the course's notebook list.
        try:
            course = self.api.get_course_by_code(session["join_code"])
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not fetch course notebooks: {e}</div>'
            ))
        notebooks = course.get("notebooks", [])
        match = next((nb for nb in notebooks if nb["name"] == target), None)
        if not match:
            return display(HTML(
                f'<div style="color: red;">❌ No notebook named <code>{target}</code> '
                f'in course <code>{session["join_code"]}</code>.</div>'
            ))
        try:
            self.api.set_current_notebook(session["session_id"], lesson_id=match["id"])
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Switch failed: {e}</div>'))

        display(HTML(
            f'<div style="color: green;">📓 Now working on '
            f'<strong>{target}</strong>.</div>'
        ))

    # ------------------------------------------------------------------
    # Teacher: register / self-test
    # ------------------------------------------------------------------

    @magic_arguments()
    @argument('checkpoint_id', help='Checkpoint identifier')
    @argument('--comparator', default='exact', choices=['exact', 'numeric', 'set', 'regex'])
    @argument('--expected', required=True, help='JSON-encoded expected value/config')
    @argument('--hint', default=None)
    @argument('--order', type=int, default=0)
    @line_magic
    def cadence_register(self, line):
        """Register the expected answer for a checkpoint in the active lesson.

        Requires `%cadence_create_lesson` or `%cadence_lesson` first.
        """
        if not self._require_api():
            return
        teacher = _progress.current_teacher()
        if not teacher:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson. Run '
                '<code>%cadence_create_lesson "My Lesson"</code> or '
                '<code>%cadence_lesson "My Lesson"</code> first.</div>'
            ))

        args = parse_argstring(self.cadence_register, line)
        expected = _parse_expected(args.expected)

        try:
            self.api.register_checkpoint(
                teacher_token=teacher["teacher_token"],
                checkpoint_id=args.checkpoint_id,
                comparator=args.comparator,
                expected_payload=expected,
                hint=args.hint,
                order_index=args.order,
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Registration failed: {e}</div>'))

        display(HTML(
            f'<div style="color: green;">✅ Checkpoint '
            f'<code>{args.checkpoint_id}</code> registered ({args.comparator}).</div>'
        ))

    @line_magic
    def cadence_self_test(self, line):
        """Submit the teacher's own expected answer for every checkpoint.

        Use this before class to catch typos in `--expected` or tolerance errors.
        Regex checkpoints are skipped because we can't synthesize a matching
        string automatically.
        """
        if not self._require_api():
            return
        teacher = _progress.current_teacher()
        if not teacher:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson — run '
                '<code>%cadence_lesson "…"</code> first.</div>'
            ))

        try:
            checkpoints = self.api.list_checkpoints(teacher["teacher_token"])
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not load checkpoints: {e}</div>'))

        if not checkpoints:
            return display(HTML(
                '<div style="color: orange;">⚠️ No checkpoints registered yet.</div>'
            ))

        # Start a throwaway student session attached to this lesson.
        try:
            session = self.api.start_session(teacher["join_code"], "self-test")
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Could not start test session: {e}</div>'))

        rows = []
        for cp in checkpoints:
            try:
                payload = json.loads(cp["expected_payload"])
            except (json.JSONDecodeError, TypeError):
                payload = cp["expected_payload"]

            comparator = cp["comparator"]
            if comparator == "regex":
                rows.append((cp["checkpoint_id"], "skipped", "regex: cannot auto-synthesize"))
                continue

            value = payload.get("value") if isinstance(payload, dict) else payload
            try:
                result = self.api.check_answer(session["session_id"], cp["checkpoint_id"], value)
                ok = bool(result.get("is_correct"))
                rows.append((cp["checkpoint_id"], "ok" if ok else "fail",
                             f"attempt {result.get('attempt_num')}, is_correct={ok}"))
            except Exception as e:
                rows.append((cp["checkpoint_id"], "error", str(e)))

        html = ['<div style="border: 1px solid #ccc; padding: 10px; margin: 8px 0;">',
                '<strong>Self-test results</strong><table style="width:100%; border-collapse: collapse;">',
                '<tr style="border-bottom: 1px solid #ddd;"><th align="left">checkpoint</th><th align="left">status</th><th align="left">detail</th></tr>']
        icon = {"ok": "✅", "fail": "❌", "error": "⚠️", "skipped": "⏭️"}
        for cp_id, status, detail in rows:
            html.append(
                f'<tr><td><code>{cp_id}</code></td>'
                f'<td>{icon.get(status, "?")} {status}</td>'
                f'<td>{detail}</td></tr>'
            )
        html.append('</table></div>')
        display(HTML(''.join(html)))

    # ------------------------------------------------------------------
    # Teacher: rotate a leaked teacher_token
    # ------------------------------------------------------------------

    @magic_arguments()
    @argument('--course', action='store_true',
              help='Rotate the active course token instead of the active lesson token')
    @argument('--also-join-code', action='store_true',
              help='Also mint a fresh join_code. Disconnects current students — use only for hard revocation.')
    @line_magic
    def cadence_rotate_token(self, line):
        """Mint a fresh teacher_token for the active lesson (or course with --course).

        Use this when a teacher_token has leaked. After a successful call the
        old token is dead; the local ~/.cadence/lessons.yaml entry is updated
        with the new value and a fresh dashboard URL is printed.
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_rotate_token, line)

        if args.course:
            active = _progress.current_course_teacher()
            if not active:
                return display(HTML(
                    '<div style="color: red;">❌ No active course. '
                    'Run <code>%cadence_course "…"</code> first.</div>'
                ))
            try:
                resp = self.api.rotate_course_token(
                    active["teacher_token"],
                    rotate_join_code=args.also_join_code,
                )
            except Exception as e:
                return display(HTML(f'<div style="color: red;">❌ Rotation failed: {e}</div>'))

            lesson_store.put_course(
                resp["name"],
                course_id=resp["id"],
                join_code=resp["join_code"],
                teacher_token=resp["teacher_token"],
                api_url=self.api.base_url,
            )
            _progress.set_course_teacher(
                teacher_token=resp["teacher_token"],
                course_id=resp["id"],
                course_name=resp["name"],
                join_code=resp["join_code"],
                api=self.api,
            )
            self._render_course_card(resp, created=False)
            display(HTML(
                '<div style="color: #b45309;">⚠️ Old course token revoked.'
                + (' Old join code also revoked — share the new one with students.' if args.also_join_code else '')
                + '</div>'
            ))
            return

        active = _progress.current_teacher()
        if not active:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson. '
                'Run <code>%cadence_lesson "…"</code> first, or pass <code>--course</code> '
                'to rotate the active course token.</div>'
            ))
        try:
            resp = self.api.rotate_lesson_token(
                active["teacher_token"],
                rotate_join_code=args.also_join_code,
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Rotation failed: {e}</div>'))

        lesson_store.put(
            resp["name"],
            lesson_id=resp["id"],
            join_code=resp["join_code"],
            teacher_token=resp["teacher_token"],
            api_url=self.api.base_url,
        )
        _progress.set_teacher(
            teacher_token=resp["teacher_token"],
            lesson_id=resp["id"],
            lesson_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_lesson_card(resp, created=False)
        display(HTML(
            '<div style="color: #b45309;">⚠️ Old teacher token revoked.'
            + (' Old join code also revoked — update the student notebook.' if args.also_join_code else '')
            + '</div>'
        ))


    # ------------------------------------------------------------------
    # Student: timed cell check
    # ------------------------------------------------------------------

    @cell_magic
    def cadence_time(self, line, cell):
        """Run a cell, time it, then submit the last expression as the answer.

        Usage:
            %%cadence_time <checkpoint_id>
            # ... student code ...
            fib(10)        # the last expression's value is what's checked
        """
        if not self._require_api():
            return
        session = _progress.current_session()
        if not session:
            return display(HTML(
                '<div style="color: red;">❌ No active session. Run '
                '<code>%cadence_session &lt;join_code&gt; "&lt;name&gt;"</code> first.</div>'
            ))

        parts = line.strip().split()
        if not parts:
            return display(HTML(
                '<div style="color: red;">❌ Usage: '
                '<code>%%cadence_time &lt;checkpoint_id&gt;</code></div>'
            ))
        checkpoint_id = parts[0]

        start = time.perf_counter()
        result = self.shell.run_cell(cell, store_history=False, silent=True)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if not result.success:
            display(HTML(
                f'<div style="color: red;">❌ Cell raised an error '
                f'after {elapsed_ms} ms — not submitted.</div>'
            ))
            if result.error_in_exec:
                raise result.error_in_exec
            return

        if result.result is None:
            return display(HTML(
                '<div style="color: orange;">⚠️ Cell returned no value. '
                'End it with an expression whose value is your answer '
                '(e.g. <code>fib(10)</code> on the last line).</div>'
            ))

        try:
            resp = session["api"].check_answer(
                session["session_id"],
                checkpoint_id,
                result.result,
                elapsed_ms=elapsed_ms,
            )
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Submission failed: {e}</div>'
            ))

        verdict = _progress.CheckResult(
            is_correct=bool(resp.get("is_correct")),
            attempt_num=int(resp.get("attempt_num", 0)),
            hint=resp.get("hint"),
            elapsed_ms=resp.get("elapsed_ms", elapsed_ms),
        )
        display(verdict)


# IPython extension entry points live in extension.py — that's what
# `%load_ext cadence` resolves to. Don't add load/unload hooks
# here or the package will register magics twice on extension reload.
