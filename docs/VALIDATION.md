# Validation record

Local execution on Apple Silicon macOS, Python 3.11, MuJoCo 3.15 and the pinned DimOS commit. No physical arm or API key was used for the controller demonstration.

The automated suite covers persistent spend reservations, invalid/nonfinite model commands, portrait coordinate orientation and four reachable corners, preflight/deadline rejection before ink deposition, absence of marks with the pen lifted, independence of camera randomness from physics, increasing actual force/darkness under increased force targets, and independent Pinocchio-versus-MuJoCo FK at five paper locations. A separate gravity check validates the selected six-link inertials plus pen/nib load against Pinocchio, with the replaced old-finger masses explicitly excluded. Fourteen tests pass, including two viewer checks for elapsed time during model thinking and blocking secret/path-traversal access.

The included example is a four-stroke controller coupon, not a model-generated portrait. The three horizontal strokes request 0.08, 0.25 and 0.6 N; the diamond requests 0.25 N. `force-summary.json` gives actual/estimated mean force during commanded drawing. All transient forces remain in the trace; averages do not hide approach forces. The arm physically parks out of the camera's way after drawing.

A real two-worker DimOS blueprint executes this coupon. Its independent audit subscriber must receive telemetry before the run can report success. See the example's manifest and physics files for the precise run measurements and hashes. The demo is accelerated; its wall time is not a valid Astra benchmark time.

Early numerical exploration compared 0.25 ms and 0.1 ms contact integration: deposited length for a nominal 25 mm line was approximately 23.86 and 24.03 mm respectively. This supported choosing 0.1 ms, but is not a complete convergence study or empirical validation of a POSCA nib. The 3D tracking maximum includes force-induced normal displacement and movement/parking transients; planar error is reported separately. Both are waypoint-end maxima, not continuous path-wide bounds.

Protocol v0.2 adds a recoverable rejection when a proposed batch cannot fit the remaining time. The model receives the rejection and can submit fewer strokes; actual deadline expiry is a `time_limit` outcome. Tests cover both paths and ensure recording starts before the benchmark clock and stops after its terminal manifest. A real two-worker DimOS integration check separately verified that an oversized batch leaves the sheet untouched and a shorter retry executes with audit telemetry.

The first Astra pilot ended after about 24 minutes because the earlier runner incorrectly treated that preflight rejection as fatal. It executed 48 strokes before the failure; its failed manifest and artifacts are preserved. It is not reported as a completed benchmark.

Full-run recording was exercised through the actual DimOS controller demo: ffprobe confirmed 67 frames at 2 fps (33.5 seconds) for 33.01 seconds of recording wall time. The first frame precedes the benchmark clock; the final frame shows the completed coupon and terminal status. The real-time Astra run uses the same recorder.

An actual Astra run subsequently completed in 29:11 with 48 executed strokes, eight rejected batches and 2,928 independent DimOS audit events. The full video was decoded without errors and its first/last frames were checked. See [the run report](ASTRA_RUN.md); completion does not mean the portrait reproduces every reference detail.

## Remaining evidence

- Actual deadline-expiry path in a full Astra run: the completed run finished voluntarily at 29:11, so it exercised near-deadline batch rejection but not the final 1,800-second cutoff. Unit tests cover expiry.
- Measured physical arm/gripper/pen/camera parameters and hardware execution.
- Robustness sweeps over calibration error, friction, nib compliance, sensor noise and control latency; current seed tests do not establish robustness.
- Physical pen force/ink calibration and held-out validation, including whether useful pressure-induced variation is large enough for this nib.
- Multiple runs and blinded portrait-likeness judging before comparative model claims.

A completed simulation demonstrates the software path and its modeled behavior. It does not establish real-arm success or a quantitative likeness ranking.
