"""Probe the F6 Mask R-CNN environment without mutating it."""

from __future__ import annotations

import importlib
import json
import platform


def probe_module(name: str) -> dict[str, str | bool]:
    try:
        module = importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {"available": False, "error": repr(exc)}
    return {"available": True, "version": str(getattr(module, "__version__", "unknown"))}


def main() -> int:
    import torch

    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torchvision": probe_module("torchvision"),
        "mmdet": probe_module("mmdet"),
        "mmcv": probe_module("mmcv"),
        "mmengine": probe_module("mmengine"),
        "PIL": probe_module("PIL"),
        "numpy": probe_module("numpy"),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
