"""Compatibility shim — the driver now lives in the package.

It moved because every experiment needs it, which by the platform test makes it
platform code rather than experiment code. `experiments/` holds configs.

    argusvision run experiments/configs/<config>.yaml     # preferred
    python experiments/run_evaluation.py <config>.yaml    # still works

Implementation: `src/argusvision/cli.py`.
"""

import sys

from argusvision.cli import main

if __name__ == "__main__":
    argv = sys.argv[1:]
    # Old form took a bare config path; new form takes a subcommand.
    if argv and not argv[0].startswith("-") and argv[0] != "run":
        argv = ["run"] + argv
    sys.exit(main(argv))
