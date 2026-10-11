from pathlib import Path
import json
import os

ROOT = Path(os.environ.get("MADDIE_DIM_ROOT", Path(__file__).resolve().parents[2]))


def config() -> dict:
    return json.loads((ROOT / "configs/benchmark.json").read_text())
