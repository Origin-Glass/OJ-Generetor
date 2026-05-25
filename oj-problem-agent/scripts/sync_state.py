from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oj_agent.config import load_config
from oj_agent.main import build_slots
from oj_agent.state import StateStore


def main() -> None:
    config = load_config()
    slots = build_slots(config)
    store = StateStore(config.project_root / config.generation.metadata_dir)
    state = store.load(slots)
    store.save(state)
    print(store.path)


if __name__ == "__main__":
    main()
