import base64
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from dimos.core.coordination.module_coordinator import ModuleCoordinator
from .config import ROOT, config
from .modules import PaintModule, AuditModule, blueprint
from .protocol import Batch
from .policy import Astra
from .recording import RunRecorder


class BenchmarkDeadline(TimeoutError):
    pass


def demo_batch():
    # A calibration coupon, deliberately not a fabricated Astra portrait.
    return Batch.model_validate(
        {
            "strokes": [
                {"points": [[65, 110], [145, 110]], "force_N": 0.08},
                {"points": [[65, 135], [145, 135]], "force_N": 0.25},
                {"points": [[65, 160], [145, 160]], "force_N": 0.6},
                {
                    "points": [
                        [85, 190],
                        [105, 175],
                        [125, 190],
                        [105, 205],
                        [85, 190],
                    ],
                    "force_N": 0.25,
                },
            ],
            "done": True,
            "note": "Controller calibration: three force levels and a closed contour. No model call.",
        }
    )


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wait_motion(module, deadline=None):
    while True:
        state = module.status()
        if state["state"] not in ("queued", "drawing"):
            return state
        if deadline is not None and time.monotonic() >= deadline:
            module.cancel()
            raise BenchmarkDeadline("30-minute wall-clock deadline")
        time.sleep(0.2)


def save_manifest(folder, manifest):
    path = folder / "manifest.tmp.json"
    path.write_text(json.dumps(manifest, indent=2))
    path.replace(folder / "manifest.json")


def run(mode="demo", realtime=False, run_dir=None, record_video=None):
    folder = (
        Path(run_dir)
        if run_dir
        else ROOT / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    folder.mkdir(parents=True, exist_ok=False)
    c = config()
    if mode == "astra":
        realtime = True
    if record_video is None:
        record_video = mode == "astra"
    manifest = {
        "mode": mode,
        "protocol": c["protocol"],
        "config": c,
        "reference_sha256": sha(ROOT / "assets/reference.jpg"),
        "config_sha256": sha(ROOT / "configs/benchmark.json"),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in sorted((ROOT / "src/maddie_dim").glob("*.py"))
        },
        "dimos_commit": "1e7b4918bc626de4fa6592fb023d4b3aee932754",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "physical_transfer": "UNVERIFIED",
        "pen_response": "UNCALIBRATED",
        "status": "starting",
        "realtime": realtime,
        "video_requested": record_video,
    }
    save_manifest(folder, manifest)
    coordinator = None
    module = None
    audit = None
    deadline = None
    recorder = None
    try:
        policy = Astra(ROOT, folder) if mode == "astra" else None
        coordinator = ModuleCoordinator.build(blueprint(folder))
        module = coordinator.get_instance(PaintModule)
        audit = coordinator.get_instance(AuditModule)
        if record_video:
            recorder = RunRecorder(folder)
            recorder.start()
            manifest["video_ready_before_timed_run"] = True
        start = time.monotonic()
        deadline = start + c["deadline_seconds"]
        manifest["status"] = "running"
        manifest["timed_run_started_utc"] = datetime.now(timezone.utc).isoformat()
        save_manifest(folder, manifest)
        module.begin_run()
        time.sleep(0.15)
        if mode == "demo":
            batch = demo_batch()
            (folder / "commands.json").write_text(batch.model_dump_json(indent=2))
            module.submit(batch.model_dump_json(), realtime)
            final = wait_motion(module)
            if final["state"] in ("error", "rejected"):
                raise RuntimeError(final.get("error"))
        else:
            feedback = {}
            for turn in range(100):
                if recorder is not None:
                    recorder.check()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BenchmarkDeadline("30-minute wall-clock deadline")
                camera = Image.open(io.BytesIO(base64.b64decode(module.observation())))
                batch = policy.next(camera, remaining, feedback)
                if time.monotonic() >= deadline:
                    raise BenchmarkDeadline(
                        "Astra returned after deadline; no motion executed"
                    )
                if batch.strokes:
                    module.submit(batch.model_dump_json(), True)
                    state = wait_motion(module, deadline)
                    turn_dir = folder / f"turn-{turn:03d}"
                    turn_dir.mkdir(exist_ok=True)
                    (turn_dir / "execution.json").write_text(
                        json.dumps(state, indent=2)
                    )
                    # Only measured/estimated observations are exposed to model.
                    feedback = {
                        k: state[k]
                        for k in ("state", "error", "wall_seconds", "force_estimate_N")
                        if k in state
                    }
                    if state["state"] == "timed_out":
                        raise BenchmarkDeadline(state.get("error"))
                    if state["state"] == "error":
                        raise RuntimeError(state.get("error"))
                if batch.done and (not batch.strokes or state["state"] == "ready"):
                    break
            else:
                raise RuntimeError("Turn limit reached")
        module.finish()
        time.sleep(0.5)
        manifest["status"] = "completed"
        manifest["dimos_audit_events"] = audit.event_count()
        if manifest["dimos_audit_events"] < 1:
            raise RuntimeError("DimOS audit stream delivered no events")
    except TimeoutError as exc:
        if isinstance(exc, BenchmarkDeadline) or (
            deadline is not None and time.monotonic() >= deadline
        ):
            manifest["status"] = "time_limit"
            manifest["stop_reason"] = str(exc)
            if module is not None:
                module.cancel()
        else:
            manifest["status"] = "failed"
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            raise
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if audit is not None:
            try:
                manifest["dimos_audit_events"] = audit.event_count()
            except Exception as exc:
                manifest["audit_error"] = type(exc).__name__
        if coordinator is not None:
            coordinator.stop()
        manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_manifest(folder, manifest)
        if recorder is not None:
            try:
                recorder.stop()
                manifest["video_status"] = "completed"
            except Exception as exc:
                manifest["video_status"] = "failed"
                manifest["video_error"] = str(exc)
            save_manifest(folder, manifest)
        print(f"Run artifacts: {folder}", flush=True)
    return folder
