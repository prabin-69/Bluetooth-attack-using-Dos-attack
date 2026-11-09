"""Professional JSON, CSV, TXT, and HTML lab reports."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from blueforce.database.repository import Repository
from blueforce.detection.risk_scoring import assess


def build_report(repository: Repository, lab_id: str) -> dict[str, Any]:
    lab = repository.lab(lab_id)
    if lab is None:
        raise ValueError(f"Lab not found: {lab_id}")
    devices = repository.devices(lab["id"])
    sessions = repository.sessions(lab["id"])
    alerts = repository.alerts(lab["id"])
    timeline = repository.connection.execute(
        """SELECT e.timestamp,e.event_type,e.severity,e.message,e.data_json
           FROM simulation_events AS e
           JOIN simulation_sessions AS s ON s.id=e.session_id
           WHERE s.lab_id=? ORDER BY e.timestamp,e.id""",
        (lab["id"],),
    )
    risk = assess(devices)
    return {
        "title": "BLUEFORCE X Virtual Bluetooth Security Report",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "executive_summary": (
            f"Lab {lab['name']} contains {len(devices)} virtual devices, "
            f"{len(sessions)} simulations, and {len(alerts)} generated alerts."
        ),
        "lab": {"id": lab["id"], "name": lab["name"]},
        "devices": [dict(row) for row in devices],
        "scenarios": [dict(row) for row in sessions],
        "timeline": [dict(row) for row in timeline],
        "detection_results": [dict(row) for row in alerts],
        "risk_assessment": risk,
        "security_recommendations": risk["recommendations"],
        "safety": "All scenarios and generated activity are synthetic and lab-isolated.",
    }


def export(repository: Repository, lab_id: str, output: Path, fmt: str) -> Path:
    if fmt not in {"json", "csv", "txt", "html"}:
        raise ValueError("Format must be json, csv, txt, or html.")
    report = build_report(repository, lab_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    elif fmt == "csv":
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("section", "key", "value"))
            writer.writerow(("summary", "executive_summary", report["executive_summary"]))
            for key, value in report["lab"].items():
                writer.writerow(("lab_configuration", key, value))
            for device in report["devices"]:
                writer.writerow((
                    "virtual_device", device["name"],
                    json.dumps({key: device[key] for key in (
                        "device_type", "signal_dbm", "connected", "pairing",
                        "discoverable", "encrypted", "battery", "risk",
                    )}),
                ))
            for session in report["scenarios"]:
                writer.writerow(("simulation_scenario", session["id"], session["scenario"]))
            if not report["scenarios"]:
                writer.writerow(("simulation_scenario", "status", "No sessions recorded"))
            for event in report["timeline"]:
                writer.writerow(("timeline_event", event["timestamp"],
                                 f"{event['event_type']} [{event['severity']}] {event['message']}"))
            if not report["timeline"]:
                writer.writerow(("timeline_event", "status", "No events recorded"))
            for alert in report["detection_results"]:
                writer.writerow(("alert", alert["severity"], alert["explanation"]))
            if not report["detection_results"]:
                writer.writerow(("alert", "status", "No alerts recorded"))
            risk = report["risk_assessment"]
            writer.writerow(("risk_assessment", "score", risk["score"]))
            writer.writerow(("risk_assessment", "category", risk["category"]))
            writer.writerow(("risk_assessment", "evidence", risk["evidence"]))
            for finding in risk["findings"]:
                writer.writerow(("risk_finding", "evidence", finding))
            for recommendation in report["security_recommendations"]:
                writer.writerow(("recommendation", "action", recommendation))
            writer.writerow(("safety", "scope", report["safety"]))
    elif fmt == "txt":
        risk = report["risk_assessment"]
        output.write_text(
            f"{report['title']}\nGenerated: {report['generated_at']}\n\n"
            f"EXECUTIVE SUMMARY\n{report['executive_summary']}\n\n"
            f"LAB CONFIGURATION\nName: {report['lab']['name']}\n"
            f"Lab ID: {report['lab']['id']}\nVirtual devices: {len(report['devices'])}\n\n"
            "VIRTUAL DEVICE CONFIGURATION\n"
            + ("\n".join(
                f"- {item['name']} ({item['device_type']}): pairing={item['pairing']}, "
                f"discoverable={bool(item['discoverable'])}, "
                f"encrypted={bool(item['encrypted'])}, connected={bool(item['connected'])}"
                for item in report["devices"]
            ) or "- No virtual devices configured.")
            + "\n\n"
            "SIMULATION SCENARIOS\n"
            + ("\n".join(f"- {item['scenario']} [{item['status']}]"
                         for item in report["scenarios"]) or "- No sessions recorded.")
            + "\n\nEVENT TIMELINE\n"
            + ("\n".join(
                f"- {item['timestamp']} [{item['severity']}] "
                f"{item['event_type']}: {item['message']}"
                for item in report["timeline"]
            ) or "- No events recorded.")
            + "\n\nDETECTION RESULTS\n"
            + ("\n".join(
                f"- {item['timestamp']} [{item['severity']}] "
                f"{item['rule']}: {item['explanation']}"
                for item in report["detection_results"]
            ) or "- No alerts recorded.")
            + "\n\nRISK ASSESSMENT\n"
            f"RISK: {risk['category']} ({risk['score']}/100)\n"
            f"Evidence: {risk['evidence']}\n"
            + "\n".join(f"- {item}" for item in risk["findings"])
            + "\n\nRECOMMENDATIONS\n"
            + "\n".join(f"- {item}" for item in risk["recommendations"])
            + f"\n\nSAFETY\n{report['safety']}\n", encoding="utf-8"
        )
    else:
        summary = html.escape(report["executive_summary"])
        risk = report["risk_assessment"]
        list_items = lambda values: "".join(
            f"<li>{html.escape(str(item))}</li>" for item in values
        )
        scenario_rows = "".join(
            f"<tr><td>{html.escape(row['scenario'])}</td>"
            f"<td>{html.escape(row['status'])}</td></tr>"
            for row in report["scenarios"]
        )
        device_rows = "".join(
            f"<tr><td>{html.escape(row['name'])}</td>"
            f"<td>{html.escape(row['device_type'])}</td>"
            f"<td>{html.escape(row['pairing'])}</td>"
            f"<td>{'Yes' if row['discoverable'] else 'No'}</td>"
            f"<td>{'Yes' if row['encrypted'] else 'No'}</td></tr>"
            for row in report["devices"]
        )
        timeline_rows = "".join(
            f"<tr><td>{html.escape(row['timestamp'])}</td>"
            f"<td>{html.escape(row['severity'])}</td>"
            f"<td>{html.escape(row['event_type'])}</td>"
            f"<td>{html.escape(row['message'])}</td></tr>"
            for row in report["timeline"]
        )
        if not scenario_rows:
            scenario_rows = "<tr><td colspan='2'>No sessions recorded.</td></tr>"
        if not device_rows:
            device_rows = "<tr><td colspan='5'>No virtual devices configured.</td></tr>"
        if not timeline_rows:
            timeline_rows = "<tr><td colspan='4'>No events recorded.</td></tr>"
        alerts = list_items([
            f"{row['severity']} — {row['rule']}: {row['explanation']}"
            for row in report["detection_results"]
        ]) or "<li>No alerts recorded.</li>"
        output.write_text(
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>BLUEFORCE X Report</title></head><body>"
            f"<h1>{html.escape(report['title'])}</h1><p>{summary}</p>"
            f"<h2>Lab configuration</h2><p>{html.escape(report['lab']['name'])} "
            f"({html.escape(report['lab']['id'])})</p>"
            "<h3>Virtual devices</h3><table><tr><th>Name</th><th>Type</th>"
            "<th>Pairing</th><th>Discoverable</th><th>Encrypted</th></tr>"
            f"{device_rows}</table>"
            "<h2>Simulation scenarios</h2><table><tr><th>Scenario</th><th>Status</th></tr>"
            f"{scenario_rows}</table><h2>Event timeline</h2><table>"
            "<tr><th>Timestamp</th><th>Severity</th><th>Event</th><th>Details</th></tr>"
            f"{timeline_rows}</table><h2>Detection results</h2><ul>{alerts}</ul>"
            f"<h2>Risk: {risk['category']} ({risk['score']}/100)</h2>"
            f"<p>Evidence: {html.escape(risk['evidence'])}</p>"
            f"<ul>{list_items(risk['findings'])}</ul><h2>Recommendations</h2>"
            f"<ul>{list_items(report['security_recommendations'])}</ul>"
            f"<p>{html.escape(report['safety'])}</p></body></html>", encoding="utf-8"
        )
    with repository.transaction() as db:
        db.execute(
            "INSERT INTO reports VALUES(?,?,?,?,?,?)",
            (uuid4().hex, lab_id, fmt, str(output.resolve()),
             datetime.now(timezone.utc).isoformat(timespec="seconds"),
             json.dumps({"summary": report["executive_summary"]})),
        )
    return output
