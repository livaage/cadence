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
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring as _ipython_parse_argstring
from IPython.display import display, HTML, Markdown

from .api import CadenceAPI
from . import progress as _progress
from . import lesson_store
from . import creds_store
from . import scaffold as _scaffold
from . import autoregister as _autoregister


def _strip_inline_comment(line: str) -> str:
    """Strip a trailing Python-style `#` comment from a magic line argument.

    IPython line-magics get the whole post-command line as a single string,
    including any trailing `# ...` comment. argparse then chokes on the `#`
    as an unknown positional, so commands like
        %cadence_delete_my_data --yes   # actually wipes
    fail. Strip the comment here, respecting quoted strings."""
    if not line:
        return line
    in_single = False
    in_double = False
    for i, c in enumerate(line):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line


def _unwrap_quotes(value):
    """Strip a single matching pair of outer quotes from a string.

    IPython's magic_arguments runs `arg_split` in posix=False mode, which
    PRESERVES quote characters around argument values — so `--password "abc"`
    would otherwise leave `args.password == '"abc"'` (5 chars, not 3). We
    apply this uniformly across every string arg parsed by `parse_argstring`
    so quoted and unquoted invocations behave identically. Only one matching
    outer pair is removed, so an oddly-quoted real value like `"x"y"` keeps
    its inner quote characters."""
    if value is None or not isinstance(value, str) or len(value) < 2:
        return value
    if value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def parse_argstring(magic, line):
    """Like IPython's parse_argstring, with two consistency fixes applied
    once here so every magic gets them:

      1. Trailing `# ...` comments are stripped before argparse sees them, so
         `%cadence_delete_my_data --yes   # actually wipes` doesn't choke.
      2. Outer quotes are removed from every string arg (and every element of
         list-valued args), so `--password "x"` and `--password x` reach the
         magic as the same value `x`. Without this, IPython's posix=False
         arg_split would silently produce `'"x"'` — bug class that already
         bit %cadence_login once."""
    parsed = _ipython_parse_argstring(magic, _strip_inline_comment(line))
    for name, value in list(vars(parsed).items()):
        if isinstance(value, str):
            setattr(parsed, name, _unwrap_quotes(value))
        elif isinstance(value, list):
            setattr(parsed, name, [_unwrap_quotes(v) if isinstance(v, str) else v for v in value])
    return parsed


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
        """Initialize the API client.

        No network probe here — %load_ext must stay offline-safe. A transient
        gateway response (non-JSON body, captive portal, corporate proxy) used
        to surface as a scary "API request failed: Expecting value..." in the
        load cell AND wedge self.api=None for the rest of the kernel, so every
        magic would report "❌ API not available". Each magic does its own
        network call with a real error message; let that be the source of truth.
        """
        try:
            self.api = CadenceAPI()
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
                '<div style="color: red;">❌ Could not reach Cadence. '
                'Check your internet connection and try again. '
                'If this keeps happening, contact the person who set up your class.</div>'
            ))
            return False
        return True

    def _dashboard_url(self, teacher_token: str) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "https://cadence-dash.com"))
        return f"{base.rstrip('/')}/teacher/live?token={teacher_token}"

    # ------------------------------------------------------------------
    # Teacher authentication
    # ------------------------------------------------------------------

    @magic_arguments()
    @argument('--username', default=None, help='Username for password login.')
    @argument('--password', default=None,
              help='Password for non-interactive login (less safe; prefer the prompt).')
    @argument('--token', default=None,
              help='Paste a JWT here (e.g. from web GitHub login) instead of password login.')
    @line_magic
    def cadence_login(self, line):
        """Log in as a teacher. Required for creating courses.

        Three ways:
          %cadence_login                                     # prompts for username + password
          %cadence_login --username alice                    # prompts for password only
          %cadence_login --token <jwt>                       # paste a JWT from web OAuth

        The JWT is stored in ~/.cadence/credentials.yaml (0600 perms).
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_login, line)

        if args.token:
            jwt = args.token.strip()
            self.api.set_auth_token(jwt)
            try:
                me = self.api.whoami()
            except Exception as e:
                self.api.clear_auth_token()
                return display(HTML(
                    f'<div style="color: red;">❌ That JWT was rejected: {e}</div>'
                ))
            creds_store.set_credentials(jwt, username=me.get("username"))
            return self._render_login_success(me)

        # No pre-login banner: the GitHub-no-password hint that used to live
        # here was shown to *everyone*, including users with passwords, which
        # made the flow noisy and falsely scary. The post-failure error path
        # below already surfaces the hint when it's actually relevant.

        username = args.username
        if not username:
            try:
                username = input("Cadence username: ").strip()
            except EOFError:
                return display(HTML('<div style="color: red;">❌ No username provided.</div>'))
        if not username:
            return display(HTML('<div style="color: red;">❌ Username required.</div>'))

        password = args.password
        if not password:
            try:
                import getpass
                password = getpass.getpass(f"Password for {username}: ")
            except EOFError:
                return display(HTML('<div style="color: red;">❌ No password provided.</div>'))
        if not password:
            return display(HTML('<div style="color: red;">❌ Password required.</div>'))

        web_url = os.getenv("CADENCE_DASHBOARD_URL",
                            os.getenv("CADENCE_WEB_URL", "https://cadence-dash.com"))
        try:
            resp = self.api.login(username, password)
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Login failed: {e}</div>'
                f'<div style="font-size: 0.9em; color: #475569; margin-top: 4px;">'
                f'If you signed up with GitHub and haven\'t set a Jupyter password, '
                f'<a href="{web_url.rstrip("/")}/teacher/account?prompt=password" target="_blank">set one here</a> '
                f'then retry, or paste a JWT with <code>%cadence_login --token YOUR_JWT</code>.'
                f'</div>'
            ))
        jwt = resp["access_token"]
        self.api.set_auth_token(jwt)
        try:
            me = self.api.whoami()
        except Exception as e:
            self.api.clear_auth_token()
            return display(HTML(
                f'<div style="color: red;">❌ Could not verify JWT after login: {e}</div>'
            ))
        creds_store.set_credentials(jwt, username=me.get("username"))
        self._render_login_success(me)

    def _render_login_success(self, me: dict) -> None:
        display(HTML(f'''
            <div style="border: 1px solid #15803d; border-radius: 6px;
                        padding: 10px 14px; margin: 8px 0; background: #f0fdf4;
                        line-height: 1.5; color: #1f2937;">
                <div style="font-weight: 600; color: #15803d;">
                    ✅ Signed in as {me.get("username", "?")}
                </div>
                <div style="margin-top: 4px; font-size: 0.85em; color: #475569;">
                    {me.get("email", "?")} · cached in <code>~/.cadence/credentials.yaml</code>
                </div>
            </div>
        '''))

    @line_magic
    def cadence_logout(self, line):
        """Clear the cached teacher JWT for this machine."""
        creds_store.clear()
        if self.api:
            self.api.clear_auth_token()
        display(HTML(
            '<div style="color: #475569;">👋 Signed out. The JWT cache at '
            '<code>~/.cadence/credentials.yaml</code> has been removed.</div>'
        ))

    @line_magic
    def cadence_whoami(self, line):
        """Show the currently logged-in teacher (if any)."""
        if not self._require_api():
            return
        if not creds_store.get_jwt():
            return display(HTML(
                '<div style="color: #475569;">Not signed in. Run '
                '<code>%cadence_login</code> first.</div>'
            ))
        try:
            me = self.api.whoami()
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Stored JWT is no longer valid: {e}. '
                'Run <code>%cadence_login</code> again.</div>'
            ))
        display(HTML(f'''
            <div style="font-size: 0.95em;">
                Signed in as <strong>{me.get("username")}</strong>
                (<code>{me.get("email")}</code>)
            </div>
        '''))

    # ------------------------------------------------------------------
    # Teacher attestation (13+ / school authority)
    # ------------------------------------------------------------------

    _ATTESTATION_TEXT = (
        "By creating sessions on Cadence you agree to the Terms of Service and "
        "Privacy Notice. The Terms include the age and consent requirements for "
        "students (13+, or under your institution's authority with appropriate "
        "consent in place where local law requires it)."
    )

    def _check_attestation_or_prompt(self) -> bool:
        """Return True if the teacher has accepted the Terms.

        - Logged-in teachers (JWT cached) accepted at web signup or via the
          OAuth callback — skip the local prompt entirely.
        - For token-only lesson flow (no JWT): check the local cache; if
          missing, show an inline prompt and accept in the same cell. No
          re-run needed.
        """
        if creds_store.get_jwt():
            return True
        if lesson_store.is_attested():
            return True

        terms_url = self._terms_url()
        privacy_url = self._privacy_url()
        display(HTML(f'''
            <div style="border: 1px solid #b45309; border-radius: 6px;
                        padding: 12px; margin: 8px 0; background: #fffbeb;">
                <div style="font-weight: 600; color: #b45309;">
                    📜 First-time setup
                </div>
                <div style="margin: 8px 0;">
                    {self._ATTESTATION_TEXT}
                </div>
                <div style="margin: 8px 0; font-size: 0.9em;">
                    <a href="{terms_url}" target="_blank">Read the full Terms</a>
                    · <a href="{privacy_url}" target="_blank">Privacy Notice</a>
                </div>
            </div>
        '''))
        try:
            answer = input("Type 'yes' to accept and continue: ").strip().lower()
        except EOFError:
            display(HTML('<div style="color: orange;">No input received.</div>'))
            return False
        if answer not in ("yes", "y"):
            display(HTML(
                '<div style="color: orange;">Not accepted. Nothing was created. '
                'Re-run the command to try again.</div>'
            ))
            return False
        lesson_store.record_attestation()
        display(HTML(
            '<div style="color: #15803d; font-size: 0.9em;">'
            '✅ Recorded. Continuing…</div>'
        ))
        return True

    @line_magic
    def cadence_accept_terms(self, line):
        """Pre-record acceptance of the Terms of Service.

        Optional — the create-lesson flow will prompt inline if you haven't
        accepted yet. Use this if you want to accept up front in a script.
        Saved to ~/.cadence/terms.yaml.
        """
        try:
            lesson_store.record_attestation()
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not save attestation: {e}</div>'
            ))
        display(HTML(
            '<div style="color: #15803d; font-size: 0.9em;">'
            '✅ Terms acceptance recorded. To withdraw, delete '
            '<code>~/.cadence/terms.yaml</code>.</div>'
        ))

    @staticmethod
    def _copy_button(text: str, label: str = "Copy") -> str:
        """Return HTML for a button that copies `text` to the clipboard on click.

        Two layers of escaping: first for the JS string literal (backslashes,
        single quotes, newlines), then for the HTML attribute that wraps the
        whole onclick handler (`"` would otherwise close the attribute mid-way
        — e.g. the student snippet contains `"your-name"`, which used to break
        the button and mangle everything after it in the card)."""
        safe = (text
                .replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "\\r"))
        safe = safe.replace("&", "&amp;").replace('"', "&quot;")
        return (
            f'<button onclick="navigator.clipboard.writeText(\'{safe}\');'
            f'this.innerText=\'✓ Copied\';setTimeout(()=>{{this.innerText=\'{label}\';}},1500);"'
            f' style="margin-left: 6px; padding: 1px 8px; font-size: 0.75em;'
            f' background: white; border: 1px solid #ccc; border-radius: 3px;'
            f' cursor: pointer; vertical-align: middle;">{label}</button>'
        )


    def _render_lesson_card(self, lesson: dict, created: bool) -> None:
        title = "Lesson created" if created else "Lesson loaded"
        dash = self._dashboard_url(lesson["teacher_token"])
        join_code = lesson["join_code"]
        teacher_token = lesson["teacher_token"]
        retention = lesson.get("session_retention_days", 7)
        # Built outside the HTML f-string so the literal \n in the snippet
        # doesn't appear inside an f-string expression (3.12-only syntax).
        student_snippet = f'%load_ext cadence\n%cadence_session {join_code} "your-name"'
        # If the teacher is logged in, the lesson is associated with their
        # account via teacher_id and shows up automatically in their library.
        # If not, the only way to find it again is the dashboard URL.
        logged_in = bool(creds_store.get_jwt())
        if logged_in:
            dash_hint = (
                "(saved to your library automatically — the dashboard has a "
                "<strong>Display join code</strong> button for projecting in class)"
            )
        else:
            dash_hint = (
                "(bookmark this — you're not signed in, so the URL is the only way back. "
                "The dashboard has a <strong>Display join code</strong> button for projecting in class)"
            )
        retention_word = f"{retention} day{'s' if retention != 1 else ''}"
        display(HTML(f'''
            <div style="border: 1px solid #1976d2; border-radius: 6px;
                        padding: 14px 16px; margin: 8px 0; background: #f4f9ff;
                        line-height: 1.5; color: #1f2937;">
                <div style="font-weight: 600; color: #1976d2; margin-bottom: 10px;">
                    ✅ {title}: {lesson["name"]}
                </div>

                <div style="margin-bottom: 12px;">
                    <div>Share this join code with students:</div>
                    <div style="margin-top: 4px;">
                        <code style="background: white; padding: 3px 8px; border-radius: 3px;">{join_code}</code>
                        {self._copy_button(join_code)}
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <div style="font-size: 0.85em; color: #475569;">Or paste this snippet at the top of the student notebook:</div>
                    <pre style="background: white; padding: 8px 10px; margin: 4px 0; border-radius: 3px; font-size: 0.9em; overflow-x: auto;">%load_ext cadence
%cadence_session {join_code} "your-name"</pre>
                    {self._copy_button(student_snippet, "Copy snippet")}
                </div>

                <div style="margin-bottom: 12px;">
                    <a href="{dash}" target="_blank">Open live dashboard</a>
                    {self._copy_button(dash, "Copy URL")}
                    <div style="font-size: 0.85em; color: #475569; margin-top: 2px;">{dash_hint}</div>
                </div>

                <div style="font-size: 0.85em; color: #475569; margin-bottom: 12px;">
                    Teacher token (keep secret):
                    <code style="background: white; padding: 1px 6px; border-radius: 3px;">{teacher_token[:8]}…</code>
                    {self._copy_button(teacher_token, "Copy token")}
                </div>

                <div style="font-size: 0.85em; color: #475569; padding: 8px 10px; background: white; border-radius: 4px; margin-bottom: 8px;">
                    <strong>Retention:</strong> after <strong>{retention_word}</strong> of inactivity,
                    each student session is <strong>de-identified</strong> — the display name is
                    removed but per-checkpoint stats (solve rates, common wrong answers, timing)
                    are kept for your dashboard. Default 7 days for quick lessons; pass
                    <code>--retention-days N</code> (1–365) at creation to start higher.
                    Attaching this lesson to a course bumps it to the course's retention (3 months
                    by default) automatically. Wipe everything immediately with
                    <code>%cadence_delete_lesson "{lesson["name"]}" --yes</code>.
                </div>

                <div style="font-size: 0.8em; color: #64748b;">
                    Cached in <code>~/.cadence/lessons.yaml</code>.
                    Other commands: <code>%cadence_clone_lesson</code>,
                    <code>%cadence_attach_lesson … --to "&lt;course&gt;"</code>.
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('name', help='Lesson name (used as the local cache key)', nargs='+')
    @argument('--code', default=None, help='Override the auto-generated join code')
    @argument('--retention-days', type=int, default=None,
              help='Per-session retention in days (1-365). Default 7. Can be '
                   'shortened later but never extended, so pick the value you '
                   'actually want now.')
    @argument('--force', action='store_true',
              help='Create a second lesson even if one with this name is already cached.')
    @line_magic
    def cadence_create_lesson(self, line):
        """Create a new lesson and persist credentials to ~/.cadence/lessons.yaml.

        Usage:
            %cadence_create_lesson "Week 3: Fibonacci"
            %cadence_create_lesson "Week 3: Fibonacci" --retention-days 30
            %cadence_create_lesson "..." [--code my-code] [--force]

        Re-runs are safe: if a lesson with this name is already cached, we
        load and reactivate it instead of creating a duplicate. Pass --force
        to create a fresh second lesson with the same name (different
        teacher_token and join code).
        """
        if not self._require_api():
            return
        if not self._check_attestation_or_prompt():
            return
        args = parse_argstring(self.cadence_create_lesson, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        if not name:
            return display(HTML('<div style="color: red;">❌ Provide a lesson name</div>'))

        # Rerun protection: if this kernel already has a lesson cached under
        # the same name, reload it instead of creating a duplicate. The
        # teacher almost certainly re-ran the cell by accident.
        cached = lesson_store.get(name)
        if cached and cached.get("teacher_token") and not args.force:
            try:
                resp = self.api.get_lesson_by_token(cached["teacher_token"])
            except Exception:
                resp = None
            if resp:
                display(HTML(
                    f'<div style="background: #fffbeb; border-left: 3px solid #b45309; '
                    f'padding: 8px 12px; margin-bottom: 8px; font-size: 0.9em;">'
                    f'A lesson named <code>{name}</code> is already cached on this machine — '
                    f'loaded it instead of creating a duplicate. The existing join code still '
                    f'works; new students who run <code>%cadence_session</code> with it will '
                    f'each get their own session attached to this lesson, timestamped '
                    f'server-side.<br><br>'
                    f'<strong>When to do something else:</strong><br>'
                    f'· Same content, fresh cohort (e.g. monthly workshop) and you want a '
                    f'<em>separate</em> roster: '
                    f'<code>%cadence_clone_lesson "{name}" --as "{name} — &lt;date&gt;"</code>. '
                    f'New join code, new session pool, checkpoints copied across.<br>'
                    f'· You want to wipe all the prior student data and start over: '
                    f'<code>%cadence_delete_lesson "{name}" --yes</code>, then re-run.<br>'
                    f'· You truly want two lessons with the exact same name: re-run with '
                    f'<code>--force</code>.<br>'
                    f'<em style="color: #475569; font-size: 0.85em;">Note: a "session" is a '
                    f'single student\'s join. The system creates them automatically on every '
                    f'<code>%cadence_session</code> call — you never have to "make" one.</em>'
                    f'</div>'
                ))
                _progress.set_teacher(
                    teacher_token=resp["teacher_token"],
                    lesson_id=resp["id"],
                    lesson_name=resp["name"],
                    join_code=resp["join_code"],
                    api=self.api,
                )
                return self._render_lesson_card(resp, created=False)
            # Stale cache (server doesn't know the token anymore); fall through
            # and create fresh — quieter than asking the user to "forget" it.

        join_code = args.code or lesson_store.generate_join_code()
        if args.retention_days is not None and not (1 <= args.retention_days <= 365):
            return display(HTML(
                '<div style="color: red;">❌ <code>--retention-days</code> must be between 1 and 365.</div>'
            ))
        try:
            resp = self.api.create_lesson(
                name=name,
                join_code=join_code,
                session_retention_days=args.retention_days,
            )
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
                f'<div style="color: red;">❌ Could not find lesson <code>{name}</code>: {e}.<br>'
                'If the lesson has been deleted, remove the local entry with '
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
    # Teacher: project the join code for the class
    # ------------------------------------------------------------------

    @line_magic
    def cadence_show_join(self, line):
        """Display the active lesson or course's join code in big text.

        Useful when projecting in a classroom — run this and screen-share the
        cell output. Uses the active lesson if there is one, otherwise the
        active course.
        """
        teacher = _progress.current_teacher() or _progress.current_course_teacher()
        if not teacher:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson or course. Run '
                '<code>%cadence_create_lesson</code>, <code>%cadence_lesson</code>, '
                '<code>%cadence_create_course</code>, or <code>%cadence_course</code> first.</div>'
            ))
        code = teacher["join_code"]
        name = teacher.get("lesson_name") or teacher.get("course_name") or ""
        display(HTML(f'''
            <div style="background: white; padding: 48px 24px; margin: 16px 0;
                        border: 2px solid #1976d2; border-radius: 12px; text-align: center;">
                <div style="color: #1976d2; font-size: 1.1em; margin-bottom: 20px; opacity: 0.8;">
                    Join code for <strong>{name}</strong>
                </div>
                <div style="font-family: 'JetBrains Mono', 'Menlo', monospace;
                            font-size: 4.5em; font-weight: 700; letter-spacing: 0.04em;
                            color: #0d47a1; line-height: 1.1;">{code}</div>
                <div style="color: #475569; margin-top: 28px; font-size: 0.95em;">
                    Run in a notebook: <code style="background: #f0f0f0; padding: 2px 6px;
                    border-radius: 3px;">%cadence_session {code} "your-name"</code>
                </div>
            </div>
        '''))

    # ------------------------------------------------------------------
    # Teacher: create / activate course, add notebooks
    # ------------------------------------------------------------------

    def _course_dashboard_url(self, teacher_token: str) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "https://cadence-dash.com"))
        return f"{base.rstrip('/')}/teacher/course?token={teacher_token}"

    def _render_course_card(self, course: dict, created: bool) -> None:
        title = "Course created" if created else "Course loaded"
        dash = self._course_dashboard_url(course["teacher_token"])
        join_code = course["join_code"]
        teacher_token = course["teacher_token"]
        retention = course.get("session_retention_days", 90)
        retention_word = f"{retention} day{'s' if retention != 1 else ''}"
        display(HTML(f'''
            <div style="border: 1px solid #7b1fa2; border-radius: 6px;
                        padding: 14px 16px; margin: 8px 0; background: #faf5ff;
                        line-height: 1.5; color: #1f2937;">
                <div style="font-weight: 600; color: #7b1fa2; margin-bottom: 10px;">
                    📚 {title}: {course["name"]}
                </div>

                <div style="margin-bottom: 12px;">
                    <div>Share this course join code with students:</div>
                    <div style="margin-top: 4px;">
                        <code style="background: white; padding: 3px 8px; border-radius: 3px;">{join_code}</code>
                        {self._copy_button(join_code)}
                    </div>
                </div>

                <div style="margin-bottom: 12px;">
                    <a href="{dash}" target="_blank">Open course dashboard</a>
                    {self._copy_button(dash, "Copy URL")}
                    <div style="font-size: 0.85em; color: #475569; margin-top: 2px;">
                        Saved to your library — use the dashboard's <strong>Display join code</strong> button for projecting in class.
                    </div>
                </div>

                <div style="font-size: 0.85em; color: #475569; margin-bottom: 12px;">
                    Teacher token (keep secret):
                    <code style="background: white; padding: 1px 6px; border-radius: 3px;">{teacher_token[:8]}…</code>
                    {self._copy_button(teacher_token, "Copy token")}
                </div>

                <div style="font-size: 0.85em; color: #475569; padding: 8px 10px; background: white; border-radius: 4px; margin-bottom: 8px;">
                    <strong>Retention:</strong> after <strong>{retention_word}</strong> of inactivity,
                    each student session is <strong>de-identified</strong> — the display name is
                    removed but per-checkpoint stats are kept for the dashboard. Default 90 days
                    (~3 months) for courses, since you typically want progress visible across a
                    whole term. Pass <code>--retention-days N</code> at creation to override (1–365);
                    shorten any time with <code>%cadence_set_retention --course --days N</code>.
                    Notebooks attached to this course inherit its retention automatically.
                </div>

                <div style="font-size: 0.8em; color: #64748b;">
                    Add notebooks with <code>%cadence_add_notebook "&lt;name&gt;"</code>.
                    Wipe with <code>%cadence_delete_course "{course["name"]}" --yes</code>.
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('name', help='Course name', nargs='+')
    @argument('--code', default=None, help='Override the auto-generated join code')
    @argument('--retention-days', type=int, default=None,
              help='Per-session retention in days (1–365). Default 90.')
    @argument('--yes-long-retention', action='store_true',
              help='Skip the soft warning for retention > 180 days.')
    @argument('--force', action='store_true',
              help='Create a second course even if one with this name is already cached.')
    @line_magic
    def cadence_create_course(self, line):
        """Create a course (grouping of notebooks) and persist credentials.

        Courses are owned by a teacher account, so this requires
        `%cadence_login` first. (Quick lessons via `%cadence_create_lesson`
        do not require login.)

        Re-runs are safe: if a course with this name is already cached, we
        load it instead of creating a duplicate. Pass --force to create a
        fresh second course with the same name.
        """
        if not self._require_api():
            return
        if not creds_store.get_jwt():
            return display(HTML(
                '<div style="border: 1px solid #b45309; border-radius: 6px;'
                ' padding: 10px; margin: 8px 0; background: #fffbeb;">'
                '<strong style="color: #b45309;">🔒 Sign in required</strong><br>'
                'Courses are tied to a teacher account so we can authorize student'
                ' rights requests against a named controller. Run'
                ' <code>%cadence_login</code> first, then re-run this command.<br>'
                '<span style="font-size: 0.85em; color: #475569;">Quick one-off lessons'
                ' (<code>%cadence_create_lesson</code>) do not require an account.</span>'
                '</div>'
            ))
        # Refresh the API client's Authorization header in case the token was
        # set via the web (paste-flow) and the kernel was already alive.
        self.api._refresh_auth_from_store()
        if not self._check_attestation_or_prompt():
            return
        args = parse_argstring(self.cadence_create_course, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        if not name:
            return display(HTML('<div style="color: red;">❌ Provide a course name</div>'))

        # Rerun protection: if this kernel already has a course cached under
        # the same name, reload it instead of creating a duplicate.
        cached = lesson_store.get_course(name)
        if cached and cached.get("teacher_token") and not args.force:
            try:
                resp = self.api.get_course_by_token(cached["teacher_token"])
            except Exception:
                resp = None
            if resp:
                display(HTML(
                    f'<div style="background: #fffbeb; border-left: 3px solid #b45309; '
                    f'padding: 8px 12px; margin-bottom: 8px; font-size: 0.9em;">'
                    f'A course named <code>{name}</code> is already cached on this machine — '
                    f'loaded it instead of creating a duplicate. The existing join code still '
                    f'works; new students will each get their own enrollment.<br><br>'
                    f'If that\'s not what you want:<br>'
                    f'· To start over with a clean roster: '
                    f'<code>%cadence_delete_course "{name}" --yes</code>, then re-run.<br>'
                    f'· To force a duplicate with this exact same name: re-run with '
                    f'<code>--force</code>.'
                    f'</div>'
                ))
                _progress.set_course_teacher(
                    teacher_token=resp["teacher_token"],
                    course_id=resp["id"],
                    course_name=resp["name"],
                    join_code=resp["join_code"],
                    api=self.api,
                    session_retention_days=resp.get("session_retention_days"),
                )
                return self._render_course_card(resp, created=False)
            # Stale cache; fall through and create.

        retention = args.retention_days
        if retention is not None and not (1 <= retention <= 365):
            return display(HTML(
                '<div style="color: red;">❌ <code>--retention-days</code> must be between 1 and 365.</div>'
            ))
        # Soft warning per the design doc: long retention (> 6 months) is a
        # red flag without explicit confirmation.
        if retention is not None and retention > 180 and not args.yes_long_retention:
            return display(HTML(
                f'<div style="border: 1px solid #b45309; border-radius: 6px;'
                f' padding: 10px; margin: 8px 0; background: #fffbeb;">'
                f'<strong style="color: #b45309;">⚠ Long retention</strong><br>'
                f'You asked for <strong>{retention} days</strong> of per-session'
                f' retention. Cohort-level aggregates are kept indefinitely already;'
                f' individual per-student data this long increases breach impact'
                f' without much teaching benefit after a few months.<br>'
                f'If you really need it (e.g. multi-semester course, longitudinal'
                f' study under institutional approval), re-run with'
                f' <code>--yes-long-retention</code>.'
                f'</div>'
            ))

        join_code = args.code or lesson_store.generate_join_code()
        try:
            resp = self.api.create_course(
                name=name,
                join_code=join_code,
                session_retention_days=retention,
            )
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
            session_retention_days=resp.get("session_retention_days"),
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
            session_retention_days=resp.get("session_retention_days"),
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
            # Create the lesson with the course's retention upfront so the
            # rendered lesson card matches the course card. The server-side
            # attach below has its own bump-on-attach safety net, but doing
            # this at creation avoids the local-card-vs-server-state mismatch
            # that used to show "7 days" on the lesson and "90 days" on the
            # course in the same render.
            lesson = self.api.create_lesson(
                name=name,
                join_code=join_code,
                session_retention_days=course.get("session_retention_days"),
            )
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

    @magic_arguments()
    @argument('lesson_name', help='Name of the lesson to attach (must exist in ~/.cadence/lessons.yaml)', nargs='+')
    @argument('--to', dest='course_name', required=True,
              help='Course name to attach the lesson to (must already exist).')
    @argument('--order', type=int, default=0, help='Order inside the course.')
    @line_magic
    def cadence_attach_lesson(self, line):
        """Attach an existing lesson to a course as a notebook.

        Use this when you've already created a standalone lesson and now want
        it to be part of a course. The lesson keeps its join code and teacher
        token; the only change is that the course's dashboard now shows it as
        one of the course notebooks. Use `%cadence_add_notebook` if you want
        to create a fresh lesson in one step.

        Usage:
            %cadence_attach_lesson "My Lesson" --to "Fall 2026"
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_attach_lesson, line)
        lesson_name = ' '.join(args.lesson_name).strip().strip('"').strip("'")
        course_name = args.course_name.strip().strip('"').strip("'")

        lesson_cache = lesson_store.get(lesson_name)
        if not lesson_cache or not lesson_cache.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No lesson named <code>{lesson_name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>. Did you typo, or is the lesson on '
                'another machine? You can <code>%cadence_lesson "name"</code> first to load it.</div>'
            ))
        course_cache = lesson_store.get_course(course_name)
        if not course_cache or not course_cache.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No course named <code>{course_name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>. Did you typo, or is the course on '
                'another machine? You can <code>%cadence_course "name"</code> first to load it.</div>'
            ))

        try:
            self.api.add_notebook_to_course(
                course_teacher_token=course_cache["teacher_token"],
                lesson_teacher_token=lesson_cache["teacher_token"],
                order_index=args.order,
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Attach failed: {e}</div>'))

        # Update the local cache to record the course association.
        lesson_store.put(
            lesson_name,
            lesson_id=lesson_cache.get("lesson_id"),
            join_code=lesson_cache.get("join_code"),
            teacher_token=lesson_cache.get("teacher_token"),
            api_url=lesson_cache.get("api_url", self.api.base_url),
            course=course_name,
        )

        display(HTML(f'''
            <div style="border: 1px solid #15803d; border-radius: 6px;
                        padding: 10px; margin: 8px 0; background: #f0fdf4;">
                <div style="font-weight: 600; color: #15803d;">
                    🔗 Attached <code>{lesson_name}</code> to course <code>{course_name}</code>
                </div>
                <div style="margin-top: 6px; font-size: 0.85em; color: #475569;">
                    The course dashboard now shows it as one of the notebooks.
                    Students who join via the course code can pick it with
                    <code>%cadence_notebook "{lesson_name}"</code>.
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('lesson_name', help='Lesson name', nargs='+')
    @argument('--from', dest='course_name', required=True,
              help='Course name to detach the lesson from.')
    @line_magic
    def cadence_detach_lesson(self, line):
        """Remove a lesson from a course (does not delete either).

        Pair with %cadence_attach_lesson to "move" a lesson between courses:
            %cadence_detach_lesson "X" --from "Old Course"
            %cadence_attach_lesson "X" --to "New Course"
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_detach_lesson, line)
        lesson_name = ' '.join(args.lesson_name).strip().strip('"').strip("'")
        course_name = args.course_name.strip().strip('"').strip("'")

        lesson_cache = lesson_store.get(lesson_name)
        if not lesson_cache or not lesson_cache.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No lesson named <code>{lesson_name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>.</div>'
            ))
        course_cache = lesson_store.get_course(course_name)
        if not course_cache or not course_cache.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No course named <code>{course_name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>.</div>'
            ))
        try:
            self.api.detach_notebook_from_course(
                course_teacher_token=course_cache["teacher_token"],
                lesson_teacher_token=lesson_cache["teacher_token"],
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Detach failed: {e}</div>'))
        display(HTML(
            f'<div style="color: #475569;">🔗 Detached <code>{lesson_name}</code> from course '
            f'<code>{course_name}</code>. The lesson itself is unchanged.</div>'
        ))

    @magic_arguments()
    @argument('name', help='Lesson name', nargs='+')
    @argument('--yes', action='store_true',
              help='Skip the confirmation prompt. Required to actually delete.')
    @line_magic
    def cadence_delete_lesson(self, line):
        """Wipe a lesson and ALL its student data (attempts, submissions, reveals).

        Usage:
            %cadence_delete_lesson "Lesson name"             # confirmation prompt
            %cadence_delete_lesson "Lesson name" --yes       # actually delete
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_delete_lesson, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        cached = lesson_store.get(name)
        if not cached or not cached.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No lesson named <code>{name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>.</div>'
            ))
        if not args.yes:
            return display(HTML(
                f'<div style="border: 1px solid #b91c1c; border-radius: 6px;'
                f' padding: 10px; margin: 8px 0; background: #fef2f2;">'
                f'<strong style="color: #b91c1c;">⚠ Confirm deletion</strong><br>'
                f'This wipes <code>{name}</code> AND every student session, attempt, code'
                f' submission, and solution reveal attached to it. <strong>Cannot be undone.</strong><br>'
                f'Re-run as <code>%cadence_delete_lesson "{name}" --yes</code> to proceed.'
                f'</div>'
            ))
        try:
            self.api.delete_lesson(cached["teacher_token"])
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Deletion failed: {e}</div>'))
        lesson_store.remove(name)
        display(HTML(
            f'<div style="color: #15803d;">✅ Lesson <code>{name}</code> deleted.</div>'
        ))

    @magic_arguments()
    @argument('name', help='Course name', nargs='+')
    @argument('--yes', action='store_true',
              help='Skip the confirmation prompt. Required to actually delete.')
    @line_magic
    def cadence_delete_course(self, line):
        """Wipe a course and the student sessions joined directly to it.
        Attached lessons are detached but NOT deleted — they remain available
        standalone. To wipe a lesson, use %cadence_delete_lesson separately.

        Usage:
            %cadence_delete_course "Course name"             # confirmation prompt
            %cadence_delete_course "Course name" --yes       # actually delete
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_delete_course, line)
        name = ' '.join(args.name).strip().strip('"').strip("'")
        cached = lesson_store.get_course(name)
        if not cached or not cached.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No course named <code>{name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>.</div>'
            ))
        if not args.yes:
            return display(HTML(
                f'<div style="border: 1px solid #b91c1c; border-radius: 6px;'
                f' padding: 10px; margin: 8px 0; background: #fef2f2;">'
                f'<strong style="color: #b91c1c;">⚠ Confirm deletion</strong><br>'
                f'This wipes course <code>{name}</code> and every student enrollment +'
                f' attempts joined via its code. <strong>Cannot be undone.</strong><br>'
                f'Notebooks attached to the course are <em>detached</em> but not deleted —'
                f' delete each one separately if you want those gone too.<br>'
                f'Re-run as <code>%cadence_delete_course "{name}" --yes</code> to proceed.'
                f'</div>'
            ))
        try:
            self.api.delete_course(cached["teacher_token"])
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Deletion failed: {e}</div>'))
        lesson_store.remove(name)
        display(HTML(
            f'<div style="color: #15803d;">✅ Course <code>{name}</code> deleted.</div>'
        ))

    @magic_arguments()
    @argument('name', help='Name of the lesson to clone', nargs='+')
    @argument('--as', dest='new_name', default=None,
              help='Name for the clone (default: "<original> (copy)").')
    @line_magic
    def cadence_clone_lesson(self, line):
        """Duplicate a lesson with all its checkpoints. The clone gets a fresh
        join_code and teacher_token; the original is unchanged.

        Usage:
            %cadence_clone_lesson "Fall 2026 Week 3"
            %cadence_clone_lesson "Fall 2026 Week 3" --as "Spring 2027 Week 3"
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_clone_lesson, line)
        source_name = ' '.join(args.name).strip().strip('"').strip("'")
        cached = lesson_store.get(source_name)
        if not cached or not cached.get("teacher_token"):
            return display(HTML(
                f'<div style="color: red;">❌ No lesson named <code>{source_name}</code> in '
                '<code>~/.cadence/lessons.yaml</code>.</div>'
            ))
        new_name = (args.new_name or f"{source_name} (copy)").strip().strip('"').strip("'")
        try:
            resp = self.api.clone_lesson(cached["teacher_token"], new_name=new_name)
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Clone failed: {e}</div>'))

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
        self._render_lesson_card(resp, created=True)

    @magic_arguments()
    @argument('--days', type=int, required=True,
              help='New retention in days. Must be SHORTER than the current value — retention can only be reduced, not extended (data subjects relied on the original promise).')
    @argument('--course', action='store_true',
              help='Target the active course instead of the active lesson.')
    @line_magic
    def cadence_set_retention(self, line):
        """Shorten the session retention for the active lesson (default) or
        active course (--course). Can only reduce, never extend — that's a
        design constraint, not a bug. To extend, you'd have to clone the
        lesson under a new name and migrate fresh students over.
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_set_retention, line)
        if args.course:
            active = _progress.current_course_teacher()
            if not active:
                return display(HTML(
                    '<div style="color: red;">❌ No active course. Run '
                    '<code>%cadence_course "..."</code> first.</div>'
                ))
            try:
                resp = self.api.set_course_retention(active["teacher_token"], args.days)
            except Exception as e:
                return display(HTML(f'<div style="color: red;">❌ {e}</div>'))
            _progress.set_course_teacher(
                teacher_token=resp["teacher_token"],
                course_id=resp["id"],
                course_name=resp["name"],
                join_code=resp["join_code"],
                api=self.api,
                session_retention_days=resp.get("session_retention_days"),
            )
            return self._render_course_card(resp, created=False)

        active = _progress.current_teacher()
        if not active:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson. Run '
                '<code>%cadence_lesson "..."</code> first, or pass <code>--course</code>.</div>'
            ))
        try:
            resp = self.api.set_lesson_retention(active["teacher_token"], args.days)
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ {e}</div>'))
        _progress.set_teacher(
            teacher_token=resp["teacher_token"],
            lesson_id=resp["id"],
            lesson_name=resp["name"],
            join_code=resp["join_code"],
            api=self.api,
        )
        self._render_lesson_card(resp, created=False)

    # ------------------------------------------------------------------
    # Student: just-in-time privacy notice (GDPR Article 13)
    # ------------------------------------------------------------------

    def _privacy_url(self) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "https://cadence-dash.com"))
        return f"{base.rstrip('/')}/privacy"

    def _terms_url(self) -> str:
        base = os.getenv("CADENCE_DASHBOARD_URL",
                         os.getenv("CADENCE_WEB_URL", "https://cadence-dash.com"))
        return f"{base.rstrip('/')}/terms"

    def _render_join_notice(self, display_name: str) -> None:
        """GDPR Article 13 just-in-time notice rendered before a student joins."""
        privacy_url = self._privacy_url()
        display(HTML(f'''
            <div style="border: 1px solid #1976d2; border-radius: 6px;
                        padding: 12px; margin: 8px 0; background: #f0f7ff;
                        font-size: 0.95em;">
                <div style="font-weight: 600; color: #1976d2; margin-bottom: 6px;">
                    📋 Before you join: how Cadence handles your data
                </div>
                <div style="margin: 6px 0;">
                    Cadence shows your real-time progress to your teacher so they
                    can see how the class is doing and help where needed.
                </div>
                <div style="margin: 6px 0; padding: 6px 10px; background: #fffceb;
                            border-left: 3px solid #b45309; font-size: 0.9em;">
                    You can use a pseudonym (like <code>birb_42</code>) instead of
                    your real name, and you can remove everything any time with
                    <code>%cadence_delete_my_data</code>.
                </div>
                <ul style="margin: 6px 0; padding-left: 18px; line-height: 1.5;">
                    <li><strong>Collected</strong>: display name
                        (<code>{display_name}</code>), checkpoint progress,
                        attempts, timing, and code you submit.</li>
                    <li><strong>Who sees it</strong>: your teacher only.</li>
                    <li><strong>How long</strong>: the period your teacher set
                        for this session. After that your <em>display name</em>
                        is removed; per-checkpoint aggregates (solve counts,
                        common answers) stay for the teacher's dashboard but
                        no longer point at you.</li>
                    <li><strong>Never</strong>: used to train models, shared with
                        other teachers, sold, or used for ads.</li>
                    <li><strong>Your rights</strong>: see, export, or delete your data
                        with <code>%cadence_my_data</code>,
                        <code>%cadence_export_my_data</code>,
                        <code>%cadence_delete_my_data</code>.</li>
                </ul>
                <div style="font-size: 0.85em; color: #475569; margin-top: 6px;">
                    <a href="{privacy_url}" target="_blank">Full privacy notice</a>
                    · Questions or complaints: <code>privacy@cadence-dash.com</code>
                </div>
            </div>
        '''))

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

        # Article 13 notice at the moment of collection, before the API call.
        self._render_join_notice(display_name)

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
    # Student: data rights (GDPR Articles 15, 17, 20)
    # ------------------------------------------------------------------

    def _require_active_session(self):
        """Return the active session dict or render an error and return None."""
        session = _progress.current_session()
        if not session:
            display(HTML(
                '<div style="color: red;">❌ No active session. Run '
                '<code>%cadence_session &lt;join_code&gt; "&lt;name&gt;"</code> first.</div>'
            ))
            return None
        return session

    @line_magic
    def cadence_my_data(self, line):
        """Show everything Cadence stores about your current session (Article 15)."""
        if not self._require_api():
            return
        session = self._require_active_session()
        if not session:
            return
        try:
            data = self.api.get_my_data(session["session_id"])
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not fetch your data: {e}</div>'
            ))

        sess = data.get("session", {})
        attempts = data.get("attempts", [])
        submissions = data.get("code_submissions", [])
        reveals = data.get("solution_reveals", [])

        attempt_rows = ''.join(
            f'<tr><td><code>{a["checkpoint_id"]}</code></td>'
            f'<td>{a["attempt_num"]}</td>'
            f'<td>{"✅" if a["is_correct"] else "❌"}</td>'
            f'<td style="font-size: 0.85em; color: #475569;">{a["created_at"]}</td></tr>'
            for a in attempts
        ) or '<tr><td colspan="4"><em>none</em></td></tr>'

        submission_rows = ''.join(
            f'<tr><td><code>{s["checkpoint_id"]}</code></td>'
            f'<td>{len((s["code"] or "").splitlines())} lines</td>'
            f'<td>{"image attached" if s["has_image"] else "—"}</td>'
            f'<td style="font-size: 0.85em; color: #475569;">{s["submitted_at"]}</td></tr>'
            for s in submissions
        ) or '<tr><td colspan="4"><em>none</em></td></tr>'

        display(HTML(f'''
            <div style="border: 1px solid #1976d2; border-radius: 6px;
                        padding: 12px; margin: 8px 0; background: #f8fbff;">
                <div style="font-weight: 600; color: #1976d2;">
                    📂 Your data in this session
                </div>
                <div style="margin: 6px 0; font-size: 0.9em; color: #444;">
                    <strong>Display name:</strong> {sess.get("display_name", "?")}
                    · <strong>Session started:</strong> {sess.get("started_at", "?")}
                </div>
                <div style="margin-top: 10px;"><strong>Attempts ({len(attempts)}):</strong></div>
                <table style="width: 100%; font-size: 0.9em; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #ddd; text-align: left;">
                        <th>checkpoint</th><th>#</th><th>correct</th><th>when</th>
                    </tr>
                    {attempt_rows}
                </table>
                <div style="margin-top: 10px;"><strong>Code submissions ({len(submissions)}):</strong></div>
                <table style="width: 100%; font-size: 0.9em; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #ddd; text-align: left;">
                        <th>checkpoint</th><th>code</th><th>extras</th><th>when</th>
                    </tr>
                    {submission_rows}
                </table>
                <div style="margin-top: 10px; font-size: 0.85em; color: #475569;">
                    Solution reveals: {len(reveals)}
                    · Download with <code>%cadence_export_my_data</code>
                    · Delete with <code>%cadence_delete_my_data</code>
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('--path', default=None,
              help='Output file path. Defaults to ./cadence-my-data-<timestamp>.json')
    @line_magic
    def cadence_export_my_data(self, line):
        """Download your session data as JSON (Article 20, right of portability)."""
        if not self._require_api():
            return
        session = self._require_active_session()
        if not session:
            return
        args = parse_argstring(self.cadence_export_my_data, line)
        try:
            data = self.api.get_my_data(session["session_id"])
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not export your data: {e}</div>'
            ))

        path = args.path or f"cadence-my-data-{int(time.time())}.json"
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not write to <code>{path}</code>: {e}</div>'
            ))
        display(HTML(
            f'<div style="color: green;">💾 Exported to <code>{path}</code>.'
            f' Open it in any text editor or feed it to another tool.</div>'
        ))

    @magic_arguments()
    @argument('--yes', action='store_true',
              help='Skip the confirmation prompt. Required to actually delete.')
    @line_magic
    def cadence_delete_my_data(self, line):
        """Delete everything Cadence stores about your current session (Article 17).

        Wipes attempts, code submissions, solution reveals, and the session
        record. Cannot be undone. Pass --yes to confirm.
        """
        if not self._require_api():
            return
        session = self._require_active_session()
        if not session:
            return
        args = parse_argstring(self.cadence_delete_my_data, line)
        if not args.yes:
            return display(HTML(
                '<div style="border: 1px solid #b91c1c; border-radius: 6px;'
                ' padding: 10px; margin: 8px 0; background: #fef2f2;">'
                '<strong style="color: #b91c1c;">⚠ Confirm deletion</strong><br>'
                'This wipes your display name, every attempt, every code submission,'
                ' and every solution reveal for this session. <strong>Cannot be undone.</strong><br>'
                'Re-run as <code>%cadence_delete_my_data --yes</code> to proceed.'
                '</div>'
            ))
        try:
            self.api.delete_my_data(session["session_id"])
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Deletion failed: {e}.'
                f' If this persists, email <code>privacy@cadence-dash.com</code>.</div>'
            ))
        _progress.clear_session()
        display(HTML(
            '<div style="color: green;">✅ Your session data has been deleted.'
            ' This kernel is no longer connected — run <code>%cadence_session</code>'
            ' again if you want to rejoin.</div>'
        ))

    # ------------------------------------------------------------------
    # Teacher: scaffold a student notebook from this teacher notebook
    # ------------------------------------------------------------------

    @magic_arguments()
    @argument('src', nargs='?', default=None,
              help='Path to your teacher notebook. Omit to auto-detect.')
    @argument('--out', default=None,
              help='Output path (default: <src>_registered.ipynb).')
    @argument('--lesson-name', default=None,
              help='Lesson name (default: derived from the notebook stem).')
    @argument('--all', dest='force_all', action='store_true',
              help='Treat every (markdown + code) pair as an exercise even if '
                   'you have manual `# cadence:checkpoint` markers somewhere. '
                   'Without this flag, manual markers take over when present.')
    @argument('--reveal-after', type=int, default=None,
              help='Add solution reveals after N wrong attempts. Skip to be '
                   'prompted interactively; pass `--reveal-after 0` to disable '
                   'reveals without being asked.')
    @argument('--force', action='store_true',
              help='Overwrite the output file if it already exists.')
    @line_magic
    def cadence_autoregister(self, line):
        """Turn a vanilla teacher notebook into a Cadence-wired one.

        Walks the current notebook, identifies exercise cells (either by
        `# cadence:checkpoint <id>` markers or — when no markers exist —
        by pairing every markdown-heading cell with the code cell that
        follows it), reads each answer value from the current kernel
        namespace, and writes a new notebook with `%cadence_create_lesson`
        and a pre-filled `%%cadence_register_yaml` block at the top.

        Imports and other setup cells are copied verbatim (no markers
        needed). Review the generated notebook, then run `%cadence_scaffold`
        on it to produce the student version.

        Usage:
            %cadence_autoregister                       # auto-detects this notebook
            %cadence_autoregister teacher.ipynb
            %cadence_autoregister --all                 # ignore manual markers
            %cadence_autoregister --reveal-after 3      # skip the prompt
        """
        from pathlib import Path
        args = parse_argstring(self.cadence_autoregister, line)
        if args.src:
            src = Path(args.src)
        else:
            detected = _scaffold.detect_current_notebook()
            if detected is None:
                return display(HTML(
                    '<div style="color: red;">❌ Could not auto-detect the current notebook. '
                    'Pass the path explicitly: '
                    '<code>%cadence_autoregister path/to/teacher.ipynb</code></div>'
                ))
            src = detected
            display(HTML(
                f'<div style="font-size: 0.85em; color: #475569; margin-bottom: 4px;">'
                f'Auto-detected notebook: <code>{src}</code></div>'
            ))

        target = Path(args.out) if args.out else src.with_name(f"{src.stem}_registered.ipynb")
        if target.exists() and not args.force:
            return display(HTML(
                f'<div style="color: red;">❌ <code>{target}</code> already exists. '
                f'Re-run with <code>--force</code> to overwrite.</div>'
            ))

        # Interactive prompt for solution reveals (skip if user passed --reveal-after).
        reveal_after = args.reveal_after
        if reveal_after is None:
            try:
                ans = input(
                    "Reveal solutions to students after N wrong attempts? "
                    "[empty=no, default 3 if just yes]: "
                ).strip().lower()
            except EOFError:
                ans = ""
            if ans in ("", "n", "no"):
                reveal_after = None
            elif ans in ("y", "yes"):
                reveal_after = 3
            else:
                try:
                    reveal_after = int(ans)
                except ValueError:
                    return display(HTML(
                        f'<div style="color: red;">❌ Could not parse '
                        f'<code>{ans}</code> as a number. Re-run and enter a '
                        f'plain integer (or empty for no reveals).</div>'
                    ))
        elif reveal_after == 0:
            reveal_after = None  # `--reveal-after 0` is the non-interactive "no"

        # Optional sign-in. Only prompts if the teacher isn't already signed
        # in; signing in lets them attach the lesson to a course and have it
        # show up in their /teacher/library across machines.
        already_signed_in = bool(creds_store.get_jwt())
        if not already_signed_in:
            try:
                ans = input(
                    "Sign in to track this lesson under your Cadence account "
                    "(needed for courses)? [y/N]: "
                ).strip().lower()
            except EOFError:
                ans = "n"
            if ans in ("y", "yes"):
                # Hand off to the existing login magic; it does its own prompts.
                self.cadence_login("")
                already_signed_in = bool(creds_store.get_jwt())
                if not already_signed_in:
                    return display(HTML(
                        '<div style="color: #b45309; padding: 8px;">'
                        'Sign-in didn\'t complete. Re-run <code>%cadence_autoregister</code> '
                        'when you\'re ready.</div>'
                    ))

        # Course context (only meaningful if signed in — courses require it).
        course_choice = None
        if already_signed_in:
            try:
                course_ans = input(
                    "Add this lesson to a course? "
                    "[empty=standalone, '<name>'=existing, 'new: <name>'=create]: "
                ).strip()
            except EOFError:
                course_ans = ""
            if course_ans:
                low = course_ans.lower()
                if low.startswith("new:") or low.startswith("new "):
                    new_name = course_ans.split(":", 1)[-1].strip()
                    if low.startswith("new ") and ":" not in course_ans:
                        new_name = course_ans[4:].strip()
                    new_name = new_name.strip('"').strip("'")
                    course_choice = ("new", new_name) if new_name else None
                else:
                    course_choice = ("existing", course_ans.strip('"').strip("'"))

        # Retention prompt — defaults depend on whether this is standalone
        # or part of a course. 7 days is sensible for one-off labs; 90 days
        # (~3 months) matches a typical course term. Empty input → default.
        retention_default = 90 if course_choice else 7
        retention_label = "course" if course_choice else "one-off lesson"
        retention_days: Optional[int] = None
        try:
            ret_ans = input(
                f"How many days to keep each student's data? "
                f"(empty = default {retention_default} for {retention_label}): "
            ).strip()
        except EOFError:
            ret_ans = ""
        if ret_ans:
            try:
                retention_days = int(ret_ans)
                if not (1 <= retention_days <= 365):
                    return display(HTML(
                        '<div style="color: red;">❌ Retention must be between '
                        '1 and 365 days.</div>'
                    ))
            except ValueError:
                return display(HTML(
                    f'<div style="color: red;">❌ Could not parse '
                    f'<code>{ret_ans}</code> as a number of days.</div>'
                ))

        try:
            result = _autoregister.autoregister(
                src_path=src,
                user_ns=self.shell.user_ns,
                lesson_name=args.lesson_name,
                out_path=target,
                reveal_after_attempts=reveal_after,
                force_all=args.force_all,
                course_choice=course_choice,
                retention_days=retention_days,
            )
        except (FileNotFoundError, ValueError) as e:
            return display(HTML(f'<div style="color: red;">❌ {e}</div>'))

        # Render the success card.
        if result.n_checkpoints == 0 and result.n_failed == 0:
            return display(HTML(
                '<div style="color: #b45309; border: 1px solid #b45309; padding: 10px; '
                'border-radius: 6px; background: #fffbeb;">⚠ Found no exercise cells. '
                'Either tag code cells with <code># cadence:checkpoint &lt;id&gt;</code> '
                'or use markdown headings above your code cells (then re-run with '
                '<code>--all</code> if you have manual markers elsewhere).</div>'
            ))

        ok_rows = "".join(
            f'<tr><td style="padding: 2px 8px;"><code>{c.checkpoint_id}</code></td>'
            f'<td style="padding: 2px 8px; color: #475569;">{c.comparator}</td>'
            f'<td style="padding: 2px 8px; font-family: monospace;">'
            f'{(json.dumps(c.expected.get("value")) if c.expected else "—")[:60]}</td></tr>'
            for c in result.checkpoints if c.error is None
        )
        fail_html = ""
        if result.n_failed:
            fail_rows = "".join(
                f'<li><code>{c.checkpoint_id or "?"}</code>: {c.error}</li>'
                for c in result.checkpoints if c.error is not None
            )
            fail_html = (
                f'<div style="margin-top: 8px; padding: 8px 10px; background: #fffbeb;'
                f' border-left: 3px solid #b45309; font-size: 0.85em;">'
                f'<strong>⚠ {result.n_failed} cell(s) skipped:</strong>'
                f'<ul style="margin: 4px 0 0 0; padding-left: 20px;">{fail_rows}</ul>'
                f'</div>'
            )
        reveal_html = (
            f" · solutions reveal after {reveal_after} attempts" if reveal_after else ""
        )
        display(HTML(f'''
            <div style="border: 1px solid #15803d; border-radius: 6px;
                        padding: 12px 14px; margin: 8px 0; background: #f0fdf4;
                        line-height: 1.5; color: #1f2937;">
                <div style="font-weight: 600; color: #15803d; margin-bottom: 6px;">
                    ✅ Wrote <code>{result.out_path}</code>
                </div>
                <div style="font-size: 0.9em; color: #475569; margin-bottom: 8px;">
                    {result.n_checkpoints} checkpoint(s) detected ({result.mode} mode){reveal_html} ·
                    lesson "<code>{result.lesson_name}</code>"
                </div>
                <table style="font-size: 0.85em; border-collapse: collapse; margin-top: 4px;">
                    <thead><tr style="color: #475569;">
                        <th style="text-align: left; padding: 2px 8px;">id</th>
                        <th style="text-align: left; padding: 2px 8px;">comparator</th>
                        <th style="text-align: left; padding: 2px 8px;">expected</th>
                    </tr></thead>
                    <tbody>{ok_rows}</tbody>
                </table>
                {fail_html}
                <div style="margin-top: 10px; font-size: 0.85em; color: #475569;">
                    Next: open <code>{result.out_path.name}</code>, run the setup cell at the
                    top to register the lesson, then run <code>%cadence_scaffold</code> from
                    inside it to produce the student notebook.
                </div>
            </div>
        '''))

    @magic_arguments()
    @argument('src', nargs='?', default=None,
              help='Path to the teacher notebook. Omit to auto-detect the current notebook.')
    @argument('--out', default=None,
              help='Output path (default: <src>_student.ipynb).')
    @argument('--join-code', default=None,
              help='Override the join code. Default: look up the cached lesson by name.')
    @argument('--name', default='your name',
              help='Placeholder for the student display name in the session cell.')
    @argument('--force', action='store_true',
              help='Overwrite the output file if it already exists.')
    @line_magic
    def cadence_scaffold(self, line):
        """Generate a student notebook from a teacher notebook.

        Picks up every `check("id", ...)` call as an exercise (stubs the body,
        keeps the check call) and every markdown cell tagged with
        `<!-- cadence:task -->` as a task description (copied verbatim). The
        `%cadence_session <code> "name"` line is auto-filled from the lesson
        cached in ~/.cadence/lessons.yaml.

        Usage:
            %cadence_scaffold                                  # auto-detect this notebook
            %cadence_scaffold teacher.ipynb
            %cadence_scaffold teacher.ipynb --out wk3-student.ipynb --force
        """
        from pathlib import Path
        args = parse_argstring(self.cadence_scaffold, line)
        if args.src:
            src = Path(args.src)
        else:
            detected = _scaffold.detect_current_notebook()
            if detected is None:
                return display(HTML(
                    '<div style="color: red;">❌ Could not auto-detect the current notebook. '
                    'Pass the path explicitly: '
                    '<code>%cadence_scaffold path/to/teacher.ipynb</code></div>'
                ))
            src = detected
            display(HTML(
                f'<div style="font-size: 0.85em; color: #475569; margin-bottom: 4px;">'
                f'Auto-detected notebook: <code>{src}</code></div>'
            ))
        out = Path(args.out) if args.out else None
        target = out or src.with_name(f"{src.stem}_student.ipynb")
        if target.exists() and not args.force:
            return display(HTML(
                f'<div style="color: red;">❌ <code>{target}</code> already exists. '
                f'Re-run with <code>--force</code> to overwrite.</div>'
            ))
        try:
            result = _scaffold.scaffold(
                src_path=src,
                out_path=out,
                join_code=args.join_code,
                name_placeholder=args.name,
            )
        except (FileNotFoundError, ValueError) as e:
            return display(HTML(f'<div style="color: red;">❌ {e}</div>'))

        # Live cross-check: if we have an active lesson, warn about ids that
        # appear in check() calls but were never registered on the server.
        unregistered = []
        teacher = _progress.current_teacher()
        if teacher and result.checkpoint_ids:
            try:
                registered = {
                    cp["checkpoint_id"]
                    for cp in self.api.list_checkpoints(teacher["teacher_token"])
                }
                unregistered = [cid for cid in result.checkpoint_ids if cid not in registered]
            except Exception:
                pass

        warn_html = ""
        if unregistered:
            warn_html = (
                f'<div style="margin-top: 6px; padding: 6px 10px;'
                f' background: #fffbeb; border-left: 3px solid #b45309;'
                f' font-size: 0.9em;">'
                f'⚠ {len(unregistered)} checkpoint id(s) in the notebook are not '
                f'registered on the active lesson yet — students will see '
                f'"unknown checkpoint" when they submit. Register them with '
                f'<code>%cadence_register</code> or '
                f'<code>%%cadence_register_yaml</code>:<br>'
                f'<code>{", ".join(unregistered[:8])}</code>'
                f'{"…" if len(unregistered) > 8 else ""}'
                f'</div>'
            )

        lesson_line = (
            f"Lesson: <code>{result.lesson_name}</code> · join_code <code>{result.join_code}</code>"
            if result.lesson_name
            else f"join_code <code>{result.join_code}</code> (passed explicitly; no lesson magic in source)"
        )
        display(HTML(f'''
            <div style="border: 1px solid #15803d; border-radius: 6px;
                        padding: 10px; margin: 8px 0; background: #f0fdf4;">
                <div style="font-weight: 600; color: #15803d;">
                    ✅ Wrote <code>{result.out_path}</code>
                </div>
                <div style="margin-top: 4px; font-size: 0.9em;">
                    {result.n_exercises} exercise stub(s)
                    ({len(result.checkpoint_ids)} checkpoint(s)) ·
                    {result.n_tasks} task description(s) ·
                    {result.n_solutions} solution cell(s)<br>
                    {lesson_line}
                </div>
                {warn_html}
            </div>
        '''))

    # ------------------------------------------------------------------
    # Teacher: register / self-test
    # ------------------------------------------------------------------

    @magic_arguments()
    @argument('checkpoint_id', help='Checkpoint identifier')
    @argument('--comparator', default='exact', choices=['exact', 'numeric', 'set', 'regex', 'manual'])
    @argument('--expected', default=None,
              help='JSON-encoded expected value/config. Required for every comparator except `manual`.')
    @argument('--allow-submissions', action='store_true',
              help='Let students submit code via %%cadence_submit for the teacher to review.')
    @argument('--hint', default=None)
    @argument('--hint-after-attempts', type=int, default=1,
              help='Number of attempts after which students can request the hint (default 1).')
    @argument('--order', type=int, default=0)
    @argument('--reveal-after', type=int, default=None,
              help='Number of attempts after which students can request the solution.')
    @argument('--solution-value', default=None,
              help='Short canonical answer shown when the student requests the solution.')
    @argument('--solution-code', default=None,
              help='Fully worked code snippet shown when the student requests the solution.')
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

        if args.comparator == 'manual':
            if args.expected is not None:
                return display(HTML(
                    '<div style="color: red;">❌ <code>--comparator manual</code> takes no '
                    '<code>--expected</code> — there\'s nothing to auto-check.</div>'
                ))
            expected = None
        else:
            if args.expected is None:
                return display(HTML(
                    f'<div style="color: red;">❌ <code>--expected</code> is required for '
                    f'<code>--comparator {args.comparator}</code>.</div>'
                ))
            expected = _parse_expected(args.expected)

        if args.reveal_after is not None and not (args.solution_value or args.solution_code):
            return display(HTML(
                '<div style="color: red;">❌ <code>--reveal-after</code> needs at least one '
                'of <code>--solution-value</code> or <code>--solution-code</code> set.</div>'
            ))

        hint_after = max(1, int(args.hint_after_attempts or 1))

        try:
            self.api.register_checkpoint(
                teacher_token=teacher["teacher_token"],
                checkpoint_id=args.checkpoint_id,
                comparator=args.comparator,
                expected_payload=expected,
                hint=args.hint,
                hint_after_attempts=hint_after,
                order_index=args.order,
                reveal_after_attempts=args.reveal_after,
                solution_value=args.solution_value,
                solution_code=args.solution_code,
                allow_submissions=args.allow_submissions,
            )
        except Exception as e:
            return display(HTML(f'<div style="color: red;">❌ Registration failed: {e}</div>'))

        extras = []
        if args.hint:
            extras.append(f"hint revealable after {hint_after} attempt{'s' if hint_after != 1 else ''}")
        if args.reveal_after is not None:
            kinds = []
            if args.solution_value: kinds.append('value')
            if args.solution_code: kinds.append('code')
            extras.append(f"solution ({'+'.join(kinds)}) revealable after {args.reveal_after} attempts")
        if args.allow_submissions:
            extras.append("accepts %%cadence_submit code")
        suffix = f' — {", ".join(extras)}' if extras else ''
        display(HTML(
            f'<div style="color: green;">✅ Checkpoint '
            f'<code>{args.checkpoint_id}</code> registered ({args.comparator}){suffix}.</div>'
        ))

    @cell_magic
    def cadence_register_yaml(self, line, cell):
        """Register many checkpoints at once from an inline YAML body.

        Usage:
            %%cadence_register_yaml
            - id: setup.mean-value
              comparator: numeric
              expected: {value: 49.5, tolerance: 0.001}
              hint: average of 0..99
            - id: discovery.higgs-peak
              comparator: exact
              expected: 125
              reveal_after: 3
              solution_code: |
                bin_edges = np.arange(100, 151)
                counts, _ = np.histogram(m_gg, bins=bin_edges)
                int(bin_edges[np.argmax(counts)])
              allow_submissions: true

        Field names mirror the `%cadence_register` flags (snake_case). To
        load from a separate file, use `%cadence_register_yaml_file <path>`.
        """
        if not self._require_api():
            return
        return self._process_yaml_register(cell)

    @magic_arguments()
    @argument('path', help='Path to a YAML file containing a list of checkpoint definitions.')
    @line_magic
    def cadence_register_yaml_file(self, line):
        """Register checkpoints from a YAML file on disk.

        Useful when you keep your checkpoint definitions in version control
        alongside the lesson notebook. The file must contain the same
        top-level list of mappings %%cadence_register_yaml expects.

        Usage:
            %cadence_register_yaml_file checkpoints/week3.yaml
        """
        if not self._require_api():
            return
        args = parse_argstring(self.cadence_register_yaml_file, line)
        path = args.path.strip().strip('"').strip("'")
        try:
            with open(path, "r", encoding="utf-8") as f:
                yaml_text = f.read()
        except OSError as e:
            return display(HTML(
                f'<div style="color: red;">❌ Could not read <code>{path}</code>: {e}</div>'
            ))
        return self._process_yaml_register(yaml_text)

    def _process_yaml_register(self, yaml_text: str) -> None:
        """Parse a YAML body (list of checkpoint mappings) and register each
        entry. Shared by the cell magic (%%cadence_register_yaml) and the
        file magic (%cadence_register_yaml_file)."""
        teacher = _progress.current_teacher()
        if not teacher:
            return display(HTML(
                '<div style="color: red;">❌ No active lesson. Run '
                '<code>%cadence_create_lesson "My Lesson"</code> or '
                '<code>%cadence_lesson "My Lesson"</code> first.</div>'
            ))

        try:
            import yaml
        except ImportError:
            return display(HTML(
                '<div style="color: red;">❌ PyYAML not installed. <code>pip install pyyaml</code>.</div>'
            ))

        try:
            entries = yaml.safe_load(yaml_text) or []
        except yaml.YAMLError as e:
            return display(HTML(f'<div style="color: red;">❌ YAML parse error: {e}</div>'))

        if not isinstance(entries, list):
            return display(HTML(
                '<div style="color: red;">❌ Expected a top-level list of checkpoints. '
                'Each entry is a mapping with at least <code>id</code> and <code>comparator</code>.</div>'
            ))

        ok: list = []
        failed: list = []
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                failed.append((i, "entry is not a mapping"))
                continue
            cp_id = entry.get('id') or entry.get('checkpoint_id')
            comparator = entry.get('comparator', 'exact')
            if not cp_id:
                failed.append((i, "missing required field 'id'"))
                continue
            if comparator not in {'exact', 'numeric', 'set', 'regex', 'manual'}:
                failed.append((cp_id, f"unknown comparator {comparator!r}"))
                continue

            expected = entry.get('expected')
            if comparator == 'manual':
                if expected is not None:
                    failed.append((cp_id, "manual comparator takes no `expected`"))
                    continue
                expected_payload = None
            else:
                if expected is None:
                    failed.append((cp_id, f"`expected` is required for comparator={comparator}"))
                    continue
                expected_payload = expected if isinstance(expected, dict) else {"value": expected}

            hint_after = entry.get('hint_after', entry.get('hint_after_attempts', 1))
            try:
                hint_after = max(1, int(hint_after))
            except (TypeError, ValueError):
                hint_after = 1
            try:
                self.api.register_checkpoint(
                    teacher_token=teacher["teacher_token"],
                    checkpoint_id=cp_id,
                    comparator=comparator,
                    expected_payload=expected_payload,
                    hint=entry.get('hint'),
                    hint_after_attempts=hint_after,
                    order_index=entry.get('order', entry.get('order_index', 0)),
                    reveal_after_attempts=entry.get('reveal_after', entry.get('reveal_after_attempts')),
                    solution_value=entry.get('solution_value'),
                    solution_code=entry.get('solution_code'),
                    allow_submissions=bool(entry.get('allow_submissions', False)),
                )
                ok.append(cp_id)
            except Exception as e:
                failed.append((cp_id, str(e)))

        rows = ''.join(f'<li>✅ <code>{cp}</code></li>' for cp in ok)
        if failed:
            rows += ''.join(
                f'<li>❌ <code>{cp}</code> — <em>{reason}</em></li>' for cp, reason in failed
            )
        failed_html = (
            f', <strong style="color: #b91c1c;">{len(failed)} failed</strong>'
            if failed else ''
        )
        display(HTML(
            f'<div>Bulk register: <strong>{len(ok)} registered</strong>'
            f'{failed_html}.'
            f'<ul style="margin: 6px 0 0 0; padding-left: 18px;">{rows}</ul></div>'
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
                session_retention_days=resp.get("session_retention_days"),
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

    def _eval_cell_last_expr(self, cell: str):
        """Exec the cell's statements in the user namespace; return the value
        of the last expression (or None if the cell doesn't end in one).

        Bypasses self.shell.run_cell(silent=True) — that sets ast_node
        interactivity to "none" and drops the trailing-expression value,
        which is exactly what we need. Imports and defs still persist into
        the user namespace because we exec in self.shell.user_ns."""
        import ast as _ast
        tree = _ast.parse(cell)
        if not tree.body:
            return None
        ns = self.shell.user_ns
        last = tree.body[-1]
        if len(tree.body) > 1:
            body_module = _ast.Module(body=tree.body[:-1], type_ignores=[])
            exec(compile(body_module, "<cadence_time>", "exec"), ns)
        if isinstance(last, _ast.Expr):
            return eval(compile(_ast.Expression(body=last.value), "<cadence_time>", "eval"), ns)
        last_module = _ast.Module(body=[last], type_ignores=[])
        exec(compile(last_module, "<cadence_time>", "exec"), ns)
        return None

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
        try:
            value = self._eval_cell_last_expr(cell)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            display(HTML(
                f'<div style="color: red;">❌ Cell raised an error '
                f'after {elapsed_ms} ms — not submitted.</div>'
            ))
            raise exc
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if value is None:
            return display(HTML(
                '<div style="color: orange;">⚠️ Cell returned no value. '
                'End it with an expression whose value is your answer '
                '(e.g. <code>fib(10)</code> on the last line).</div>'
            ))

        try:
            resp = session["api"].check_answer(
                session["session_id"],
                checkpoint_id,
                value,
                elapsed_ms=elapsed_ms,
            )
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Submission failed: {e}</div>'
            ))

        verdict = _progress.CheckResult(
            is_correct=bool(resp.get("is_correct")),
            attempt_num=int(resp.get("attempt_num", 0)),
            elapsed_ms=resp.get("elapsed_ms", elapsed_ms),
            is_manual=bool(resp.get("is_manual")),
            hint_available=bool(resp.get("hint_available")),
            solution_available=bool(resp.get("solution_available")),
            checkpoint_id=checkpoint_id,
        )
        display(verdict)

    @cell_magic
    def cadence_submit(self, line, cell):
        """Execute the cell normally AND submit its source as a code submission.

        Usage:
            %%cadence_submit <checkpoint_id>
            # ... student code ...

        Only works when the teacher registered the checkpoint with
        `--allow-submissions`. The cell runs first so the student still sees
        their output; the source is then sent to the teacher's dashboard.
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
                '<code>%%cadence_submit &lt;checkpoint_id&gt;</code></div>'
            ))
        checkpoint_id = parts[0]

        # Run the cell so the student sees the normal output, then submit.
        result = self.shell.run_cell(cell, store_history=True, silent=False)
        if not result.success:
            display(HTML(
                '<div style="color: red;">❌ Cell raised an error — '
                'not submitted. Fix the code and re-run.</div>'
            ))
            if result.error_in_exec:
                raise result.error_in_exec
            return

        try:
            session["api"].submit_code(session["session_id"], checkpoint_id, cell)
        except Exception as e:
            return display(HTML(
                f'<div style="color: red;">❌ Submission failed: {e}</div>'
            ))

        display(HTML(
            f'<div style="color: #6b21a8;">📤 Code submitted to '
            f'<code>{checkpoint_id}</code>. The teacher can see it on the dashboard.</div>'
        ))

    # ------------------------------------------------------------------
    # Discoverability: cheatsheet of every magic, grouped, with syntax.
    # ------------------------------------------------------------------

    @line_magic
    def cadence_help(self, line):
        """Print a one-stop cheatsheet of every %cadence_* magic.

        Usage:
            %cadence_help            # show everything
            %cadence_help register   # filter to commands matching a substring

        Each row gives the exact syntax and a one-line summary, grouped by
        role (auth / lessons / courses / checkpoints / student / data rights).
        Pair this with `%<magic>?` for full argparse-style help on any one
        command.
        """
        groups = _help_table()
        needle = (line or "").strip().lower()
        rows_html: list[str] = []
        total_shown = 0
        for group_name, entries in groups:
            shown = [
                e for e in entries
                if not needle or needle in e["cmd"].lower() or needle in e["what"].lower()
            ]
            if not shown:
                continue
            rows_html.append(
                f'<tr><td colspan="2" style="padding-top: 14px; '
                f'font-size: 0.72em; letter-spacing: 0.06em; text-transform: uppercase; '
                f'color: #475569; font-weight: 700;">{group_name}</td></tr>'
            )
            for e in shown:
                total_shown += 1
                # Tag the role so a teacher screen-sharing sees who runs what.
                role_color = {"teacher": "#1d4ed8", "student": "#047857", "both": "#6b7280"}.get(e["role"], "#6b7280")
                role_tag = (
                    f'<span style="font-size: 0.7em; padding: 1px 6px; border-radius: 8px; '
                    f'background: {role_color}1a; color: {role_color}; '
                    f'margin-left: 6px; vertical-align: 1px;">{e["role"]}</span>'
                )
                cmd_html = (
                    f'<code style="font-family: ui-monospace, Menlo, monospace; font-size: 0.85em; '
                    f'color: #0f172a; background: rgba(15,23,42,0.05); padding: 1px 6px; '
                    f'border-radius: 3px; white-space: nowrap;">{e["cmd"]}</code>{role_tag}'
                )
                rows_html.append(
                    f'<tr>'
                    f'<td style="padding: 4px 14px 4px 0; vertical-align: top; white-space: nowrap;">{cmd_html}</td>'
                    f'<td style="padding: 4px 0; vertical-align: top; color: #334155; font-size: 0.92em;">'
                    f'{e["what"]}</td>'
                    f'</tr>'
                )

        if total_shown == 0:
            return display(HTML(
                f'<div style="color: #b45309;">No Cadence magics matched '
                f'<code>{needle}</code>. Try <code>%cadence_help</code> with no filter.</div>'
            ))

        header_filter = (
            f' filtered to <code>{needle}</code>' if needle else ''
        )
        display(HTML(f'''
            <div style="font-family: ui-sans-serif, system-ui, sans-serif;
                        border: 1px solid #e2e8f0; border-radius: 8px;
                        padding: 14px 18px; margin: 6px 0; background: #fafafa;">
                <div style="font-weight: 600; font-size: 1rem; margin-bottom: 2px;">
                    Cadence magics cheatsheet
                </div>
                <div style="font-size: 0.82em; color: #64748b; margin-bottom: 8px;">
                    {total_shown} command{'s' if total_shown != 1 else ''}{header_filter}.
                    Append <code>?</code> to any magic for full argument help —
                    e.g. <code>%cadence_register?</code>.
                </div>
                <table style="border-collapse: collapse; width: 100%;">
                    {''.join(rows_html)}
                </table>
            </div>
        '''))


def _help_table() -> list:
    """Static cheatsheet — kept in one place so %cadence_help and the Guide
    stay consistent. Update here when a magic is added or its arguments shift.

    Each entry: {"cmd": <exact syntax>, "what": <one-liner>, "role": one of
    "teacher" / "student" / "both"}. The grouping order is the order they'd
    naturally come up in a fresh classroom.
    """
    return [
        ("Setup", [
            {"cmd": "%load_ext cadence", "what": "Enable Cadence magics in this notebook.", "role": "both"},
            {"cmd": "%cadence_help [substr]", "what": "This cheatsheet. Optional substring filters the list.", "role": "both"},
        ]),
        ("Teacher: auth", [
            {"cmd": "%cadence_login", "what": "Sign in to the hosted dashboard (username/password or GitHub).", "role": "teacher"},
            {"cmd": "%cadence_logout", "what": "Forget the current teacher token cached on this machine.", "role": "teacher"},
            {"cmd": "%cadence_whoami", "what": "Show which teacher account this kernel is signed in as.", "role": "teacher"},
        ]),
        ("Teacher: lessons", [
            {"cmd": '%cadence_create_lesson "<name>" [--code X] [--force]',
             "what": "Mint a new lesson. Prints the join code and dashboard URL.", "role": "teacher"},
            {"cmd": '%cadence_lesson "<name>"',
             "what": "Re-activate a previously-created lesson from the local cache.", "role": "teacher"},
            {"cmd": '%cadence_show_join "<name>"',
             "what": "Reprint the join code + dashboard URL for a cached lesson.", "role": "teacher"},
            {"cmd": '%cadence_clone_lesson "<name>" [--as "<new>"]',
             "what": "Duplicate a lesson and its checkpoints under a fresh join code.", "role": "teacher"},
            {"cmd": '%cadence_delete_lesson "<name>" [--yes]',
             "what": "Permanently delete a lesson and every session that touched it.", "role": "teacher"},
            {"cmd": "%cadence_rotate_token [--also-join-code]",
             "what": "Mint a fresh teacher_token (useful if leaked).", "role": "teacher"},
            {"cmd": "%cadence_set_retention --days N [--course]",
             "what": "Lower the per-session retention window for this lesson/course.", "role": "teacher"},
        ]),
        ("Teacher: courses", [
            {"cmd": '%cadence_create_course "<name>" [--retention-days N]',
             "what": "Create a course (a bundle of lessons + a single join code).", "role": "teacher"},
            {"cmd": '%cadence_course "<name>"',
             "what": "Re-activate a previously-created course from the local cache.", "role": "teacher"},
            {"cmd": '%cadence_add_notebook "<name>" [--order N]',
             "what": "Add a new notebook to the active course.", "role": "teacher"},
            {"cmd": '%cadence_attach_lesson "<lesson>" --to "<course>"',
             "what": "Attach an existing lesson to a course (cached locally).", "role": "teacher"},
            {"cmd": '%cadence_detach_lesson "<lesson>" --from "<course>"',
             "what": "Remove a lesson from a course (lesson data is kept).", "role": "teacher"},
            {"cmd": '%cadence_delete_course "<name>" [--yes]',
             "what": "Permanently delete a course (lessons are detached, not deleted).", "role": "teacher"},
        ]),
        ("Teacher: checkpoints", [
            {"cmd": "%cadence_register <id> --comparator X --expected '<json>' [--hint ...] [--allow-submissions]",
             "what": "Register a single checkpoint. Flag-driven, fits on one line.", "role": "teacher"},
            {"cmd": "%%cadence_register_yaml",
             "what": "Bulk-register from an inline YAML body — same fields, block layout.", "role": "teacher"},
            {"cmd": "%cadence_register_yaml_file path/to/file.yaml",
             "what": "Bulk-register from a YAML file on disk (easy to version-control).", "role": "teacher"},
            {"cmd": "%cadence_self_test",
             "what": "Submit the teacher's expected answer for every auto-checked checkpoint.", "role": "teacher"},
        ]),
        ("Student: session + answers", [
            {"cmd": '%cadence_session <join_code> "<display name>"',
             "what": "Join a lesson or course under your chosen name (pseudonyms welcome).", "role": "student"},
            {"cmd": '%cadence_notebook "<name>"',
             "what": "Switch to a different notebook within an enrolled course.", "role": "student"},
            {"cmd": 'check("<id>", value)',
             "what": "Submit an answer for an auto-checked checkpoint. Returns ✅/❌ inline.", "role": "student"},
            {"cmd": 'mark_done("<id>")',
             "what": "Self-attest a manual / reflection checkpoint.", "role": "student"},
            {"cmd": 'cadence.show_hint("<id>")',
             "what": "Reveal the teacher's hint once you've made enough attempts.", "role": "student"},
            {"cmd": 'cadence.show_solution("<id>")',
             "what": "Reveal the worked solution once the threshold is hit.", "role": "student"},
            {"cmd": 'cadence.submit_image("<id>", fig)',
             "what": "Ship a matplotlib figure (or PNG bytes) to a submission-enabled checkpoint.", "role": "student"},
            {"cmd": '%%cadence_submit <id>',
             "what": "Run the cell normally AND ship its source to the teacher dashboard.", "role": "student"},
            {"cmd": '%%cadence_time <id>',
             "what": "Time the cell's execution and record it against this checkpoint.", "role": "student"},
        ]),
        ("Student: data rights", [
            {"cmd": "%cadence_my_data",
             "what": "Show exactly what Cadence has stored about this session.", "role": "student"},
            {"cmd": "%cadence_export_my_data [--path FILE]",
             "what": "Export your session data to a JSON file you keep.", "role": "student"},
            {"cmd": "%cadence_delete_my_data [--yes]",
             "what": "Wipe everything Cadence holds about this session. Irreversible.", "role": "student"},
            {"cmd": "%cadence_accept_terms",
             "what": "Record acceptance of the privacy notice + terms (for adults).", "role": "student"},
        ]),
    ]


# IPython extension entry points live in extension.py — that's what
# `%load_ext cadence` resolves to. Don't add load/unload hooks
# here or the package will register magics twice on extension reload.
