import random

import pytest

from blueforce.database.repository import Repository
from blueforce.models import DeviceType, VirtualDevice
from blueforce.simulator.dos_scenarios import events
from blueforce.simulator.resource_model import resource_snapshot
from blueforce.simulator.virtual_lab import VirtualLab


def test_scenario_generators_are_seed_reproducible():
    left = list(events("resource_exhaustion", 6, random.Random(7)))
    right = list(events("resource_exhaustion", 6, random.Random(7)))
    assert left == right
    assert all("SIMULATED" in item["message"] for item in left)


def test_resource_model_is_bounded_and_seeded():
    first = resource_snapshot(4, random.Random(5))
    second = resource_snapshot(4, random.Random(5))
    assert first == second
    assert all(0 <= value <= 100 for value in first.values())


@pytest.mark.parametrize("scenario", [
    "connection_exhaustion", "resource_exhaustion", "availability_degradation",
    "repeated_request_anomaly", "service_disruption",
])
def test_all_scenarios_emit_bounded_synthetic_events(scenario):
    results = list(events(scenario, 5, random.Random(12)))
    assert len(results) == 5
    assert all(item["type"] == scenario for item in results)


def test_device_validation_and_lab_lifecycle(tmp_path):
    with pytest.raises(ValueError):
        VirtualDevice(name="bad", device_type=DeviceType.LAPTOP, lab_id="lab", battery=101)
    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("isolated")
    lab = VirtualLab(db, lab_id)
    device = lab.add_device("Headset", "headphones")
    assert len(lab.devices()) == 1
    assert db.update_device(
        lab.lab_id, device.identifier, {"signal_dbm": -42, "connected": True}
    )
    updated = lab.devices()[0]
    assert updated["signal_dbm"] == -42
    assert updated["connected"] == 1
    assert updated["history_json"] != "[]"
    risky = lab.add_device(
        "Legacy", "smartphone", pairing="legacy",
        discoverable=True, encrypted=False,
    )
    assert risky.risk == "CRITICAL"
    assert lab.devices()[1]["risk"] == "CRITICAL"
    assert lab.remove_device(device.identifier)
    assert len(lab.devices()) == 1
    assert lab.remove_device(risky.identifier)
    assert lab.devices() == []
    db.close()
