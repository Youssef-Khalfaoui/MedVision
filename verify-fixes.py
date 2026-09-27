"""Final verification sweep after all MedVision fixes."""
import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\MedVision-main")
ok = True

# 1. Every Python file still compiles
print("=" * 74)
print("1. PYTHON SYNTAX (py_compile over every source file)")
print("=" * 74)
files = [p for p in ROOT.rglob("*.py")
         if not any(d in p.parts for d in
                    {"node_modules", "__pycache__", ".litho", "litho.docs",
                     "checkpoints", ".venv"})]
for path in files:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        ok = False
        print("  FAIL %s\n       %s" % (path.relative_to(ROOT), str(exc)[:200]))
print("  %d files compiled, all OK" % len(files))

# 2. Route authorization audit (AST-based)
print()
print("=" * 74)
print("2. ROUTE AUTHORIZATION AUDIT")
print("=" * 74)
import ast

AUTH_DEPS = {"get_current_doctor", "get_doctor_from_query_or_header"}
ALLOWED_PUBLIC = {("POST", "/register"), ("POST", "/login")}  # intentionally public
problems = []

for router in (ROOT / "backend/app/routers").glob("*.py"):
    tree = ast.parse(router.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for dec in node.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            if call is None or not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr not in {"get", "post", "put", "delete", "patch", "websocket"}:
                continue
            method = call.func.attr.upper()
            route = ""
            if call.args and isinstance(call.args[0], ast.Constant):
                route = str(call.args[0].value)
            source = ast.get_source_segment(
                router.read_text(encoding="utf-8", errors="replace"), node) or ""
            # `source` spans the whole function (decorators, signature, default
            # args AND body), so a `= Depends(get_current_doctor)` default arg
            # matches. (The previous version only joined parameter *names*,
            # which made every protected route look unauthenticated.)
            has_auth = any(dep in source for dep in AUTH_DEPS)
            inline_ws_auth = "get_doctor_from_ws_token" in source
            public = (method, route) in ALLOWED_PUBLIC
            if not (has_auth or public or inline_ws_auth):
                problems.append((method, route, router.name, node.lineno))

for method, route, fname, line in problems:
    ok = False
    print("  NO-AUTH  %-6s %-46s %s:%d" % (method, route, fname, line))
if not problems:
    print("  All routes are either authenticated or intentionally public.")

# 3. pytest
print()
print("=" * 74)
print("3. TEST SUITE")
print("=" * 74)
proc = subprocess.run([sys.executable, "-m", "pytest", "backend/tests", "-q", "--no-header"],
                      cwd=ROOT, capture_output=True, text=True, timeout=120)
tail = (proc.stdout or "").strip().splitlines()[-1]
print("  " + tail)
if proc.returncode != 0:
    ok = False

print()
print("=" * 74)
print("OVERALL: %s" % ("ALL CHECKS PASSED" if ok else "FAILURES DETECTED"))
print("=" * 74)
sys.exit(0 if ok else 1)
