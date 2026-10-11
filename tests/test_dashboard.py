import json, os, time
import pytest
from fastapi import HTTPException
from maddie_dim import dashboard


def test_clock_keeps_running_during_model_thinking(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    run = tmp_path / "runs/demo"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps({"status": "starting", "mode": "astra"})
    )
    status = run / "status.json"
    status.write_text(json.dumps({"state": "ready", "wall_seconds": 10}))
    stamp = time.time() - 30
    os.utime(status, (stamp, stamp))
    result = dashboard.runs()[0]
    assert 39 <= result["live"]["elapsed_now_seconds"] <= 42
    (run / "manifest.json").write_text(
        json.dumps({"status": "completed", "mode": "astra"})
    )
    assert dashboard.runs()[0]["live"]["elapsed_now_seconds"] == 10


def test_viewer_cannot_serve_env_or_escape_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    run = tmp_path / "runs/demo"
    run.mkdir(parents=True)
    (tmp_path / ".env").write_text("TEST_SECRET=local-only")
    for filename in [".env", "../../.env", "request.json"]:
        with pytest.raises(HTTPException):
            dashboard.artifact("demo", filename)
    with pytest.raises(HTTPException):
        dashboard.run_path("../..")
