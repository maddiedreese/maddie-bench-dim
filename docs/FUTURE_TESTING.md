# Future testing and hardware experiments

The completed 30-minute simulation is the baseline. These are planned experiments; they have not been performed and do not change the recorded run or current protocol.

## 1. Longer wall-clock budgets

Compare the current 30-minute limit with a separate 60-minute condition, optionally including 45 minutes. Keep the reference, model settings, paper, pen, camera, controller and starting state fixed, and record the full wall-clock video for every attempt. Model thinking, API latency, planning, drawing and inspections still count toward the limit.

Measure composition coverage, blinded portrait likeness, executed strokes, rejected batches, model latency, motion time and API cost. Repeat each condition before attributing improvement to additional time. The first completed run left the curtain background and extra hair strands unfinished, making those useful details to track. Also examine batch-duration feedback and time allocation: a longer budget may help, but it does not by itself fix inefficient motion or repeated oversized requests.

An hour-long run requires a separately versioned protocol and an audit of every deadline check, model instruction, error message, viewer clock and test that currently assumes 30 minutes. Preserve the $100 project ledger; do not launch additional paid runs as part of this documentation change.

## 2. Actual paper and paint-pen specifications

Record the exact paper manufacturer/product, size, grammage, thickness, surface finish, coating/absorbency, backing surface and tape layout. Obtain published specifications where available and measure the remaining properties on the physical setup.

For the black POSCA PC-1MR, record the product and tip variant, actual uncapped mass, barrel dimensions, nib protrusion, grip position, wrist-to-tip transform and priming procedure. Characterize nib deflection, contact friction and slip in the mounted gripper. The nominal 0.7 mm tip specification does not supply a force-to-mark calibration.

Use repeated dots and lines across several force targets, speeds and directions. Measure line width, darkness, continuity, pooling, drying and paper damage, including approach/lift transients and different priming states. Use independent force measurements during commissioning if available and explicitly document uncertainty otherwise. Fit the simulator on calibration coupons, then test it on held-out coupons and the full paper workspace. Physical measurements replace provisional constants; they are not selected to make portraits look better.

## 3. Actual paints

Explore paint applied with a brush or another suitable applicator as a separate task variant. Begin with one black paint so that changes in tool and material behavior can be studied before adding color. Choose and record the paint formulation, dilution, applicator geometry and loading procedure when materials are available.

Start with controlled coupons to characterize applicator deformation, force/speed/angle effects, paint loading and depletion, transfer, spreading, drying and paper absorption. Then attempt the portrait under a frozen material profile. Define whether dipping, reloading, cleaning and tool changes are included in the timed task; a preloaded-tool experiment and an autonomous reload experiment are different conditions.

The current rigid fine-tip pen and heuristic ink model cannot represent a loaded brush accurately. Extend and validate the contact and deposition models before claiming sim-to-real transfer for actual paints. New material/tool conditions should be reported separately from the PC-1MR baseline.

## Hardware prerequisites

Resolve which DimOS models and calibration data apply to the supplied Anvil OpenYAM and retained gripper. The planning/gravity split and a draft question for the maintainers are documented in [MODEL_ALIGNMENT.md](MODEL_ALIGNMENT.md). Then follow the measured commissioning steps in [TRANSFER.md](TRANSFER.md), beginning with noncontact motion and calibration coupons before replaying a portrait.

Record hardware/firmware versions, model hashes, transforms, material specifications and measurement uncertainty with each hardware run. Simulation completion is evidence of the software workflow; hardware results must establish physical accuracy separately.
