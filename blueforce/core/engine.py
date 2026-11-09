"""Async simulation orchestration, event persistence, and detection."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

from blueforce.config import MAX_SIMULATION_STEPS, SCENARIOS
from blueforce.database.repository import Repository
from blueforce.detection.anomaly_engine import AnomalyEngine
from blueforce.simulator.dos_scenarios import events

logger = logging.getLogger(__name__)


class SimulationEngine:
    def __init__(self, repository: Repository, detector: AnomalyEngine | None = None):
        self.repository = repository
        self.detector = detector or AnomalyEngine()

    async def run(self, lab_id: str, scenario: str, steps: int = 20,
                  seed: int | None = None, interval: float = 0.0) -> dict[str, Any]:
        if scenario not in SCENARIOS:
            raise ValueError(f"Scenario must be one of: {', '.join(SCENARIOS)}")
        if not 1 <= steps <= MAX_SIMULATION_STEPS:
            raise ValueError(f"Steps must be between 1 and {MAX_SIMULATION_STEPS}.")
        if not 0 <= interval <= 5:
            raise ValueError("Interval must be between 0 and 5 seconds.")
        if self.repository.lab(lab_id) is None:
            raise ValueError(f"Lab not found: {lab_id}")
        session_id = self.repository.start_session(lab_id, scenario, seed)
        rng = random.Random(seed)
        detector = self.detector.new_session()
        alerts, records = 0, []
        started = time.perf_counter()
        logger.info("Started synthetic scenario %s in lab %s", scenario, lab_id)
        try:
            for item in events(scenario, steps, rng):
                item["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
                self.repository.add_event(session_id, item)
                records.append(item)
                alert = detector.inspect(item)
                if alert:
                    self.repository.add_alert(lab_id, session_id, alert)
                    alerts += 1
                if interval:
                    await asyncio.sleep(interval)
                else:
                    await asyncio.sleep(0)
            elapsed = max(time.perf_counter() - started, 0.000001)
            summary = {"events": len(records), "alerts": alerts, "seed": seed,
                       "duration_seconds": round(elapsed, 6),
                       "events_per_second": round(len(records) / elapsed, 2),
                       "scenario": scenario, "synthetic_only": True}
            self.repository.finish_session(session_id, "COMPLETED", summary)
            return {"session_id": session_id, **summary}
        except asyncio.CancelledError:
            logger.info("Cancelled synthetic scenario session %s", session_id)
            self.repository.finish_session(
                session_id, "CANCELLED", {"events": len(records), "alerts": alerts}
            )
            raise
        except Exception as exc:
            logger.exception("Synthetic scenario session %s failed", session_id)
            self.repository.finish_session(
                session_id, "FAILED", {"events": len(records), "error": str(exc)}
            )
            raise
