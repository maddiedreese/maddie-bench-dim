"""Full wall-clock video of saved simulator cameras, including thinking time."""

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw


class RunRecorder:
    fps = 2

    def __init__(self, folder):
        self.folder = Path(folder)
        self._stop = threading.Event()
        self._ready = threading.Event()
        self.error = None
        self.frames = 0

    def start(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to record the full Astra run")
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.started = time.monotonic()
        self._log = (self.folder / "recording-encoder.log").open("w")
        self._proc = subprocess.Popen(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                "1280x760",
                "-r",
                str(self.fps),
                "-i",
                "-",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(self.folder / "full-run.mp4"),
            ],
            stdin=subprocess.PIPE,
            stderr=self._log,
        )
        self._thread = threading.Thread(target=self._record, daemon=True)
        self._thread.start()
        if not self._ready.wait(15):
            self.stop()
            raise RuntimeError("Video recorder did not become ready")
        self.check()

    def check(self):
        if self.error:
            raise RuntimeError(f"Full-run recording failed: {self.error}")

    def _frame(self):
        frame = Image.new("RGB", (1280, 760), (20, 23, 23))
        draw = ImageDraw.Draw(frame)
        for x, name, label in [
            (0, "overview.jpg", "Arm overview"),
            (640, "overhead.jpg", "Overhead camera"),
        ]:
            with Image.open(self.folder / name) as source:
                im = source.convert("RGB")
            im.thumbnail((640, 640))
            frame.paste(im, (x + (640 - im.width) // 2, 60 + (640 - im.height) // 2))
            draw.text((x + 16, 42), label, fill="white")
        state = json.loads((self.folder / "status.json").read_text())
        manifest = json.loads((self.folder / "manifest.json").read_text())
        elapsed = max(0, time.monotonic() - self.started)
        if manifest.get("timed_run_started_utc"):
            elapsed = max(
                0,
                (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(manifest["timed_run_started_utc"])
                ).total_seconds(),
            )
        draw.text(
            (16, 14),
            "maddie-bench / dim | full wall-clock run | 1x playback | 2 fps saved cameras",
            fill="white",
        )
        draw.text(
            (16, 712),
            f"Elapsed {elapsed:07.1f} s | {manifest['status']} / {state['state']} | last camera motion sample {state.get('wall_seconds', 0):.1f} s",
            fill="white",
        )
        draw.text(
            (16, 738),
            "Provisional simulation. Physical transfer and POSCA force/ink response are unverified. Camera views hold during model thinking.",
            fill=(190, 200, 200),
        )
        return frame

    def _write(self):
        frame = self._frame()
        # Preserve wall-clock duration even if the encoder temporarily falls behind.
        target = int((time.monotonic() - self.started) * self.fps) + 1
        for _ in range(max(1, target - self.frames)):
            self._proc.stdin.write(frame.tobytes())
            self.frames += 1

    def _record(self):
        try:
            self._write()
            self._ready.set()
            while not self._stop.wait(
                max(0, self.frames / self.fps - (time.monotonic() - self.started))
            ):
                self._write()
            self._write()  # Retain the terminal result as well as the initial blank sheet.
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self._ready.set()
        finally:
            try:
                self._proc.stdin.close()
                code = self._proc.wait(timeout=30)
                if code:
                    self.error = f"ffmpeg exited {code}; see recording-encoder.log"
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {exc}"
                self._proc.kill()
                self._proc.wait()
            self._log.close()
            (self.folder / "recording.json").write_text(
                json.dumps(
                    {
                        "file": "full-run.mp4",
                        "frames": self.frames,
                        "fps": self.fps,
                        "playback_speed": 1,
                        "started_utc": self.started_utc,
                        "finished_utc": datetime.now(timezone.utc).isoformat(),
                        "wall_duration_s": time.monotonic() - self.started,
                        "video_duration_s": self.frames / self.fps,
                        "status": "failed" if self.error else "completed",
                        "error": self.error,
                        "coverage": "Recorder ready before timed benchmark begins; stops after terminal manifest. Includes model thinking. Setup excluded.",
                        "camera_sampling": "Actual saved camera views, updated every 0.5 simulation seconds during motion. Views hold while idle; no interpolated motion.",
                    },
                    indent=2,
                )
            )

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=45)
        if self._thread.is_alive():
            self.error = "Video recorder shutdown timed out"
        self.check()
