import asyncio
import time

from blueforce.core.engine import SimulationEngine
from blueforce.database.repository import Repository


def test_deterministic_simulation_persists_events_and_alerts(tmp_path):
    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("test")
    first = asyncio.run(SimulationEngine(db).run(
        lab_id, "repeated_request_anomaly", steps=8, seed=42
    ))
    assert first["synthetic_only"] is True
    assert first["events"] == 8
    assert first["alerts"] > 0
    assert db.sessions(lab_id)[0]["status"] == "COMPLETED"
    assert db.alerts(lab_id)
    db.close()


def test_invalid_scenario_is_rejected(tmp_path):
    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("test")
    try:
        asyncio.run(SimulationEngine(db).run(lab_id, "real_radio_attack"))
    except ValueError as exc:
        assert "Scenario must be" in str(exc)
    else:
        raise AssertionError("Invalid scenario accepted")
    db.close()


def test_cancelled_run_is_persisted_as_cancelled(tmp_path):
    async def cancel_run(db, lab_id):
        task = asyncio.create_task(SimulationEngine(db).run(
            lab_id, "resource_exhaustion", steps=20, seed=2, interval=0.1
        ))
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("Simulation task did not propagate cancellation")

    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("cancel-test")
    asyncio.run(cancel_run(db, lab_id))
    assert db.sessions(lab_id)[0]["status"] == "CANCELLED"
    db.close()


def test_large_bounded_run_completes_within_performance_budget(tmp_path):
    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("performance")
    started = time.perf_counter()
    result = asyncio.run(SimulationEngine(db).run(
        lab_id, "resource_exhaustion", steps=1000, seed=11
    ))
    elapsed = time.perf_counter() - started
    assert result["events"] == 1000
    assert elapsed < 10
    db.close()


def test_failed_event_write_marks_session_failed(tmp_path):
    db = Repository(tmp_path / "test.sqlite3")
    lab_id = db.create_lab("failure")

    def fail_write(session_id, event):
        raise OSError("synthetic database write failure")

    db.add_event = fail_write
    try:
        asyncio.run(SimulationEngine(db).run(
            lab_id, "resource_exhaustion", steps=1, seed=1
        ))
    except OSError as exc:
        assert "synthetic database write failure" in str(exc)
    else:
        raise AssertionError("Expected the persistence failure to propagate")
    assert db.sessions(lab_id)[0]["status"] == "FAILED"
    db.close()
