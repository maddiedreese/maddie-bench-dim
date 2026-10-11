# Validation record

Local execution on Apple Silicon macOS, Python 3.11, MuJoCo 3.15 and the pinned DimOS commit. No physical arm or API key was used for the controller demonstration.

The automated suite covers persistent spend reservations, invalid/nonfinite model commands, portrait coordinate orientation and four reachable corners, preflight/deadline rejection before ink deposition, absence of marks with the pen lifted, independence of camera randomness from physics, increasing actual force/darkness under increased force targets, and independent Pinocchio-versus-MuJoCo FK at five paper locations. Eight tests pass.

The included example is a four-stroke controller coupon, not a model-generated portrait. The three horizontal strokes request 0.08, 0.25 and 0.6 N; the diamond requests 0.25 N. `force-summary.json` gives actual/estimated mean force during commanded drawing. All transient forces remain in the trace; averages do not hide approach forces. The arm physically parks out of the camera's way after drawing.

A real two-worker DimOS blueprint executes this coupon. Its independent audit subscriber must receive telemetry before the run can report success. See the example's manifest and physics files for the precise run measurements and hashes. The demo is accelerated; its wall time is not a valid Astra benchmark time.

Early numerical exploration compared 0.25 ms and 0.1 ms contact integration: deposited length for a nominal 25 mm line was approximately 23.86 and 24.03 mm respectively. This supported choosing 0.1 ms, but is not a complete convergence study or empirical validation of a POSCA nib. The 3D tracking maximum includes force-induced normal displacement and movement/parking transients; planar error is reported separately. Both are waypoint-end maxima, not continuous path-wide bounds.

## Remaining evidence

- Actual Astra portrait run and full 30-minute timing path with API latency.
- Measured physical arm/gripper/pen/camera parameters and hardware execution.
- Robustness sweeps over calibration error, friction, nib compliance, sensor noise and control latency; current seed tests do not establish robustness.
- Physical pen force/ink calibration and held-out validation, including whether useful pressure-induced variation is large enough for this nib.
- Multiple runs and blinded portrait-likeness judging before comparative model claims.

A completed simulation demonstrates the software path and its modeled behavior. It does not establish real-arm success or a quantitative likeness ranking.
