# DimOS planning and gravity model alignment

## What the pinned source establishes

This review concerns DimOS commit `1e7b4918bc626de4fa6592fb023d4b3aee932754`, used by the recorded benchmark. It does not assert that a later DimOS release has the same configuration.

| Use | Selected model | Evidence |
| --- | --- | --- |
| Visualization and motion planning | `yam_description/i2rt/yam.urdf` | [OpenYAM configuration](https://github.com/dimensionalOS/dimos/blob/1e7b4918bc626de4fa6592fb023d4b3aee932754/dimos/robot/manipulators/openyam/config.py); arm joints are renamed to `yam_joint1`…`yam_joint6`, planning base is `base`, tip is `gripper_tip` |
| Hardware gravity compensation | `yam_description/urdf/yam_gripper_gravity.urdf` | [OpenYamDamiaoAdapter](https://github.com/dimensionalOS/dimos/blob/1e7b4918bc626de4fa6592fb023d4b3aee932754/dimos/hardware/whole_body/openyam_damiao/adapter.py); gravity is evaluated using measured arm positions by the [Damiao adapter](https://github.com/dimensionalOS/dimos/blob/1e7b4918bc626de4fa6592fb023d4b3aee932754/dimos/hardware/whole_body/damiao/adapter.py) |
| This benchmark's simulation | Six-link conversion of the gravity URDF, with a provisional Anvil gripper/pen load | [Provenance](PROVENANCE.md) and independent FK/gravity checks in `tests/test_kinematics.py` |

The bundled [SOURCE_COMMIT.txt](../assets/vendor/yam_description/SOURCE_COMMIT.txt) explicitly documents the separate upstream sources and their intended uses. This is an intentional model split, not evidence by itself of a DimOS defect. Different link frames and URDF joint-axis representations can describe equivalent motion; raw transform differences alone do not prove incompatible kinematics.

The unanswered compatibility question is which geometry, joint zero/sign conventions, base/tool transforms and mass properties match the actual Anvil arm and gripper being supplied. Our independent checks establish that our conversion agrees with the selected source model. They do not establish that the planning model is equivalent or that either model is calibrated to that hardware.

There is also a separate, known payload approximation in our scene: the upstream wrist mass remains 0.95 kg, while the two old flexible-finger masses of 0.120713 kg each are removed when substituting the Anvil gripper visuals and pen. The reported approximately 0.87 Nm difference at the sampled paper poses concerns that payload change relative to the full gravity URDF. It is **not** a measured planning-versus-gravity-model error. The real replacement hand mass distribution remains unverified.

## Draft question for the DimOS team

Suggested subject: **Which OpenYAM model and payload calibration should we use for Anvil sim-to-real contact drawing?**

I'm building [maddie-bench-dim](https://github.com/maddiedreese/maddie-bench-dim), a DimOS-based contact-drawing benchmark intended for the Anvil OpenYAM with its customizable gripper holding a POSCA PC-1MR. A 29-minute Astra run has completed in simulation; I don't yet have the physical arm.

At DimOS commit `1e7b4918bc626de4fa6592fb023d4b3aee932754`, the planning configuration uses `yam_description/i2rt/yam.urdf`, while `OpenYamDamiaoAdapter.kinematic_model` uses `urdf/yam_gripper_gravity.urdf`. The bundled provenance documents this split. I'm trying to confirm how to align the simulator and controller with the arm we'll receive:

1. Are these two models intended to be compatible with the same current Anvil OpenYAM hardware revision? Which pinned model/revision should be authoritative for arm geometry, joint limits and dynamics?
2. Is the joint-position mapping between them identity after joint renaming, or are there encoder zero/sign offsets and base/wrist/tool transforms we should apply? Do you have a validated mapping or sample joint poses with expected tool poses?
3. What mass, center of mass and inertia does the default gravity URDF assume for the wrist and gripper? Does that include the purchasable Anvil customizable gripper and which fingers? What is the recommended way to configure the retained gripper plus mounted pen payload?
4. For a custom contact-force controller using motor-torque feedback, which DimOS integration path do you recommend so that gravity is applied once and the torque estimate uses the same calibrated model? Are torque calibration data or measured limitations available for this arm?

Our current simulator uses the gravity URDF's arm chain, with explicitly provisional gripper/pen properties. We can provide the model hashes, conversion checks, commands and run traces. A known-good model/calibration configuration for the supplied arm would help us replace those assumptions before hardware testing.

This is a prepared draft; it has not been sent or posted to the DimOS team.

## How we will close the question

Record the team's answer and exact hardware/model versions. Establish joint and base/tool mappings, then compare FK at identical physical joint configurations using matched physical reference frames across the drawing workspace. Reconcile wrist, gripper, fingers and pen mass contributions without double-counting them, and check predicted static torques against physical measurements. Use one owner of gravity compensation in the control path. Update the simulator and tests under a new protocol revision, then validate noncontact and contact coupons before replaying the portrait.
