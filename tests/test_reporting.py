"""Run provenance: manifest + metrics writing (finding F5)."""

import json

import numpy as np

from argusvision.evaluation.reporting import (
    create_run_dir,
    git_provenance,
    write_metrics,
    write_run_manifest,
)


def test_create_run_dir_layout(tmp_path):
    run_dir = create_run_dir("unit_test_exp", results_root=str(tmp_path))
    assert run_dir.exists()
    assert run_dir.parent.name == "unit_test_exp"
    assert run_dir.parent.parent == tmp_path


def test_manifest_contents(tmp_path):
    run_dir = create_run_dir("unit_test_exp", results_root=str(tmp_path))
    path = write_run_manifest(run_dir, "unit_test_exp", config={"iou": 0.5})
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for key in ("experiment", "created_utc", "config", "git_sha", "git_branch", "environment"):
        assert key in manifest, key
    assert manifest["config"] == {"iou": 0.5}
    assert manifest["environment"]["python"]


def test_write_metrics_handles_numpy_and_float_keys(tmp_path):
    run_dir = create_run_dir("unit_test_exp", results_root=str(tmp_path))
    metrics = {
        "per_threshold": {0.5: {"micro_f1": np.float64(0.75), "tp": np.int64(3)}},
        "curve": np.array([1.0, 0.5]),
    }
    path = write_metrics(run_dir, metrics)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["per_threshold"]["0.5"]["micro_f1"] == 0.75
    assert loaded["per_threshold"]["0.5"]["tp"] == 3
    assert loaded["curve"] == [1.0, 0.5]


def test_git_provenance_never_raises():
    prov = git_provenance()
    assert "git_sha" in prov and "git_branch" in prov
