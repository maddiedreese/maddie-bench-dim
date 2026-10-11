"""Paper coordinates: short edge toward arm, long edge extending away."""

import numpy as np

# Arm base is at world origin; the sheet lies flat in front along +X.
RIGHT = np.array([0.0, -1.0, 0.0])
DOWN = np.array([-1.0, 0.0, 0.0])
NORMAL = np.array([0.0, 0.0, 1.0])
PAPER_ROTATION = np.column_stack((RIGHT, -DOWN, NORMAL))
