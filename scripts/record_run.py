"""Record sampled run artifacts as a clearly labeled accelerated review video.

No rendering or physics is synthesized here: frames are the actual saved cameras.
Start alongside a run; the recording may begin after the benchmark begins.
"""

import argparse, json, subprocess, time, shutil
from pathlib import Path
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument("run_dir")
p.add_argument("--interval", type=float, default=2)
a = p.parse_args()
if not 0 < a.interval <= 60:
    p.error("interval must be in (0,60] seconds")
r = Path(a.run_dir)
ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    raise SystemExit("ffmpeg is required for optional video recording")
out = r / "review-timelapse.mp4"
proc = subprocess.Popen(
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
        "840x630",
        "-r",
        "12",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ],
    stdin=subprocess.PIPE,
)
first = None
count = 0
try:
    while True:
        manifest = json.loads((r / "manifest.json").read_text())
        try:
            state = json.loads((r / "status.json").read_text())
            frame = Image.new("RGB", (840, 630), (20, 23, 23))
            draw = ImageDraw.Draw(frame)
            for x, name in [(0, "overview.jpg"), (420, "overhead.jpg")]:
                im = Image.open(r / name).convert("RGB")
                im.thumbnail((420, 570))
                frame.paste(im, (x + (420 - im.width) // 2, 40))
            wall = state.get("wall_seconds", 0)
            if first is None:
                first = wall
            draw.text(
                (15, 12),
                f"maddie-bench / dim | {manifest['mode']} | sampled cameras, {12 * a.interval:g}x playback",
                fill="white",
            )
            draw.text(
                (15, 610),
                f"Last motion sample: {wall:.1f} s | {state['state']} | physical calibration pending",
                fill="white",
            )
            proc.stdin.write(frame.tobytes())
            count += 1
        except (FileNotFoundError, ValueError, OSError):
            pass
        if manifest["status"] in ["completed", "failed"]:
            break
        time.sleep(a.interval)
finally:
    proc.stdin.close()
    proc.wait()
(r / "recording.json").write_text(
    json.dumps(
        {
            "file": out.name,
            "frames": count,
            "sample_interval_wall_s": a.interval,
            "playback_fps": 12,
            "first_motion_wall_s": first,
            "note": "Sampled actual camera artifacts; recording started after run began; not a full video of setup or all initial strokes.",
        },
        indent=2,
    )
)
print(out)
