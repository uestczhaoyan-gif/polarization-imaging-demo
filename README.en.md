# Polarization Imaging Demo: XY Scanning and Current-Image Reconstruction

[中文](README.md) | **English**

A unified imaging demonstration project: an STM32F103 drives a ZDT XY stage through a serpentine scan, a source meter records photocurrent, and Python reconstructs a 2D image with an offline viewer linking every pixel to its original samples.

This repository combines the stage controller and reconstruction example while retaining both Git histories, measured data, and published results. **The current implementation provides single-channel current imaging.** Acquisition is performed using the instrument's software; automatic motor–meter synchronization is not implemented, and the software does not calculate Stokes parameters, degree of polarization, or polarization angle.

![Measured reconstruction of the taped Z](reconstruction/examples/z_tape/reference/02_reconstruction.png)

## Start here

Download the [complete release](https://github.com/uestczhaoyan-gif/polarization-imaging-demo/releases/latest), or choose Code → Download ZIP on GitHub, then extract it.

1. **View the results:** double-click `open_results.cmd`, or open `reconstruction/results/z_tape/viewer.html` in a browser. No Python installation or network connection is required.
2. **Explore the mapping:** click an image pixel to inspect its scan line and all original samples; click a trace to locate the corresponding pixel. See the [reading guide](reconstruction/docs/reading-guide.md).
3. **Prepare a measurement:** read the [measurement checklist](reconstruction/docs/measurement.md), and save timestamps, per-line motion records, and instrument settings.
4. **Run the stage:** follow the [wiring and first-run guide](docs/hardware/硬件接线与首次运行.md), progressing through communication-only, 1 mm, 10 mm, and full-scan checks.
5. **Reconstruct your data:** install the Python dependencies and use the example or configuration wizard below.

GitHub's HTML source preview is not interactive. Download the viewer and open it locally.

## Measurement workflow

```text
Mount the sample, identify the origin/directions, and record dark/bright references
                                  ↓
Start saving raw current and per-sample timestamps from the source meter
                                  ↓
STM32: horizontal X scan → Y step → reverse X scan
                                  ↓
Save each valid scan interval, direction, stop time, and actual settings
                                  ↓
Python: select horizontal intervals → bin samples → reverse alternate rows
                                  ↓
Original I–point/I–t + 2D image + bidirectional tables + offline linked viewer
```

Acquisition may continue during startup, vertical moves, and turnarounds. Keep those raw samples and exclude the appropriate intervals using synchronized motion records. An estimation mode is available for older recordings without synchronization, but estimated boundaries are not calibrated motion measurements.

## Repository layout

| Path | Contents |
|---|---|
| `firmware/` | STM32 scan logic, ZDT protocol functions, HAL/CMSIS, and four Keil projects |
| `docs/hardware/` | Wiring, scan parameters, troubleshooting, validation, and sources |
| `docs/异常加速排查.md` | Review of the reported mid-scan acceleration and an evidence-collection procedure |
| `reconstruction/snake_scan/` | Python input validation, scan windows, pixel aggregation, and linked viewer |
| `reconstruction/examples/` | Measured taped-Z data, settings, synthetic examples, and explanatory figures |
| `reconstruction/results/` | Complete published results and a SHA256 manifest |
| `reconstruction/docs/` | Reading guide, input formats, measurement requirements, and extension notes |
| `reconstruction/outputs/` | Newly generated outputs, ignored by Git by default |

Hardware: [firmware guide](firmware/README.md), [scan parameters](docs/hardware/参数与扫描路径.md), [troubleshooting](docs/hardware/常见问题.md).

Measurement and reconstruction: [what to save](reconstruction/docs/measurement.md), [experiment template](reconstruction/docs/experiment.template.json), [configuration](reconstruction/docs/configuration.md), [irregular-pixel analysis](reconstruction/docs/artifacts.md). Detailed documentation remains in Chinese.

## Stage hardware and operation

| Item | Repository default |
|---|---|
| Controller | Wildfire Xiaozhi STM32F103C8T6, dual-USB board |
| Programmer | Wildfire DAP over SWD |
| Motors | ZDT X42S second-generation closed-loop steppers, Emm V5 compatible |
| Serial interface | USART1, PA9/PA10, 115200 baud, 8N1; TTL/RS485 as appropriate for the hardware |
| Axis addresses | X=2, Y=1 |
| Mechanics | 1.8° step angle, 16 microsteps, T6×1 lead screw with 1 mm/revolution lead |
| Default scan | 100×100 mm, 2 mm line spacing, 1 mm/s |
| Status LED | Active-low red LED on PA1 |

Edit [snake_scan_config.h](firmware/Core/Inc/snake_scan_config.h) for routine parameters. The user-reported measurement ran at **2 mm/s with a changed Y direction**; the repository's default header remains at 1 mm/s. Save the actual flashed configuration and firmware revision rather than treating repository defaults as the measurement record.

Open the projects in `firmware/MDK-ARM/` in this order:

1. `01_COMM_CHECK_NO_MOVE.uvprojx`: communication only.
2. `02_1MM_MOTION_TEST.uvprojx`: X moves 1 mm in each direction; total Y travel is 2 mm.
3. `03_10MM_MOTION_TEST.uvprojx`: X moves 10 mm in each direction; total Y travel is 4 mm.
4. `04_ACTUAL_SNAKE_RUN.uvprojx`: the configured scan area.

Rebuild and flash after changing parameters or switching projects. The motion program performs one scan after startup/reset, communication checks, and a five-second countdown. Every completed horizontal pass is followed by a Y step, including the last pass. See the parameter guide for scan-line positions and the final stage position.

There is no mechanical homing, hardware limit input, or emergency-stop input. Confirm available travel, turn off motor power while flashing, and retain a direct means of cutting motor power. Two episodes of unexpected mid-line acceleration were reported; see the [investigation notes](docs/异常加速排查.md). Subsequent normal operation alone does not establish that the fault is resolved.

## Python reconstruction

From the repository root:

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/reconstruct.py run --config reconstruction/examples/z_tape/config.json --open
```

On Windows, you can also double-click `run_reconstruction.cmd`. New results are written to `reconstruction/outputs/z_tape/`; published reference results remain in `reconstruction/results/z_tape/`.

Configure a new recording:

```bash
python reconstruction/reconstruct.py wizard --output reconstruction/local/config.json
python reconstruction/reconstruct.py run --config reconstruction/local/config.json --open
```

| Mode | Required information |
|---|---|
| `time_windows` | Per-sample timestamps and valid constant-speed scan start/end times and directions; supports irregular sampling |
| `index_windows` | Valid per-line sample-index boundaries and directions; sampling must be uniform within each line |
| `constant` | Stable samples per scan cycle and the first complete cycle's starting index |
| `estimate` | A period search range, fitting interval, and signal continuity between adjacent rows; intended for unsynchronized legacy data |

All modes also require the input path, scan width, line spacing, column count, and threshold strategy. Integration time is not the sample interval, and an approximate startup wait cannot directly determine a sample offset. The spatial model assumes equal-width rows, constant line spacing, and constant-speed valid horizontal intervals. Encoder-based nonuniform-motion mapping, multichannel polarization quantities, and automatic acquisition are future extensions.

## Measured example and validation limits

The taped-Z recording contains 120,311 original samples. Its current estimated reconstruction has 29×50 pixels, with 77 or 78 samples per pixel. Blue represents low current and yellow represents high current. No photograph-based filling, isolated-pixel removal, or contour correction is applied. The origin, scan period, and turnaround duration are uncertain, and the image also contains actual I/rail occlusion.

Run the Python mapping, input-validation, and published-result checks:

```bash
python scripts/run_tests.py
python scripts/check_project.py
```

This integration preserves the existing firmware motion code. Project paths and references are checked statically; firmware flashing and mechanical testing were not performed. Static checks do not establish hardware validation. See the [firmware validation record](docs/hardware/验证记录.md).

## Licensing and maintenance

Original code, documentation, and measured examples retain their respective [root license](LICENSE) and [reconstruction license](reconstruction/LICENSE). ST, Arm, and ZDT notices are retained in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This is the unified maintenance repository. The former reconstruction repository retains its history and points here instead of being maintained as a separate functional project. See the [integration record](docs/项目合并记录.md).
