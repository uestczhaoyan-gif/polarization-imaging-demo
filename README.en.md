# Polarization Imaging Demo

Choose bidirectional serpentine or unidirectional scanning in START.cmd. Unidirectional mode scans, returns at the same speed, then steps Y after every row, including the last. Exclude returns from reconstruction using explicit row windows; the mode does not control acquisition or add synchronized event logs. [Mode guide](docs/hardware/scan-modes.md)

[中文](README.md) | **English**

An STM32 drives an XY stage in a serpentine pattern, a source meter records current, and Python reconstructs a 2D image. The project includes firmware, a graphical parameter editor, two measured examples, and offline viewers linking each pixel to its raw samples.

The current implementation provides single-channel current imaging. Acquisition uses the instrument software; motor–meter synchronization and Stokes/polarization calculations are not implemented.

## Start here

Download and extract the [complete project](https://github.com/uestczhaoyan-gif/polarization-imaging-demo/releases/latest).

1. **Edit stage parameters:** double-click `START.cmd`, the single Windows entry point. Enter scan dimensions (including fractional line spacing such as 0.5 or 0.1 mm), speed and directions, preview the changes, then save. Rebuild and flash the appropriate Keil project afterward. [Editor guide](docs/hardware/configuration-ui.md)
2. **View measurements:** choose a case in the workspace's experiments tab, or open a `viewer.html` from the table below. Viewing saved results does not require Python.
3. **Prepare a measurement:** read the [wiring guide](docs/hardware/wiring-and-first-run.md) and [measurement checklist](docs/reconstruction/measurement.md). Save actual settings, timestamps and per-line motion events.
4. **Review reconstruction:** start with the [core processing guide](docs/reconstruction/core-process.md), then run an example.

The editor requires Python 3.10+ with Tkinter and no third-party packages. On macOS/Linux run `python tools/control_panel.py`. Download HTML viewers before opening them; GitHub does not execute them. Detailed documentation and the editor interface are in Chinese.

## Measured examples

| Case | Data, settings and notes | Saved results |
|---|---|---|
| Taped Z · ambient light | [tape-z](experiments/tape-z/README.md): 120,311 samples without synchronization | [Viewer](experiments/tape-z/results/viewer.html) · [Image](experiments/tape-z/results/02_reconstruction.png) |
| Rectangular tape frame · darkness | [tape-frame](experiments/tape-frame/README.md): 20,059 samples, 80×80 mm | [Viewer](experiments/tape-frame/results/anchored/viewer.html) · [Photo comparison](experiments/tape-frame/photo-comparison.md) |

The two cases are peers. Each contains its own raw data, configurations, notes and `results/`. A separate [synthetic example](experiments/synthetic/README.md) provides a known answer for validation.

## Layout

```text
START.cmd                 Single Windows workspace launcher
firmware/                 STM32 firmware and four Keil projects
tools/                    Desktop editor and parameter validation
reconstruction/           Python reconstruction code and tests
experiments/
  tape-z/                 Z: raw data, settings, notes, results
  tape-frame/             Frame: raw data, settings, photo, results
  synthetic/              Synthetic validation with known answers
  manifest.sha256         Published result checksums
docs/                     Hardware, reconstruction, templates, maintenance
scripts/                  Maintainer checks and release utilities
local/                    Local backups and new outputs (Git-ignored)
```

See the [documentation index](docs/README.md) and [layout conventions](docs/project/layout.md). Keil/CubeMX directory and project names are retained inside the firmware module.

## Run reconstruction

Run all commands from the repository root:

```bash
python -m pip install -r reconstruction/requirements.txt
python reconstruction/simple_reconstruct.py --config experiments/tape-frame/config.json
python reconstruction/reconstruct.py run --config experiments/tape-z/config.json --open
```

New outputs go to `local/reconstruction/<case>/`; published snapshots remain in each case's `results/`. The full CLI refuses to overwrite existing outputs unless `--overwrite` is supplied. Copy a configuration for your measurement and enter its actual records rather than reusing estimated example timings. [Reconstruction module](reconstruction/README.md)

## Firmware and validation limits

The controller is an STM32F103C8T6 with ZDT X42S motors (X address 2, Y address 1). Repository defaults are 100×100 mm, 2 mm row spacing and 1 mm/s. The editor updates [snake_scan_config.h](firmware/Core/Inc/snake_scan_config.h); saving does not flash the board. Progress through communication-only, 1 mm, 10 mm and full-scan Keil projects. [Firmware guide](firmware/README.md)

Reported rapid motion and reset problems remain unresolved. The fractional-distance update adds acceptance, nominal-duration and consecutive reached-status checks; passing host simulations does not prove the hardware issue is fixed. [Motion investigation](docs/hardware/motion-anomalies.md) · [Reset and vendor checklist](docs/hardware/reset-and-vendor-checklist.md)

Distances are entered in millimeters with up to three decimal places and stored as integer micrometers. With the default mechanics, the smallest supported setting is 0.005 mm (16 pulses); this is a software setting increment, not measured positioning accuracy. Set both drivers' Response mode to Receive or Both for short moves. Older `_MM` configuration backups must not replace the new `_UM` header; re-enter the original millimeter values in the updated editor.

Unsynchronized measured images use estimated row boundaries and are not edited to match photographs. Software checks do not replace firmware flashing or physical testing. Mechanical homing, hardware limits and emergency-stop inputs are not implemented; follow the hardware guide before running the stage.

Maintainer checks: `python scripts/check_project.py` and `python scripts/run_tests.py`.

Original code retains the [root license](LICENSE) and [reconstruction license](reconstruction/LICENSE); [third-party notices](docs/project/third-party-notices.md) are preserved. Both original project histories are retained here. [Changelog](docs/project/changelog.md)
