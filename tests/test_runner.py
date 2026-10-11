import base64, io, json
from types import SimpleNamespace
from PIL import Image
import pytest
from maddie_dim import runner
from maddie_dim.protocol import Batch


@pytest.mark.parametrize("timeout", [False, True])
def test_runner_replans_rejection_or_records_time_limit(tmp_path, monkeypatch, timeout):
    root = tmp_path / "project"
    (root / "assets").mkdir(parents=True)
    (root / "configs").mkdir()
    (root / "assets/reference.jpg").write_bytes(b"reference-test")
    (root / "configs/benchmark.json").write_text("{}")
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setattr(
        runner, "config", lambda: {"protocol": "test", "deadline_seconds": 1800}
    )
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(image, format="JPEG")

    recording_events = []

    class Recorder:
        def __init__(self, folder):
            self.folder = folder

        def start(self):
            assert (
                json.loads((self.folder / "manifest.json").read_text())["status"]
                == "starting"
            )
            recording_events.append("start")

        def check(self):
            pass

        def stop(self):
            assert json.loads((self.folder / "manifest.json").read_text())[
                "status"
            ] in ("completed", "time_limit")
            recording_events.append("stop")

    monkeypatch.setattr(runner, "RunRecorder", Recorder)

    class Module:
        cancelled = False

        def begin_run(self):
            assert recording_events == ["start"]
            recording_events.append("begin")

        def observation(self):
            return base64.b64encode(image.getvalue()).decode()

        def submit(self, *args):
            pass

        def status(self):
            return {"state": "rejected", "error": "Submit fewer strokes"}

        def finish(self):
            pass

        def cancel(self):
            self.cancelled = True

    module = Module()
    audit = SimpleNamespace(event_count=lambda: 1)
    coordinator = SimpleNamespace(
        get_instance=lambda cls: module if cls is runner.PaintModule else audit,
        stop=lambda: None,
    )
    monkeypatch.setattr(runner.ModuleCoordinator, "build", lambda _: coordinator)

    class Policy:
        calls = 0

        def __init__(self, *args):
            pass

        def next(self, camera, remaining, feedback):
            self.calls += 1
            if timeout:
                raise runner.BenchmarkDeadline("30-minute wall-clock deadline")
            if self.calls == 1:
                return Batch.model_validate(
                    {"strokes": [{"points": [[20, 20], [30, 30]]}], "done": True}
                )
            assert feedback["state"] == "rejected"
            return Batch.model_validate({"strokes": [], "done": True})

    monkeypatch.setattr(runner, "Astra", Policy)
    folder = runner.run("astra", run_dir=tmp_path / "result")
    manifest = json.loads((folder / "manifest.json").read_text())
    assert manifest["status"] == ("time_limit" if timeout else "completed")
    assert module.cancelled == timeout
    assert recording_events == ["start", "begin", "stop"]
    assert manifest["video_status"] == "completed"
