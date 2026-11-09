from blueforce.database.repository import Repository


def test_lab_device_and_incident_persist(tmp_path):
    repository = Repository(tmp_path / "test.sqlite3")
    lab_id = repository.create_lab("persistent")
    incident_id = repository.create_incident(lab_id, "Synthetic outage", "SIMULATED")
    assert repository.set_incident(incident_id, "INVESTIGATING", "Reviewing events")
    incident = repository.incidents(lab_id)[0]
    assert incident["status"] == "INVESTIGATING"
    assert "Reviewing events" in incident["notes"]
    repository.close()


def test_lab_configuration_round_trip_and_alert_review(tmp_path):
    from blueforce.models import DeviceType, VirtualDevice

    repository = Repository(tmp_path / "test.sqlite3")
    original = repository.create_lab("original")
    repository.add_device(VirtualDevice(
        name="Sensor", device_type=DeviceType.IOT_SENSOR, lab_id=original,
        discoverable=True,
    ))
    config = repository.export_lab(original)
    restored = repository.import_lab({**config, "lab_name": "restored"})
    assert len(repository.devices(restored)) == 1
    alert_id = repository.add_alert(restored, None, {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "rule": "test", "severity": "LOW", "confidence": 0.8,
        "explanation": "test alert",
    })
    assert repository.mark_false_positive(alert_id)
    alert = repository.alerts(restored)[0]
    assert alert["false_positive"] == 1
    assert alert["acknowledged"] == 1
    repository.close()


def test_invalid_import_has_no_partial_lab(tmp_path):
    import pytest

    repository = Repository(tmp_path / "test.sqlite3")
    with pytest.raises(ValueError):
        repository.import_lab({"format_version": 1, "lab_name": "bad",
                               "devices": [{"device_type": "not-a-device"}]})
    assert repository.labs() == []
    repository.close()
