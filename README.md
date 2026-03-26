# Pioreactor pH Plugin Pack

pH integration for Pioreactor using an Atlas Scientific EZO-pH circuit.

This repository package provides three Python plugins that work together:

- `atlas_ezo_ph.py` - shared low-level I2C communication helper for Atlas EZO-pH.
- `ph_reading.py` - continuous pH tracking job, MQTT publishing, and DB sink registration.
- `ph_calibration.py` - guided calibration protocol in **Calibration -> Protocols**.

It also includes UI and export dataset YAML files in subfolders:

- `ui/contrib/jobs/ph_reading.yaml`
- `ui/charts/ph.yaml`
- `exportable_datasets/ph_readings.yaml`

## Requirements

- Pioreactor installed and running
- Atlas Scientific EZO-pH board + compatible pH probe
- I2C wiring configured correctly
- Pioreactor documentation familiarity:
  - [Plugin introduction](https://docs.pioreactor.com/developer-guide/intro-plugins)
  - [Hardware calibrations](https://docs.pioreactor.com/user-guide/hardware-calibrations)
  - [Adding calibration types](https://docs.pioreactor.com/developer-guide/adding-calibration-type)

## Installation

1. Copy all files from this repository `plugins` folder into:
   - `~/.pioreactor/plugins/`
2. Restart Pioreactor services (or reboot the unit) so plugins are reloaded.
3. Open Pioreactor UI and confirm:
   - `ph_reading` is available in job controls.
   - pH chart appears in Overview (if configured in your UI setup).
   - pH protocol appears in Calibration -> Protocols.

## Plugin Overview

### 1) `atlas_ezo_ph.py`

Shared helper module for EZO-pH I2C operations:

- Create probe connection from Pioreactor config
- Send commands and parse EZO responses
- Handle Atlas status codes (including pending/no-data)
- Provide averaged pH reads

### 2) `ph_reading.py`

Continuous pH acquisition job:

- Runs a background job `ph_reading`
- Publishes pH values to MQTT
- Streams values into `pH_readings` table for charting/export
- Enforces minimum read interval (`time_between_readings >= 2.0s`)

### 3) `ph_calibration.py`

Guided Atlas EZO-pH calibration protocol:

- Available in Calibration -> Protocols
- Supports 2-point flow (pH 7 and 4) and optional 3rd point (pH 10)
- Executes `Cal,clear`, calibration point commands, and status check `Cal,?`
- Stores calibration record in Pioreactor calibration storage

## Operational Notes

- Do not run `ph_reading` simultaneously with calibration.  
  Stop pH tracking first, then run calibration to avoid I2C contention and transient EZO errors.
- During each calibration buffer step, wait about 30 seconds for probe stabilization before pressing Continue.
- If Pioreactor UI shows protocol-loading issues after restart, open the Plugins tab once and retry (known behavior on some Pioreactor software versions).

## Repository Structure

```text
plugins/
  atlas_ezo_ph.py
  ph_reading.py
  ph_calibration.py
  ui/
    charts/ph.yaml
    contrib/jobs/ph_reading.yaml
  exportable_datasets/
    ph_readings.yaml
```

## Screenshots

Add images in your repository `images/` folder and keep (or rename) these references:

### Main Pioreactor UI with pH chart

![Main UI with pH chart](../images/main-ui-ph-chart.png)

### Calibration protocol - first window

![Calibration first window](../images/calibration-first-window.png)

### Calibration result curve

![Calibration result curve](../images/calibration-ready-curve.png)

## License

Use the same license as your repository/project.
