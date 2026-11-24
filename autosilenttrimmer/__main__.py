"""Package entrypoint: python -m autosilenttrimmer."""

import sys
from autosilenttrimmer.presentation.cli.runner import run_cli

if __name__ == "__main__":
    sys.exit(run_cli())
