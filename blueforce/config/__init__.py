"""Application settings and safety boundaries."""

import os
from pathlib import Path

APP_NAME = "BLUEFORCE X"
TAGLINE = "Analyze. Simulate. Detect. Defend."
DEFAULT_DB = Path(os.environ.get(
    "BLUEFORCE_DB",
    str(Path.home() / ".blueforce-x" / "blueforce.sqlite3"),
))
MAX_SIMULATION_STEPS = 10_000
SCENARIOS = (
    "connection_exhaustion",
    "resource_exhaustion",
    "availability_degradation",
    "repeated_request_anomaly",
    "service_disruption",
)
