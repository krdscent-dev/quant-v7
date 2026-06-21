"""Minimal local pytest-compatible runner.

This shim exists because the workspace environment does not provide the
real `pytest` package. It discovers `tests/test_*.py` modules and runs
unittest-style test cases plus simple `test_*` functions.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import pathlib
import sys
import traceback
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parent
TEST_DIR = ROOT / "tests"


def _load_module(path: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def _run_function_tests(module: types.ModuleType, result: unittest.TestResult) -> None:
    for name, obj in inspect.getmembers(module):
        if name.startswith("test_") and inspect.isfunction(obj):
            test = unittest.FunctionTestCase(obj)
            test.run(result)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = set(sys.argv[1:])
    os.environ["CODEX_PYTEST_RUNNING"] = "1"
    if "--full" not in args:
        os.environ.setdefault("CODEX_TEST_FAST", "1")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    if TEST_DIR.exists():
        for path in sorted(TEST_DIR.glob("test_*.py")):
            module = _load_module(path)
            suite.addTests(loader.loadTestsFromModule(module))
    result = unittest.TestResult()
    suite.run(result)
    if TEST_DIR.exists():
        for path in sorted(TEST_DIR.glob("test_*.py")):
            module = sys.modules.get(path.stem)
            if module is not None:
                _run_function_tests(module, result)
    print(f"collected={result.testsRun}")
    print(f"passed={result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"failed={len(result.failures) + len(result.errors)}")
    summary_path = ROOT / ".codex_last_pytest.json"
    summary = {
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures) + len(result.errors),
        "success": not (result.failures or result.errors),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.failures or result.errors:
        print("failures:")
        for test, tb in result.failures + result.errors:
            print(f"- {test}")
            print(tb)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
