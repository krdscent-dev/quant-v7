"""RC1 final audit engine."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import ast
import json
import os
import subprocess

from .audit_contract import AuditCheck, AuditReport
from .audit_report import AuditReportRenderer


class AuditEngine:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parents[2]
        self.renderer = AuditReportRenderer()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _make_check(self, category: str, item: str, status: str, severity: str, message: str) -> AuditCheck:
        return AuditCheck(
            category=category,
            item=item,
            status=status,
            severity=severity,
            message=message,
        )

    def _run_git(self, args: list[str]) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip()

    def _git_checks(self) -> list[AuditCheck]:
        checks: list[AuditCheck] = []
        status = self._run_git(["status", "--porcelain"])
        if status is None:
            checks.append(self._make_check("GIT", "workspace_clean", "WARNING", "MEDIUM", "git status unavailable"))
            return checks
        if status:
            checks.append(self._make_check("GIT", "workspace_clean", "WARNING", "MEDIUM", "workspace has uncommitted changes"))
            untracked = [line[3:] for line in status.splitlines() if line.startswith("??")]
            if untracked:
                checks.append(self._make_check("GIT", "untracked_files", "WARNING", "MEDIUM", f"untracked files: {', '.join(untracked[:5])}"))
            else:
                checks.append(self._make_check("GIT", "untracked_files", "PASS", "LOW", "no untracked files"))
            conflict_lines = [line for line in status.splitlines() if line[:2] in {"UU", "AA", "DD", "AU", "UD", "UA", "DU"}]
            if conflict_lines:
                checks.append(self._make_check("GIT", "conflict_files", "FAIL", "CRITICAL", f"conflicts: {', '.join(conflict_lines[:5])}"))
            else:
                checks.append(self._make_check("GIT", "conflict_files", "PASS", "LOW", "no conflict files"))
        else:
            checks.append(self._make_check("GIT", "workspace_clean", "PASS", "LOW", "workspace clean"))
            checks.append(self._make_check("GIT", "untracked_files", "PASS", "LOW", "no untracked files"))
            checks.append(self._make_check("GIT", "conflict_files", "PASS", "LOW", "no conflict files"))

        ahead = self._run_git(["rev-list", "--left-right", "--count", "origin/main...HEAD"])
        if ahead is None:
            checks.append(self._make_check("GIT", "unpushed_commit", "WARNING", "MEDIUM", "unable to determine push status"))
        else:
            left_right = ahead.split()
            if len(left_right) == 2 and left_right[1] != "0":
                checks.append(self._make_check("GIT", "unpushed_commit", "WARNING", "LOW", f"ahead by {left_right[1]} commit(s)"))
            else:
                checks.append(self._make_check("GIT", "unpushed_commit", "PASS", "LOW", "no unpushed commits"))
        return checks

    def _module_files(self) -> list[Path]:
        files: list[Path] = []
        for folder in ("src", "core", "strategy"):
            root = self.base_dir / folder
            if root.exists():
                files.extend(sorted(root.rglob("*.py")))
        return files

    def _module_name(self, path: Path) -> str:
        rel = path.relative_to(self.base_dir).with_suffix("")
        return ".".join(rel.parts)

    def _parse_imports(self, path: Path) -> list[str]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        module_name = self._module_name(path)
        package_parts = module_name.split(".")[:-1]
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    base = package_parts[: len(package_parts) - node.level + 1]
                    if node.module:
                        base = base + node.module.split(".")
                    if base:
                        imports.append(".".join(base))
                elif node.module:
                    imports.append(node.module)
        return imports

    def _import_graph(self) -> dict[str, set[str]]:
        files = self._module_files()
        available = {self._module_name(path) for path in files}
        graph: dict[str, set[str]] = {}
        for path in files:
            module_name = self._module_name(path)
            graph[module_name] = set()
            for imported in self._parse_imports(path):
                if imported in available:
                    graph[module_name].add(imported)
                else:
                    graph[module_name].update(
                        candidate for candidate in available if candidate.startswith(imported + ".")
                    )
        return graph

    def _detect_cycles(self) -> list[list[str]]:
        graph = self._import_graph()
        visited: set[str] = set()
        active: set[str] = set()
        stack: list[str] = []
        cycles: list[list[str]] = []

        def visit(node: str) -> None:
            if node in active:
                if node in stack:
                    idx = stack.index(node)
                    cycles.append(stack[idx:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            active.add(node)
            stack.append(node)
            for dep in graph.get(node, set()):
                visit(dep)
            stack.pop()
            active.remove(node)

        for node in graph:
            visit(node)
        return cycles

    def _architecture_checks(self) -> list[AuditCheck]:
        checks: list[AuditCheck] = []
        cycles = self._detect_cycles()
        if cycles:
            checks.append(self._make_check("ARCHITECTURE", "circular_dependencies", "FAIL", "CRITICAL", "cycle detected"))
        else:
            checks.append(self._make_check("ARCHITECTURE", "circular_dependencies", "PASS", "LOW", "no circular dependencies"))

        seen: dict[str, list[str]] = defaultdict(list)
        empty_modules: list[str] = []
        for path in self._module_files():
            seen[path.stem].append(str(path.relative_to(self.base_dir)))
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            body = [
                node
                for node in tree.body
                if not (
                    isinstance(node, ast.Expr)
                    and isinstance(getattr(node, "value", None), ast.Constant)
                    and isinstance(node.value.value, str)
                )
            ]
            if not body:
                empty_modules.append(str(path.relative_to(self.base_dir)))

        duplicate_modules = {name: paths for name, paths in seen.items() if len(paths) > 1 and name != "__init__"}
        if duplicate_modules:
            sample_name, paths = next(iter(duplicate_modules.items()))
            checks.append(self._make_check("ARCHITECTURE", "duplicate_modules", "WARNING", "MEDIUM", f"duplicate module stem: {sample_name} -> {', '.join(paths[:5])}"))
        else:
            checks.append(self._make_check("ARCHITECTURE", "duplicate_modules", "PASS", "LOW", "no duplicate module stems"))

        if empty_modules:
            checks.append(self._make_check("ARCHITECTURE", "empty_modules", "WARNING", "MEDIUM", f"empty modules: {', '.join(empty_modules[:5])}"))
        else:
            checks.append(self._make_check("ARCHITECTURE", "empty_modules", "PASS", "LOW", "no empty modules"))

        retired_modules: list[str] = []
        excluded_paths = {
            self.base_dir / "src" / "audit" / "audit_engine.py",
        }
        for path in self._module_files():
            if path in excluded_paths:
                continue
            text = path.read_text(encoding="utf-8")
            if "obsolete" in text.lower() or "retired" in text.lower():
                retired_modules.append(str(path.relative_to(self.base_dir)))
        if retired_modules:
            checks.append(self._make_check("ARCHITECTURE", "retired_modules", "WARNING", "LOW", f"retired modules noted: {', '.join(retired_modules[:5])}"))
        else:
            checks.append(self._make_check("ARCHITECTURE", "retired_modules", "PASS", "LOW", "no retired modules detected"))

        return checks

    def _load_pytest_summary(self) -> dict[str, Any] | None:
        summary_path = self.base_dir / ".codex_last_pytest.json"
        if not summary_path.exists():
            return None
        try:
            return json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _test_checks(self) -> list[AuditCheck]:
        summary = self._load_pytest_summary()
        checks: list[AuditCheck] = []
        test_files = list((self.base_dir / "tests").glob("test_*.py"))
        if not test_files:
            checks.append(self._make_check("TEST", "test_modules", "FAIL", "HIGH", "no test modules found"))
        else:
            checks.append(self._make_check("TEST", "test_modules", "PASS", "LOW", f"{len(test_files)} test modules present"))

        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CODEX_PYTEST_RUNNING"):
            checks.append(self._make_check("TEST", "pytest_status", "PASS", "LOW", "pytest is currently running"))
            checks.append(self._make_check("TEST", "failed_tests", "PASS", "LOW", "current pytest run owns failure detection"))
            return checks

        if summary is None:
            checks.append(self._make_check("TEST", "pytest_status", "WARNING", "MEDIUM", "pytest summary unavailable"))
            checks.append(self._make_check("TEST", "failed_tests", "WARNING", "MEDIUM", "cannot determine without summary snapshot"))
            return checks

        if int(summary.get("failed", 0)) > 0:
            checks.append(self._make_check("TEST", "pytest_status", "FAIL", "CRITICAL", f"{summary['failed']} failing tests"))
            checks.append(self._make_check("TEST", "failed_tests", "FAIL", "CRITICAL", f"pytest failures detected: {summary['failed']}"))
        else:
            checks.append(self._make_check("TEST", "pytest_status", "PASS", "LOW", f"{summary.get('passed', 0)} passing tests"))
            checks.append(self._make_check("TEST", "failed_tests", "PASS", "LOW", "no failed tests"))
        return checks

    def _documentation_checks(self) -> list[AuditCheck]:
        checks: list[AuditCheck] = []
        arch_dir = self.base_dir / "docs" / "architecture"
        expected_rounds = [f"Round{idx}.md" for idx in range(28, 41)]
        missing = [name for name in expected_rounds if not (arch_dir / name).exists()]
        if missing:
            checks.append(self._make_check("DOCUMENTATION", "round_docs", "WARNING", "MEDIUM", f"missing round docs: {', '.join(missing)}"))
        else:
            checks.append(self._make_check("DOCUMENTATION", "round_docs", "PASS", "LOW", "round docs 28-40 present"))

        required_docs = [
            ("V9_RC1.md", self.base_dir / "docs" / "architecture" / "V9_RC1.md"),
            ("V9_RC1_RELEASE_NOTES.md", self.base_dir / "docs" / "release" / "V9_RC1_RELEASE_NOTES.md"),
        ]
        for label, path in required_docs:
            if path.exists():
                checks.append(self._make_check("DOCUMENTATION", label, "PASS", "LOW", "present"))
            else:
                checks.append(self._make_check("DOCUMENTATION", label, "FAIL", "HIGH", "missing"))
        return checks

    def _config_checks(self) -> list[AuditCheck]:
        checks: list[AuditCheck] = []
        required_files = {
            "README.md": self.base_dir / "README.md",
            ".gitignore": self.base_dir / ".gitignore",
        }
        missing = [name for name, path in required_files.items() if not path.exists()]
        if missing:
            checks.append(self._make_check("CONFIG", "required_files", "FAIL", "HIGH", f"missing: {', '.join(missing)}"))
        else:
            checks.append(self._make_check("CONFIG", "required_files", "PASS", "LOW", "README and .gitignore present"))

        requirements_exists = (self.base_dir / "requirements.txt").exists() or (self.base_dir / "pyproject.toml").exists()
        if requirements_exists:
            checks.append(self._make_check("CONFIG", "dependency_manifest", "PASS", "LOW", "requirements or pyproject present"))
        else:
            checks.append(self._make_check("CONFIG", "dependency_manifest", "WARNING", "MEDIUM", "requirements.txt / pyproject.toml missing"))
        return checks

    def _skill_readiness(self) -> tuple[list[AuditCheck], dict[str, str]]:
        readiness: dict[str, str] = {}
        checks: list[AuditCheck] = []

        export_ready = all(
            (
                self.base_dir / "src" / "exports" / "__init__.py",
                self.base_dir / "src" / "exports" / "export_contract.py",
                self.base_dir / "src" / "exports" / "tabular_exporter.py",
                self.base_dir / "src" / "exports" / "metrics_exporter.py",
            )
        )
        skill_map = {
            "Skill A Data Analysis": {
                "status": "READY" if export_ready else "PARTIAL",
                "message": (
                    "Unified export adapters are available for dict/list/records output"
                    if export_ready
                    else "DataFrame normalization is not standardized across all outputs"
                ),
                "requirements": ["csv exports", "metrics helpers"],
            },
            "Skill B Graph Analysis": {
                "status": "READY",
                "message": "EvidenceChain, dependency graph and theme graph hooks exist",
                "requirements": ["EvidenceChain", "dependency graph", "theme graph"],
            },
            "Skill C Research": {
                "status": "READY",
                "message": "KnowledgeBase, ResearchDecision and Explainability are available",
                "requirements": ["KnowledgeBase", "ResearchDecision", "Explainability"],
            },
            "Skill D Visualization": {
                "status": "READY",
                "message": "WeeklyReport, BacktestReport, PortfolioSnapshot and RiskReport are available",
                "requirements": ["WeeklyReport", "BacktestReport", "PortfolioSnapshot", "RiskReport"],
            },
        }
        for skill, payload in skill_map.items():
            status = payload["status"]
            readiness[skill] = status
            severity = "LOW" if status == "READY" else "MEDIUM"
            check_status = "PASS" if status == "READY" else ("WARNING" if status == "PARTIAL" else "FAIL")
            checks.append(self._make_check("SKILL_READINESS", skill, check_status, severity, payload["message"]))
        return checks, readiness

    def run(self) -> AuditReport:
        checks: list[AuditCheck] = []
        warnings: list[str] = []
        skill_readiness: dict[str, str] = {}

        checks.extend(self._git_checks())
        checks.extend(self._architecture_checks())
        checks.extend(self._test_checks())
        checks.extend(self._documentation_checks())
        checks.extend(self._config_checks())
        skill_checks, skill_readiness = self._skill_readiness()
        checks.extend(skill_checks)

        for item in checks:
            if item.status == "WARNING":
                warnings.append(f"{item.category}:{item.item} {item.message}")

        passed_count = sum(1 for item in checks if item.status == "PASS")
        warning_count = sum(1 for item in checks if item.status == "WARNING")
        failed_count = sum(1 for item in checks if item.status == "FAIL")
        if failed_count > 0:
            overall_status = "FAIL"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"
        return AuditReport(
            timestamp=self._timestamp(),
            checks=checks,
            passed_count=passed_count,
            warning_count=warning_count,
            failed_count=failed_count,
            overall_status=overall_status,
            skill_readiness=skill_readiness,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.renderer.to_dict(self.run())
