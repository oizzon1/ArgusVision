"""Every subpackage imports; runtime/ carries no evaluation imports (F6 rule)."""

import sys


def test_all_subpackages_import():
    import argusvision.data
    import argusvision.evaluation
    import argusvision.models
    import argusvision.pipeline
    import argusvision.runtime
    import argusvision.viz  # noqa: F401


def test_runtime_does_not_import_evaluation():
    for mod in [m for m in list(sys.modules) if m.startswith("argusvision")]:
        del sys.modules[mod]
    import argusvision.runtime  # noqa: F401

    loaded = [m for m in sys.modules if m.startswith("argusvision.evaluation")]
    assert loaded == [], f"runtime pulled in evaluation modules: {loaded}"
