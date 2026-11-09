"""SQLite repository with transactional, parameterized CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from blueforce.models import DeviceType, VirtualDevice
from blueforce.database.models import SecurityAlertRecord, SimulationEventRecord


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        migration = Path(__file__).parent / "migrations" / "001_initial.sql"
        self.connection.executescript(migration.read_text(encoding="utf-8"))
        self.connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (1)"
        )
        applied = self.connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]
        if applied < 2:
            migration = Path(__file__).parent / "migrations" / "002_false_positive_tracking.sql"
            self.connection.executescript(migration.read_text(encoding="utf-8"))
            self.connection.execute(
                "INSERT INTO schema_migrations(version) VALUES (2)"
            )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            with self.connection:
                yield self.connection
        except sqlite3.Error:
            raise

    def close(self) -> None:
        self.connection.close()

    def create_lab(self, name: str) -> str:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Lab name must contain 1–80 characters.")
        lab_id = uuid4().hex
        with self.transaction() as db:
            db.execute(
                "INSERT INTO laboratories(id,name,created_at) VALUES(?,?,?)",
                (lab_id, name, now()),
            )
        return lab_id

    def labs(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT id,name,created_at FROM laboratories ORDER BY created_at,rowid"
        ))

    def lab(self, lab_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM laboratories WHERE id=? OR name=?", (lab_id, lab_id)
        ).fetchone()

    def add_device(self, device: Any) -> None:
        from blueforce.detection.risk_scoring import device_risk

        device.risk = device_risk(device.pairing, device.discoverable, device.encrypted)
        with self.transaction() as db:
            db.execute(
                """INSERT INTO virtual_devices VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (device.identifier, device.lab_id, device.name, device.device_type.value,
                 device.signal_dbm, int(device.connected), device.pairing,
                 int(device.discoverable), int(device.encrypted), device.battery,
                 device.risk, json.dumps(device.history), now()),
            )

    def devices(self, lab_id: str) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM virtual_devices WHERE lab_id=? ORDER BY name", (lab_id,)
        ))

    def remove_device(self, lab_id: str, identifier: str) -> bool:
        with self.transaction() as db:
            cursor = db.execute(
                "DELETE FROM virtual_devices WHERE lab_id=? AND id=?",
                (lab_id, identifier),
            )
        return cursor.rowcount > 0

    def update_device(self, lab_id: str, identifier: str, changes: dict[str, Any]) -> bool:
        allowed = {"name", "signal_dbm", "connected", "pairing",
                   "discoverable", "encrypted", "battery"}
        if not changes or changes.keys() - allowed:
            raise ValueError("Provide supported device properties to update.")
        row = self.connection.execute(
            "SELECT * FROM virtual_devices WHERE lab_id=? AND id=?",
            (lab_id, identifier),
        ).fetchone()
        if row is None:
            return False
        history = json.loads(row["history_json"])
        history.append({"at": now(), "event": "Virtual properties updated",
                        "changed": sorted(changes)})
        device = VirtualDevice(
            identifier=row["id"], lab_id=lab_id,
            name=changes.get("name", row["name"]),
            device_type=DeviceType(row["device_type"]),
            signal_dbm=changes.get("signal_dbm", row["signal_dbm"]),
            connected=changes.get("connected", bool(row["connected"])),
            pairing=changes.get("pairing", row["pairing"]),
            discoverable=changes.get("discoverable", bool(row["discoverable"])),
            encrypted=changes.get("encrypted", bool(row["encrypted"])),
            battery=changes.get("battery", row["battery"]),
            risk="LOW", history=history,
        )
        from blueforce.detection.risk_scoring import device_risk

        device.risk = device_risk(device.pairing, device.discoverable, device.encrypted)
        with self.transaction() as db:
            db.execute(
                """UPDATE virtual_devices SET name=?,signal_dbm=?,connected=?,pairing=?,
                   discoverable=?,encrypted=?,battery=?,risk=?,history_json=?
                   WHERE lab_id=? AND id=?""",
                (device.name, device.signal_dbm, int(device.connected), device.pairing,
                 int(device.discoverable), int(device.encrypted), device.battery,
                 device.risk, json.dumps(device.history), lab_id, identifier),
            )
        return True

    def export_lab(self, lab_id: str) -> dict[str, Any]:
        lab = self.lab(lab_id)
        if lab is None:
            raise ValueError(f"Lab not found: {lab_id}")
        devices = []
        for row in self.devices(lab["id"]):
            devices.append({
                "name": row["name"], "device_type": row["device_type"],
                "signal_dbm": row["signal_dbm"], "connected": bool(row["connected"]),
                "pairing": row["pairing"], "discoverable": bool(row["discoverable"]),
                "encrypted": bool(row["encrypted"]), "battery": row["battery"],
                "risk": row["risk"], "history": json.loads(row["history_json"]),
            })
        return {"format_version": 1, "lab_name": lab["name"], "devices": devices}

    def import_lab(self, data: dict[str, Any]) -> str:
        if not isinstance(data, dict):
            raise ValueError("Lab configuration must be a JSON object.")
        if data.get("format_version") != 1:
            raise ValueError("Unsupported lab configuration format.")
        name, devices = data.get("lab_name"), data.get("devices")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Imported lab must have a non-empty lab_name.")
        if not isinstance(devices, list) or len(devices) > 500:
            raise ValueError("Imported lab must contain at most 500 virtual devices.")
        lab_id = uuid4().hex
        prepared: list[VirtualDevice] = []
        for item in devices:
            if not isinstance(item, dict):
                raise ValueError("Every imported device must be a JSON object.")
            item = dict(item)
            item["device_type"] = DeviceType(item.get("device_type"))
            prepared.append(VirtualDevice(lab_id=lab_id, **item))
        from blueforce.detection.risk_scoring import device_risk

        for device in prepared:
            device.risk = device_risk(
                device.pairing, device.discoverable, device.encrypted
            )
        with self.transaction() as db:
            db.execute(
                "INSERT INTO laboratories(id,name,created_at,config_json) VALUES(?,?,?,?)",
                (lab_id, name.strip(), now(), json.dumps({"format_version": 1})),
            )
            for device in prepared:
                db.execute(
                    """INSERT INTO virtual_devices VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (device.identifier, lab_id, device.name, device.device_type.value,
                     device.signal_dbm, int(device.connected), device.pairing,
                     int(device.discoverable), int(device.encrypted), device.battery,
                     device.risk, json.dumps(device.history), now()),
                )
        return lab_id

    def start_session(self, lab_id: str, scenario: str, seed: int | None) -> str:
        session_id = uuid4().hex
        with self.transaction() as db:
            db.execute(
                """INSERT INTO simulation_sessions
                   (id,lab_id,scenario,seed,status,started_at) VALUES(?,?,?,?,?,?)""",
                (session_id, lab_id, scenario, seed, "RUNNING", now()),
            )
        return session_id

    def finish_session(self, session_id: str, status: str, summary: dict[str, Any]) -> None:
        with self.transaction() as db:
            db.execute(
                """UPDATE simulation_sessions SET status=?,ended_at=?,summary_json=?
                   WHERE id=?""",
                (status, now(), json.dumps(summary), session_id),
            )

    def add_event(self, session_id: str, event: dict[str, Any]) -> None:
        record = SimulationEventRecord(
            timestamp=event["timestamp"], event_type=event["type"],
            severity=event["severity"], message=event["message"],
            data=event.get("data", {}),
        )
        with self.transaction() as db:
            db.execute(
                """INSERT INTO simulation_events
                   (session_id,timestamp,event_type,severity,message,data_json)
                   VALUES(?,?,?,?,?,?)""",
                (session_id, record.timestamp, record.event_type, record.severity.value,
                 record.message, json.dumps(record.data)),
            )

    def add_alert(self, lab_id: str, session_id: str | None,
                  alert: dict[str, Any]) -> str:
        record = SecurityAlertRecord(**alert)
        alert_id = uuid4().hex
        with self.transaction() as db:
            db.execute(
                """INSERT INTO security_alerts
                   (id,session_id,lab_id,timestamp,rule,severity,confidence,
                    explanation,data_json) VALUES(?,?,?,?,?,?,?,?,?)""",
                (alert_id, session_id, lab_id, record.timestamp, record.rule,
                 record.severity.value, record.confidence, record.explanation,
                 json.dumps(record.data)),
            )
        return alert_id

    def alerts(self, lab_id: str, unacknowledged: bool = False) -> list[sqlite3.Row]:
        query = "SELECT * FROM security_alerts WHERE lab_id=?"
        if unacknowledged:
            query += " AND acknowledged=0"
        return list(self.connection.execute(query + " ORDER BY timestamp DESC", (lab_id,)))

    def acknowledge_alert(self, alert_id: str) -> bool:
        with self.transaction() as db:
            cursor = db.execute(
                "UPDATE security_alerts SET acknowledged=1 WHERE id=?", (alert_id,)
            )
        return cursor.rowcount > 0

    def mark_false_positive(self, alert_id: str) -> bool:
        with self.transaction() as db:
            cursor = db.execute(
                "UPDATE security_alerts SET false_positive=1,acknowledged=1 WHERE id=?",
                (alert_id,),
            )
        return cursor.rowcount > 0

    def sessions(self, lab_id: str | None = None) -> list[sqlite3.Row]:
        if lab_id:
            query = """SELECT * FROM simulation_sessions WHERE lab_id=?
                       ORDER BY started_at DESC,rowid DESC"""
            return list(self.connection.execute(query, (lab_id,)))
        return list(self.connection.execute(
            "SELECT * FROM simulation_sessions ORDER BY started_at DESC,rowid DESC"
        ))

    def create_incident(self, lab_id: str, title: str, classification: str) -> str:
        incident_id, created = uuid4().hex, now()
        timeline = [{"at": created, "event": "Incident created"}]
        with self.transaction() as db:
            db.execute(
                """INSERT INTO incidents
                   (id,lab_id,title,classification,status,created_at,updated_at,timeline_json)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (incident_id, lab_id, title, classification, "OPEN", created, created,
                 json.dumps(timeline)),
            )
        return incident_id

    def incidents(self, lab_id: str | None = None) -> list[sqlite3.Row]:
        if lab_id:
            return list(self.connection.execute(
                """SELECT * FROM incidents WHERE lab_id=?
                   ORDER BY created_at DESC,rowid DESC""", (lab_id,)
            ))
        return list(self.connection.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC,rowid DESC"
        ))

    def set_incident(self, incident_id: str, status: str, note: str | None = None) -> bool:
        valid = {"OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"}
        if status not in valid:
            raise ValueError(f"Status must be one of {', '.join(sorted(valid))}.")
        with self.transaction() as db:
            row = db.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if row is None:
                return False
            timeline = json.loads(row["timeline_json"])
            timeline.append({"at": now(), "event": f"Status changed to {status}"})
            notes = row["notes"]
            if note:
                notes += ("\n" if notes else "") + note
            db.execute(
                "UPDATE incidents SET status=?,updated_at=?,timeline_json=?,notes=? WHERE id=?",
                (status, now(), json.dumps(timeline), notes, incident_id),
            )
        return True
