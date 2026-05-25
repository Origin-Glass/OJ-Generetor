import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
if len(sys.argv) == 1 or sys.argv[1].startswith("-"):
    sys.argv.insert(1, "resume")

from oj_agent.main import main


if __name__ == "__main__":
    main()
