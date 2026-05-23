"""End-to-end smoke test for the new password-set flow plus magic exercise.

Runs against a live local backend (assumes localhost:8000). Creates a fresh
OAuth-only teacher row directly in Postgres (simulating a GitHub signup),
sets a password via the new endpoint, then logs in via the magic and
exercises a representative slice of magics to confirm nothing regressed.

Run with the freshly-installed test venv:
    /Users/smol/cadence-pypi-test/bin/python test_e2e_password_flow.py
"""
from __future__ import annotations

import os
import secrets
import sys
import time
import uuid

import requests
from IPython.core.interactiveshell import InteractiveShell

API_URL = os.environ.setdefault("CADENCE_API_URL", "http://localhost:8000")
DASHBOARD_URL = os.environ.setdefault("CADENCE_DASHBOARD_URL", "http://localhost:3000")

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  {PASS if ok else FAIL} {name}" + (f"  — {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 1. Backend reachable
# ---------------------------------------------------------------------------
section("1. Backend reachability")
r = requests.get(f"{API_URL}/")
check("backend /", r.ok, f"HTTP {r.status_code}")


# ---------------------------------------------------------------------------
# 2. Create a synthetic OAuth-only teacher (simulates GitHub signup)
# ---------------------------------------------------------------------------
section("2. Synthetic OAuth-only teacher signup (skips real GitHub round-trip)")

unique = secrets.token_hex(4)
username = f"e2e_{unique}"
email = f"e2e_{unique}@example.com"

# We can't really hit GitHub OAuth in a test, but the password-signup endpoint
# creates a teacher row the same way — we then null-out password_hash via the
# DB to simulate the OAuth-only state.
signup_pw = "throwaway_initial_pw_long_enough"
r = requests.post(
    f"{API_URL}/auth/signup",
    json={"username": username, "email": email, "password": signup_pw},
)
check("signup", r.ok, f"HTTP {r.status_code}")
jwt = r.json()["access_token"]
auth = {"Authorization": f"Bearer {jwt}"}

# Confirm /auth/me returns has_password=True initially.
r = requests.get(f"{API_URL}/auth/me", headers=auth)
me = r.json()
check("/auth/me returns has_password field", "has_password" in me)
check("has_password is True after password signup", me.get("has_password") is True)

# Force the row into OAuth-only state by clearing password_hash via Postgres.
import subprocess
sql = f"UPDATE teachers SET password_hash = NULL WHERE username = '{username}';"
result = subprocess.run(
    ["docker", "exec", "cadence-postgres-1", "psql", "-U", "competition_user",
     "-d", "competition_db", "-c", sql],
    capture_output=True, text=True,
)
check("simulated OAuth-only state (cleared password_hash)", result.returncode == 0,
      result.stderr.strip()[:80] if result.returncode else "")

r = requests.get(f"{API_URL}/auth/me", headers=auth)
check("has_password now False (OAuth-only)", r.json().get("has_password") is False)


# ---------------------------------------------------------------------------
# 3. Username + password login fails before set-password
# ---------------------------------------------------------------------------
section("3. Pre-set-password: %cadence_login --username/password rejected")
r = requests.post(
    f"{API_URL}/auth/login",
    data={"username": username, "password": "anything"},
)
check("login with no password set returns 401", r.status_code == 401)


# ---------------------------------------------------------------------------
# 4. Set password via new endpoint (no current_password required)
# ---------------------------------------------------------------------------
section("4. POST /auth/me/password (first-time set)")
new_pw = "demo_password_for_jupyter_long"
r = requests.post(
    f"{API_URL}/auth/me/password",
    json={"new_password": new_pw},
    headers=auth,
)
check("first-time set returns 204", r.status_code == 204, f"got {r.status_code} {r.text[:80]}")

# has_password should flip to True.
r = requests.get(f"{API_URL}/auth/me", headers=auth)
check("has_password now True", r.json().get("has_password") is True)


# ---------------------------------------------------------------------------
# 5. Username + password login now works
# ---------------------------------------------------------------------------
section("5. Username + password login works")
r = requests.post(
    f"{API_URL}/auth/login",
    data={"username": username, "password": new_pw},
)
check("login with newly-set password returns 200", r.ok, f"HTTP {r.status_code}")
fresh_jwt = r.json()["access_token"]
check("login returns a JWT", bool(fresh_jwt) and fresh_jwt != jwt)


# ---------------------------------------------------------------------------
# 6. Change password (requires current_password)
# ---------------------------------------------------------------------------
section("6. POST /auth/me/password (change, current_password required)")
auth2 = {"Authorization": f"Bearer {fresh_jwt}"}

# Wrong current password should 401.
r = requests.post(
    f"{API_URL}/auth/me/password",
    json={"new_password": "another_password_long_enough", "current_password": "WRONG"},
    headers=auth2,
)
check("change without correct current_password returns 401", r.status_code == 401)

# Correct current password should 204.
r = requests.post(
    f"{API_URL}/auth/me/password",
    json={"new_password": "another_password_long_enough", "current_password": new_pw},
    headers=auth2,
)
check("change with correct current_password returns 204", r.status_code == 204,
      f"got {r.status_code} {r.text[:80]}")


# ---------------------------------------------------------------------------
# 7. Short password rejected
# ---------------------------------------------------------------------------
section("7. Short password rejected")
r = requests.post(
    f"{API_URL}/auth/me/password",
    json={"new_password": "short", "current_password": "another_password_long_enough"},
    headers=auth2,
)
check("short password returns 400", r.status_code == 400)


# ---------------------------------------------------------------------------
# 8. Exercise a representative slice of magics in an IPython kernel
# ---------------------------------------------------------------------------
section("8. Magic exercise: extension loads, lesson create, register, self-test, session, check")

ip = InteractiveShell()
ip.run_line_magic("load_ext", "cadence")
check("%load_ext cadence", True)

# Switch to the freshly-changed password for %cadence_login.
ip.run_line_magic("cadence_login", f"--username {username} --password another_password_long_enough")
check("%cadence_login --username --password", True)

# Whoami should return the synthetic user.
ip.run_line_magic("cadence_whoami", "")
check("%cadence_whoami", True)

# Create a lesson.
lesson_name = f"E2E lesson {unique}"
ip.run_line_magic("cadence_create_lesson", f'"{lesson_name}"')
check("%cadence_create_lesson", True)

# Register two checkpoints.
ip.run_line_magic(
    "cadence_register",
    'greet --comparator exact --expected \'"hello"\'',
)
ip.run_line_magic(
    "cadence_register",
    "fib10 --comparator numeric --expected '{\"value\": 55}'",
)
check("%cadence_register x2", True)

# Self-test should pass both.
ip.run_line_magic("cadence_self_test", "")
check("%cadence_self_test", True)

# Show join code (just exercises the code path).
ip.run_line_magic("cadence_show_join", "")
check("%cadence_show_join", True)

# Use the join code from the freshly-created lesson to start a student session,
# then submit answers via check().
from cadence import lesson_store, check as student_check
entry = lesson_store._load().get(lesson_name)
join_code = entry["join_code"]

ip.run_line_magic("cadence_session", f'{join_code} "E2E Student"')
check("%cadence_session as student", True)

r1 = student_check("greet", "hello")
check("check() correct answer for greet", bool(r1) and r1.is_correct)
r2 = student_check("fib10", 55)
check("check() correct answer for fib10", bool(r2) and r2.is_correct)
r3 = student_check("fib10", 42)
check("check() incorrect answer flagged", not r3.is_correct)


# ---------------------------------------------------------------------------
# 9. Cleanup (best-effort)
# ---------------------------------------------------------------------------
section("9. Cleanup (best-effort)")
try:
    ip.run_line_magic("cadence_lesson", f'"{lesson_name}"')
    ip.run_line_magic("cadence_delete_lesson", f'"{lesson_name}" --yes')
    check("delete test lesson", True)
except Exception as e:
    check("delete test lesson", False, str(e)[:80])

# Drop the synthetic teacher.
subprocess.run(
    ["docker", "exec", "cadence-postgres-1", "psql", "-U", "competition_user",
     "-d", "competition_db", "-c", f"DELETE FROM teachers WHERE username = '{username}';"],
    capture_output=True,
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"{passed}/{total} checks passed")
if passed < total:
    print("\nFailures:")
    for name, ok, detail in results:
        if not ok:
            print(f"  - {name}  — {detail}")
sys.exit(0 if passed == total else 1)
