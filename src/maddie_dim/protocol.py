from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import math


class Stroke(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    points: list[tuple[float, float]] = Field(min_length=2, max_length=128)
    speed_mm_s: float = Field(default=18, ge=2, le=30)
    force_N: float = Field(default=0.25, ge=0.05, le=0.8)

    @field_validator("points")
    @classmethod
    def inside_paper(cls, points):
        for x, y in points:
            if not (
                math.isfinite(x)
                and math.isfinite(y)
                and 12 <= x <= 198
                and 12 <= y <= 285
            ):
                raise ValueError(
                    "Coordinates must be finite millimetres inside the 12 mm A4 margin"
                )
        return points


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strokes: list[Stroke] = Field(max_length=12)
    done: bool = False
    note: str = Field(default="", max_length=800)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.strokes and not self.done:
            raise ValueError("Empty batch must declare done")
        return self
