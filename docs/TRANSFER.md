# Path to physical OpenYAM

The policy protocol, portrait coordinate frame, trajectory constraints, telemetry format and force-estimation equations are designed for reuse. **This release does not enable live hardware motion.** It has no tested physical commissioning profile. Presenting a simulator as a calibrated plug-and-play hardware implementation would overstate the evidence.

The pinned DimOS release supplies `OpenYamDamiaoAdapter` and native macOS `gs_usb` transport. Its arm joints are `yam_joint1`…`yam_joint6`; DM4340 motors occupy IDs 1–3 and DM4310 motors IDs 4–6, with the gripper at ID 8. The adapter reads position, velocity and motor torque, and writes MIT commands. This supplies the concrete hardware integration point without introducing a different robotics middleware.

Two upstream behaviors must be addressed before swapping transports:

1. `DamiaoWholeBodyAdapter.write_motor_commands` **adds gravity compensation** unless `DamiaoRuntimeConfig.gravity_comp=False`. Our simulation already includes bias compensation. Passing those torques directly would double-count gravity. Use one owner of gravity compensation and validate its mass model. The simulation excludes the source URDF's old flexible-finger masses when substituting the Anvil hand, so its provisional load model also differs from the adapter's full default URDF.
2. Adapter activation calibrates the gripper. The benchmark starts with a mounted, primed pen, so activation/calibration must finish before mounting the pen and before the timed run. Confirm that later activation cannot open or recalibrate the grasp.

## Commissioning evidence required

1. Confirm Anvil's exact arm version, zero poses, axis directions, joint limits, motor mapping, inertias and effort limits. Confirm the intended alignment of DimOS's separate planning/gravity models with Dimensional/Anvil; see the [model-alignment review](MODEL_ALIGNMENT.md). Match independent FK and measured poses across the workspace.
2. Measure the mounted PC-1MR tool transform and mass. Record finger variant, grip width, protrusion, slip behavior and gripper hold settings. The current 190 mm tool length is an estimate.
3. Calibrate camera intrinsics/distortion, camera-to-base and paper-to-base transforms. Fit the plane and identify its four corners. Validate across the full 12 mm margin rectangle.
4. Begin with noncontact motions above the sheet, then single dots and short lines. Measure normal force externally during commissioning if available; do not treat motor-torque inference as a calibrated force sensor. Fit torque offsets/friction, nib compliance and an empirical force/speed/ink response with held-out coupons.
5. Measure feedback age and CAN/control timing on the intended Mac. A 500 Hz simulation controller does not establish a reliable 500 Hz Python/macOS hardware loop. Use the DimOS/native control path for bounded execution; handle stale telemetry, disconnects, sustained tracking errors and emergency stops locally.
6. Validate held-out force targets and trajectories, including near/far corners and approach/lift transients. Re-run the same benchmark commands under a frozen measured profile before allowing model commands.

The existing contact abort (3 N), 0.5 rad/s joint velocity, 1 rad/s² acceleration, and 10 Nm effort limits are **simulation settings, not certified hardware limits**. No live operation is attempted in this project without the arm. The grant demonstration can show real DimOS orchestration, reproducible physics, force-estimation control, camera feedback and a clear calibration plan; physical accuracy remains an explicit future measurement.

The planned longer-duration, measured paper/pen and actual-paint experiments are described in [FUTURE_TESTING.md](FUTURE_TESTING.md).
