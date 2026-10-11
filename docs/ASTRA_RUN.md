# Astra simulation run — October 11, 2026

Run `20261011T214132720309Z` completed through the real two-worker DimOS blueprint. Astra chose to finish before the deadline. This demonstrates a working simulated execution and observation loop; it does not establish physical-arm performance or a portrait-likeness score.

![Actual contact-deposited portrait](../examples/astra/paper.png)

| Measurement | Result |
| --- | --- |
| Model | `gpt-6-astra`, high reasoning |
| Protocol | `maddie-dim-v0.2-draft` |
| Recorded source revision | `e538b29`; all recorded Python hashes matched the checkout |
| Wall time | 1,751 seconds, approximately 29:11, including API latency |
| Model turns | 13 |
| Executed strokes | 48 in four accepted batches |
| Rejected batches | Eight; none deposited ink |
| Final model action | Empty batch with `done=true` |
| Deposited path length | 5,311.74 mm |
| Requested drawing forces | 0.23, 0.24, 0.25, 0.26 and 0.27 N |
| Peak actual simulated contact force | 0.532 N |
| Maximum planar waypoint-end error | 1.50 mm; not a continuous path-wide bound |
| Independent DimOS audit events | 2,928 |
| Conservative API cost accounting | $2.41255 for this run; $3.725125 project cumulative |
| Full camera recording | 29:12, 3,504 frames, 2 fps, 1280 × 760, 1× wall-clock playback |

The cost figures use the project's conservative token rates, not a provider invoice. The persistent $100 budget ledger remains intact.

The drawing contains the hair silhouette, face, hands, forearms and hatched clothing. The planned curtain background and additional interior hair strands were not executed. Near the deadline, Astra repeatedly proposed batches exceeding the remaining motion budget; the controller rejected them before execution and returned duration feedback. The model ultimately finished with the existing drawing. The timing-recovery fix worked, while time allocation and composition completeness remain weaknesses exposed by this run.

The full video began before the timed benchmark and includes model thinking, motion, and the terminal result. Its complete stream decoded without errors. The first and last frames were visually checked. It is retained locally as `runs/20261011T214132720309Z/full-run.mp4` (about 42 MB); its hash and stream measurements are published in [video-verification.json](../examples/astra/video-verification.json). Camera views hold while the simulator is idle; there is no interpolated motion. This is full timed-run coverage, excluding setup.

The [evidence directory](../examples/astra/) retains the final images, manifest, recording metadata, physical metrics, force analysis and all validated commands with execution outcomes. Full API responses, camera observations, joint traces and audit logs remain in the local run directory. The earlier failed pilot is also retained locally and is described in [validation](VALIDATION.md).

The gripper remains mounted. Hand mass, grip transform, pen compliance, pressure-dependent ink behavior, camera optics and motor sensing remain provisional. Physical calibration and commissioning described in [TRANSFER.md](TRANSFER.md) are still required. The narrow range of force targets in this run does not establish broad pressure-control robustness or empirical POSCA behavior.
