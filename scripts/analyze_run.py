"""Summarize a recorded run without inventing a portrait-likeness score."""

import argparse, json
from pathlib import Path
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("run_dir")
a = p.parse_args()
r = Path(a.run_dir)
m = json.loads((r / "manifest.json").read_text())
trace = r / "trajectory.jsonl"
rows = [json.loads(l) for l in trace.read_text().splitlines()] if trace.exists() else []
turns = []
for d in sorted(r.glob("turn-*")):
    item = {"turn": d.name}
    if (d / "commands.json").exists():
        b = json.loads((d / "commands.json").read_text())
        item.update(
            strokes=len(b["strokes"]),
            points=sum(len(s["points"]) for s in b["strokes"]),
            done=b["done"],
            note=b["note"],
        )
    if (d / "execution.json").exists():
        item["execution_state"] = json.loads((d / "execution.json").read_text())[
            "state"
        ]
    if (d / "response.json").exists():
        response = json.loads((d / "response.json").read_text())
        item["usage"] = response.get("usage")
        item["status"] = response.get("status")
    if (d / "error.json").exists():
        item["error"] = json.loads((d / "error.json").read_text())
    turns.append(item)
if not turns and (r / "commands.json").exists():
    b = json.loads((r / "commands.json").read_text())
    turns.append(
        {
            "turn": "controller-demo",
            "strokes": len(b["strokes"]),
            "points": sum(len(s["points"]) for s in b["strokes"]),
            "done": b["done"],
            "note": b["note"],
        }
    )
forces = []
for target in sorted(
    {x["force_target_N"] for x in rows if x["force_target_N"] is not None}
):
    subset = [x for x in rows if x["expected_ink"] and x["force_target_N"] == target]
    if not subset:
        continue
    actual = np.array([x["force_N"] for x in subset])
    estimate = np.array([x["force_estimate_N"] for x in subset])
    forces.append(
        {
            "target_N": target,
            "samples": len(subset),
            "actual_mean_N": float(actual.mean()),
            "actual_p95_N": float(np.percentile(actual, 95)),
            "estimated_mean_N": float(estimate.mean()),
            "tracking_rmse_N": float(np.sqrt(np.mean((actual - target) ** 2))),
        }
    )
report = {
    "mode": m["mode"],
    "status": m["status"],
    "error": m.get("error"),
    "physical_transfer": "UNVERIFIED",
    "portrait_likeness_score": None,
    "likeness_note": "Requires blinded human evaluation; no automatic score claimed.",
    "turns": turns,
    "force_groups": forces,
}
if (r / "physics.json").exists():
    report["physics"] = json.loads((r / "physics.json").read_text())
(r / "analysis.json").write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "status": report["status"],
            "turns": len(turns),
            "commanded_strokes": sum(t.get("strokes", 0) for t in turns),
            "force_targets": len(forces),
            "report": str(r / "analysis.json"),
        },
        indent=2,
    )
)
