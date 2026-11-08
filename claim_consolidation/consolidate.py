import os
import subprocess
from pathlib import Path

from database import LOGS, host

from . import timed

CRATE = Path(__file__).parents[1] / "consolidator"


@timed
def consolidate():
    subprocess.run(["cargo", "build", "--release"], cwd=CRATE, check=True)
    with open(LOGS / "consolidation.log", "a", encoding="utf-8") as log:
        subprocess.run([str(CRATE / "target" / "release" / "consolidate"), "run", "--host", host(), "--threads", str(os.cpu_count() - 2)], check=True, stderr=log)
