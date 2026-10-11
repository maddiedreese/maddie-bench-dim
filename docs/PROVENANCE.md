# Sources and assumptions

## Pinned source chain

| Item | Source |
| --- | --- |
| DimOS | https://github.com/dimensionalOS/dimos at `1e7b4918bc626de4fa6592fb023d4b3aee932754` |
| Hardware gravity URDF | DimOS LFS `yam_description`; upstream https://github.com/TomCC7/OpenYAM_description at `c24ef66cdcf87b9a767ec6ecd8ac8ae971bab2f7` |
| Different upstream planning model | https://github.com/i2rt-robotics/i2rt at `5d47b358bafb30c65e397f2ece506550a0db4594`; retained in vendor archive but NOT used by our simulator |
| Anvil gripper CAD | https://github.com/Anvil-Robotics/anvil-gripper-hw at `b688f64136c472f253b7ee0470a40cfce62a11c6` |
| Reference | https://github.com/maddiedreese/maddie-bench at `89f18f8c722711b3e1a666e16cb6e67b935b4428`, `reference-maddie-target.jpg` |

The DimOS LFS archive SHA-256 is `db9a2160e414830eb1c2203b573ec7557563d3f963667c19752d7da7e3e940f1`, 5,388,932 bytes. See the included `assets/vendor/yam_description/SOURCE_COMMIT.txt`. The official Anvil OpenYAM description/hardware repositories contained “Coming Soon” placeholders when inspected; no claim is made that this imported model is manufacturer-validated for the delivered arm.

Product sources: [OpenYAM](https://shop.anvil.bot/products/openyam), [gripper](https://shop.anvil.bot/products/customizable-gripper), [camera](https://shop.anvil.bot/products/60-fps-camera-module), [POSCA PC-1MR](https://www.posca.com/en-uk/product/pc-1mr/). The 0.7 mm PC-1MR has a calibrated fine tip; published specifications do not establish a pressure-to-width law.

The two upstream models are selected intentionally for different roles in the pinned DimOS source. Their alignment with each other and the supplied Anvil hardware still requires confirmation; separate source files alone do not establish a defect. See the [model-alignment review and draft maintainer question](MODEL_ALIGNMENT.md).

## Parameter status

| Parameter | Implementation | Status |
| --- | --- | --- |
| Arm frames, axes, mass/inertia, limits | Hardware gravity URDF conversion | Sourced; actual Anvil match unverified |
| Gripper outer geometry | Wide-tip fingers + base, STEP tessellation | Manufacturer CAD; assembly pose/closed offset estimated |
| Gripper inertia | Upstream wrist retains 0.95 kg; the two old flexible-finger masses (0.120713 kg each) are excluded | Replacement-hand approximation; not a measured Anvil gripper model |
| Pen | 130 mm long, 10 mm diameter, 12 g; wrist-to-tip 190 mm | Estimates; measure physical unit and grip |
| Nib | 1,500 N/m spring, damping 1.5 N·s/m; 1.5 mm travel | Provisional numerical/contact model |
| Paint marks | Actual normal contact >0.015 N; width 0.5–0.85 mm, force-dependent darkness | Heuristic, not measured POSCA data |
| Paper | 210 × 297 mm, margins 12 mm, center (0.24,0,0.0002) m | Benchmark fixture specification |
| Table/paper | Rigid plane; friction 0.4 | Provisional; no paper wrinkle/bending model |
| Joint/torque feedback | Ideal simulated position/velocity; torque noise σ=0.003 Nm; acceleration from sampled velocity | No measured encoder quantization, latency or independent model mismatch |
| Motor control | 500 Hz estimated-force admittance + torque-limited PD | Simulated; macOS/CAN timing unmeasured |
| Physics | MuJoCo 3.15, implicitfast, 0.1 ms step | Numerical choice, not measured hardware bandwidth |
| Camera | Fixed overhead, 42° vertical FoV, 840 × 1188 render, Gaussian noise σ=1 | Synthetic optics; not measured Anvil sensor specs |
| Ink dynamics | Bounded darkness and width; marks never erase | No ink depletion, drying, pooling, paper absorption or re-priming model |

The simulation freezes while waiting for model responses; the pen is parked between batches. The run's wall clock continues. Static holding drift and failures during idle API time are therefore not modeled. The initial ready pose is prepositioned and no setup trajectory is counted.

The replacement hand is a material dynamics assumption. Compared with the full upstream URDF, excluding its old flexible fingers changes static gravity torques by up to about 0.87 Nm at the tested paper corners/center. Independent Pinocchio checks agree with MuJoCo after those explicitly excluded inertials are removed and the new pen/nib mass is added. This validates the selected conversion, **not** the real gripper mass distribution. The full upstream hardware adapter's default gravity model is therefore also not interchangeable with this provisional scene without calibration.

Do not tune force-response constants to produce a nicer portrait and then report improved model capability. Freeze the protocol before comparing models, record any revisions, and replace heuristics with measured calibration curves when hardware access is granted.

## OpenAI interface

Model: `gpt-6-astra`, high reasoning, strict structured output, image input, no retries. [Model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [pricing](https://developers.openai.com/api/docs/pricing).

Budget reservations use conservative upper rates of $25/M input and $75/M output tokens, rather than claiming exact invoice charges. Input images are resized to at most 768 pixels; each reserves 32,768 input tokens. Request text is bounded by UTF-8 byte count. Output reserves 8,192 tokens, including reasoning. Check current pricing before future protocol releases.
