"""Run provenance and result writing (TODO_RESTRUCTURE.md F5).

Every experiment run gets `results/<experiment>/<run_id>/` containing at least:
  - manifest.json : git SHA + dirty flag, config, environment, timestamp
  - metrics.json  : whatever the evaluator summarized

A number without a manifest next to it does not exist for paper purposes.
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _git(*args: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, check=False
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def git_provenance() -> Dict[str, object]:
    """Best-effort git state; never raises (git may be absent on Windows)."""
    sha = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "git_sha": sha if sha else "unknown",
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "git_dirty": bool(status) if status is not None else None,
    }


def environment_provenance() -> Dict[str, object]:
    env: Dict[str, object] = {
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", "unknown"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    try:
        import torch

        env["torch"] = torch.__version__
        env["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            env["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    try:
        import numpy

        env["numpy"] = numpy.__version__
    except ImportError:
        pass
    return env


def create_run_dir(experiment: str, results_root: str = "results") -> Path:
    """`results/<experiment>/<UTC timestamp>_<short sha>/`, created."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sha = git_provenance()["git_sha"]
    short = sha[:7] if isinstance(sha, str) and sha != "unknown" else "nosha"
    run_dir = Path(results_root) / experiment / f"{stamp}_{short}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_run_manifest(run_dir: Path, experiment: str, config: Dict) -> Path:
    """manifest.json capturing what produced the numbers next to it."""
    manifest = {
        "experiment": experiment,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "command": " ".join(sys.argv),
        **git_provenance(),
        "environment": environment_provenance(),
    }
    path = Path(run_dir) / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path


def write_metrics(run_dir: Path, metrics: Dict, name: str = "metrics.json") -> Path:
    """Serialize a metrics dict; float-keys (IoU thresholds) become strings."""
    path = Path(run_dir) / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=_jsonable)
    return path


def _jsonable(obj):
    import numpy as np

    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"not JSON serializable: {type(obj)}")
