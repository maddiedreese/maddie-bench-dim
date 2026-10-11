"""Export an existing calibration run, retaining data and normalizing local paths."""

import argparse, json, shutil
from pathlib import Path
import numpy as np
from maddie_dim.config import ROOT

p = argparse.ArgumentParser()
p.add_argument("run_dir")
args = p.parse_args()
source = Path(args.run_dir)
out = ROOT / "examples/calibration"
out.mkdir(parents=True, exist_ok=True)
for name in [
    "commands.json",
    "manifest.json",
    "physics.json",
    "trajectory.jsonl",
    "overhead.jpg",
    "overview.jpg",
    "paper.png",
]:
    shutil.copy2(source / name, out / name)
events = [
    json.loads(l) for l in (source / "dimos-events.jsonl").read_text().splitlines()
]
for event in events:
    event["run_dir"] = "examples/calibration"
(out / "dimos-events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
rows = [json.loads(l) for l in (out / "trajectory.jsonl").read_text().splitlines()]
metrics = []
for target in [0.08, 0.25, 0.6]:
    subset = [x for x in rows if x["expected_ink"] and x["force_target_N"] == target]
    metrics.append(
        {
            "target_N": target,
            "actual_mean_N": float(np.mean([x["force_N"] for x in subset])),
            "estimated_mean_N": float(np.mean([x["force_estimate_N"] for x in subset])),
        }
    )
(out / "force-summary.json").write_text(json.dumps(metrics, indent=2))
# Optional publication figure; matplotlib is not required by the runtime.
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 4))
    t = [x["t"] for x in rows]
    ax.plot(
        t, [x["force_N"] for x in rows], lw=0.8, label="Actual simulated normal force"
    )
    ax.plot(
        t,
        [x["force_estimate_N"] for x in rows],
        lw=0.6,
        alpha=0.7,
        label="Motor-torque estimate",
    )
    ax.plot(
        t,
        [
            x["force_target_N"] if x["force_target_N"] is not None else np.nan
            for x in rows
        ],
        "k--",
        lw=1.3,
        label="Commanded target",
    )
    ax.set(
        xlabel="Simulation time (s)",
        ylabel="Force (N)",
        title="Controller calibration coupon · provisional PC-1MR contact model",
    )
    ax.legend(frameon=False)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(out / "force-profile.png", dpi=160)
except ImportError:
    pass
print(json.dumps(metrics, indent=2))
