"""Run heartbeat: a small JSON file any other process can read mid-run.

The user runs experiments in their own terminal; ATHENA is a separate process
with no access to that terminal's stdout. `status.json` is the seam — the run
rewrites it as it goes, and anyone can read progress, ETA and partial metrics
without attaching to, interrupting, or slowing the run.

Written atomically (temp file + replace) because the reader is polling
concurrently and a half-written file would be parsed as a crash.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

__all__ = ["RunStatus", "read_status"]

STATUS_FILENAME = "status.json"


class RunStatus:
    """Tracks progress of a run and persists it to `<run_dir>/status.json`.

    Use as a context manager so the terminal state is correct even when the
    run dies: an exception marks the run `failed` with the message, rather
    than leaving a stale `running` that looks alive forever.
    """

    def __init__(
        self,
        run_dir: Path,
        experiment: str,
        total: int,
        write_every: int = 10,
        extra: Optional[Dict] = None,
    ):
        self.path = Path(run_dir) / STATUS_FILENAME
        self.experiment = experiment
        self.total = int(total)
        self.write_every = max(1, int(write_every))
        self.extra = dict(extra or {})
        self.done = 0
        self.phase = ""
        self.state = "starting"
        self.error: Optional[str] = None
        self.metrics: Dict = {}
        self.started = time.time()
        self._last_write = 0.0

    def __enter__(self) -> "RunStatus":
        self.state = "running"
        self._write()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.state = "failed"
            self.error = f"{exc_type.__name__}: {exc}"
        elif self.state == "running":
            self.state = "done"
        self._write(force=True)
        return False  # never swallow the exception

    def advance(self, n: int = 1, phase: Optional[str] = None) -> None:
        self.done += n
        if phase is not None:
            self.phase = phase
        if self.done % self.write_every == 0 or self.done >= self.total:
            self._write()

    def set_phase(self, phase: str) -> None:
        self.phase = phase
        self._write(force=True)

    def set_metrics(self, metrics: Dict) -> None:
        self.metrics = metrics
        self._write(force=True)

    def finish(self, metrics: Optional[Dict] = None) -> None:
        if metrics is not None:
            self.metrics = metrics
        self.state = "done"
        self._write(force=True)

    # -- internals ---------------------------------------------------------

    def _payload(self) -> Dict:
        elapsed = time.time() - self.started
        rate = self.done / elapsed if elapsed > 0 and self.done else 0.0
        remaining = max(self.total - self.done, 0)
        payload = {
            "experiment": self.experiment,
            "state": self.state,
            "phase": self.phase,
            "done": self.done,
            "total": self.total,
            "percent": round(100.0 * self.done / self.total, 1) if self.total else 0.0,
            "elapsed_seconds": round(elapsed, 1),
            "rate_per_second": round(rate, 3),
            "eta_seconds": round(remaining / rate, 1) if rate > 0 else None,
            "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pid": os.getpid(),
        }
        if self.error:
            payload["error"] = self.error
        if self.metrics:
            payload["metrics"] = self.metrics
        payload.update(self.extra)
        return payload

    def _write(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_write < 1.0:
            return  # throttle: a fast loop must not turn into an I/O benchmark
        self._last_write = now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._payload(), fh, indent=2)
        os.replace(tmp, self.path)


def read_status(run_dir: Path) -> Optional[Dict]:
    """Read a run's status, or None if it has not written one yet."""
    path = Path(run_dir) / STATUS_FILENAME
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def latest_run_dir(results_root: Path, experiment: Optional[str] = None) -> Optional[Path]:
    """Most recently modified run directory containing a status file."""
    root = Path(results_root)
    if experiment:
        root = root / experiment
    if not root.exists():
        return None
    candidates = [p.parent for p in root.rglob(STATUS_FILENAME)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p / STATUS_FILENAME).stat().st_mtime)
