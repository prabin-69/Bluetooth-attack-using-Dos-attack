# BLUEFORCE X

**Analyze. Simulate. Detect. Defend.**

BLUEFORCE X is a local Bluetooth security learning and analysis application. Its
scenarios generate deterministic, synthetic events in isolated SQLite-backed
laboratories. They do not use Bluetooth radios, discover nearby devices, send
packets, manipulate connections, or interfere with real devices.

## Requirements

[Back to requirements](#requirements)

- Python 3.12 or newer.
- Linux, Windows 10, or Windows 11.
- Bluetooth tools and hardware are not required; lab activity is simulated.

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

## Usage

[See usage examples](#usage)

From the BLUEFORCE-X project directory, create and activate a virtual
environment, then install the application:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Show CLI options:

```bash
python main.py --help
```

Create a virtual lab:

```bash
python main.py lab create classroom
```

Add a simulated IoT sensor:

```bash
python main.py device add --lab classroom --name Sensor-01 --type iot_sensor
```

Run a reproducible synthetic scenario:

```bash
python main.py simulation start --lab classroom \
  --scenario repeated_request_anomaly --steps 20 --seed 7
```

Review alerts and generate a JSON report:

```bash
python main.py alerts --lab classroom
python main.py report generate --lab classroom --format json --output report.json
```

Start the interactive dashboard:

```bash
python main.py dashboard
```

Linux supports virtual labs, simulations, reports, and the dashboard. Bluetooth
adapter inspection currently uses Windows-only APIs and is reported as
unavailable on Linux. BLUEFORCE X does not scan for nearby devices, transmit
packets, or interfere with real Bluetooth connections.

### Windows setup

From this directory in PowerShell:

```powershell
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
& $python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Invoke commands with `blueforce` after installation or `python main.py` from
the project folder. Use `--db C:\path\lab.sqlite3` to select a database. The
default database is `%USERPROFILE%\.blueforce-x\blueforce.sqlite3`.
If Windows Application Control blocks the generated `blueforce.exe` launcher,
run the same commands as `python main.py ...`; do not weaken the execution policy.

## Quick start

```powershell
blueforce --help
blueforce status
blueforce lab create classroom
blueforce lab list
blueforce lab export --lab classroom --output .\classroom.json
blueforce lab import --input .\classroom.json
blueforce device add --lab classroom --name Sensor-01 --type iot_sensor
blueforce device list --lab classroom
blueforce device configure --lab classroom --id SIM-ID --connected --signal-db -48
blueforce device remove --lab classroom --id SIM-ID
blueforce simulation start --lab classroom --scenario repeated_request_anomaly --steps 20 --seed 7
blueforce alerts --lab classroom
blueforce security risk --lab classroom
blueforce security audit
blueforce dashboard
blueforce incidents --lab classroom --create "Synthetic service degradation"
blueforce report generate --lab classroom --format html --output .\report.html
blueforce report chart --lab classroom --output .\resources.png
```

Supported virtual types: `smartphone`, `laptop`, `headphones`, `smartwatch`,
`iot_sensor`, `bluetooth_speaker`, and `ble_peripheral`. Device configuration
changes are recorded in virtual activity history and never affect host devices.

Scenarios: `connection_exhaustion`, `resource_exhaustion`,
`availability_degradation`, `repeated_request_anomaly`, and `service_disruption`.
Use `--seed` to reproduce a generated scenario. Every run has a bounded step
count and records events and defensive alerts to SQLite.
`blueforce report chart` plots synthetic CPU/memory history from a resource
scenario; the Textual dashboard refreshes lab counters and its ASCII resource
graph on a two-second interval.

Incident workflows support `OPEN`, `INVESTIGATING`, `CONTAINED`, and `RESOLVED`:

```powershell
blueforce incidents --lab classroom
blueforce incidents --update INCIDENT_ID --status INVESTIGATING --note "Review synthetic timeline"
blueforce incidents --recover INCIDENT_ID
```

Use `blueforce alerts --lab classroom --ack ALERT_ID` to acknowledge an alert,
or `--false-positive ALERT_ID` to record a reviewed false positive.

## Modules

- `blueforce/cli.py`: command parsing, validation, and application wiring.
- `blueforce/database/`: SQLite schema migration, repositories, and transactional writes.
- `blueforce/database/models.py`: validated simulation-event and alert records.
- `blueforce/simulator/`: validated virtual-device lifecycle and seeded synthetic scenarios.
- `blueforce/simulator/resource_model.py`: deterministic virtual CPU/memory model.
- `blueforce/simulator/virtual_device.py`: validated virtual-device creation and activity history.
- `blueforce/core/engine.py`: asynchronous event orchestration, cancellation handling, and persistence.
- `blueforce/detection/`: configurable threshold rules, bounded statistical baselines, recent-event correlation, and evidence-based lab risk scoring.
- `blueforce/analytics/`: separate actual-host metrics, synthetic lab metrics, and Matplotlib PNG chart export.
- `blueforce/bluetooth/`: read-only Windows PnP inventory and an audit that labels unavailable data UNKNOWN.
- `blueforce/incidents/`: incident status workflow and virtual-only recovery rehearsal.
- `blueforce/tui.py`: live Textual terminal dashboard.
- `blueforce/reporting/`: JSON, CSV, TXT, and HTML report exports.
- `tests/`: deterministic engine, simulator, detection, and database checks.

The adapter query reports only device names and PnP state. Pairing mode,
discoverability, link encryption, Bluetooth version, and negotiated capabilities
are reported as unknown unless a future platform adapter can confirm them. An
unknown value is not treated as a confirmed vulnerability.

## Test

```powershell
python -m pytest
```

Pydantic validates virtual-device and persisted-event input, Rich formats CLI
output, Textual powers the terminal dashboard, psutil provides separately
labeled actual-host measurements, and Matplotlib exports charts.
