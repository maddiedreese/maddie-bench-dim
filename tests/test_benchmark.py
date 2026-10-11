import time
import numpy as np
import pytest
from pydantic import ValidationError
from maddie_dim.budget import Budget, BudgetExceeded
from maddie_dim.protocol import Batch
from maddie_dim.sim import PaintSim, DeadlineReached, PreflightError


def batch(force=0.25):
    return Batch.model_validate(
        {"strokes": [{"points": [[85, 140], [115, 140]], "force_N": force}]}
    )


def test_budget_reservations_survive_restart_and_timeout(tmp_path):
    path = tmp_path / "budget.json"
    b = Budget(path, limit=1)
    token = b.reserve(10000, 1000)
    assert Budget(path, limit=1).total() == pytest.approx(0.325)
    with pytest.raises(BudgetExceeded):
        b.reserve(30000, 1000)
    b.settle(token, 1000, 100)
    assert Budget(path, limit=1).total() == pytest.approx(0.0325)


def test_protocol_rejects_unsafe_coordinates_and_nonfinite_force():
    for stroke in [
        {"points": [[0, 0], [100, 100]]},
        {"points": [[20, 20], [30, 30]], "force_N": float("nan")},
        {"points": [[20, 20], [30, 30]], "force_N": 2},
    ]:
        with pytest.raises(ValidationError):
            Batch.model_validate({"strokes": [stroke]})


def test_portrait_frame_roundtrip_and_reachable_corners():
    sim = PaintSim()
    assert sim.world([105, 12])[0] > sim.world([105, 285])[0]  # top is away from arm
    assert sim.world([12, 148.5])[1] > sim.world([198, 148.5])[1]
    for p in [[12, 12], [198, 12], [12, 285], [198, 285]]:
        np.testing.assert_allclose(sim.paper_xy(sim.world(p)), p, atol=1e-10)
        sim.ik(sim.world(p, -0.00035), sim.qtarget)


def test_rejected_plan_and_deadline_do_not_deposit_ink():
    sim = PaintSim()
    before = sim.data.qpos.copy()
    with pytest.raises(PreflightError):
        sim.ik(np.array([9.0, 0.0, 0.0]), sim.qtarget)
    sim.started = time.monotonic() - 1800
    with pytest.raises(DeadlineReached):
        sim.execute(batch())
    np.testing.assert_equal(sim.data.qpos, before)
    assert np.asarray(sim.canvas).min() == 255


def test_lifted_pen_cannot_draw_even_when_ink_requested():
    sim = PaintSim()
    for _ in range(1000):
        sim.step(expected_ink=True)
    assert sim.force == 0
    assert np.asarray(sim.canvas).min() == 255


def test_camera_randomness_does_not_change_motor_simulation():
    a = PaintSim()
    b = PaintSim()
    b.camera_rng.normal(size=10000)
    for _ in range(500):
        a.step()
        b.step()
    np.testing.assert_array_equal(a.data.qpos, b.data.qpos)


def test_increasing_force_changes_actual_contact_and_marks():
    outcomes = []
    for target in [0.08, 0.6]:
        sim = PaintSim()
        sim.execute(batch(target))
        samples = [
            t["force_N"]
            for t in sim.trace
            if t["expected_ink"] and t["force_target_N"] == target
        ]
        arr = np.asarray(sim.canvas)
        outcomes.append((np.mean(samples), arr[arr < 240].mean(), sim.peak_force))
    assert outcomes[1][0] > outcomes[0][0] + 0.10
    assert outcomes[1][1] < outcomes[0][1] - 5
    assert all(o[2] < 3 for o in outcomes)
