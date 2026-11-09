import asyncio

from textual.widgets import Static

from blueforce.analytics.charts import export_resource_chart
from blueforce.analytics.metrics import actual_host_metrics, lab_metrics
from blueforce.core.engine import SimulationEngine
from blueforce.database.repository import Repository
from blueforce.tui import create_dashboard


def test_synthetic_metrics_and_chart_are_labeled(tmp_path):
    repository = Repository(tmp_path / "test.sqlite3")
    lab_id = repository.create_lab("metrics")
    asyncio.run(SimulationEngine(repository).run(
        lab_id, "resource_exhaustion", steps=4, seed=3
    ))
    metrics = lab_metrics(repository, lab_id)
    assert metrics["synthetic_event_count_latest_session"] == 4
    assert "SIMULATED" in metrics["measurements"]
    assert "CPU" in metrics["simulated_resource_graph_ascii"]
    assert export_resource_chart(
        repository, lab_id, tmp_path / "resources.png"
    ).exists()
    assert "ACTUAL HOST" in actual_host_metrics()["source"]
    repository.close()


def test_textual_dashboard_renders_local_state(tmp_path):
    database = tmp_path / "dashboard.sqlite3"

    async def verify():
        app = create_dashboard(database)
        async with app.run_test() as pilot:
            await pilot.pause(0.8)
            assert "SYNTHETIC BLUETOOTH SECURITY LAB" in str(
                app.query_one("#panel", Static).content
            )

    asyncio.run(verify())
