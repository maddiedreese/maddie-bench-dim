"""Controller equations shared with the eventual hardware commissioning path.

Force is inferred from motor torque and rigid-body dynamics. This is not a
wrist force sensor: model error, friction and telemetry noise affect accuracy.
"""

import numpy as np


class NormalForceControl:
    def __init__(self):
        self.filtered = 0.0
        self.offset = 0.0

    def update(self, normal_estimate, target, dt):
        self.filtered += (1 - np.exp(-dt / 0.04)) * (
            max(0.0, normal_estimate) - self.filtered
        )
        if target is None:
            desired = 0.0
        else:
            # Admittance: higher target moves the nominal tip into the sheet.
            desired = np.clip(
                self.offset - 0.002 * (target - self.filtered) * dt, -0.003, 0.001
            )
        self.offset += np.clip(desired - self.offset, -0.001 * dt, 0.001 * dt)
        return self.offset


def estimate_normal_force(
    mass, acceleration, bias, passive, motor_torque, jacobian, normal
):
    residual = mass @ acceleration + bias - passive - motor_torque
    wrench = np.linalg.lstsq(jacobian.T, residual, rcond=1e-4)[0]
    return float(np.dot(wrench[:3], normal))
