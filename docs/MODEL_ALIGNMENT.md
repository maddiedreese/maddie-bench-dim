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

## Alignment validation

Confirm and record the exact hardware/model versions. Establish joint and base/tool mappings, then compare FK at identical physical joint configurations using matched physical reference frames across the drawing workspace. Reconcile wrist, gripper, fingers and pen mass contributions without double-counting them, and check predicted static torques against physical measurements. Use one owner of gravity compensation in the control path. Update the simulator and tests under a new protocol revision, then validate noncontact and contact coupons before replaying the portrait.
