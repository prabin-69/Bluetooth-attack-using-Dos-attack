import json
import asyncio

from blueforce.core.engine import SimulationEngine
from blueforce.database.repository import Repository
from blueforce.reporting.report_generator import export


def test_report_formats_are_written_and_registered(tmp_path):
    repository = Repository(tmp_path / "test.sqlite3")
    lab_id = repository.create_lab("report-lab")
    asyncio.run(SimulationEngine(repository).run(
        lab_id, "availability_degradation", steps=4, seed=3
    ))
    for extension in ("json", "csv", "txt", "html"):
        output = tmp_path / f"report.{extension}"
        assert export(repository, lab_id, output, extension) == output
        assert output.exists()
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "executive_summary" in payload
    assert "risk_assessment" in payload
    csv_content = (tmp_path / "report.csv").read_text(encoding="utf-8").lower()
    for section in ("lab_configuration", "simulation_scenario", "timeline_event",
                    "recommendation"):
        assert section in csv_content
    for extension in ("txt", "html"):
        content = (tmp_path / f"report.{extension}").read_text(encoding="utf-8")
        for section in ("Lab configuration", "Simulation scenarios",
                        "Event timeline", "Recommendations"):
            assert section.lower() in content.lower()
    assert repository.connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 4
    repository.close()
