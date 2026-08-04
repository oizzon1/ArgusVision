"""The heartbeat is read by a second process, so its contract is pinned.

A stale or malformed `status.json` is worse than none: it reports a dead run as
alive, and the user plans around it.
"""

import json

import pytest

from argusvision.runtime.status import RunStatus, latest_run_dir, read_status


def test_status_file_appears_at_entry(tmp_path):
    with RunStatus(tmp_path, "exp", total=10):
        assert read_status(tmp_path)["state"] == "running"


def test_progress_is_reported(tmp_path):
    with RunStatus(tmp_path, "exp", total=10, write_every=1) as st:
        for _ in range(4):
            st.advance()
        st._write(force=True)
        payload = read_status(tmp_path)
    assert payload["done"] == 4
    assert payload["percent"] == pytest.approx(40.0)


def test_completion_is_recorded(tmp_path):
    with RunStatus(tmp_path, "exp", total=2, write_every=1) as st:
        st.advance()
        st.advance()
    assert read_status(tmp_path)["state"] == "done"


def test_failure_is_recorded_with_the_reason(tmp_path):
    with pytest.raises(RuntimeError):
        with RunStatus(tmp_path, "exp", total=5) as st:
            st.advance()
            raise RuntimeError("cuda out of memory")

    payload = read_status(tmp_path)
    assert payload["state"] == "failed"
    assert "cuda out of memory" in payload["error"]


def test_exception_is_not_swallowed(tmp_path):
    # A run that fails must fail — the heartbeat is an observer, not a handler.
    with pytest.raises(ValueError):
        with RunStatus(tmp_path, "exp", total=1):
            raise ValueError("boom")


def test_eta_is_absent_before_any_progress(tmp_path):
    with RunStatus(tmp_path, "exp", total=100):
        assert read_status(tmp_path)["eta_seconds"] is None


def test_phase_is_visible(tmp_path):
    with RunStatus(tmp_path, "exp", total=1) as st:
        st.set_phase("segmentation")
        assert read_status(tmp_path)["phase"] == "segmentation"


def test_metrics_can_be_attached(tmp_path):
    with RunStatus(tmp_path, "exp", total=1) as st:
        st.set_metrics({"micro_f1": 0.77})
    assert read_status(tmp_path)["metrics"]["micro_f1"] == 0.77


def test_extra_fields_survive(tmp_path):
    with RunStatus(tmp_path, "exp", total=1, extra={"kind": "pipeline"}):
        assert read_status(tmp_path)["kind"] == "pipeline"


def test_written_file_is_always_valid_json(tmp_path):
    # Atomic replace: a reader polling concurrently must never see a partial file.
    with RunStatus(tmp_path, "exp", total=50, write_every=1) as st:
        for _ in range(50):
            st.advance()
            json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))


def test_missing_status_reads_as_none(tmp_path):
    assert read_status(tmp_path) is None


def test_corrupt_status_reads_as_none(tmp_path):
    (tmp_path / "status.json").write_text("{not json", encoding="utf-8")
    assert read_status(tmp_path) is None


def test_latest_run_dir_finds_the_newest(tmp_path):
    older = tmp_path / "exp" / "run_a"
    newer = tmp_path / "exp" / "run_b"
    with RunStatus(older, "exp", total=1):
        pass
    with RunStatus(newer, "exp", total=1):
        pass
    assert latest_run_dir(tmp_path) == newer


def test_latest_run_dir_can_narrow_by_experiment(tmp_path):
    with RunStatus(tmp_path / "a" / "run", "a", total=1):
        pass
    with RunStatus(tmp_path / "b" / "run", "b", total=1):
        pass
    assert latest_run_dir(tmp_path, "a") == tmp_path / "a" / "run"


def test_latest_run_dir_is_none_when_empty(tmp_path):
    assert latest_run_dir(tmp_path) is None
