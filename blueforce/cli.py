"""Interactive-friendly command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

from rich.console import Console
from rich.json import JSON

from blueforce import __version__
from blueforce.bluetooth.security_audit import audit
from blueforce.config import DEFAULT_DB, SCENARIOS
from blueforce.core.engine import SimulationEngine
from blueforce.database.repository import Repository
from blueforce.detection.risk_scoring import assess
from blueforce.models import DeviceType
from blueforce.reporting.report_generator import export
from blueforce.simulator.virtual_lab import VirtualLab


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="blueforce",
        description="BLUEFORCE X — Analyze. Simulate. Detect. Defend. (synthetic lab only)",
    )
    root.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    root.add_argument("--version", action="version", version=f"BLUEFORCE X {__version__}")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("status", help="Show application and host adapter status")
    commands.add_parser("dashboard", help="Open the live local terminal dashboard")
    lab = commands.add_parser("lab", help="Manage isolated virtual laboratories")
    lab_commands = lab.add_subparsers(dest="lab_command", required=True)
    lab_commands.add_parser("list", help="List labs")
    create = lab_commands.add_parser("create", help="Create an isolated lab")
    create.add_argument("name")
    lab_export = lab_commands.add_parser("export", help="Export lab configuration as JSON")
    lab_export.add_argument("--lab", required=True)
    lab_export.add_argument("--output", type=Path, required=True)
    lab_import = lab_commands.add_parser("import", help="Import a JSON virtual lab")
    lab_import.add_argument("--input", type=Path, required=True)
    device = commands.add_parser("device", help="Manage virtual devices")
    device_commands = device.add_subparsers(dest="device_command", required=True)
    listing = device_commands.add_parser("list", help="List virtual devices")
    listing.add_argument("--lab", required=True)
    add = device_commands.add_parser("add", help="Add a virtual device")
    add.add_argument("--lab", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--type", required=True, choices=[item.value for item in DeviceType])
    add.add_argument("--pairing", choices=["secure", "legacy", "unknown"], default="secure")
    add.add_argument("--discoverable", action="store_true")
    add.add_argument("--unencrypted", action="store_true")
    remove = device_commands.add_parser("remove", help="Remove a virtual device")
    remove.add_argument("--lab", required=True)
    remove.add_argument("--id", required=True)
    configure = device_commands.add_parser("configure", help="Change virtual-only device properties")
    configure.add_argument("--lab", required=True)
    configure.add_argument("--id", required=True)
    configure.add_argument("--name")
    configure.add_argument("--signal-db", type=int)
    configure.add_argument("--connected", action=argparse.BooleanOptionalAction, default=None)
    configure.add_argument("--pairing", choices=["secure", "legacy", "unknown"])
    configure.add_argument("--discoverable", action=argparse.BooleanOptionalAction, default=None)
    configure.add_argument("--encrypted", action=argparse.BooleanOptionalAction, default=None)
    configure.add_argument("--battery", type=int)
    simulations = commands.add_parser("simulation", help="Run synthetic scenarios")
    sim_commands = simulations.add_subparsers(dest="simulation_command", required=True)
    sim_commands.add_parser("list", help="List saved simulation sessions")
    start = sim_commands.add_parser("start", help="Start a synthetic simulation")
    start.add_argument("--lab", required=True)
    start.add_argument("--scenario", required=True, choices=SCENARIOS)
    start.add_argument("--steps", type=int, default=20)
    start.add_argument("--seed", type=int)
    alerts = commands.add_parser("alerts", help="List lab security alerts")
    alerts.add_argument("--lab", required=True)
    alerts.add_argument("--ack", metavar="ALERT_ID", help="Acknowledge one alert")
    alerts.add_argument("--false-positive", metavar="ALERT_ID",
                        help="Mark an alert as a false positive")
    incidents = commands.add_parser("incidents", help="Review and update incidents")
    incidents.add_argument("--lab")
    incidents.add_argument("--create", metavar="TITLE")
    incidents.add_argument("--classification", default="SIMULATED")
    incidents.add_argument("--update", metavar="ID")
    incidents.add_argument("--status", choices=["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"])
    incidents.add_argument("--note")
    incidents.add_argument("--recover", metavar="ID", help="Rehearse virtual recovery")
    report = commands.add_parser("report", help="Generate a lab report")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    generate = report_commands.add_parser("generate", help="Export JSON, CSV, TXT, or HTML")
    generate.add_argument("--lab", required=True)
    generate.add_argument("--format", required=True, choices=["json", "csv", "txt", "html"])
    generate.add_argument("--output", type=Path, required=True)
    chart = report_commands.add_parser("chart", help="Export synthetic resource chart as PNG")
    chart.add_argument("--lab", required=True)
    chart.add_argument("--output", type=Path, required=True)
    security = commands.add_parser("security", help="Read-only security assessment")
    security_commands = security.add_subparsers(dest="security_command", required=True)
    security_commands.add_parser("audit", help="Inspect host adapter and unknown security settings")
    risk = security_commands.add_parser("risk", help="Score virtual lab configuration")
    risk.add_argument("--lab", required=True)
    return root


def _json(value: object) -> None:
    Console().print(JSON.from_data(value, indent=2))


def dispatch(args: argparse.Namespace, repository: Repository) -> int:
    command = args.command
    if command == "status":
        _json({"application": "BLUEFORCE X", "version": __version__,
               "safety": "SIMULATION ONLY — no radio operations",
               "host_bluetooth": audit()["adapter_inventory"]})
    elif command == "dashboard":
        from blueforce.tui import run_dashboard
        return run_dashboard(repository.path)
    elif command == "lab":
        if args.lab_command == "create":
            _json({"id": repository.create_lab(args.name), "name": args.name})
        elif args.lab_command == "list":
            _json([dict(row) for row in repository.labs()])
        elif args.lab_command == "export":
            payload = repository.export_lab(args.lab)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(args.output)
        else:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            _json({"id": repository.import_lab(payload), "imported": True})
    elif command == "device":
        lab = VirtualLab(repository, args.lab)
        if args.device_command == "add":
            device = lab.add_device(
                args.name, args.type, pairing=args.pairing,
                discoverable=args.discoverable, encrypted=not args.unencrypted,
            )
            _json({"id": device.identifier, "name": device.name,
                   "type": device.device_type.value, "simulated": True})
        elif args.device_command == "list":
            _json([dict(row) for row in lab.devices()])
        elif args.device_command == "remove":
            if not lab.remove_device(args.id):
                raise ValueError(f"Virtual device not found: {args.id}")
            print("Virtual device removed.")
        else:
            changes = {
                "name": args.name, "signal_dbm": args.signal_db,
                "connected": args.connected, "pairing": args.pairing,
                "discoverable": args.discoverable, "encrypted": args.encrypted,
                "battery": args.battery,
            }
            changes = {key: value for key, value in changes.items() if value is not None}
            if not repository.update_device(lab.lab_id, args.id, changes):
                raise ValueError(f"Virtual device not found: {args.id}")
            print("Virtual device configuration updated.")
    elif command == "simulation":
        if args.simulation_command == "list":
            _json([dict(row) for row in repository.sessions()])
        else:
            lab = repository.lab(args.lab)
            if lab is None:
                raise ValueError(f"Lab not found: {args.lab}")
            result = asyncio.run(SimulationEngine(repository).run(
                lab["id"], args.scenario, args.steps, args.seed,
            ))
            _json(result)
    elif command == "alerts":
        lab = repository.lab(args.lab)
        if lab is None:
            raise ValueError(f"Lab not found: {args.lab}")
        if args.ack:
            if not repository.acknowledge_alert(args.ack):
                raise ValueError(f"Alert not found: {args.ack}")
            print("Alert acknowledged.")
            return 0
        if args.false_positive:
            if not repository.mark_false_positive(args.false_positive):
                raise ValueError(f"Alert not found: {args.false_positive}")
            print("Alert marked as a false positive and acknowledged.")
            return 0
        _json([dict(row) for row in repository.alerts(lab["id"])])
    elif command == "incidents":
        if args.recover:
            from blueforce.incidents.response_engine import ResponseEngine
            _json(ResponseEngine(repository).rehearse_recovery(args.recover))
        elif args.create:
            lab = repository.lab(args.lab) if args.lab else None
            if lab is None:
                raise ValueError("Provide --lab with an existing lab to create an incident.")
            _json({"id": repository.create_incident(
                lab["id"], args.create, args.classification
            )})
        elif args.update:
            if not args.status:
                raise ValueError("--status is required with --update.")
            if not repository.set_incident(args.update, args.status, args.note):
                raise ValueError(f"Incident not found: {args.update}")
            print("Incident updated.")
        else:
            _json([dict(row) for row in repository.incidents(args.lab)])
    elif command == "report":
        lab = repository.lab(args.lab)
        if lab is None:
            raise ValueError(f"Lab not found: {args.lab}")
        if args.report_command == "chart":
            from blueforce.analytics.charts import export_resource_chart
            print(export_resource_chart(repository, lab["id"], args.output))
        else:
            print(export(repository, lab["id"], args.output, args.format))
    elif command == "security":
        if args.security_command == "audit":
            _json(audit())
        else:
            lab = repository.lab(args.lab)
            if lab is None:
                raise ValueError(f"Lab not found: {args.lab}")
            _json(assess(repository.devices(lab["id"])))
    else:
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.command:
        parser().print_help()
        return 0
    repository = None
    try:
        repository = Repository(args.db)
        return dispatch(args, repository)
    except (ValueError, OSError, RuntimeError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        if repository:
            repository.close()
