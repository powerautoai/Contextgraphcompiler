#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:
    Draft202012Validator = None


DEFAULT_CONFIG: Dict[str, Any] = {
    "name": "CGC_M8_Productization_Gate",
    "description": "M8.0 productization and DX gate covering M8.1-M8.3",
    "version": "1.0",
    "sections": [],
    "output": {
        "report_file": "report.json",
        "summary_file": "summary.json",
        "pass_fail_strategy": "all_sections_must_pass",
    },
}


@dataclass
class CheckResult:
    check_id: str
    kind: str
    status: str
    target: Any
    details: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.check_id,
            "kind": self.kind,
            "status": self.status,
            "target": self.target,
            "details": self.details,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _deep_get(payload: Any, dotted_path: str) -> Any:
    current = payload
    for segment in str(dotted_path or "").split("."):
        if not segment:
            continue
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _current_host_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _resolve_build_matrix_dir(check: Dict[str, Any], runtime_context: Dict[str, Any]) -> Path:
    explicit = str(check.get("matrix_dir") or runtime_context.get("build_matrix_dir") or "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (Path(str(runtime_context["output_dir"])) / "m84_release_matrix").resolve()


def _build_report_payload_ok(payload: Dict[str, Any], required_fields: list[str], *, platform_name: str = "", expected_package_format: str = "") -> Dict[str, Any]:
    missing_fields = _check_required_fields(payload, required_fields)
    actual_platform = str(payload.get("platform") or "").strip()
    actual_package_format = str(payload.get("package_format") or "").strip()
    ok = (
        bool(payload)
        and not missing_fields
        and str(payload.get("status") or "") == "PASS"
        and bool(payload.get("output_exists"))
        and (not platform_name or actual_platform == platform_name)
        and (not expected_package_format or actual_package_format == expected_package_format)
        and int(payload.get("size_bytes") or 0) > 0
        and int(payload.get("executable_size_bytes") or 0) > 0
    )
    return {
        "ok": ok,
        "missing_fields": missing_fields,
        "actual_platform": actual_platform,
        "actual_package_format": actual_package_format,
    }


def _prepare_model_fixtures(output_dir: Path) -> Dict[str, str]:
    fixture_root = (output_dir / "m8_gate_fixtures").resolve()
    local_root = (fixture_root / "local_models").resolve()
    nfs_root = (fixture_root / "nfs_models").resolve()
    local_root.mkdir(parents=True, exist_ok=True)
    nfs_root.mkdir(parents=True, exist_ok=True)

    (local_root / "demo-local.gguf").write_bytes(b"GGUF")
    mlx_dir = (local_root / "demo-mlx-model").resolve()
    mlx_dir.mkdir(parents=True, exist_ok=True)
    (mlx_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    (mlx_dir / "config.json").write_text('{"model_type":"qwen2"}', encoding="utf-8")
    (mlx_dir / "model.safetensors").write_bytes(b"")
    (nfs_root / "demo-nfs.gguf").write_bytes(b"GGUF")
    bin_dir = (fixture_root / "bin").resolve()
    bin_dir.mkdir(parents=True, exist_ok=True)
    claude_stub = (bin_dir / "claude").resolve()
    claude_stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "print(json.dumps({\n"
        "  'argv': sys.argv[1:],\n"
        "  'env': {\n"
        "    'CLAUDE_CODE_SIMPLE': os.environ.get('CLAUDE_CODE_SIMPLE', ''),\n"
        "    'ANTHROPIC_BASE_URL': os.environ.get('ANTHROPIC_BASE_URL', ''),\n"
        "    'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),\n"
        "    'ANTHROPIC_CUSTOM_MODEL_OPTION': os.environ.get('ANTHROPIC_CUSTOM_MODEL_OPTION', ''),\n"
        "  }\n"
        "}))\n",
        encoding="utf-8",
    )
    claude_stub.chmod(0o755)

    return {
        "fixture_root": str(fixture_root),
        "local_root": str(local_root),
        "nfs_root": str(nfs_root),
        "local_gguf_model": str((local_root / "demo-local.gguf").resolve()),
        "local_mlx_model": str(mlx_dir),
        "nfs_gguf_model": str((nfs_root / "demo-nfs.gguf").resolve()),
        "bin_dir": str(bin_dir),
        "claude_stub": str(claude_stub),
    }


def _run_subprocess_json(command: list[str], *, cwd: Path, env: Optional[Dict[str, str]] = None, timeout: int = 600) -> tuple[Dict[str, Any], Dict[str, Any]]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    stdout = str(completed.stdout or "").strip()
    stderr = str(completed.stderr or "").strip()
    payload: Dict[str, Any] = {}
    parse_error = ""
    if stdout:
        try:
            payload = json.loads(stdout)
        except Exception as exc:
            parse_error = str(exc)
    return payload, {
        "command": command,
        "returncode": int(completed.returncode),
        "stdout": stdout,
        "stderr": stderr,
        "parse_error": parse_error,
    }


def _validate_against_schema(payload: Dict[str, Any], schema_path: Path) -> Dict[str, Any]:
    if not schema_path.exists():
        return {"ok": False, "errors": [f"schema_missing:{schema_path}"]}
    schema = _read_json(schema_path)
    if not schema:
        return {"ok": False, "errors": [f"schema_unreadable:{schema_path}"]}
    if Draft202012Validator is None:
        return {"ok": bool(isinstance(payload, dict) and payload), "errors": [] if payload else ["schema_validation_fallback_failed"]}
    validator = Draft202012Validator(schema)
    errors = [f"{'/'.join(str(x) for x in err.absolute_path)}:{err.message}" for err in validator.iter_errors(payload)]
    return {"ok": len(errors) == 0, "errors": errors[:20]}


def _check_required_fields(payload: Dict[str, Any], required_fields: list[str]) -> list[str]:
    missing = []
    for field in required_fields:
        value = _deep_get(payload, field)
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field)
    return missing


def _resolve_check_model(check: Dict[str, Any], runtime_context: Dict[str, Any], *, default_model: str) -> str:
    fixture_key = str(check.get("model_fixture_key") or "").strip()
    if fixture_key:
        fixtures = runtime_context.get("fixtures") or {}
        resolved = str(fixtures.get(fixture_key) or "").strip()
        if resolved:
            return resolved
    return str(check.get("model") or os.environ.get("CGC_M8_TEST_MODEL") or default_model)


def _run_nested_gate(repo_root: Path, gate_name: str, output_dir: Path) -> Dict[str, Any]:
    engine_root = (repo_root / "ComputeGraphCompiler-main").resolve()
    for candidate in (repo_root, engine_root):
        raw = str(candidate)
        if raw not in sys.path:
            sys.path.insert(0, raw)
    if gate_name == "m75":
        from cgc_engine.product import run_m75_gate

        return run_m75_gate(output_dir=str(output_dir))
    raise ValueError(f"unsupported_nested_gate:{gate_name}")


def _load_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists() and yaml is not None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def _find_check(section: Dict[str, Any], check_id: str) -> Dict[str, Any]:
    for check in list(section.get("checks") or []):
        if str(check.get("id") or "") == check_id:
            return check if isinstance(check, dict) else {}
    return {}


def _build_section_map(sections: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    section_map: Dict[str, Dict[str, Any]] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        name = str(section.get("name") or "").strip()
        if name:
            section_map[name] = section
        for alias in list(section.get("aliases") or []):
            alias_name = str(alias or "").strip()
            if alias_name:
                section_map[alias_name] = section
    return section_map


def _run_check(repo_root: Path, check: Dict[str, Any], runtime_context: Dict[str, Any]) -> CheckResult:
    check_id = str(check.get("id") or "unknown_check")
    kind = str(check.get("kind") or "unknown")

    if kind == "file_exists":
        rel_path = str(check.get("path") or "")
        target = repo_root / rel_path
        exists = target.exists()
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if exists else "FAIL",
            target=rel_path,
            details={"resolved_path": str(target), "exists": bool(exists)},
        )

    if kind == "any_path_exists":
        rel_paths = [str(x) for x in (check.get("paths") or [])]
        resolved = []
        existing = []
        for rel_path in rel_paths:
            target = repo_root / rel_path
            resolved.append(str(target))
            if target.exists():
                existing.append(rel_path)
        ok = len(existing) > 0
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target=rel_paths,
            details={"resolved_paths": resolved, "existing_paths": existing},
        )

    if kind in {"file_contains_all", "file_contains_any"}:
        rel_path = str(check.get("path") or "")
        target = repo_root / rel_path
        content = _read_text(target)
        patterns = [str(x) for x in (check.get("patterns") or [])]
        found = [pattern for pattern in patterns if pattern in content]
        if kind == "file_contains_all":
            ok = len(found) == len(patterns) and target.exists()
        else:
            ok = len(found) > 0 and target.exists()
        missing = [pattern for pattern in patterns if pattern not in found]
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target=rel_path,
            details={
                "resolved_path": str(target),
                "exists": bool(target.exists()),
                "patterns_found": found,
                "patterns_missing": missing,
            },
        )

    if kind == "cgc_list_contract":
        fixtures = runtime_context.get("fixtures") or {}
        schema_path = repo_root / str(check.get("schema_path") or "")
        env = dict(os.environ)
        env["CGC_CLUSTER_NFS_ROOT"] = str(fixtures.get("nfs_root") or "")
        payload, command_meta = _run_subprocess_json(
            [
                sys.executable,
                "-m",
                "app.cli.cgc",
                "list",
                "--json",
                "--model-root",
                str(fixtures.get("local_root") or ""),
                "--nfs-root",
                str(fixtures.get("nfs_root") or ""),
            ],
            cwd=repo_root,
            env=env,
            timeout=int(check.get("timeout_seconds") or 60),
        )
        schema_result = _validate_against_schema(payload, schema_path)
        missing_fields = _check_required_fields(payload, list(check.get("required_fields") or []))
        model_sources = {str(item.get("source") or "") for item in (payload.get("models") or []) if isinstance(item, dict)}
        model_ids = {str(item.get("model_id") or "") for item in (payload.get("models") or []) if isinstance(item, dict)}
        required_sources = [str(x) for x in (check.get("required_sources") or [])]
        required_model_ids = [str(x) for x in (check.get("required_model_ids") or [])]
        missing_sources = [source for source in required_sources if source not in model_sources]
        missing_model_ids = [model_id for model_id in required_model_ids if model_id not in model_ids]
        ok = (
            command_meta["returncode"] == 0
            and schema_result["ok"]
            and not missing_fields
            and not missing_sources
            and not missing_model_ids
            and len(payload.get("models") or []) > 0
        )
        runtime_context["last_list_response"] = payload
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target="cgc list --json",
            details={
                **command_meta,
                "schema_path": str(schema_path),
                "schema_ok": schema_result["ok"],
                "schema_errors": schema_result["errors"],
                "missing_fields": missing_fields,
                "missing_sources": missing_sources,
                "missing_model_ids": missing_model_ids,
                "model_count": len(payload.get("models") or []),
            },
        )

    if kind == "build_contract":
        build_dir = (Path(runtime_context["output_dir"]) / check_id).resolve()
        build_dir.mkdir(parents=True, exist_ok=True)
        build_matrix_dir = _resolve_build_matrix_dir(check, runtime_context)
        build_matrix_dir.mkdir(parents=True, exist_ok=True)
        payload, command_meta = _run_subprocess_json(
            [
                sys.executable,
                "-m",
                "app.cli.cgc",
                "build",
                "--output-dir",
                str(build_dir),
                "--aggregate-dir",
                str(build_matrix_dir),
                "--json",
            ],
            cwd=repo_root,
            env=dict(os.environ),
            timeout=int(check.get("timeout_seconds") or 3600),
        )
        missing_fields = _check_required_fields(payload, list(check.get("required_fields") or []))
        expected_platform = str(check.get("expected_platform") or _current_host_platform()).strip()
        actual_platform = str(payload.get("platform") or "").strip()
        expected_package_format = str(check.get("expected_package_format") or "").strip()
        actual_package_format = str(payload.get("package_format") or "").strip()
        supported_platforms = [str(x) for x in (payload.get("supported_platforms") or [])]
        required_supported_platforms = [str(x) for x in (check.get("required_supported_platforms") or [])]
        missing_supported_platforms = [x for x in required_supported_platforms if x not in supported_platforms]
        output_path = Path(str(payload.get("output_path") or "")).expanduser()
        executable_path = Path(str(payload.get("executable_path") or "")).expanduser()
        output_exists = bool(payload.get("output_exists")) and output_path.exists()
        size_bytes = int(payload.get("size_bytes") or 0)
        executable_size_bytes = int(payload.get("executable_size_bytes") or 0)
        ok = (
            command_meta["returncode"] == 0
            and not command_meta["parse_error"]
            and not missing_fields
            and output_exists
            and executable_path.exists()
            and size_bytes > 0
            and executable_size_bytes > 0
            and (not expected_platform or actual_platform == expected_platform)
            and (not expected_package_format or actual_package_format == expected_package_format)
            and not missing_supported_platforms
        )
        runtime_context["last_build_response"] = payload
        runtime_context["build_matrix_dir"] = str(build_matrix_dir)
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target="cgc build --json",
            details={
                **command_meta,
                "output_dir": str(build_dir),
                "missing_fields": missing_fields,
                "expected_platform": expected_platform,
                "actual_platform": actual_platform,
                "expected_package_format": expected_package_format,
                "actual_package_format": actual_package_format,
                "required_supported_platforms": required_supported_platforms,
                "supported_platforms": supported_platforms,
                "missing_supported_platforms": missing_supported_platforms,
                "output_path": str(output_path),
                "output_exists": output_exists,
                "executable_path": str(executable_path),
                "size_bytes": size_bytes,
                "executable_size_bytes": executable_size_bytes,
                "build_matrix_dir": str(build_matrix_dir),
                "platform_report_file": str((build_matrix_dir / f"{actual_platform}.json").resolve()) if actual_platform else "",
                "build_matrix_file": str((build_matrix_dir / "build_matrix.json").resolve()),
            },
        )

    if kind == "build_matrix_contract":
        matrix_dir = _resolve_build_matrix_dir(check, runtime_context)
        matrix_dir.mkdir(parents=True, exist_ok=True)
        matrix_file = (matrix_dir / "build_matrix.json").resolve()
        matrix_payload = _read_json(matrix_file) if matrix_file.exists() else {}
        required_platforms = [str(x) for x in (check.get("required_platforms") or ["windows", "macos", "linux"])]
        required_fields = [str(x) for x in (check.get("required_fields") or [])]
        package_format_map = check.get("expected_package_formats") if isinstance(check.get("expected_package_formats"), dict) else {}
        reports: Dict[str, Dict[str, Any]] = {}
        missing_platforms = []
        invalid_platforms = []
        platform_details: Dict[str, Any] = {}
        platform_paths = (matrix_payload.get("platform_reports") if isinstance(matrix_payload.get("platform_reports"), dict) else {}) or {}
        for platform_name in required_platforms:
            candidate_path = str(platform_paths.get(platform_name) or "")
            if not candidate_path:
                candidate_path = str((matrix_dir / f"{platform_name}.json").resolve())
            report_path = Path(candidate_path).expanduser()
            payload = _read_json(report_path) if report_path.exists() else {}
            validation = _build_report_payload_ok(
                payload,
                required_fields,
                platform_name=platform_name,
                expected_package_format=str(package_format_map.get(platform_name) or ""),
            )
            if not report_path.exists():
                missing_platforms.append(platform_name)
            elif not validation["ok"]:
                invalid_platforms.append(platform_name)
            reports[platform_name] = payload
            platform_details[platform_name] = {
                "report_path": str(report_path),
                "exists": report_path.exists(),
                "missing_fields": validation["missing_fields"],
                "actual_platform": validation["actual_platform"],
                "actual_package_format": validation["actual_package_format"],
                "status": str(payload.get("status") or ""),
                "size_bytes": int(payload.get("size_bytes") or 0),
                "executable_size_bytes": int(payload.get("executable_size_bytes") or 0),
            }
        ok = matrix_file.exists() and not missing_platforms and not invalid_platforms
        runtime_context["build_matrix_reports"] = reports
        runtime_context["build_matrix_dir"] = str(matrix_dir)
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target=str(matrix_dir),
            details={
                "matrix_dir": str(matrix_dir),
                "matrix_file": str(matrix_file),
                "matrix_file_exists": matrix_file.exists(),
                "required_platforms": required_platforms,
                "missing_platforms": missing_platforms,
                "invalid_platforms": invalid_platforms,
                "platform_details": platform_details,
            },
        )

    if kind == "artifact_size_budget":
        report_platform = str(check.get("report_platform") or "").strip()
        if report_platform:
            payload = ((runtime_context.get("build_matrix_reports") or {}) if isinstance(runtime_context.get("build_matrix_reports"), dict) else {}).get(report_platform) or {}
        else:
            payload = runtime_context.get("last_build_response") or {}
        platform_name = str(payload.get("platform") or "")
        package_format = str(payload.get("package_format") or "")
        size_bytes = int(payload.get("size_bytes") or 0)
        executable_size_bytes = int(payload.get("executable_size_bytes") or 0)
        max_size_bytes = int(check.get("max_size_bytes") or 0)
        max_executable_size_bytes = int(check.get("max_executable_size_bytes") or 0)
        expected_platform = str(check.get("expected_platform") or "").strip()
        expected_package_format = str(check.get("expected_package_format") or "").strip()
        ok = (
            bool(payload)
            and size_bytes > 0
            and executable_size_bytes > 0
            and (not expected_platform or platform_name == expected_platform)
            and (not expected_package_format or package_format == expected_package_format)
            and (max_size_bytes <= 0 or size_bytes <= max_size_bytes)
            and (max_executable_size_bytes <= 0 or executable_size_bytes <= max_executable_size_bytes)
        )
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target=str(payload.get("output_path") or ""),
            details={
                "report_platform": report_platform,
                "platform": platform_name,
                "package_format": package_format,
                "size_bytes": size_bytes,
                "executable_size_bytes": executable_size_bytes,
                "max_size_bytes": max_size_bytes,
                "max_executable_size_bytes": max_executable_size_bytes,
                "expected_platform": expected_platform,
                "expected_package_format": expected_package_format,
            },
        )

    if kind == "nested_gate_contract":
        gate_name = str(check.get("gate_name") or "").strip()
        nested_output_dir = (Path(runtime_context["output_dir"]) / check_id).resolve()
        nested_output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = _run_nested_gate(repo_root, gate_name, nested_output_dir)
            gate_result = result.get("gate_result") if isinstance(result, dict) else {}
            nested_gate = (gate_result or {}).get(gate_name) if isinstance(gate_result, dict) else {}
            passed_checks = list(nested_gate.get("passed_checks") or []) if isinstance(nested_gate, dict) else []
            failed_checks = list(nested_gate.get("failed_checks") or []) if isinstance(nested_gate, dict) else []
            required_checks = [str(x) for x in (check.get("required_checks") or [])]
            missing_required = [name for name in required_checks if name not in passed_checks]
            ok = bool(result.get("ok")) and not failed_checks and not missing_required and bool(str(result.get("report_path") or "").strip())
            runtime_context[f"nested_gate_{gate_name}"] = result
            return CheckResult(
                check_id=check_id,
                kind=kind,
                status="PASS" if ok else "FAIL",
                target=f"nested gate {gate_name}",
                details={
                    "gate_name": gate_name,
                    "output_dir": str(nested_output_dir),
                    "report_path": str(result.get("report_path") or ""),
                    "ok": bool(result.get("ok")),
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                    "required_checks": required_checks,
                    "missing_required_checks": missing_required,
                },
            )
        except Exception as exc:
            return CheckResult(
                check_id=check_id,
                kind=kind,
                status="FAIL",
                target=f"nested gate {gate_name}",
                details={"gate_name": gate_name, "error": str(exc)},
            )

    if kind == "cgc_run_contract":
        schema_path = repo_root / str(check.get("schema_path") or "")
        report_dir = (Path(runtime_context["output_dir"]) / check_id).resolve()
        report_dir.mkdir(parents=True, exist_ok=True)
        model = _resolve_check_model(
            check,
            runtime_context,
            default_model="mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
        )
        prompt = str(check.get("prompt") or "Say OK")
        command = [
            sys.executable,
            "-m",
            "app.cli.cgc",
            "run",
            model,
        ]
        if bool(check.get("use_omlx", True)):
            command.append("--use-omlx")
        if bool(check.get("use_flashmoe")):
            command.append("--use-flashmoe")
        command.extend(
            [
                "--prompt",
                prompt,
                "--max-tokens",
                str(int(check.get("max_tokens") or 8)),
                "--json",
                "--report-dir",
                str(report_dir),
            ]
        )
        payload, command_meta = _run_subprocess_json(
            command,
            cwd=repo_root,
            env=dict(os.environ),
            timeout=int(check.get("timeout_seconds") or 600),
        )
        schema_result = _validate_against_schema(payload, schema_path)
        missing_fields = _check_required_fields(payload, list(check.get("required_fields") or []))
        evidence_paths = payload.get("evidence_paths") or {}
        missing_evidence = [
            key
            for key in (check.get("required_evidence_keys") or [])
            if not str(evidence_paths.get(key) or "").strip() or not Path(str(evidence_paths.get(key))).expanduser().exists()
        ]
        expected_route = str(check.get("expected_route") or "").strip()
        actual_route = str(payload.get("selected_route") or "")
        expected_backend = str(check.get("expected_backend") or "").strip()
        actual_backend = str(payload.get("selected_backend") or "")
        expected_local_execution = check.get("expected_local_execution")
        expected_cloud_bridge_used = check.get("expected_cloud_bridge_used")
        ok = (
            command_meta["returncode"] == 0
            and schema_result["ok"]
            and not missing_fields
            and not missing_evidence
            and (not expected_route or actual_route == expected_route)
            and (not expected_backend or actual_backend == expected_backend)
            and (
                expected_local_execution is None
                or bool(payload.get("local_execution")) is bool(expected_local_execution)
            )
            and (
                expected_cloud_bridge_used is None
                or bool(payload.get("cloud_bridge_used")) is bool(expected_cloud_bridge_used)
            )
        )
        runtime_context["last_run_response"] = payload
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target="cgc run --prompt --json",
            details={
                **command_meta,
                "schema_path": str(schema_path),
                "schema_ok": schema_result["ok"],
                "schema_errors": schema_result["errors"],
                "missing_fields": missing_fields,
                "missing_evidence": missing_evidence,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "expected_backend": expected_backend,
                "actual_backend": actual_backend,
                "expected_local_execution": expected_local_execution,
                "actual_local_execution": bool(payload.get("local_execution")),
                "expected_cloud_bridge_used": expected_cloud_bridge_used,
                "actual_cloud_bridge_used": bool(payload.get("cloud_bridge_used")),
            },
        )

    if kind == "serve_contract":
        schema_path = repo_root / str(check.get("schema_path") or "")
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from fastapi.testclient import TestClient
        from app.servers.cgc_api_server import app

        model = _resolve_check_model(
            check,
            runtime_context,
            default_model="mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
        )
        request_payload = {
            "model": model,
            "prompt": str(check.get("prompt") or "Say OK"),
            "stream": True,
            "use_omlx": bool(check.get("use_omlx", True)),
            "use_flashmoe": bool(check.get("use_flashmoe", False)),
            "max_tokens": int(check.get("max_tokens") or 8),
        }
        with TestClient(app) as client:
            with client.stream("POST", "/api/generate", json=request_payload) as response:
                raw_lines = [line for line in response.iter_lines() if line]
        events = [json.loads(line) for line in raw_lines]
        first_event = events[0] if events else {}
        final_event = events[-1] if events else {}
        first_schema = _validate_against_schema(first_event, schema_path)
        final_schema = _validate_against_schema(final_event, schema_path)
        missing_first = _check_required_fields(first_event, list(check.get("required_first_fields") or []))
        missing_final = _check_required_fields(final_event, list(check.get("required_final_fields") or []))
        expected_first_route = str(check.get("expected_first_route") or "").strip()
        expected_final_route = str(check.get("expected_final_route") or "").strip()
        expected_final_backend = str(check.get("expected_final_backend") or "").strip()
        expected_final_local_execution = check.get("expected_final_local_execution")
        expected_final_cloud_bridge_used = check.get("expected_final_cloud_bridge_used")
        ok = (
            bool(events)
            and first_schema["ok"]
            and final_schema["ok"]
            and not missing_first
            and not missing_final
            and (not expected_first_route or str(first_event.get("selected_route") or "") == expected_first_route)
            and (not expected_final_route or str(final_event.get("selected_route") or "") == expected_final_route)
            and (not expected_final_backend or str(final_event.get("selected_backend") or "") == expected_final_backend)
            and (
                expected_final_local_execution is None
                or bool(final_event.get("local_execution")) is bool(expected_final_local_execution)
            )
            and (
                expected_final_cloud_bridge_used is None
                or bool(final_event.get("cloud_bridge_used")) is bool(expected_final_cloud_bridge_used)
            )
        )
        runtime_context["last_serve_events"] = events
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target="/api/generate",
            details={
                "event_count": len(events),
                "schema_path": str(schema_path),
                "first_event": first_event,
                "final_event": final_event,
                "first_schema_ok": first_schema["ok"],
                "final_schema_ok": final_schema["ok"],
                "first_schema_errors": first_schema["errors"],
                "final_schema_errors": final_schema["errors"],
                "missing_first_fields": missing_first,
                "missing_final_fields": missing_final,
                "expected_first_route": expected_first_route,
                "expected_final_route": expected_final_route,
                "expected_final_backend": expected_final_backend,
                "expected_final_local_execution": expected_final_local_execution,
                "actual_final_local_execution": bool(final_event.get("local_execution")),
                "expected_final_cloud_bridge_used": expected_final_cloud_bridge_used,
                "actual_final_cloud_bridge_used": bool(final_event.get("cloud_bridge_used")),
            },
        )

    if kind == "route_decision_evidence":
        last_run = runtime_context.get("last_run_response") or {}
        evidence_paths = last_run.get("evidence_paths") or {}
        route_path = Path(str(evidence_paths.get("route_decision") or runtime_context.get("latest_route_decision") or "")).expanduser()
        bridge_path = Path(str(evidence_paths.get("edge_inference_bridge") or "")).expanduser()
        route_payload = _read_json(route_path) if route_path.exists() else {}
        bridge_payload = _read_json(bridge_path) if bridge_path.exists() else {}
        missing_fields = _check_required_fields(route_payload, list(check.get("required_fields") or []))
        expected_route = str(check.get("expected_route") or "").strip()
        expected_backend = str(check.get("expected_backend") or "").strip()
        expected_bridge_status = str(check.get("expected_bridge_status") or "").strip()
        ok = (
            route_path.exists()
            and bridge_path.exists()
            and not missing_fields
            and bool(route_payload)
            and bool(bridge_payload)
            and (not expected_route or str(route_payload.get("selected_route") or "") == expected_route)
            and (not expected_backend or str(route_payload.get("selected_backend") or "") == expected_backend)
            and (not expected_bridge_status or str(bridge_payload.get("status") or "") == expected_bridge_status)
        )
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target=str(route_path),
            details={
                "route_decision_path": str(route_path),
                "route_decision_exists": route_path.exists(),
                "edge_bridge_path": str(bridge_path),
                "edge_bridge_exists": bridge_path.exists(),
                "missing_fields": missing_fields,
                "selected_route": route_payload.get("selected_route"),
                "selected_backend": route_payload.get("selected_backend"),
                "bridge_status": bridge_payload.get("status"),
                "expected_route": expected_route,
                "expected_backend": expected_backend,
                "expected_bridge_status": expected_bridge_status,
            },
        )

    if kind == "claude_contract":
        env = dict(os.environ)
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli.cgc",
                "claude",
                "--version",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=int(check.get("timeout_seconds") or 60),
        )
        stdout = str(completed.stdout or "").strip()
        stderr = str(completed.stderr or "").strip()
        expected_patterns = [str(x) for x in (check.get("expected_patterns") or [])]
        missing_patterns = [pattern for pattern in expected_patterns if pattern not in stdout and pattern not in stderr]
        ok = int(completed.returncode) == 0 and not missing_patterns
        return CheckResult(
            check_id=check_id,
            kind=kind,
            status="PASS" if ok else "FAIL",
            target="cgc claude",
            details={
                "returncode": int(completed.returncode),
                "stdout": stdout,
                "stderr": stderr,
                "expected_patterns": expected_patterns,
                "missing_patterns": missing_patterns,
            },
        )

    return CheckResult(
        check_id=check_id,
        kind=kind,
        status="FAIL",
        target=check.get("path") or check.get("paths") or "",
        details={"reason": f"unsupported_check_kind:{kind}"},
    )


def _evaluate_section(repo_root: Path, section: Dict[str, Any], runtime_context: Dict[str, Any]) -> Dict[str, Any]:
    name = str(section.get("name") or "unknown_section")
    checks = section.get("checks") or []
    min_pass_ratio = float(section.get("min_pass_ratio") or 1.0)

    results = [_run_check(repo_root, check, runtime_context) for check in checks]
    total = len(results)
    passed = sum(1 for result in results if result.status == "PASS")
    pass_ratio = float(passed / total) if total > 0 else 0.0
    status = "PASS" if pass_ratio >= min_pass_ratio and passed == total else "FAIL"

    return {
        "name": name,
        "aliases": [str(alias) for alias in (section.get("aliases") or []) if str(alias).strip()],
        "description": str(section.get("description") or ""),
        "status": status,
        "total_checks": total,
        "passed_checks": passed,
        "pass_ratio": pass_ratio,
        "min_pass_ratio": min_pass_ratio,
        "checks": [result.as_dict() for result in results],
    }


def run_m8_gate(*, repo_root: str, output_dir: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    repo_root_p = Path(repo_root).expanduser().resolve()
    output_dir_p = Path(output_dir).expanduser().resolve()
    output_dir_p.mkdir(parents=True, exist_ok=True)

    default_config_path = Path(__file__).with_name("m8_gate.yaml")
    active_config_path = Path(config_path).expanduser().resolve() if config_path else default_config_path
    config = _load_config(active_config_path)
    runtime_context: Dict[str, Any] = {
        "output_dir": str(output_dir_p),
        "fixtures": _prepare_model_fixtures(output_dir_p),
    }

    sections = [_evaluate_section(repo_root_p, section, runtime_context) for section in (config.get("sections") or [])]
    overall_status = "PASS" if sections and all(section["status"] == "PASS" for section in sections) else "FAIL"

    section_index = _build_section_map(sections)
    m81_section = section_index.get("m81_productization", {})
    m82_section = section_index.get("m82_cli_build", {})
    m83_section = section_index.get("m83_cloud_native", {})
    m84_section = section_index.get("m84_release_build", {})
    nested_m75 = runtime_context.get("nested_gate_m75") if isinstance(runtime_context.get("nested_gate_m75"), dict) else {}
    m75_gate = (nested_m75.get("gate_result") or {}).get("m75") if isinstance(nested_m75.get("gate_result"), dict) else {}
    m75_check = _find_check(m81_section, "m75_api_compat_foundation")
    claude_check = _find_check(m81_section, "claude_takeover_contract")
    m82_local_run_check = _find_check(m82_section, "cgc_run_response_contract")
    m82_local_route_check = _find_check(m82_section, "route_decision_contract")
    m82_takeover_run_check = _find_check(m82_section, "cgc_run_takeover_contract")
    m82_takeover_route_check = _find_check(m82_section, "route_decision_takeover_contract")
    m83_local_stream_check = _find_check(m83_section, "serve_response_contract")
    m83_takeover_stream_check = _find_check(m83_section, "serve_takeover_contract")
    m84_build_check = _find_check(m84_section, "cgc_build_release_contract")
    m84_matrix_check = _find_check(m84_section, "build_release_matrix_contract")
    m84_size_check = _find_check(m84_section, "artifact_size_budget_contract")
    m84_windows_size_check = _find_check(m84_section, "windows_artifact_size_budget_contract")
    m84_macos_size_check = _find_check(m84_section, "macos_artifact_size_budget_contract")
    m84_linux_size_check = _find_check(m84_section, "linux_artifact_size_budget_contract")
    m8_cgc_sections = {
        "m81_productization": str(m81_section.get("status") or "FAIL"),
        "m82_cli_build": str(m82_section.get("status") or "FAIL"),
        "m83_cloud_native": str(m83_section.get("status") or "FAIL"),
        "m84_release_build": str(m84_section.get("status") or "FAIL"),
    }
    acceptance_contract = config.get("acceptance_contract") if isinstance(config.get("acceptance_contract"), dict) else {}
    dual_acceptance = {
        "m8_overall": {
            "status": "PASS" if bool(nested_m75.get("ok")) and all(status == "PASS" for status in m8_cgc_sections.values()) else "FAIL",
            "description": str(((acceptance_contract.get("m8_overall") or {}) if isinstance(acceptance_contract.get("m8_overall"), dict) else {}).get("description") or "M8 dual acceptance"),
            "components": {
                "m75_api_compatibility": {
                    "status": "PASS" if bool(nested_m75.get("ok")) else "FAIL",
                    "report_path": str(nested_m75.get("report_path") or ""),
                    "passed_checks": list(m75_gate.get("passed_checks") or []) if isinstance(m75_gate, dict) else [],
                    "failed_checks": list(m75_gate.get("failed_checks") or []) if isinstance(m75_gate, dict) else [],
                },
                "m8_cgc_commands": {
                    "status": "PASS" if all(status == "PASS" for status in m8_cgc_sections.values()) else "FAIL",
                    "section_statuses": m8_cgc_sections,
                },
            },
        },
        "m81_dual_acceptance": {
            "status": "PASS" if str(m75_check.get("status") or "FAIL") == "PASS" and str(claude_check.get("status") or "FAIL") == "PASS" else "FAIL",
            "description": str(((acceptance_contract.get("m81_dual_acceptance") or {}) if isinstance(acceptance_contract.get("m81_dual_acceptance"), dict) else {}).get("description") or "M8.1 dual acceptance"),
            "components": {
                "m75_api_compatibility": {
                    "status": str(m75_check.get("status") or "FAIL"),
                    "report_path": str(((m75_check.get("details") or {}) if isinstance(m75_check.get("details"), dict) else {}).get("report_path") or ""),
                },
                "claude_code": {
                    "status": str(claude_check.get("status") or "FAIL"),
                    "target": str(claude_check.get("target") or ""),
                },
            },
        },
        "m82_cgc_run_route_dual_acceptance": {
            "status": "PASS" if all(str(check.get("status") or "FAIL") == "PASS" for check in (m82_local_run_check, m82_local_route_check, m82_takeover_run_check, m82_takeover_route_check)) else "FAIL",
            "description": str(((acceptance_contract.get("m82_cgc_run_route_dual_acceptance") or {}) if isinstance(acceptance_contract.get("m82_cgc_run_route_dual_acceptance"), dict) else {}).get("description") or "M8.2 dual acceptance"),
            "components": {
                "cgc_run_local_success": {
                    "status": str(m82_local_run_check.get("status") or "FAIL"),
                },
                "route_decision_local_success": {
                    "status": str(m82_local_route_check.get("status") or "FAIL"),
                },
                "cgc_run_m73_takeover": {
                    "status": str(m82_takeover_run_check.get("status") or "FAIL"),
                },
                "route_decision_m73_takeover": {
                    "status": str(m82_takeover_route_check.get("status") or "FAIL"),
                },
            },
        },
        "m83_serve_streaming_takeover_acceptance": {
            "status": "PASS" if all(str(check.get("status") or "FAIL") == "PASS" for check in (m83_local_stream_check, m83_takeover_stream_check)) else "FAIL",
            "description": str(((acceptance_contract.get("m83_serve_streaming_takeover_acceptance") or {}) if isinstance(acceptance_contract.get("m83_serve_streaming_takeover_acceptance"), dict) else {}).get("description") or "M8.3 dual acceptance"),
            "components": {
                "serve_streaming_local_success": {
                    "status": str(m83_local_stream_check.get("status") or "FAIL"),
                },
                "serve_streaming_m73_takeover": {
                    "status": str(m83_takeover_stream_check.get("status") or "FAIL"),
                },
            },
        },
        "m84_cgc_build_release_acceptance": {
            "status": "PASS" if all(str(check.get("status") or "FAIL") == "PASS" for check in (m84_build_check, m84_matrix_check, m84_size_check, m84_windows_size_check, m84_macos_size_check, m84_linux_size_check)) else "FAIL",
            "description": str(((acceptance_contract.get("m84_cgc_build_release_acceptance") or {}) if isinstance(acceptance_contract.get("m84_cgc_build_release_acceptance"), dict) else {}).get("description") or "M8.4 build acceptance"),
            "components": {
                "cgc_build_release_contract": {
                    "status": str(m84_build_check.get("status") or "FAIL"),
                    "platform": str(((m84_build_check.get("details") or {}) if isinstance(m84_build_check.get("details"), dict) else {}).get("actual_platform") or ""),
                    "package_format": str(((m84_build_check.get("details") or {}) if isinstance(m84_build_check.get("details"), dict) else {}).get("actual_package_format") or ""),
                },
                "build_matrix_contract": {
                    "status": str(m84_matrix_check.get("status") or "FAIL"),
                    "matrix_dir": str(((m84_matrix_check.get("details") or {}) if isinstance(m84_matrix_check.get("details"), dict) else {}).get("matrix_dir") or ""),
                },
                "artifact_size_budget": {
                    "status": str(m84_size_check.get("status") or "FAIL"),
                    "size_bytes": int((((m84_size_check.get("details") or {}) if isinstance(m84_size_check.get("details"), dict) else {}).get("size_bytes") or 0)),
                },
                "windows_artifact_size_budget": {
                    "status": str(m84_windows_size_check.get("status") or "FAIL"),
                },
                "macos_artifact_size_budget": {
                    "status": str(m84_macos_size_check.get("status") or "FAIL"),
                },
                "linux_artifact_size_budget": {
                    "status": str(m84_linux_size_check.get("status") or "FAIL"),
                },
            },
        },
    }
    report = {
        "name": str(config.get("name") or "CGC_M8_Productization_Gate"),
        "description": str(config.get("description") or ""),
        "version": str(config.get("version") or "1.0"),
        "generated_at": _utc_now(),
        "repo_root": str(repo_root_p),
        "config_path": str(active_config_path),
        "status": overall_status,
        "runtime_context": {
            "fixtures": runtime_context.get("fixtures", {}),
        },
        "acceptance_contract": acceptance_contract,
        "dual_acceptance": dual_acceptance,
        "sections_by_name": _build_section_map(sections),
        "gate_result": {
            "m81": m81_section,
            "m82": m82_section,
            "m83": m83_section,
            "m84": m84_section,
            "m81_productization": m81_section,
            "m81_m75_claude_dual_acceptance": m81_section,
            "m82_cli_build": m82_section,
            "m82_cgc_run_route_dual_acceptance": m82_section,
            "m83_cloud_native": m83_section,
            "m83_serve_streaming_takeover_acceptance": m83_section,
            "m84_release_build": m84_section,
            "m84_cgc_build_release_acceptance": m84_section,
        },
        "sections": sections,
    }

    report_file = str((output_dir_p / str((config.get("output") or {}).get("report_file") or "report.json")).resolve())
    summary_file = str((output_dir_p / str((config.get("output") or {}).get("summary_file") or "summary.json")).resolve())

    summary = {
        "name": report["name"],
        "status": overall_status,
        "generated_at": report["generated_at"],
        "sections": {
            key: {
                "status": value["status"],
                "passed_checks": value["passed_checks"],
                "total_checks": value["total_checks"],
                "pass_ratio": value["pass_ratio"],
                "canonical_name": value["name"],
            }
            for key, value in _build_section_map(sections).items()
        },
        "acceptance_contract": acceptance_contract,
        "dual_acceptance": {
            key: {
                "status": str(value.get("status") or "FAIL"),
                "description": str(value.get("description") or ""),
            }
            for key, value in dual_acceptance.items()
            if isinstance(value, dict)
        },
        "report_path": report_file,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "status": overall_status,
        "report_path": report_file,
        "summary_path": summary_file,
        "gate_result": report["gate_result"],
    }


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_repo_root = script_dir.parent
    default_output_dir = script_dir / "Output" / "m8_gate"

    parser = argparse.ArgumentParser(description="Run CGC M8.0 productization gate (M8.1-M8.3).")
    parser.add_argument("--repo-root", type=str, default=str(default_repo_root), help="Repository root to inspect.")
    parser.add_argument("--output-dir", type=str, default=str(default_output_dir), help="Directory for gate reports.")
    parser.add_argument("--config", type=str, default=None, help="Optional override for m8 gate config.")
    parser.add_argument("--print-report", action="store_true", help="Print gate result as JSON.")
    args = parser.parse_args()

    result = run_m8_gate(repo_root=args.repo_root, output_dir=args.output_dir, config_path=args.config)
    if args.print_report:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"M8 gate status: {result['status']}")
        print(f"report: {result['report_path']}")
        print(f"summary: {result['summary_path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
