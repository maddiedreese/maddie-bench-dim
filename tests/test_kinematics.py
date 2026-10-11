"""Check the converter against an independent URDF implementation."""

import numpy as np
import mujoco
import pinocchio as pin
from maddie_dim.config import ROOT
from maddie_dim.sim import PaintSim


def test_mujoco_tip_matches_pinocchio_across_paper():
    sim = PaintSim()
    model = pin.buildModelFromUrdf(
        str(ROOT / "assets/vendor/yam_description/urdf/yam_gripper_gravity.urdf")
    )
    data = model.createData()
    for xy in [[12, 12], [198, 12], [12, 285], [198, 285], [105, 148.5]]:
        q = sim.ik(sim.world(xy, 0.01), sim.qtarget)
        sim.data.qpos[:6] = q
        mujoco.mj_forward(sim.model, sim.data)
        pin.forwardKinematics(model, data, q)
        pin.updateFramePlacements(model, data)
        wrist = data.oMf[model.getFrameId("yam_link_6")]
        expected = wrist.translation + wrist.rotation @ np.array([0, 0, 0.19])
        np.testing.assert_allclose(expected, sim.tip(), atol=1e-8)


def test_selected_arm_gravity_matches_source_without_replaced_fingers():
    """Validate arm inertials separately from the provisional replacement hand."""
    import xml.etree.ElementTree as ET

    sim = PaintSim()
    urdf = ET.parse(
        ROOT / "assets/vendor/yam_description/urdf/yam_gripper_gravity.urdf"
    )
    for name in ["yam_right_finger", "yam_left_finger"]:
        link = urdf.find(f"link[@name='{name}']")
        link.remove(link.find("inertial"))
    model = pin.buildModelFromXML(ET.tostring(urdf.getroot(), encoding="unicode"))
    data = model.createData()
    for xy in [[12, 12], [198, 12], [12, 285], [198, 285], [105, 148.5]]:
        q = sim.ik(sim.world(xy, 0.01), sim.qtarget)
        sim.data.qpos[:6] = q
        sim.data.qvel[:] = 0
        mujoco.mj_forward(sim.model, sim.data)
        expected = pin.computeGeneralizedGravity(model, data, q).copy()
        for name in ["pen", "nib"]:
            body = sim.model.body(name).id
            jp = np.zeros((3, sim.model.nv))
            jr = np.zeros_like(jp)
            mujoco.mj_jacBodyCom(sim.model, sim.data, jp, jr, body)
            expected -= jp[:, :6].T @ (
                sim.model.body_mass[body] * sim.model.opt.gravity
            )
        np.testing.assert_allclose(expected, sim.data.qfrc_bias[:6], atol=1e-8)
