"""Check the converter against an independent URDF implementation."""
import numpy as np
import mujoco
import pinocchio as pin
from maddie_dim.config import ROOT
from maddie_dim.sim import PaintSim


def test_mujoco_tip_matches_pinocchio_across_paper():
    sim=PaintSim()
    model=pin.buildModelFromUrdf(str(ROOT/'assets/vendor/yam_description/urdf/yam_gripper_gravity.urdf'))
    data=model.createData()
    for xy in [[12,12],[198,12],[12,285],[198,285],[105,148.5]]:
        q=sim.ik(sim.world(xy,.01),sim.qtarget)
        sim.data.qpos[:6]=q;mujoco.mj_forward(sim.model,sim.data)
        pin.forwardKinematics(model,data,q);pin.updateFramePlacements(model,data)
        wrist=data.oMf[model.getFrameId('yam_link_6')]
        expected=wrist.translation+wrist.rotation@np.array([0,0,.19])
        np.testing.assert_allclose(expected,sim.tip(),atol=1e-8)
