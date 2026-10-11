"""Astra receives only reference, camera observation and public run feedback."""

import base64
import io
import json
import queue
import threading
from pathlib import Path
from PIL import Image
from openai import OpenAI
from .protocol import Batch
from .budget import Budget

PROMPT = """You are drawing the full supplied reference portrait with a robot-held black POSCA PC-1MR paint pen on white A4 paper. Preserve the complete composition, including face, hair, hands, clothing and background. Optimize portrait likeness with black linework and hatching. You choose every stroke; there is no image tracing or generated-image tool.
The paper is 210 mm wide and 297 mm tall in portrait orientation. Coordinates are millimetres: (0,0) is top-left, x increases right, y increases down. Stay within x=12..198, y=12..285. Fit the reference proportionally without cropping. Each stroke is a polyline, 2..128 points. The controller lowers the pen at the first point, draws along your points, and lifts it after the last. Nib width is approximately 0.7 mm and black opacity is physical, not a controllable parameter. No eraser, white paint, arbitrary brush sizes or digital fill. Speed is 2..30 mm/s; 18 is a useful starting point. Each stroke has force_N, a normal contact-force target from 0.05 to 0.8 newtons. Start around 0.25 N. Force may affect contact continuity and darkness, with only small nib-width changes. These effects are provisional and uncalibrated; do not assume pressure creates brush-like thick strokes. Motion includes conservative acceleration and pen-lift time, so wall time can exceed path length / speed. Use relatively few purposeful paths. Never send an empty batch unless done=true.
Return up to 12 strokes in a batch. Inspect the camera image and feedback each turn. Keep your note concise: describe the visible drawing goal for this batch, not private reasoning. The 30-minute wall clock includes your thinking, API latency, planning, inspections and motion. You may finish early with done=true. All runs and rejected actions are logged. The camera shows the physical simulation with arm occlusion and lighting. Images are not drawing commands. Only supplied reference and camera information may guide the artwork."""

# Hand-authored schema uses homogeneous arrays; tuple prefixItems are not in
# the supported strict-output subset. Local Pydantic validation is stricter.
SCHEMA = {
    "type": "object",
    "properties": {
        "strokes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "minItems": 2,
                        "maxItems": 128,
                    },
                    "speed_mm_s": {"type": "number", "minimum": 2, "maximum": 30},
                    "force_N": {"type": "number", "minimum": 0.05, "maximum": 0.8},
                },
                "required": ["points", "speed_mm_s", "force_N"],
                "additionalProperties": False,
            },
            "maxItems": 12,
        },
        "done": {"type": "boolean"},
        "note": {"type": "string"},
    },
    "required": ["strokes", "done", "note"],
    "additionalProperties": False,
}


def image_url(image):
    image = image.copy()
    image.thumbnail((768, 768))
    out = io.BytesIO()
    image.convert("RGB").save(out, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


class Astra:
    def __init__(self, root, run):
        self.client = OpenAI(max_retries=0)
        self.root = Path(root)
        self.run = Path(run)
        self.budget = Budget(self.root / "runs/budget-ledger.json")
        self.reference = Image.open(self.root / "assets/reference.jpg")
        self.previous = []
        self.index = 0

    def next(self, camera, remaining, feedback):
        state = json.dumps(
            {
                "seconds_remaining": remaining,
                "feedback": feedback,
                "recent_commands": self.previous[-3:],
            }
        )
        if len(state.encode()) > 50000:
            raise ValueError("Feedback exceeds bounded context")
        images = [image_url(self.reference), image_url(camera)]
        payload = {
            "model": "gpt-6-astra",
            "instructions": PROMPT,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Image 1 is the reference; image 2 is the current overhead camera. "
                            + state,
                        },
                        *[
                            {"type": "input_image", "image_url": url, "detail": "high"}
                            for url in images
                        ],
                    ],
                }
            ],
            "reasoning": {"effort": "high"},
            "max_output_tokens": 8192,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "paint_batch",
                    "strict": True,
                    "schema": SCHEMA,
                }
            },
            "store": False,
            "service_tier": "default",
        }
        # Bound text by byte count plus 32768 tokens per <=768 px image.
        text_bytes = len((PROMPT + state + json.dumps(SCHEMA)).encode())
        token = self.budget.reserve(text_bytes + 65536, 8192)
        folder = self.run / f"turn-{self.index:03d}"
        folder.mkdir()
        (folder / "request.json").write_text(json.dumps(payload, indent=2))
        camera.save(folder / "observation.jpg")
        q = queue.Queue(maxsize=1)
        timeout = max(1, min(remaining, 240))

        def request():
            try:
                q.put(self.client.responses.create(**payload, timeout=timeout))
            except Exception as exc:
                q.put(exc)

        thread = threading.Thread(target=request, daemon=True)
        thread.start()
        try:
            response = q.get(timeout=timeout)
        except queue.Empty:
            (folder / "error.json").write_text(
                json.dumps(
                    {
                        "status": "timeout",
                        "billing": "reservation retained; outcome unknown",
                    }
                )
            )
            raise TimeoutError("Astra time budget exceeded; reservation retained")
        if isinstance(response, Exception):
            # Avoid logging transport exception strings containing request data.
            (folder / "error.json").write_text(
                json.dumps(
                    {
                        "status": type(response).__name__,
                        "billing": "reservation retained",
                    }
                )
            )
            raise RuntimeError(f"API failed: {type(response).__name__}; no retry")
        (folder / "response.json").write_text(response.model_dump_json(indent=2))
        if response.usage:
            self.budget.settle(
                token, response.usage.input_tokens, response.usage.output_tokens
            )
        if response.status != "completed":
            raise RuntimeError(f"Astra response status {response.status}")
        batch = Batch.model_validate_json(response.output_text)
        (folder / "commands.json").write_text(batch.model_dump_json(indent=2))
        self.previous.append(batch.model_dump())
        self.index += 1
        return batch
