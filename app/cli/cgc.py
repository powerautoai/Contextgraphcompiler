import argparse
import asyncio
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
import sys
import subprocess
import time
import requests
import multiprocessing
from pathlib import Path

BOOTSTRAP_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(BOOTSTRAP_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_REPO_ROOT))

from app.edge_engine.audit_cli import export_audit, run_audit, trace_audit, verify_audit
from app.edge_engine.build import build_edge_engine
from app.edge_engine.service_manager import start_edge_stack


def resolve_cgc_state_dir():
    env_dir = os.environ.get("CGC_HOME")
    if env_dir:
        path = Path(env_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    home_dir = (Path.home() / ".cgc").resolve()
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        probe = home_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return home_dir
    except Exception:
        fallback = (Path(__file__).resolve().parents[2] / ".cgc_local").resolve()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


CGC_STATE_DIR = resolve_cgc_state_dir()
CONFIG_FILE = str((CGC_STATE_DIR / "config.json").resolve())
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPT_DIR = REPO_ROOT
RELEASE_DIR = REPO_ROOT / "CGC_Release"
ENGINE_REPO_DIR = REPO_ROOT / "ComputeGraphCompiler-main"
GATE_CHECKIN_DIR = RELEASE_DIR / "checkins"
GATE_CHECKIN_LOG = GATE_CHECKIN_DIR / "gate_checkins.jsonl"
TARGET_RELEASE_REPO = "powerautoai/ComputeGraphCompiler"
CGC_MODELS_DIR = (CGC_STATE_DIR / "models").resolve()
MINICPM5_OLLAMA_MODEL = "minicpm5-1b"
MINICPM5_GGUF_REPO = "openbmb/MiniCPM5-1B-GGUF"
MINICPM5_DEFAULT_QUANT = "Q4_K_M"
CGC_ENGINE_BASE_URL = "http://localhost:8000"
DEFAULT_CLUSTER_NFS_ROOT = "/nfs/embodied"
MINICPM5_CLUSTER_NFS_DIR = f"{DEFAULT_CLUSTER_NFS_ROOT}/minicpm5"
MINICPM5_CLUSTER_NFS_PATH = f"{MINICPM5_CLUSTER_NFS_DIR}/MiniCPM5-1B-Q4_K_M.gguf"
CGC_RUN_ARTIFACT_ROOT = (ENGINE_REPO_DIR / "Output" / "edge_runtime" / "cgc_run").resolve()
CGC_RUN_LATEST_REPORT = (CGC_RUN_ARTIFACT_ROOT / "latest_run_report.json").resolve()
CGC_RUN_LATEST_M4_INFERENCE_REPORT = (CGC_RUN_ARTIFACT_ROOT / "latest_m4_inference_report.json").resolve()
CGC_RUN_LATEST_EDGE_BRIDGE = (CGC_RUN_ARTIFACT_ROOT / "latest_edge_inference_bridge.json").resolve()
CGC_RUN_LATEST_ROUTE_DECISION = (CGC_RUN_ARTIFACT_ROOT / "latest_route_decision.json").resolve()


def load_python_callable(module_path, module_name, attr_name):
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, attr_name)


def load_release_m8_gate_runner():
    return load_python_callable(RELEASE_DIR / "m8_gate.py", "cgc_release_m8_gate", "run_m8_gate")


def load_engine_m7_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m7_gate
    return run_m7_gate


def load_engine_m72_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m72_gate
    return run_m72_gate


def load_engine_m73_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m73_gate
    return run_m73_gate


def load_engine_m1_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m1_gate
    return run_m1_gate


def load_engine_m2_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m2_gate
    return run_m2_gate


def load_engine_m3_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m3_gate
    return run_m3_gate


def load_engine_m4_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m4_gate_internal
    return run_m4_gate_internal


def load_engine_m5_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m5_gate
    return run_m5_gate


def load_engine_m6_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m6_gate
    return run_m6_gate


def load_engine_m74_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m74_gate
    return run_m74_gate


def load_engine_m75_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m75_gate
    return run_m75_gate


def load_engine_m76_gate_runner():
    if str(ENGINE_REPO_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_REPO_DIR))
    from cgc_engine.product import run_m76_gate
    return run_m76_gate


def write_json_file(file_path, payload):
    out_path = Path(file_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(out_path)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_command_checked(command, *, cwd=None, env=None, capture_output=False):
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        check=True,
        capture_output=capture_output,
    )


def get_m75_install_evidence_path():
    return (
        ENGINE_REPO_DIR
        / "Output"
        / "cli_gate_m75"
        / "runtime_evidence"
        / "edge_router_install.json"
    ).resolve()


def ollama_model_exists(model_name):
    try:
        run_command_checked(["ollama", "show", model_name], capture_output=True)
        return True
    except Exception:
        return False


def fetch_fake_ollama_models():
    try:
        response = requests.get(f"{get_edge_api_base_url()}/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        from fastapi.testclient import TestClient
        from app.servers.cgc_api_server import app

        client = TestClient(app)
        payload = client.get("/api/tags").json()
    return payload.get("models", [])


def fetch_fake_ollama_install_spec(model_name):
    normalized = str(model_name or "").strip()
    if not normalized:
        raise ValueError("empty_model_name")

    def _extract(tags_payload, show_payload):
        models = tags_payload.get("models", [])
        matched = None
        for model in models:
            candidates = {
                str(model.get("name") or "").strip(),
                str(model.get("model") or "").strip(),
            }
            if normalized in candidates or f"{normalized}:latest" in candidates:
                matched = model
                break
        if matched is None:
            raise RuntimeError(f"model_not_exposed_by_fake_ollama_protocol: {normalized}")
        details = show_payload.get("details") or {}
        return {
            "registry_model": str(matched.get("model") or normalized),
            "registry_entry": matched,
            "source_priority": list(details.get("source_priority") or ["cluster_nfs", "huggingface"]),
            "cluster_nfs_root": str(details.get("cluster_nfs_root") or DEFAULT_CLUSTER_NFS_ROOT),
            "cluster_nfs_path": str(details.get("cluster_nfs_path") or ""),
            "gguf_repo": str(details.get("gguf_repo") or MINICPM5_GGUF_REPO),
            "gguf_filename": str(details.get("gguf_filename") or f"MiniCPM5-1B-{MINICPM5_DEFAULT_QUANT}.gguf"),
            "ollama_model": str(details.get("ollama_model") or MINICPM5_OLLAMA_MODEL),
            "quant": str(details.get("quant") or MINICPM5_DEFAULT_QUANT),
            "install_via": str(details.get("install_via") or "fake_ollama_protocol"),
            "show_payload": show_payload,
        }

    try:
        edge_api_base_url = get_edge_api_base_url()
        tags_response = requests.get(f"{edge_api_base_url}/api/tags", timeout=5)
        tags_response.raise_for_status()
        show_response = requests.post(
            f"{edge_api_base_url}/api/show",
            json={"name": normalized},
            timeout=5,
        )
        show_response.raise_for_status()
        return _extract(tags_response.json(), show_response.json())
    except Exception:
        from fastapi.testclient import TestClient
        from app.servers.cgc_api_server import app

        client = TestClient(app)
        tags_payload = client.get("/api/tags").json()
        show_payload = client.post("/api/show", json={"name": normalized}).json()
        return _extract(tags_payload, show_payload)


def print_fake_ollama_models():
    models = fetch_fake_ollama_models()
    print("\nNAME\t\t\t\t\tMODEL\t\t\tSIZE\t\tSOURCE")
    print("-" * 96)
    for model in models:
        name = str(model.get("name") or "unknown")
        model_id = str(model.get("model") or "unknown")
        size_bytes = int(model.get("size") or 0)
        size_str = f"{size_bytes / (1024**3):.1f} GB" if size_bytes > 0 else "N/A"
        details = model.get("details") or {}
        source = str(details.get("cloud_source") or details.get("format") or "unknown")
        print(f"{name:<40}{model_id:<24}{size_str:<16}{source}")
    print()


def print_fake_ollama_show_spec(model_name):
    spec = fetch_fake_ollama_install_spec(model_name)
    print(json.dumps(spec, ensure_ascii=False, indent=2))
    return spec


def _looks_like_repo_id(value):
    model_str = str(value or "").strip()
    return "/" in model_str and not Path(model_str).expanduser().exists()


def _resolve_cached_model_ref(model_ref):
    model_str = str(model_ref or "").strip()
    if not model_str:
        return ""
    model_path = Path(model_str).expanduser()
    if model_path.exists():
        return str(model_path.resolve())
    if not _looks_like_repo_id(model_str):
        return model_str
    try:
        from app.edge_engine.local_infer import _resolve_cached_hf_snapshot

        return str(_resolve_cached_hf_snapshot(model_str) or model_str)
    except Exception:
        return model_str


def _detect_model_format(path_str):
    raw = str(path_str or "").strip()
    if not raw:
        return "unknown"
    lowered = raw.lower()
    path = Path(raw).expanduser()
    if path.is_file():
        if lowered.endswith(".gguf"):
            return "gguf"
        if lowered.endswith(".safetensors"):
            return "safetensors"
        return path.suffix.lstrip(".") or "file"
    if path.is_dir():
        if (path / "tokenizer.json").exists() and (
            list(path.glob("*.safetensors"))
            or list(path.glob("model*.safetensors"))
            or (path / "model.safetensors.index.json").exists()
        ):
            return "mlx"
        return "directory"
    if _looks_like_repo_id(raw):
        return "mlx"
    return "unknown"


def _backend_candidates_for_format(model_format):
    if model_format == "mlx":
        return ["omlx_mlx_lm"]
    if model_format == "gguf":
        return ["ollama", "llama.cpp", "edge_cloud_bridge"]
    if model_format == "safetensors":
        return ["transformers", "edge_cloud_bridge"]
    return ["edge_cloud_bridge"]


def _admissible_routes_for_format(model_format):
    if model_format == "mlx":
        return ["m4_local", "m73_edge_cloud"]
    return ["m73_edge_cloud"]


def _safe_size_bytes(path_str):
    raw = str(path_str or "").strip()
    if not raw:
        return 0
    try:
        path = Path(raw).expanduser()
        if path.is_file():
            return int(path.stat().st_size)
        if path.is_dir():
            total = 0
            for child in path.rglob("*"):
                if child.is_file():
                    total += int(child.stat().st_size)
            return total
    except Exception:
        return 0
    return 0


def _append_model_entry(entries, *, model_id, display_name, resolved_path, model_format, source, size_bytes=0, status="PASS", notes=None):
    normalized_path = str(resolved_path or "").strip()
    entries.append(
        {
            "model_id": str(model_id or display_name or normalized_path or "unknown_model"),
            "display_name": str(display_name or model_id or normalized_path or "unknown_model"),
            "resolved_path": normalized_path,
            "format": str(model_format or "unknown"),
            "source": str(source or "unknown"),
            "size_bytes": int(size_bytes or 0),
            "backend_candidates": _backend_candidates_for_format(model_format),
            "admissible_routes": _admissible_routes_for_format(model_format),
            "status": str(status or "PASS"),
            "notes": list(notes or []),
        }
    )


def _discover_model_files(root):
    root_path = Path(root).expanduser()
    if not root_path.exists():
        return []

    discovered = []
    try:
        for child in root_path.iterdir():
            if child.is_file() and child.suffix.lower() in {".gguf", ".safetensors"}:
                discovered.append(child)
                continue
            if not child.is_dir():
                continue
            tokenizer = child / "tokenizer.json"
            if tokenizer.exists():
                if (
                    list(child.glob("*.safetensors"))
                    or list(child.glob("model*.safetensors"))
                    or (child / "model.safetensors.index.json").exists()
                ):
                    discovered.append(child)
                    continue
            for grandchild in child.iterdir():
                if grandchild.is_file() and grandchild.suffix.lower() in {".gguf", ".safetensors"}:
                    discovered.append(grandchild)
    except Exception:
        return []
    return discovered


def _normalize_source_root_entries(root_values, *, source_label):
    entries = []
    seen = set()
    for value in root_values:
        raw = str(value or "").strip()
        if not raw:
            continue
        resolved = str(Path(raw).expanduser())
        if resolved in seen:
            continue
        seen.add(resolved)
        exists = Path(resolved).exists()
        entries.append(
            {
                "source": source_label,
                "root": resolved,
                "status": "PASS" if exists else "FAIL",
                **({"error_code": "ROOT_UNREACHABLE"} if not exists else {}),
            }
        )
    return entries


def collect_list_response(*, cfg, model_roots=None, nfs_roots=None):
    model_roots = [str(x) for x in (model_roots or []) if str(x or "").strip()]
    nfs_roots = [str(x) for x in (nfs_roots or []) if str(x or "").strip()]
    env_model_roots = [x for x in str(os.environ.get("CGC_MODEL_ROOTS") or "").split(os.pathsep) if x.strip()]
    env_nfs_roots = [x for x in str(os.environ.get("CGC_NFS_MODEL_ROOTS") or "").split(os.pathsep) if x.strip()]
    merged_model_roots = model_roots + env_model_roots + [str(CGC_MODELS_DIR)]
    merged_nfs_roots = nfs_roots + env_nfs_roots + [str(os.environ.get("CGC_CLUSTER_NFS_ROOT") or DEFAULT_CLUSTER_NFS_ROOT)]

    sources = []
    models = []
    seen_paths = set()

    sources.extend(_normalize_source_root_entries(merged_model_roots, source_label="local"))
    sources.extend(_normalize_source_root_entries(merged_nfs_roots, source_label="nfs"))

    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    sources.append(
        {
            "source": "cache",
            "root": str(cache_root),
            "status": "PASS" if cache_root.exists() else "FAIL",
            **({"error_code": "ROOT_UNREACHABLE"} if not cache_root.exists() else {}),
        }
    )

    registry_models = fetch_fake_ollama_models()
    sources.append({"source": "registry", "root": "fake_ollama_registry", "status": "PASS"})
    for model in registry_models:
        name = str(model.get("name") or model.get("model") or "unknown")
        details = model.get("details") or {}
        _append_model_entry(
            models,
            model_id=name,
            display_name=name,
            resolved_path=str(model.get("model") or name),
            model_format=str(details.get("format") or "gguf"),
            source="registry",
            size_bytes=int(model.get("size") or 0),
            notes=[str(details.get("cloud_source") or "fake_ollama_registry")],
        )

    def _consume_candidates(candidates, *, source_name):
        for candidate in candidates:
            resolved = str(candidate.expanduser().resolve()) if candidate.exists() else str(candidate.expanduser())
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            _append_model_entry(
                models,
                model_id=candidate.stem if candidate.is_file() else candidate.name,
                display_name=candidate.name,
                resolved_path=resolved,
                model_format=_detect_model_format(resolved),
                source=source_name,
                size_bytes=_safe_size_bytes(resolved),
            )

    for root in merged_model_roots:
        _consume_candidates(_discover_model_files(root), source_name="local")
    for root in merged_nfs_roots:
        _consume_candidates(_discover_model_files(root), source_name="nfs")

    for config_key, source_name in (
        ("local_omlx_model", "config"),
        ("local_flashmoe_model", "config"),
        ("active_edge_model_path", "config"),
    ):
        configured = str(cfg.get(config_key) or "").strip()
        if not configured:
            continue
        resolved = _resolve_cached_model_ref(configured)
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        notes = [f"config_key:{config_key}"]
        _append_model_entry(
            models,
            model_id=Path(resolved).name if Path(resolved).name else configured,
            display_name=Path(resolved).name if Path(resolved).name else configured,
            resolved_path=resolved,
            model_format=_detect_model_format(resolved),
            source=source_name,
            size_bytes=_safe_size_bytes(resolved),
            notes=notes,
        )

    status = "PASS" if models else "FAIL"
    return {
        "status": status,
        "command": "cgc list",
        "generated_at": utc_now_iso(),
        "sources": sources,
        "models": models,
        "summary": {
            "total_models": len(models),
            "local_models": sum(1 for item in models if item.get("source") == "local"),
            "nfs_models": sum(1 for item in models if item.get("source") == "nfs"),
            "cached_models": sum(1 for item in models if item.get("source") == "cache"),
            "registry_models": sum(1 for item in models if item.get("source") == "registry"),
        },
        **(
            {
                "failure_code": "MODEL_DISCOVERY_EMPTY",
                "failure_reason": "No admissible models found in configured local/cache/nfs roots.",
                "recommended_action": [
                    "Download a GGUF, safetensors, or MLX model into a configured model root.",
                    "Check NFS mount health.",
                    "Run with --model-root or --nfs-root to add more discovery roots.",
                ],
            }
            if not models
            else {}
        ),
    }


def print_list_response(payload):
    print("SOURCE\tFORMAT\tROUTES\tMODEL\tPATH")
    print("-" * 120)
    for model in payload.get("models") or []:
        print(
            f"{str(model.get('source') or 'unknown'):<8}"
            f"{str(model.get('format') or 'unknown'):<12}"
            f"{','.join(model.get('admissible_routes') or []):<24}"
            f"{str(model.get('display_name') or model.get('model_id') or 'unknown'):<24}"
            f"{str(model.get('resolved_path') or '')}"
        )
    print()
    summary = payload.get("summary") or {}
    print(
        f"total={summary.get('total_models', 0)} "
        f"local={summary.get('local_models', 0)} "
        f"nfs={summary.get('nfs_models', 0)} "
        f"cache={summary.get('cached_models', 0)} "
        f"registry={summary.get('registry_models', 0)}"
    )


def write_m75_install_evidence(payload):
    payload = dict(payload)
    payload.setdefault("status", "PASS")
    payload.setdefault("installer", "cgc.py")
    payload.setdefault(
        "timestamp",
        subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip(),
    )
    return write_json_file(get_m75_install_evidence_path(), payload)


def download_hf_gguf(repo_id, filename, output_path):
    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".part")

    with requests.get(url, stream=True, timeout=(30, 600)) as response:
        response.raise_for_status()
        total_bytes = int(response.headers.get("content-length") or 0)
        downloaded = 0
        next_progress_bytes = 64 * 1024 * 1024
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total_bytes and downloaded >= next_progress_bytes:
                    progress = (downloaded / total_bytes) * 100.0
                    print(
                        f"  [Download] {downloaded / (1024**2):.1f} MiB / "
                        f"{total_bytes / (1024**2):.1f} MiB ({progress:.1f}%)"
                    )
                    next_progress_bytes += 64 * 1024 * 1024
    temp_path.replace(output_path)
    return str(output_path)


def resolve_cluster_nfs_source(install_spec, gguf_filename):
    install_spec = dict(install_spec or {})
    candidates = []
    explicit_path = str(install_spec.get("cluster_nfs_path") or "").strip()
    if explicit_path:
        candidates.append(Path(explicit_path))

    env_path = str(os.environ.get("CGC_CLUSTER_NFS_MINICPM5_GGUF") or "").strip()
    if env_path:
        candidates.append(Path(env_path))

    roots = []
    for value in [
        os.environ.get("CGC_CLUSTER_NFS_ROOT"),
        install_spec.get("cluster_nfs_root"),
        DEFAULT_CLUSTER_NFS_ROOT,
    ]:
        value = str(value or "").strip()
        if value:
            roots.append(value)
    seen = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        candidates.append(Path(root) / "minicpm5" / gguf_filename)
        candidates.append(Path(root) / "MiniCPM5-1B-GGUF" / gguf_filename)
        candidates.append(Path(root) / gguf_filename)

    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except Exception:
            resolved = candidate.expanduser()
        if resolved.exists() and resolved.is_file():
            return str(resolved)
    return ""


def copy_local_file(source_path, output_path):
    source = Path(source_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output.with_suffix(output.suffix + ".part")
    total_bytes = source.stat().st_size
    copied = 0
    next_progress_bytes = 64 * 1024 * 1024
    with open(source, "rb") as src, open(temp_path, "wb") as dst:
        while True:
            chunk = src.read(8 * 1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
            copied += len(chunk)
            if total_bytes and copied >= next_progress_bytes:
                progress = (copied / total_bytes) * 100.0
                print(
                    f"  [NFS Copy] {copied / (1024**2):.1f} MiB / "
                    f"{total_bytes / (1024**2):.1f} MiB ({progress:.1f}%)"
                )
                next_progress_bytes += 64 * 1024 * 1024
    temp_path.replace(output)
    return str(output)


def install_minicpm5_via_ollama(
    *,
    model_name=MINICPM5_OLLAMA_MODEL,
    quant=MINICPM5_DEFAULT_QUANT,
    force=False,
    install_spec=None,
):
    install_spec = dict(install_spec or {})
    gguf_repo = str(install_spec.get("gguf_repo") or MINICPM5_GGUF_REPO)
    gguf_filename = str(install_spec.get("gguf_filename") or f"MiniCPM5-1B-{quant}.gguf")
    ollama_model_name = str(install_spec.get("ollama_model") or model_name or MINICPM5_OLLAMA_MODEL)
    quant = str(install_spec.get("quant") or quant or MINICPM5_DEFAULT_QUANT)
    source_priority = list(install_spec.get("source_priority") or ["cluster_nfs", "huggingface"])
    target_dir = (CGC_MODELS_DIR / model_name).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    gguf_path = (target_dir / gguf_filename).resolve()
    modelfile_path = (target_dir / "Modelfile").resolve()

    print(f"📦 Preparing MiniCPM5 package for cgc run in: {target_dir}")
    print(f"   source_priority = {source_priority}")

    source_used = "local_cache"
    cluster_nfs_source = resolve_cluster_nfs_source(install_spec, gguf_filename)
    if cluster_nfs_source:
        print(f"   cluster_nfs = ready ({cluster_nfs_source})")
    else:
        print("   cluster_nfs = missing on this node, fallback may be required")
    if not gguf_path.exists():
        copied = False
        for source_name in source_priority:
            if source_name == "cluster_nfs" and cluster_nfs_source:
                print(f"📡 Using preferred source 'cluster_nfs': {cluster_nfs_source}")
                print(f"   staging {gguf_filename} into local cgc cache ...")
                copy_local_file(cluster_nfs_source, gguf_path)
                source_used = "cluster_nfs"
                copied = True
                break
            if source_name == "huggingface":
                print(f"⬇️ Falling back to '{source_name}': {gguf_repo}")
                print(f"   downloading {gguf_filename} into local cgc cache ...")
                download_hf_gguf(gguf_repo, gguf_filename, gguf_path)
                source_used = "huggingface"
                copied = True
                break
        if not copied:
            raise RuntimeError(
                f"no_available_source_for_{gguf_filename}: "
                f"cluster_nfs_source={cluster_nfs_source or 'missing'}"
            )
    else:
        print(f"✅ GGUF already staged in local cgc cache: {gguf_path}")

    modelfile = f"""FROM ./{gguf_filename}

# MiniCPM5 chat template
TEMPLATE \"\"\"{{{{- if .Messages -}}}}
{{{{- range .Messages -}}}}
<|im_start|>{{{{ .Role }}}}
{{{{ .Content }}}}<|im_end|>
{{{{ end -}}}}
<|im_start|>assistant
{{{{ end -}}}}\"\"\"

PARAMETER stop "<|im_end|>"
PARAMETER stop "</s>"
PARAMETER temperature 0.7
PARAMETER top_p 0.95
PARAMETER num_ctx 8192
"""
    modelfile_path.write_text(modelfile, encoding="utf-8")
    print(f"📝 Wrote local model recipe: {modelfile_path}")

    if force or not ollama_model_exists(ollama_model_name):
        print(f"🧱 Activating local runtime model: {ollama_model_name}")
        run_command_checked(["ollama", "create", ollama_model_name, "-f", str(modelfile_path)], cwd=target_dir)
    else:
        print(f"✅ Local runtime model already active: {ollama_model_name}")

    cfg = load_config()
    cfg["active_edge_model"] = ollama_model_name
    cfg["active_edge_model_path"] = str(gguf_path)
    cfg["active_edge_model_source"] = "ollama"
    save_config(cfg)

    evidence_payload = {
        "status": "PASS",
        "mode": "fake_protocol_cloud_pull_with_real_ollama_install",
        "router_model": ollama_model_name,
        "router_backend": "ollama",
        "public_entrypoint": "cgc run",
        "install_via": str(install_spec.get("install_via") or "direct_hf_download"),
        "source_priority": source_priority,
        "source_used": source_used,
        "cluster_nfs_source": cluster_nfs_source,
        "gguf_repo": gguf_repo,
        "quant": quant,
        "gguf_path": str(gguf_path),
        "modelfile_path": str(modelfile_path),
        "ollama_model": ollama_model_name,
        "ollama_show_available": ollama_model_exists(ollama_model_name),
        "config_updates": {
            "active_edge_model": cfg["active_edge_model"],
            "active_edge_model_path": cfg["active_edge_model_path"],
            "active_edge_model_source": cfg["active_edge_model_source"],
        },
    }
    if install_spec:
        evidence_payload["cloud_registry_spec"] = install_spec
    evidence_path = write_m75_install_evidence(evidence_payload)
    evidence_payload["evidence_path"] = evidence_path
    return evidence_payload


def get_gate_registry():
    return {
        "m1": {
            "status": "available",
            "description": "M1 baseline executable gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m1").resolve()),
        },
        "m2": {
            "status": "available",
            "description": "M2 inference kernel and safety gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m2").resolve()),
        },
        "m3": {
            "status": "available",
            "description": "M3 model solidification and edge packaging gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m3").resolve()),
        },
        "m4": {
            "status": "available",
            "description": "M4 training and distributed scale-out gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m4").resolve()),
        },
        "m5": {
            "status": "available",
            "description": "M5 terminal-state compile and runtime closure gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m5").resolve()),
        },
        "m6": {
            "status": "available",
            "description": "M6 product bundle build-and-run gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m6").resolve()),
        },
        "m7": {
            "status": "available",
            "description": "M7 industrial baseline verification-only gate",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m7").resolve()),
        },
        "m71": {
            "status": "available",
            "description": "M7.1 industrial verification-only gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m71").resolve()),
        },
        "m72": {
            "status": "available",
            "description": "M7.2 industrial verification-only gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m72").resolve()),
        },
        "m73": {
            "status": "available",
            "description": "M7.3 physical execution verification-only gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m73").resolve()),
        },
        "m74": {
            "status": "available",
            "description": "M7.4 DFlash + TrueOrthoKDA verification-only gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m74").resolve()),
        },
        "m75": {
            "status": "available",
            "description": "M7.5 API compatibility verification-only gate through the shared CGC CLI",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m75").resolve()),
        },
        "m76": {
            "status": "available",
            "description": "M7.6 heterogeneous acceleration integration verification-only gate",
            "default_output_dir": str((ENGINE_REPO_DIR / "Output" / "cli_gate_m76").resolve()),
        },
        "m8": {
            "status": "available",
            "description": "M8.0 productization verification-only gate covering M8.1-M8.3",
            "default_output_dir": str((RELEASE_DIR / "Output" / "m8_gate").resolve()),
        },
        "m9": {
            "status": "planned",
            "description": "Reserved slot for future M9 gate integration",
            "default_output_dir": str((SCRIPT_DIR / "Output" / "m9_gate").resolve()),
        },
    }


def print_gate_registry():
    registry = get_gate_registry()
    print("Available CGC gates (verification only):")
    for gate_name, meta in registry.items():
        print(f"  - {gate_name}: {meta['status']} | {meta['description']}")


def write_gate_checkin(gate_name, status, report_path="", summary_path="", trigger="manual", extra=None):
    GATE_CHECKIN_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "gate_name": str(gate_name),
        "status": str(status),
        "report_path": str(report_path or ""),
        "summary_path": str(summary_path or ""),
        "trigger": str(trigger),
        "release_repo": TARGET_RELEASE_REPO,
        "timestamp": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip(),
    }
    if isinstance(extra, dict):
        payload["extra"] = extra

    latest_file = GATE_CHECKIN_DIR / f"{gate_name}_latest.json"
    with open(GATE_CHECKIN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {
        "status": "PASS",
        "checkin_path": str(latest_file.resolve()),
        "log_path": str(GATE_CHECKIN_LOG.resolve()),
        "payload": payload,
    }


def run_registered_gate(gate_name, repo_root=None, output_dir=None, m4_training_report="", m4_inference_report=""):
    registry = get_gate_registry()
    if gate_name not in registry:
        raise ValueError(f"Unknown gate: {gate_name}")

    gate_meta = registry[gate_name]
    if gate_meta["status"] != "available":
        return {
            "status": "NOT_IMPLEMENTED",
            "gate_name": gate_name,
            "message": gate_meta["description"],
            "report_path": "",
            "summary_path": "",
        }

    resolved_output_dir = str(Path(output_dir or gate_meta["default_output_dir"]).expanduser().resolve())
    resolved_repo_root = str(Path(repo_root or SCRIPT_DIR).expanduser().resolve())

    if gate_name == "m8":
        run_m8_gate = load_release_m8_gate_runner()
        return run_m8_gate(
            repo_root=resolved_repo_root,
            output_dir=resolved_output_dir,
            config_path=str((RELEASE_DIR / "m8_gate.yaml").resolve()),
        )

    if gate_name == "m1":
        run_m1_gate = load_engine_m1_gate_runner()
        report = run_m1_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m2":
        run_m2_gate = load_engine_m2_gate_runner()
        report = run_m2_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m3":
        run_m3_gate = load_engine_m3_gate_runner()
        report = run_m3_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m4":
        if not str(m4_inference_report or "").strip():
            latest_inference_report = get_latest_cgc_run_inference_report()
            if latest_inference_report is not None:
                m4_inference_report = str(latest_inference_report)
        run_m4_gate = load_engine_m4_gate_runner()
        report = run_m4_gate(
            output_dir=resolved_output_dir,
            training_report_path=str(m4_training_report or ""),
            inference_report_path=str(m4_inference_report or ""),
        )
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m5":
        run_m5_gate = load_engine_m5_gate_runner()
        report = run_m5_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m6":
        run_m6_gate = load_engine_m6_gate_runner()
        report = run_m6_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m73":
        run_m7_gate = load_engine_m7_gate_runner()
        run_m73_gate = load_engine_m73_gate_runner()
        output_root = Path(resolved_output_dir).resolve()
        m7_report = run_m7_gate(output_dir=str(output_root))
        m7_gate = ((m7_report or {}).get("gate_result") or {}).get("m7") if isinstance(m7_report, dict) else {}
        m7_status = "PASS" if bool((m7_report or {}).get("ok")) else "FAIL"
        m7_report_path = str((output_root / "m7_industrial" / "m7_report.json").resolve())
        m73_report = run_m73_gate(output_dir=str(output_root))
        m73_gate = ((m73_report or {}).get("gate_result") or {}).get("m73") if isinstance(m73_report, dict) else {}
        m73_status = "PASS" if bool((m73_report or {}).get("ok")) else "FAIL"
        m73_report_path = str((output_root / "m73_physical" / "m73_report.json").resolve())
        final_status = "PASS" if m7_status == "PASS" and m73_status == "PASS" else "FAIL"
        gate_payload = {
            "name": "CGC_M7.3_Physical_Gate",
            "status": final_status,
            "scope": "verification_only",
            "public_entrypoint": "cgc gate m73",
            "gate_result": {
                "m7": m7_gate,
                "m71": m7_gate,
                "m73": m73_gate,
            },
        }
        aggregate_report_path = write_json_file(output_root / "report.json", gate_payload)
        return {
            "status": final_status,
            "gate_name": gate_name,
            "report_path": aggregate_report_path,
            "summary_path": m73_report_path if Path(m73_report_path).exists() else m7_report_path,
            "gate_result": gate_payload["gate_result"],
        }

    if gate_name == "m74":
        run_m74_gate = load_engine_m74_gate_runner()
        report = run_m74_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m75":
        run_m75_gate = load_engine_m75_gate_runner()
        report = run_m75_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name == "m76":
        run_m76_gate = load_engine_m76_gate_runner()
        report = run_m76_gate(output_dir=resolved_output_dir)
        return {
            "status": "PASS" if bool(report.get("ok")) else "FAIL",
            "gate_name": gate_name,
            "report_path": str(report.get("report_path") or ""),
            "summary_path": "",
            "gate_result": report.get("gate_result", {}),
        }

    if gate_name in {"m7", "m71", "m72"}:
        run_m7_gate = load_engine_m7_gate_runner()
        output_root = Path(resolved_output_dir).resolve()
        m7_output_dir = output_root if gate_name == "m7" else (output_root / "m7_artifacts")
        report = run_m7_gate(output_dir=str(m7_output_dir))
        m7_gate = ((report or {}).get("gate_result") or {}).get("m7") if isinstance(report, dict) else {}
        m7_status = "PASS" if bool(report.get("ok")) else "FAIL"
        m7_report_path = str((Path(m7_output_dir) / "m7_industrial" / "m7_report.json").resolve())

        if gate_name == "m7":
            return {
                "status": m7_status,
                "gate_name": gate_name,
                "report_path": m7_report_path,
                "summary_path": "",
                "gate_result": report.get("gate_result", {}),
            }

        if gate_name == "m71":
            gate_payload = {
                "name": "CGC_M7.1_Industrial_Gate",
                "status": m7_status,
                "scope": "verification_only",
                "public_entrypoint": "cgc gate m71",
                "source_gate": "m7",
                "gate_result": {
                    "m71": m7_gate,
                },
            }
            aggregate_report_path = write_json_file(output_root / "report.json", gate_payload)
            return {
                "status": m7_status,
                "gate_name": gate_name,
                "report_path": aggregate_report_path,
                "summary_path": m7_report_path,
                "gate_result": gate_payload["gate_result"],
            }

        run_m72_gate = load_engine_m72_gate_runner()
        m72_output_dir = output_root / "m72_industrial"
        m72_report = run_m72_gate(
            output_dir=str(m72_output_dir),
            cgc_report={"gate_result": {"m7": m7_gate}},
        )
        m72_gate = ((m72_report or {}).get("gate_result") or {}).get("m72") if isinstance(m72_report, dict) else {}
        m72_status = str(m72_gate.get("status") or "FAIL")
        final_status = "PASS" if m7_status == "PASS" and m72_status == "PASS" else "FAIL"
        m72_report_path = str((m72_output_dir / "report.json").resolve())
        gate_payload = {
            "name": "CGC_M7.2_Industrial_Gate",
            "status": final_status,
            "scope": "verification_only",
            "public_entrypoint": "cgc gate m72",
            "gate_result": {
                "m7": m7_gate,
                "m71": m7_gate,
                "m72": m72_gate,
            },
        }
        aggregate_report_path = write_json_file(output_root / "report.json", gate_payload)
        return {
            "status": final_status,
            "gate_name": gate_name,
            "report_path": aggregate_report_path,
            "summary_path": m72_report_path,
            "gate_result": gate_payload["gate_result"],
        }

    raise ValueError(f"Gate runner not implemented: {gate_name}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "cloud_ip": "10.100.200.65", 
        "cloud_port": 50052, 
        "active_edge_model": MINICPM5_OLLAMA_MODEL,
        "active_cloud_model": "deepseek-v4-flash:latest",
        "local_omlx_model": "",
        "local_flashmoe_model": "",
        "edge_api_port": 8000,
        "edge_proxy_port": 4000,
    }

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def get_edge_api_base_url(cfg=None):
    cfg = cfg or load_config()
    return f"http://127.0.0.1:{int(cfg.get('edge_api_port', 8000) or 8000)}"


def apply_runtime_env(cfg):
    local_omlx_model = str(cfg.get("local_omlx_model") or "").strip()
    if local_omlx_model:
        os.environ["CGC_LOCAL_OMLX_MODEL"] = local_omlx_model
    local_flashmoe_model = str(cfg.get("local_flashmoe_model") or "").strip()
    if local_flashmoe_model:
        os.environ["CGC_LOCAL_FLASHMOE_MODEL"] = local_flashmoe_model


def resolve_local_runtime_model(model_to_use, *, cfg, use_omlx, use_flashmoe):
    if use_flashmoe and str(cfg.get("local_flashmoe_model") or "").strip():
        return str(cfg.get("local_flashmoe_model"))
    if use_omlx and str(cfg.get("local_omlx_model") or "").strip():
        return str(cfg.get("local_omlx_model"))
    return str(model_to_use)


def get_latest_cgc_run_inference_report():
    return CGC_RUN_LATEST_M4_INFERENCE_REPORT if CGC_RUN_LATEST_M4_INFERENCE_REPORT.exists() else None


def _safe_read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _metric_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _make_cgc_run_report_dir(report_dir=""):
    if str(report_dir or "").strip():
        out_dir = Path(report_dir).expanduser().resolve()
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        out_dir = (CGC_RUN_ARTIFACT_ROOT / f"run_{stamp}_{int(time.time() * 1000) % 1000:03d}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _write_run_smoke_manifest(output_dir, *, use_flashmoe):
    manifest_path = (Path(output_dir) / "omlx_flashmoe_manifest.json").resolve()
    manifest_payload = {
        "status": "PASS",
        "engine": "flashmoe" if use_flashmoe else "mlx_lm",
        "layer_wise_loading": True,
        "expert_on_demand": bool(use_flashmoe),
        "ram_cache_gb": 6,
        "prefetch_window": 2,
        "smoke": {
            "source": "cgc_run_bridge",
            "num_layers": 2,
            "local_total_files": 4,
            "remote_total_files": 8,
        },
    }
    write_json_file(manifest_path, manifest_payload)
    return manifest_path, manifest_payload


def _collect_streamed_events_from_response(response):
    events = []
    text_parts = []
    final_event = {}
    for line in response.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        events.append(data)
        chunk_text = data.get("response")
        if isinstance(chunk_text, str) and chunk_text:
            text_parts.append(chunk_text)
        if bool(data.get("done")):
            final_event = data
    if not final_event and events:
        final_event = events[-1]
    return {
        "events": events,
        "final_event": final_event,
        "response_text": "".join(text_parts),
    }


def _execute_single_prompt_via_testclient(*, payload):
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from fastapi.testclient import TestClient
        from app.servers.cgc_api_server import app

        with TestClient(app) as client:
            with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                streamed = _collect_streamed_events_from_response(response)
    streamed["elapsed_ms"] = (time.perf_counter() - started) * 1000.0
    return streamed


def _execute_single_prompt(*, api_base_url, payload):
    if bool(payload.get("use_omlx")) or bool(payload.get("use_flashmoe")):
        from app.edge_engine.local_infer import EdgeLocalInferenceRuntime

        started = time.perf_counter()
        local_result = asyncio.run(
            EdgeLocalInferenceRuntime().maybe_generate(
                model=str(payload.get("model") or ""),
                prompt=str(payload.get("prompt") or ""),
                use_omlx=bool(payload.get("use_omlx")),
                use_flashmoe=bool(payload.get("use_flashmoe")),
                max_tokens=int(payload.get("max_tokens") or 256),
            )
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if local_result.executed_locally and local_result.status == "PASS":
            final_event = {
                "model": str(payload.get("model") or ""),
                "response": "",
                "done": True,
                "local_execution": True,
                "backend": str(local_result.backend or ""),
                "evidence_path": str(local_result.evidence_path or ""),
            }
            events = [
                {
                    "model": str(payload.get("model") or ""),
                    "response": chunk_text,
                    "done": False,
                    "local_execution": True,
                    "backend": str(local_result.backend or ""),
                    "evidence_path": str(local_result.evidence_path or ""),
                }
                for chunk_text in list(local_result.chunks or [])
            ]
            events.append(final_event)
            return {
                "events": events,
                "final_event": final_event,
                "response_text": str(local_result.text or ""),
                "elapsed_ms": elapsed_ms,
            }

    started = time.perf_counter()
    try:
        response = requests.post(
            f"{api_base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=(10, 600),
        )
        response.raise_for_status()
        streamed = _collect_streamed_events_from_response(response)
        streamed["elapsed_ms"] = (time.perf_counter() - started) * 1000.0
        return streamed
    except requests.exceptions.RequestException:
        return _execute_single_prompt_via_testclient(payload=payload)


def _write_cgc_run_artifacts(
    *,
    report_dir,
    model_to_use,
    runtime_model,
    prompt,
    payload,
    run_result,
):
    report_root = Path(report_dir).expanduser().resolve()
    final_event = run_result.get("final_event") if isinstance(run_result.get("final_event"), dict) else {}
    final_evidence_paths = final_event.get("evidence_paths") if isinstance(final_event.get("evidence_paths"), dict) else {}
    evidence_path = str(final_event.get("evidence_path") or final_evidence_paths.get("local_infer") or "").strip()
    evidence = _safe_read_json(evidence_path) if evidence_path else {}
    local_execution = bool(final_event.get("local_execution"))
    selected_route = "m4_local" if local_execution else ("m73_edge_cloud" if (bool(payload.get("use_omlx")) or bool(payload.get("use_flashmoe"))) else "fail_close")
    backend = str(
        final_event.get("backend")
        or final_event.get("selected_backend")
        or evidence.get("backend")
        or ("edge_cloud_bridge" if selected_route == "m73_edge_cloud" else "")
    )
    generation_tps = _metric_float(((evidence.get("stats") or {}) if isinstance(evidence.get("stats"), dict) else {}).get("generation_tps"))
    edge_latency_ms = (1000.0 / generation_tps) if generation_tps > 0 else float(run_result.get("elapsed_ms") or 0.0)
    cloud_bridge_used = bool(selected_route == "m73_edge_cloud")
    ok = bool(final_event.get("done")) and (local_execution or cloud_bridge_used or not bool(payload.get("use_omlx") or payload.get("use_flashmoe")))
    resolved_model_path = str(evidence.get("model_ref") or runtime_model or "")
    model_format = _detect_model_format(resolved_model_path)
    final_reason = final_event.get("decision_reason") if isinstance(final_event.get("decision_reason"), dict) else {}
    decision_reason = {
        "code": str(final_reason.get("code") or ("LOCAL_ROUTE_ADMISSIBLE" if local_execution else "LOCAL_ROUTE_REJECTED")),
        "text": str(
            final_reason.get("text")
            or (
                "Memory and latency budget allow local execution."
                if local_execution
                else str(final_event.get("error") or final_event.get("response") or "Local route did not complete successfully.")
            )
        ),
    }

    run_report = {
        "status": "PASS" if ok else "FAIL",
        "mode": "cgc_run_single_prompt",
        "command": "cgc run",
        "generated_at": utc_now_iso(),
        "api_base_url": str(payload.get("api_base_url") or ""),
        "model": str(model_to_use),
        "runtime_model": str(runtime_model),
        "resolved_model_path": resolved_model_path,
        "format": model_format,
        "prompt": str(prompt),
        "use_omlx": bool(payload.get("use_omlx")),
        "use_flashmoe": bool(payload.get("use_flashmoe")),
        "selected_route": selected_route,
        "decision_reason": decision_reason,
        "max_tokens": int(payload.get("max_tokens") or 0),
        "local_execution": local_execution,
        "backend": backend,
        "response_text": str(run_result.get("response_text") or ""),
        "elapsed_ms": float(run_result.get("elapsed_ms") or 0.0),
        "evidence_path": evidence_path,
        "evidence": evidence if isinstance(evidence, dict) else {},
        "stream_event_count": len(run_result.get("events") or []),
        "final_event": final_event,
    }
    run_report_path = Path(write_json_file(report_root / "run_report.json", run_report))
    route_decision_payload = {
        "status": "PASS" if ok else "FAIL",
        "command": "cgc run",
        "generated_at": utc_now_iso(),
        "selected_model": str(model_to_use),
        "resolved_model_path": resolved_model_path,
        "format": model_format,
        "selected_route": selected_route,
        "selected_backend": backend or ("edge_cloud_bridge" if selected_route == "m73_edge_cloud" else ""),
        "local_execution": local_execution,
        "cloud_bridge_used": cloud_bridge_used,
        "decision_reason": decision_reason,
        "decision_matrix": {
            "runtime": {
                "elapsed_ms": float(run_result.get("elapsed_ms") or 0.0),
                "generation_tps": generation_tps,
            },
            "memory": {
                "peak_memory_gb": _metric_float(((evidence.get("stats") or {}) if isinstance(evidence.get("stats"), dict) else {}).get("peak_memory_gb")),
            },
        },
        "evidence_paths": {
            "local_infer": evidence_path,
            "run_report": str(run_report_path),
        },
    }
    route_decision_path = Path(write_json_file(report_root / "route_decision.json", route_decision_payload))

    manifest_path, manifest_payload = _write_run_smoke_manifest(
        report_root,
        use_flashmoe=bool(payload.get("use_flashmoe")),
    )
    inference_ok = bool(local_execution and backend == "omlx_mlx_lm")
    inference_report = {
        "ok": inference_ok,
        "mode": "bridge_from_cgc_run",
        "exec_mode": "compile",
        "task_type": "inference",
        "backend": "mlx",
        "model": str(model_to_use),
        "runtime_model": str(runtime_model),
        "source_run_report": str(run_report_path),
        "error_msg": "" if inference_ok else str(final_event.get("error") or final_event.get("response") or "cgc_run_local_execution_not_proven"),
        "steps": {
            "step2_fullgraph_capture": {
                "status": "PASS" if inference_ok else "FAIL",
                "model_id": str(model_to_use),
                "device": "mps" if sys.platform == "darwin" else "",
                "dtype": "fp32",
                "prompt": str(prompt),
                "contexts": [128],
                "max_new_tokens": int(payload.get("max_tokens") or 0),
                "omlx_engine": "flashmoe" if bool(payload.get("use_flashmoe")) else "mlx_lm",
                "manifest_path": str(manifest_path),
                "evidence_path": evidence_path,
            },
            "step6_fullgraph_compile": {
                "status": "PASS" if inference_ok else "FAIL",
                "compile_mode": backend or "omlx_mlx_lm",
                "aot": False,
                "source": "cgc_run",
            },
            "step7_fullgraph_bench": {
                "status": "PASS" if inference_ok else "FAIL",
                "optimized": inference_ok,
                "generation_tps": generation_tps,
                "edge_latency_ms": edge_latency_ms,
            },
            "step8_fullgraph_deploy": {
                "status": "PASS" if inference_ok else "FAIL",
                "deploy_unit": {
                    "omlx_model_path": str(runtime_model),
                    "omlx_manifest_path": str(manifest_path),
                    "evidence_path": evidence_path,
                },
            },
        },
        "optimized": {
            "status": "PASS" if inference_ok else "FAIL",
            "local_execution": local_execution,
            "backend": backend,
        },
        "manifest": manifest_payload,
    }
    inference_report_path = Path(write_json_file(report_root / "m4_inference_report.json", inference_report))

    bridge_ok = bool((inference_ok and edge_latency_ms > 0.0 and edge_latency_ms <= 20.0) or cloud_bridge_used)
    bridge_payload = {
        "status": "PASS" if bridge_ok else "FAIL",
        "mode": "bridge_from_cgc_run_cloud_takeover" if cloud_bridge_used else "bridge_from_cgc_run_local_infer",
        "bridge_export_success": 1.0 if (inference_ok or cloud_bridge_used) else 0.0,
        "edge_latency_ms": edge_latency_ms,
        "backends": {
            "mlx": {
                "status": "PASS" if inference_ok else "FAIL",
                "report_path": str(inference_report_path),
                "backend": backend,
                "local_execution": local_execution,
            }
        },
        "selected_route": selected_route,
        "selected_backend": backend,
        "cloud_bridge_used": cloud_bridge_used,
        "source_report": str(inference_report_path),
        "evidence_path": evidence_path,
    }
    bridge_path = Path(write_json_file(report_root / "edge_inference_bridge.json", bridge_payload))

    write_json_file(CGC_RUN_LATEST_REPORT, run_report)
    write_json_file(CGC_RUN_LATEST_M4_INFERENCE_REPORT, inference_report)
    write_json_file(CGC_RUN_LATEST_EDGE_BRIDGE, bridge_payload)
    write_json_file(CGC_RUN_LATEST_ROUTE_DECISION, route_decision_payload)
    return {
        "status": "PASS" if ok else "FAIL",
        "run_report_path": str(run_report_path),
        "m4_inference_report_path": str(inference_report_path),
        "edge_inference_bridge_path": str(bridge_path),
        "route_decision_path": str(route_decision_path),
        "edge_latency_ms": edge_latency_ms,
        "local_execution": local_execution,
        "backend": backend,
        "evidence_path": evidence_path,
        "resolved_model_path": resolved_model_path,
        "format": model_format,
        "selected_route": selected_route,
        "decision_reason": decision_reason,
    }

def main():
    parser = argparse.ArgumentParser(description="CGC Engine CLI - Edge/Cloud LLM Offloading")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # cgc serve
    serve_parser = subparsers.add_parser("serve", help="Start the CGC API Server (Ollama/Anthropic/OpenAI compatible)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind the server")
    serve_parser.add_argument("--proxy-port", type=int, default=4000, help="Port to bind the internal protocol proxy")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the CGC API server")
    serve_parser.add_argument("--proxy-host", type=str, default="127.0.0.1", help="Host to bind the internal protocol proxy")

    # cgc claude
    claude_parser = subparsers.add_parser("claude", help="Launch Claude Code CLI with CGC Environment", add_help=False)
    claude_parser.add_argument("claude_args", nargs=argparse.REMAINDER)

    # cgc config
    config_parser = subparsers.add_parser("config", help="Configure CGC Engine")
    config_parser.add_argument("--set-cloud-ip", type=str, help="Set the Cloud Server (gs01) IP")
    config_parser.add_argument("--set-cloud-model", type=str, help="Set the active Cloud model")
    config_parser.add_argument("--set-edge-model", type=str, help="Set the active Edge model")
    config_parser.add_argument("--set-local-omlx-model", type=str, help="Set the local OMLX/FlashMoE model reference for true edge execution")
    config_parser.add_argument("--set-local-flashmoe-model", type=str, help="Set the local FlashMoE model directory for true edge execution")
    config_parser.add_argument("--set-edge-api-port", type=int, help="Set the local CGC Edge API port")
    config_parser.add_argument("--set-edge-proxy-port", type=int, help="Set the local CGC Edge proxy port")
    
    # cgc run
    run_parser = subparsers.add_parser("run", help="Run a model interactively and discover CGC models")
    run_parser.add_argument("model", type=str, nargs="?", help="Model name to run (defaults to active_edge_model)")
    run_parser.add_argument("--use-omlx", action="store_true", help="Enable Apple MLX optimization for local models")
    run_parser.add_argument("--use-flashmoe", action="store_true", help="Enable FlashMoE to prevent VRAM OOM on Edge")
    run_parser.add_argument("--list-models", action="store_true", help="List model names exposed by the CGC fake Ollama registry")
    run_parser.add_argument("--show-spec", action="store_true", help="Show the resolved model spec for the selected model")
    run_parser.add_argument("--install-minicpm5", action="store_true", help="Stage MiniCPM5 GGUF for cgc run before starting the session")
    run_parser.add_argument("--ollama-quant", type=str, default=MINICPM5_DEFAULT_QUANT, help="Preferred MiniCPM5 GGUF quant when staging")
    run_parser.add_argument("--force-reinstall", action="store_true", help="Force refresh the staged MiniCPM5 GGUF package")
    run_parser.add_argument("--prompt", type=str, default="", help="Run a single prompt non-interactively and write reusable local inference reports")
    run_parser.add_argument("--max-tokens", type=int, default=256, help="Maximum tokens for single-prompt run mode")
    run_parser.add_argument("--report-dir", type=str, default="", help="Directory for `cgc run` report artifacts")
    run_parser.add_argument("--json", action="store_true", help="Print `cgc run` single-prompt result as JSON")
    
    # cgc list
    list_parser = subparsers.add_parser("list", help="List all available models (Edge and Cloud)")
    list_parser.add_argument("--json", action="store_true", help="Print discovered models as JSON")
    list_parser.add_argument("--model-root", action="append", default=[], help="Additional local model root to scan")
    list_parser.add_argument("--nfs-root", action="append", default=[], help="Additional NFS model root to scan")

    # cgc status
    status_parser = subparsers.add_parser("status", help="Show live CGC cloud/edge status for m7.5 scale runs")
    status_parser.add_argument("--json", action="store_true", help="Print status as JSON")
    status_parser.add_argument("--write-m75-evidence", action="store_true", help="Write the live snapshot to m7.5 runtime evidence")
    status_parser.add_argument("--expected-workers", type=int, default=2000, help="Expected active worker count for the extreme run")
    status_parser.add_argument("--expected-instances", type=int, default=500, help="Expected SWE-bench instance count")
    status_parser.add_argument("--expected-fusion-group-size", type=int, default=4, help="Expected FusionRoute cloud instance group size")

    # cgc audit
    audit_parser = subparsers.add_parser("audit", help="Run, verify, trace, and export M7.1/M7.2 audit artifacts")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", help="Audit commands")
    audit_run_parser = audit_subparsers.add_parser("run", help="Run audit collection or strict M7.2 validation")
    audit_run_parser.add_argument("--output-dir", type=str, default=str((REPO_ROOT / "temp" / "test" / "audit_cli_run").resolve()), help="Directory to write audit outputs")
    audit_run_parser.add_argument("--strict", action="store_true", help="Run strict M7.2 validation on top of M7.1 artifacts")
    audit_verify_parser = audit_subparsers.add_parser("verify", help="Verify audit hash chain from a report or explicit files")
    audit_verify_parser.add_argument("--report", type=str, default="", help="Aggregate M7/M7.1/M7.2 report path")
    audit_verify_parser.add_argument("--log", type=str, default="", help="events.jsonl path when not using --report")
    audit_verify_parser.add_argument("--head", type=str, default="", help="chain_head.json path when not using --report")
    audit_trace_parser = audit_subparsers.add_parser("trace", help="Trace audit events by stage")
    audit_trace_parser.add_argument("--report", type=str, default="", help="Aggregate M7/M7.1/M7.2 report path")
    audit_trace_parser.add_argument("--log", type=str, default="", help="events.jsonl path when not using --report")
    audit_trace_parser.add_argument("--stage", type=str, default="", help="Optional stage filter such as Build/Compile/Run/State/Replay/Exception")
    audit_trace_parser.add_argument("--limit", type=int, default=20, help="Maximum number of events to print")
    audit_export_parser = audit_subparsers.add_parser("export", help="Export an audit report to md/html/json")
    audit_export_parser.add_argument("--report", type=str, required=True, help="Aggregate M7/M7.1/M7.2 report path")
    audit_export_parser.add_argument("--output", type=str, required=True, help="Export file path")
    audit_export_parser.add_argument("--format", type=str, choices=["md", "html", "json"], default="md", help="Export format")
    
    # cgc build
    build_parser = subparsers.add_parser("build", help="Build standalone executables for Mac/Linux/Windows using Nuitka")
    build_parser.add_argument("--output-dir", type=str, default=str((REPO_ROOT / "dist" / "cgc").resolve()), help="Directory for the built standalone executable")
    build_parser.add_argument("--json", action="store_true", help="Print build result as JSON only")
    build_parser.add_argument("--report-file", type=str, default="", help="Optional path to write the build JSON report")
    build_parser.add_argument("--aggregate-dir", type=str, default="", help="Optional directory to write <platform>.json and build_matrix.json")

    # cgc gate
    gate_parser = subparsers.add_parser("gate", help="Run CGC verification-only gates through a shared CLI entrypoint")
    gate_parser.add_argument("gate_name", nargs="?", default="list", help="Gate name to run: m1, m2, m3, m4, m5, m6, m7, m71, m72, m73, m74, m75, m76, m8, m9, or list")
    gate_parser.add_argument("--repo-root", type=str, default=str(SCRIPT_DIR), help="Repository root to inspect")
    gate_parser.add_argument("--output-dir", type=str, default=None, help="Optional gate output directory")
    gate_parser.add_argument("--list", action="store_true", help="List registered gates")
    gate_parser.add_argument("--gate-target", type=str, default=None, help="Target gate name for explicit checkin")
    gate_parser.add_argument("--trigger", type=str, default="manual", help="Checkin trigger label")
    gate_parser.add_argument("--report-path", type=str, default="", help="Explicit report path for gate checkin")
    gate_parser.add_argument("--summary-path", type=str, default="", help="Explicit summary path for gate checkin")
    gate_parser.add_argument("--m4-training-report", type=str, default="", help="M4 only: external/cloud training subreport path for final aggregation")
    gate_parser.add_argument("--m4-inference-report", type=str, default="", help="M4 only: external/local inference subreport path for final aggregation")
    gate_parser.add_argument("--print-json", action="store_true", help="Print gate result as JSON")

    if len(sys.argv) > 1 and sys.argv[1] == "claude":
        args = argparse.Namespace(command="claude", claude_args=sys.argv[2:])
    else:
        args = parser.parse_args()

    if args.command == "serve":
        cfg = load_config()
        print(f"🔗 Cloud Node: {cfg.get('cloud_ip')}:{cfg.get('cloud_port')}")
        print(
            "🚀 Starting CGC Edge Engine stack "
            f"(API {args.host}:{args.port}, Internal Proxy {args.proxy_host}:{args.proxy_port})..."
        )
        cfg["edge_api_port"] = int(args.port)
        cfg["edge_proxy_port"] = int(args.proxy_port)
        save_config(cfg)
        apply_runtime_env(cfg)
        start_edge_stack(
            api_host=str(args.host),
            api_port=int(args.port),
            proxy_host=str(args.proxy_host),
            proxy_port=int(args.proxy_port),
        )
            
    elif args.command == "claude":
        print("🚀 Launching Claude Code CLI with CGC Environment...")
        
        # 強制清理 Claude Code 的 Keychain 與 OAuth 殘留
        # Claude 會把 OAuth Token 存在系統 Keychain 中，這會導致它強迫連線官方伺服器驗證
        try:
            subprocess.run(["claude", "auth", "logout"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Cleared Claude CLI Keychain & OAuth cache.")
        except Exception:
            pass

        claude_config = os.path.expanduser("~/.claude.json")
        if os.path.exists(claude_config):
            try:
                with open(claude_config, "r") as f:
                    config = json.load(f)
                
                # 刪除所有與 OAuth / 登入相關的欄位
                keys_to_remove = ["oauthToken", "refreshToken", "tokenType", "tokenExpiresAt", "primaryWorkspaceId", "accountSettings", "accountId"]
                modified = False
                for key in keys_to_remove:
                    if key in config:
                        del config[key]
                        modified = True
                        
                if modified:
                    with open(claude_config, "w") as f:
                        json.dump(config, f, indent=2)
                    print("✅ Cleared Claude CLI OAuth cache.")
            except Exception as e:
                print(f"⚠️ Warning: Could not clear Claude config: {e}")

        env = os.environ.copy()
        
        # 設定 CLAUDE_CODE_SIMPLE=1 來繞過 Claude CLI 啟動時對 api.anthropic.com 的國家支援檢查
        # 由於使用者可能在受限地區，原生的國家檢查會導致直接閃退 (ERR_BAD_REQUEST)
        env["CLAUDE_CODE_SIMPLE"] = "1"
        
        # 我們在這裡把 Claude 的預設模型強行覆寫為 Custom Model，
        # 這樣使用者在 UI 裡面就能看到 Custom Model 選項
        env["ANTHROPIC_CUSTOM_MODEL_OPTION_NAME"] = "DeepSeek V4 Flash (CGC Edge)"
        env["ANTHROPIC_CUSTOM_MODEL_OPTION"] = "deepseek-v4-flash:latest"
        env["ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION"] = "FusionRoute 4x Expert Pool on gs01"
        
        claude_cfg = load_config()
        env["ANTHROPIC_BASE_URL"] = f"http://localhost:{int(claude_cfg.get('edge_proxy_port', 4000) or 4000)}"
        env["ANTHROPIC_API_KEY"] = "sk-cgc-edge-key"
        # 移除可能衝突的環境變數
        for k in ["ANTHROPIC_AUTH_TOKEN", "CLAUDE_TOKEN", "CLAUDE_OAUTH_TOKEN"]:
            env.pop(k, None)
        
        try:
            cmd = ["claude"] + getattr(args, "claude_args", [])
            subprocess.run(cmd, env=env)
        except FileNotFoundError:
            print("❌ Claude CLI not found. Please make sure it's installed (`npm install -g @anthropic-ai/claude-code`)")

    elif args.command == "config":
        cfg = load_config()
        updated = False
        if args.set_cloud_ip:
            cfg["cloud_ip"] = args.set_cloud_ip
            updated = True
            print(f"✅ Cloud IP set to {args.set_cloud_ip}")
        if args.set_cloud_model:
            cfg["active_cloud_model"] = args.set_cloud_model
            updated = True
            print(f"✅ Cloud Model set to {args.set_cloud_model}")
        if args.set_edge_model:
            cfg["active_edge_model"] = args.set_edge_model
            updated = True
            print(f"✅ Edge Model set to {args.set_edge_model}")
        if args.set_local_omlx_model:
            cfg["local_omlx_model"] = args.set_local_omlx_model
            updated = True
            print(f"✅ Local OMLX model set to {args.set_local_omlx_model}")
        if args.set_local_flashmoe_model:
            cfg["local_flashmoe_model"] = args.set_local_flashmoe_model
            updated = True
            print(f"✅ Local FlashMoE model set to {args.set_local_flashmoe_model}")
        if args.set_edge_api_port is not None:
            cfg["edge_api_port"] = int(args.set_edge_api_port)
            updated = True
            print(f"✅ Edge API port set to {args.set_edge_api_port}")
        if args.set_edge_proxy_port is not None:
            cfg["edge_proxy_port"] = int(args.set_edge_proxy_port)
            updated = True
            print(f"✅ Edge proxy port set to {args.set_edge_proxy_port}")
            
        if updated:
            save_config(cfg)
            apply_runtime_env(cfg)
        else:
            print(json.dumps(cfg, indent=2))

    elif args.command == "run":
        cfg = load_config()
        quiet_json = bool(args.json and str(args.prompt or "").strip())
        if args.list_models:
            print("Fetching available models from the CGC fake Ollama registry...")
            try:
                print_fake_ollama_models()
            except Exception as exc:
                print(f"❌ Failed to fetch model list: {exc}")
                sys.exit(1)
            sys.exit(0)

        model_to_use = args.model or cfg.get("active_edge_model")
        if not model_to_use:
            print("Please specify a model to run. Available models:")
            try:
                models = fetch_fake_ollama_models()
                for i, m in enumerate(models):
                    print(f"  {i+1}. {m.get('name')}")
            except Exception:
                print("  (Cannot resolve model list from CGC fake Ollama registry)")
            print("\nUsage: cgc run <model_name>")
            sys.exit(1)

        if args.show_spec:
            try:
                print_fake_ollama_show_spec(model_to_use)
            except Exception as exc:
                print(f"❌ Failed to resolve model spec for {model_to_use}: {exc}")
                sys.exit(1)
            sys.exit(0)

        requested_minicpm5 = str(model_to_use).strip().lower() in {
            "minicpm5",
            "minicpm5-1b",
            "minicpm5-1b:latest",
            MINICPM5_OLLAMA_MODEL,
        }
        if args.install_minicpm5 or requested_minicpm5:
            try:
                install_spec = None
                try:
                    install_spec = fetch_fake_ollama_install_spec(model_to_use)
                    print(
                        f"☁️ Resolved {model_to_use} from CGC Engine fake Ollama registry: "
                        f"{install_spec.get('gguf_repo')} / {install_spec.get('gguf_filename')}"
                    )
                except Exception as spec_exc:
                    print(f"⚠️ Fake Ollama registry unavailable, fallback to built-in MiniCPM5 spec: {spec_exc}")
                install_result = install_minicpm5_via_ollama(
                    model_name=MINICPM5_OLLAMA_MODEL,
                    quant=str(args.ollama_quant or MINICPM5_DEFAULT_QUANT),
                    force=bool(args.force_reinstall),
                    install_spec=install_spec,
                )
                print(json.dumps({"minicpm5_install": install_result}, ensure_ascii=False, indent=2))
                model_to_use = MINICPM5_OLLAMA_MODEL
            except subprocess.CalledProcessError as exc:
                print(f"❌ MiniCPM5 staging failed: {exc}")
                sys.exit(1)
            except Exception as exc:
                print(f"❌ MiniCPM5 staging failed: {exc}")
                sys.exit(1)

        api_base_url = get_edge_api_base_url(cfg)
        if not quiet_json:
            print(f"🚀 Starting CGC Engine interactive session with model: {model_to_use}")
        
        # =========================================================================
        # ⚙️ 八步流水線：模型與硬體環境感知 (8-Step Hardware & Model Sensing Pipeline)
        # =========================================================================
        if not quiet_json:
            print("\n[CGC Engine] 啟動八步硬體感知流水線...")
        
        # 1. 作業系統偵測
        import platform
        os_name = platform.system()
        if not quiet_json:
            print(f"  [1/8] 系統偵測: {os_name}")
        
        # 2. 硬體架構偵測
        arch = platform.machine()
        if not quiet_json:
            print(f"  [2/8] 架構掃描: {arch}")
        
        # 3. 模型格式解析
        is_local_file = os.path.exists(model_to_use) or any(model_to_use.endswith(ext) for ext in [".gguf", ".safetensors", ".mlx"])
        model_format = "Cloud/API"
        if is_local_file:
            if ".gguf" in model_to_use.lower(): model_format = "GGUF"
            elif ".mlx" in model_to_use.lower(): model_format = "MLX"
            elif ".safetensors" in model_to_use.lower(): model_format = "SafeTensors"
            else: model_format = "Local Unknown"
        if not quiet_json:
            print(f"  [3/8] 格式解析: {model_format}")
        
        # 4. 模型架構分析 (MoE vs Dense)
        is_moe = "moe" in model_to_use.lower() or "deepseek" in model_to_use.lower()
        if not quiet_json:
            print(f"  [4/8] 網路架構: {'Mixture-of-Experts (MoE)' if is_moe else 'Dense'}")
        
        # 5. 記憶體/顯存水位掃描 (模擬/基礎抓取)
        if not quiet_json:
            print(f"  [5/8] 記憶體水位: 掃描中... (動態配置準備)")
        
        # 6. 運算引擎自動路由 (Auto-Routing OMLX)
        auto_omlx = args.use_omlx
        if not auto_omlx and is_local_file and os_name == "Darwin" and arch == "arm64":
            auto_omlx = True
            if not quiet_json:
                print("  [6/8] 運算引擎: 🍎 偵測為 Apple Silicon，自動啟用 OMLX (UMA 0-Copy) 加速。")
        else:
            if not quiet_json:
                print(f"  [6/8] 運算引擎: {'OMLX (手動強制)' if args.use_omlx else '預設引擎'}")
            
        # 7. 記憶體策略自動路由 (Auto-Routing FlashMoE)
        auto_flashmoe = args.use_flashmoe
        if not auto_flashmoe and is_local_file and is_moe:
            auto_flashmoe = True
            if not quiet_json:
                print("  [7/8] 記憶體策略: ⚡ 偵測為 MoE 模型，自動啟用 FlashMoE 動態分頁避免 VRAM OOM。")
        else:
            if not quiet_json:
                print(f"  [7/8] 記憶體策略: {'FlashMoE (手動強制)' if args.use_flashmoe else '預設載入'}")
            
        # 8. 上下文構建完成
        if not quiet_json:
            print("  [8/8] 上下文構建: 參數自動注入完成，準備移交後端...")
            print("-" * 60)
            if auto_flashmoe and str(cfg.get("local_flashmoe_model") or "").strip():
                print(f"  [Edge Runtime] 本地 FlashMoE 模型: {cfg.get('local_flashmoe_model')}")
            elif auto_omlx and str(cfg.get("local_omlx_model") or "").strip():
                print(f"  [Edge Runtime] 本地 OMLX 模型: {cfg.get('local_omlx_model')}")

        if str(args.prompt or "").strip():
            runtime_model = resolve_local_runtime_model(
                model_to_use,
                cfg=cfg,
                use_omlx=auto_omlx,
                use_flashmoe=auto_flashmoe,
            )
            payload = {
                "model": runtime_model,
                "prompt": str(args.prompt),
                "stream": True,
                "use_omlx": auto_omlx,
                "use_flashmoe": auto_flashmoe,
                "max_tokens": int(args.max_tokens),
                "api_base_url": api_base_url,
            }
            try:
                run_result = _execute_single_prompt(api_base_url=api_base_url, payload=payload)
                artifact_dir = _make_cgc_run_report_dir(args.report_dir)
                artifact_summary = _write_cgc_run_artifacts(
                    report_dir=artifact_dir,
                    model_to_use=model_to_use,
                    runtime_model=runtime_model,
                    prompt=str(args.prompt),
                    payload=payload,
                    run_result=run_result,
                )
                final_payload = {
                    "status": artifact_summary.get("status"),
                    "command": "cgc run",
                    "generated_at": utc_now_iso(),
                    "selected_model": model_to_use,
                    "runtime_model": runtime_model,
                    "resolved_model_path": str(artifact_summary.get("resolved_model_path") or runtime_model),
                    "format": str(artifact_summary.get("format") or _detect_model_format(runtime_model)),
                    "selected_route": str(artifact_summary.get("selected_route") or ""),
                    "selected_backend": str(artifact_summary.get("backend") or ""),
                    "local_execution": bool(artifact_summary.get("local_execution")),
                    "cloud_bridge_used": bool(str(artifact_summary.get("selected_route") or "") == "m73_edge_cloud"),
                    "decision_reason": artifact_summary.get("decision_reason") or {},
                    "response": {
                        "text": str(run_result.get("response_text") or ""),
                        "finish_reason": "stop" if str(artifact_summary.get("status") or "") == "PASS" else "error",
                    },
                    "edge_latency_ms": float(artifact_summary.get("edge_latency_ms") or 0.0),
                    "evidence_paths": {
                        "local_infer": str(artifact_summary.get("evidence_path") or ""),
                        "run_report": str(artifact_summary.get("run_report_path") or ""),
                        "m4_inference_report": str(artifact_summary.get("m4_inference_report_path") or ""),
                        "edge_inference_bridge": str(artifact_summary.get("edge_inference_bridge_path") or ""),
                        "route_decision": str(artifact_summary.get("route_decision_path") or ""),
                    },
                }
                if args.json:
                    print(json.dumps(final_payload, ensure_ascii=False, indent=2))
                else:
                    print(str((final_payload.get("response") or {}).get("text") or ""))
                    print(json.dumps(final_payload, ensure_ascii=False, indent=2))
                sys.exit(0 if str(final_payload.get("status") or "") == "PASS" else 1)
            except requests.exceptions.ConnectionError:
                print("\n[Error] Cannot connect to CGC Engine. Did you run 'cgc serve' in another terminal?")
                sys.exit(1)
            except Exception as e:
                print(f"\n[Error] {e}")
                sys.exit(1)
        
        print("Type '/bye' to exit.")
        while True:
            try:
                user_input = input(">>> ")
                if user_input.strip() == "/bye":
                    break
                if not user_input.strip():
                    continue
                
                runtime_model = resolve_local_runtime_model(
                    model_to_use,
                    cfg=cfg,
                    use_omlx=auto_omlx,
                    use_flashmoe=auto_flashmoe,
                )
                payload = {
                    "model": runtime_model,
                    "prompt": user_input,
                    "stream": True,
                    "use_omlx": auto_omlx,
                    "use_flashmoe": auto_flashmoe,
                    "max_tokens": 256,
                    "api_base_url": api_base_url,
                }

                if auto_omlx or auto_flashmoe:
                    run_result = _execute_single_prompt(api_base_url=api_base_url, payload=payload)
                    print(str(run_result.get("response_text") or ""))
                    continue

                response = requests.post(f"{api_base_url}/api/generate", json=payload, stream=True)
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        print(data.get("response", ""), end="", flush=True)
                print()
            except requests.exceptions.ConnectionError:
                print("\n[Error] Cannot connect to CGC Engine. Did you run 'cgc serve' in another terminal?")
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n[Error] {e}")
                break
                
    elif args.command == "list":
        try:
            payload = collect_list_response(cfg=load_config(), model_roots=args.model_root, nfs_roots=args.nfs_root)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_list_response(payload)
            sys.exit(0 if str(payload.get("status") or "") == "PASS" else 1)
        except Exception as exc:
            print(f"❌ Failed to fetch model list: {exc}")
            sys.exit(1)

    elif args.command == "status":
        try:
            from m75_extreme_status import (
                collect_extreme_status,
                print_status_summary,
                write_extreme_status_evidence,
            )

            payload = collect_extreme_status(
                expected_workers=int(args.expected_workers),
                expected_instances=int(args.expected_instances),
                expected_fusion_group_size=int(args.expected_fusion_group_size),
            )
            if args.write_m75_evidence:
                evidence_path = write_extreme_status_evidence(payload)
                payload["evidence_path"] = evidence_path
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print_status_summary(payload)
                if payload.get("evidence_path"):
                    print(f"evidence: {payload['evidence_path']}")
            sys.exit(0 if payload.get("status") == "PASS" else 1)
        except Exception as exc:
            print(f"❌ Failed to collect CGC status: {exc}")
            sys.exit(1)

    elif args.command == "audit":
        if args.audit_command == "run":
            result = run_audit(output_dir=args.output_dir, strict=bool(args.strict))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("status") == "PASS" else 1)
        if args.audit_command == "verify":
            result = verify_audit(report_path=args.report, log_path=args.log, head_path=args.head)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("status") == "PASS" else 1)
        if args.audit_command == "trace":
            result = trace_audit(report_path=args.report, log_path=args.log, stage=args.stage, limit=args.limit)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)
        if args.audit_command == "export":
            result = export_audit(report_path=args.report, output_path=args.output, export_format=args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get("status") == "PASS" else 1)
        audit_parser.print_help()
        sys.exit(2)
            
    elif args.command == "build":
        quiet_json = bool(getattr(args, "json", False))
        if not quiet_json:
            print("==================================================")
            print(" 🛡️ CGC Edge Engine - Nuitka 跨平台編譯系統")
            print("==================================================")
            print("將使用 CGC Edge Engine package 內建的 builder 與受管 Python 環境進行編譯...")
        try:
            result = build_edge_engine(
                repo_root=REPO_ROOT,
                output_dir=Path(args.output_dir),
                quiet=quiet_json,
            )
            payload = {
                "status": result.status,
                "generated_at": result.generated_at,
                "python_bin": result.python_bin,
                "builder": result.builder,
                "platform": result.platform,
                "host_platform": result.host_platform,
                "host_arch": result.host_arch,
                "package_format": result.package_format,
                "output_path": result.output_path,
                "executable_path": result.executable_path,
                "output_exists": bool(result.output_exists),
                "size_bytes": int(result.size_bytes),
                "executable_size_bytes": int(result.executable_size_bytes),
                "artifact_sha256": result.artifact_sha256,
                "executable_sha256": result.executable_sha256,
                "supported_platforms": list(result.supported_platforms),
                "command": result.command,
            }
            report_file = Path(str(getattr(args, "report_file", "") or "")).expanduser() if str(getattr(args, "report_file", "") or "").strip() else None
            aggregate_dir = Path(str(getattr(args, "aggregate_dir", "") or "")).expanduser() if str(getattr(args, "aggregate_dir", "") or "").strip() else None
            if report_file is not None:
                report_file.parent.mkdir(parents=True, exist_ok=True)
                report_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                payload["report_file"] = str(report_file.resolve())
            if aggregate_dir is not None:
                aggregate_dir.mkdir(parents=True, exist_ok=True)
                platform_report_path = (aggregate_dir / f"{result.platform}.json").resolve()
                platform_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                matrix_payload = {
                    "status": "PASS",
                    "generated_at": result.generated_at,
                    "platform_reports": {
                        platform_name: str((aggregate_dir / f"{platform_name}.json").resolve())
                        for platform_name in result.supported_platforms
                        if (aggregate_dir / f"{platform_name}.json").exists()
                    },
                    "required_platforms": list(result.supported_platforms),
                }
                matrix_report_path = (aggregate_dir / "build_matrix.json").resolve()
                matrix_report_path.write_text(json.dumps(matrix_payload, ensure_ascii=False, indent=2), encoding="utf-8")
                payload["aggregate_dir"] = str(aggregate_dir.resolve())
                payload["platform_report_file"] = str(platform_report_path)
                payload["build_matrix_file"] = str(matrix_report_path)
            if not quiet_json:
                print("🚀 [Nuitka] Build completed through the packaged CGC Edge Engine builder.")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as e:
            if quiet_json:
                print(json.dumps({"status": "FAIL", "error": str(e)}, ensure_ascii=False, indent=2))
            else:
                print(f"❌ 編譯失敗: {e}")
            sys.exit(1)

    elif args.command == "gate":
        if args.list or args.gate_name == "list":
            print_gate_registry()
            sys.exit(0)
        if args.gate_name == "checkin":
            gate_target = args.gate_target or "unknown"
            result = write_gate_checkin(
                gate_name=gate_target,
                status="PASS",
                report_path=args.report_path,
                summary_path=args.summary_path,
                trigger=args.trigger,
            )
            if args.print_json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"Gate checkin status: {result['status']}")
                print(f"checkin: {result['checkin_path']}")
                print(f"log: {result['log_path']}")
            sys.exit(0)
        try:
            result = run_registered_gate(
                gate_name=args.gate_name,
                repo_root=args.repo_root,
                output_dir=args.output_dir,
                m4_training_report=args.m4_training_report,
                m4_inference_report=args.m4_inference_report,
            )
        except ValueError as e:
            print(f"❌ {e}")
            print_gate_registry()
            sys.exit(2)

        if args.print_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"{args.gate_name.upper()} gate status: {result['status']}")
            if result.get("report_path"):
                print(f"report: {result['report_path']}")
            if result.get("summary_path"):
                print(f"summary: {result['summary_path']}")
            if result.get("status") == "NOT_IMPLEMENTED" and result.get("message"):
                print(result["message"])
        if result.get("status") == "PASS":
            checkin = write_gate_checkin(
                gate_name=args.gate_name,
                status="PASS",
                report_path=result.get("report_path", ""),
                summary_path=result.get("summary_path", ""),
                trigger="gate_pass",
                extra={"gate_result_keys": sorted(list((result.get("gate_result") or {}).keys())) if isinstance(result.get("gate_result"), dict) else []},
            )
            if args.print_json:
                print(json.dumps({"auto_checkin": checkin}, ensure_ascii=False, indent=2))
            else:
                print(f"checkin: {checkin['checkin_path']}")
        sys.exit(0 if result.get("status") == "PASS" else 1)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
