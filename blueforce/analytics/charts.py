"""Optional PNG chart export for a lab's synthetic event timeline."""

from __future__ import annotations

from pathlib import Path

from blueforce.database.repository import Repository


def export_resource_chart(repository: Repository, lab_id: str, output: Path) -> Path:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Chart export requires Matplotlib; install project requirements.") from exc
    lab = repository.lab(lab_id)
    if lab is None:
        raise ValueError(f"Lab not found: {lab_id}")
    sessions = repository.sessions(lab["id"])
    points: list[tuple[int, int, int]] = []
    if sessions:
        rows = repository.connection.execute(
            """SELECT data_json FROM simulation_events WHERE session_id=?
               ORDER BY id""", (sessions[0]["id"],)
        )
        import json
        for index, row in enumerate(rows):
            data = json.loads(row["data_json"])
            if "simulated_cpu" in data:
                points.append((index, data["simulated_cpu"], data["simulated_memory"]))
    if not points:
        raise ValueError("The most recent simulation contains no resource metrics.")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots()
    axis.plot([point[0] for point in points], [point[1] for point in points], label="Simulated CPU")
    axis.plot([point[0] for point in points], [point[2] for point in points], label="Simulated memory")
    axis.set(title="BLUEFORCE X — Synthetic Resource Model",
             xlabel="Event index", ylabel="Virtual utilization (%)", ylim=(0, 100))
    axis.legend()
    figure.tight_layout()
    figure.savefig(output)
    plt.close(figure)
    return output
