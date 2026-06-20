"""RC1 quality gate implementation."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import ast
import importlib
import re
import uuid

from core.research_engine import run_research_pipeline
from src.agent_workflow.workflow_steps import build_default_workflow_engine

from .quality_contract import QualityCheck, QualityReport
from .quality_report import QualityReportRenderer


CORE_MODULE_PATHS = [
    Path("src/backtest"),
    Path("src/knowledge_base"),
    Path("src/agent_workflow"),
    Path("src/quality"),
    Path("core"),
    Path("strategy"),
]


class QualityGate:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parents[2]
        self.renderer = QualityReportRenderer()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _module_files(self) -> list[Path]:
        files: list[Path] = []
        for root in CORE_MODULE_PATHS:
            abs_root = self.base_dir / root
            if abs_root.exists():
                files.extend(sorted(abs_root.rglob("*.py")))
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
        imports: list[str] = []
        package_parts = module_name.split(".")[:-1]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
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

    def _build_import_graph(self) -> dict[str, set[str]]:
        module_files = self._module_files()
        graph: dict[str, set[str]] = {}
        available_modules = {self._module_name(path) for path in module_files}
        for path in module_files:
            module_name = self._module_name(path)
            graph[module_name] = set()
            for imported in self._parse_imports(path):
                if imported in available_modules:
                    graph[module_name].add(imported)
                else:
                    for candidate in available_modules:
                        if candidate.startswith(imported + "."):
                            graph[module_name].add(candidate)
        return graph

    def _detect_cycles(self) -> list[list[str]]:
        graph = self._build_import_graph()
        visited: set[str] = set()
        visiting: set[str] = set()
        stack: list[str] = []
        cycles: list[list[str]] = []

        def visit(node: str) -> None:
            if node in visiting:
                if node in stack:
                    idx = stack.index(node)
                    cycles.append(stack[idx:] + [node])
                return
            if node in visited:
                return
            visiting.add(node)
            stack.append(node)
            for dep in graph.get(node, set()):
                visit(dep)
            stack.pop()
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
        return cycles

    def _make_check(self, name: str, status: str, message: str, severity: str) -> QualityCheck:
        return QualityCheck(check_name=name, status=status, message=message, severity=severity)

    def _check_core_modules(self) -> QualityCheck:
        required = [
            "src/backtest/backtest_engine.py",
            "src/knowledge_base/kb_store.py",
            "src/agent_workflow/workflow_engine.py",
            "src/quality/quality_gate.py",
        ]
        missing = [item for item in required if not (self.base_dir / item).exists()]
        if missing:
            return self._make_check("core_modules", "FAIL", f"missing: {', '.join(missing)}", "CRITICAL")
        return self._make_check("core_modules", "PASS", "all core modules present", "LOW")

    def _check_circular_dependencies(self) -> QualityCheck:
        cycles = self._detect_cycles()
        if cycles:
            sample = " -> ".join(cycles[0])
            return self._make_check("circular_dependencies", "FAIL", f"cycle detected: {sample}", "CRITICAL")
        return self._make_check("circular_dependencies", "PASS", "no internal cycles detected", "LOW")

    def _check_registry_usage(self) -> QualityCheck:
        research_path = self.base_dir / "core" / "research_engine.py"
        text = research_path.read_text(encoding="utf-8") if research_path.exists() else ""
        if "DEFAULT_FACTOR_REGISTRY" not in text:
            return self._make_check("registry_usage", "FAIL", "DEFAULT_FACTOR_REGISTRY not referenced", "HIGH")
        return self._make_check("registry_usage", "PASS", "registry is wired into research engine", "LOW")

    def _check_adapter_usage(self) -> QualityCheck:
        weekly_path = self.base_dir / "core" / "weekly_pipeline.py"
        mapping_path = self.base_dir / "core" / "data_mapping.py"
        weekly_text = weekly_path.read_text(encoding="utf-8") if weekly_path.exists() else ""
        mapping_text = mapping_path.read_text(encoding="utf-8") if mapping_path.exists() else ""
        weekly_required = ["ProviderRouter", "build_default_workflow_engine"]
        mapping_required = ["DataMappingLayer", "build_factor_input"]
        missing = [item for item in weekly_required if item not in weekly_text]
        missing.extend([item for item in mapping_required if item not in mapping_text])
        if missing:
            return self._make_check("adapter_usage", "FAIL", f"missing adapters: {', '.join(missing)}", "HIGH")
        return self._make_check("adapter_usage", "PASS", "adapter layers are wired into orchestration", "LOW")

    def _check_module_boundaries(self) -> QualityCheck:
        offenders: list[str] = []
        for path in self._module_files():
            if path.parts[-2] == "quality":
                continue
            text = path.read_text(encoding="utf-8")
            if "src.quality" in text:
                offenders.append(str(path.relative_to(self.base_dir)))
        allowed = {"core\\weekly_pipeline.py", "core/weekly_pipeline.py"}
        if any(offender not in allowed for offender in offenders):
            return self._make_check("module_boundaries", "FAIL", f"unexpected quality imports: {', '.join(offenders)}", "MEDIUM")
        return self._make_check("module_boundaries", "PASS", "quality layer is kept at the edge", "LOW")

    def _check_empty_modules(self) -> tuple[QualityCheck, list[str]]:
        empty: list[str] = []
        for path in self._module_files():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            body = [node for node in tree.body if not isinstance(node, ast.Expr) or not isinstance(getattr(node, "value", None), ast.Constant) or not isinstance(node.value.value, str)]
            if not body:
                empty.append(str(path.relative_to(self.base_dir)))
        if empty:
            return self._make_check("empty_modules", "WARNING", f"empty modules: {', '.join(empty[:5])}", "MEDIUM"), [f"empty modules: {', '.join(empty)}"]
        return self._make_check("empty_modules", "PASS", "no empty modules detected", "LOW"), []

    def _check_todos(self) -> tuple[QualityCheck, list[str]]:
        matches: list[str] = []
        for path in self._module_files():
            text = path.read_text(encoding="utf-8")
            if "TODO" in text or "FIXME" in text:
                matches.append(str(path.relative_to(self.base_dir)))
        if matches:
            return self._make_check("todo_fixme", "WARNING", f"todo/fixme found in {', '.join(matches[:5])}", "LOW"), [f"todo/fixme: {', '.join(matches)}"]
        return self._make_check("todo_fixme", "PASS", "no TODO/FIXME markers found", "LOW"), []

    def _check_duplicate_objects(self) -> tuple[QualityCheck, list[str]]:
        seen: dict[str, list[str]] = defaultdict(list)
        for path in self._module_files():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.startswith("_"):
                        continue
                    seen[node.name].append(str(path.relative_to(self.base_dir)))
        duplicates = {name: files for name, files in seen.items() if len(files) > 1}
        if duplicates:
            sample_name, files = next(iter(duplicates.items()))
            return self._make_check("duplicate_objects", "WARNING", f"duplicate {sample_name} in {', '.join(files)}", "LOW"), [f"duplicate objects: {sample_name}"]
        return self._make_check("duplicate_objects", "PASS", "no obvious duplicate public objects", "LOW"), []

    def _build_sample_row(self) -> dict[str, Any]:
        result = run_research_pipeline("000001.SZ")
        return {
            "company_code": result["company_code"],
            "name": result["factor_input_summary"]["name"],
            "theme": result["factor_input_summary"]["theme"],
            "watch_priority": "A",
            "period": "TTM",
            "strategic_score": result["strategic_score"],
            "confidence_score": sum(
                float(item.get("final_confidence", 0.0))
                for item in result.get("factor_confidences", {}).values()
                if isinstance(item, dict)
            )
            / max(len(result.get("factor_confidences", {})), 1),
            "final_decision": "WATCH",
            "catalyst_strength": result["catalyst_strength"],
            "order_confirmation_level": result["order_confirmation_level"],
            "risk_summary": result["risk_summary"],
            "research_conclusion": result["research_conclusion"],
            "factor_input_summary": result["factor_input_summary"],
            "factor_scores": result["factor_scores"],
            "theme_exposure": result["theme_exposure"],
            "evidence_summary": result.get("evidence_summary", {}),
            "score_explanation": result.get("score_explanation", {}),
            "decision_explanation": result.get("decision_explanation", {}),
            "factor_confidences": result.get("factor_confidences", {}),
            "evidence_refs": result.get("evidence_refs", {}),
        }

    def _check_research_flow(self) -> tuple[QualityCheck, list[str]]:
        warnings: list[str] = []
        errors: list[str] = []
        try:
            sample = self._build_sample_row()
            workflow = build_default_workflow_engine()
            run = workflow.run_workflow(
                period="TTM",
                symbols=["000001.SZ"],
                context={
                    "rows": [sample],
                    "portfolio_snapshot": {},
                    "position_snapshot": {},
                    "risk_report": {},
                    "rebalance_plan": {},
                    "backtest_result": {},
                },
            )
            if run.final_status != "SUCCESS":
                errors.append(f"workflow_status={run.final_status}")
            warnings.extend(run.warnings[:5])
        except Exception as exc:
            return self._make_check("research_flow", "FAIL", f"workflow execution failed: {exc}", "CRITICAL"), [str(exc)]
        try:
            weekly_module = importlib.import_module("core.weekly_pipeline")
            if not hasattr(weekly_module, "generate_weekly_report"):
                errors.append("weekly_report_missing_entrypoint")
        except Exception as exc:
            return self._make_check("research_flow", "FAIL", f"weekly report import failed: {exc}", "CRITICAL"), [str(exc)]
        if errors:
            return self._make_check("research_flow", "FAIL", "; ".join(errors), "HIGH"), warnings + errors
        return self._make_check("research_flow", "PASS", "main research flow is connected", "LOW"), warnings

    def run(self) -> QualityReport:
        checks: list[QualityCheck] = []
        warnings: list[str] = []

        checks.append(self._check_core_modules())
        checks.append(self._check_circular_dependencies())
        checks.append(self._check_registry_usage())
        checks.append(self._check_adapter_usage())
        checks.append(self._check_module_boundaries())

        empty_check, empty_warnings = self._check_empty_modules()
        checks.append(empty_check)
        warnings.extend(empty_warnings)

        todo_check, todo_warnings = self._check_todos()
        checks.append(todo_check)
        warnings.extend(todo_warnings)

        duplicate_check, duplicate_warnings = self._check_duplicate_objects()
        checks.append(duplicate_check)
        warnings.extend(duplicate_warnings)

        flow_check, flow_warnings = self._check_research_flow()
        checks.append(flow_check)
        warnings.extend(flow_warnings)

        passed_count = sum(1 for item in checks if item.status == "PASS")
        failed_count = sum(1 for item in checks if item.status == "FAIL")
        rc1_ready = failed_count == 0
        if any(item.status == "WARNING" for item in checks):
            warnings.extend(
                f"{item.check_name}: {item.message}"
                for item in checks
                if item.status == "WARNING"
            )
        return QualityReport(
            timestamp=self._timestamp(),
            checks=checks,
            passed_count=passed_count,
            failed_count=failed_count,
            warnings=warnings,
            rc1_ready=rc1_ready,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.renderer.to_dict(self.run())
