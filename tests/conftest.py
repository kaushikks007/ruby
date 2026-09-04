"""Test isolation for the Ruby test suite.

Every phase test mutates Ruby's data store (profile.json, daily logs, project
files, screenshots, etc.). Without isolation, running `pytest` writes straight
into the user's real memory (C:\\Users\\sudha\\OneDrive\\ruby\\memory) and
corrupts Ruby's actual companion context with test junk.

Fix: point RUBY_DATA_ROOT at a throwaway temp directory BEFORE any `ruby.*`
module is imported. `ruby.config` reads that env var at import time and derives
all paths (memory/, browser_data/, scripts/) from it, so everything below flows
into the temp dir automatically. The real scripts/ is mirrored into the temp
root so the Phase-4 script-runner tests still find `system_status.py`.
"""
import os
import shutil
import tempfile
from pathlib import Path

_REAL_ROOT = Path(__file__).resolve().parent.parent
_DATA_ROOT = Path(tempfile.mkdtemp(prefix="ruby_test_data_"))

# Keep Phase-4's script-runner tests functional: they expect the real scripts/
# (system_status.py etc.) to exist under DATA_ROOT.
_scripts = _REAL_ROOT / "scripts"
if _scripts.is_dir():
    shutil.copytree(_scripts, _DATA_ROOT / "scripts")

os.environ["RUBY_DATA_ROOT"] = str(_DATA_ROOT)
