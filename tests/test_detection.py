from blueforce.detection.anomaly_engine import AnomalyEngine
from blueforce.detection.detection_rules import StatisticalAnomalyDetector
from blueforce.detection.risk_scoring import assess


def test_request_anomaly_explains_alert():
    alert = AnomalyEngine(request_threshold=10).inspect({
        "type": "repeated_request_anomaly",
        "data": {"requests": 12},
    })
    assert alert["severity"] == "HIGH"
    assert "exceeded configured baseline" in alert["explanation"]


def test_risk_unknown_does_not_claim_weakness():
    risk = assess([{"name": "Sensor", "pairing": "unknown",
                    "discoverable": False, "encrypted": True}])
    assert risk["score"] == 8
    assert "not proof of weakness" in risk["findings"][0]


def test_statistical_detector_flags_outlier_against_observed_baseline():
    detector = StatisticalAnomalyDetector(minimum_samples=3, z_threshold=3)
    for value in (1, 2, 3):
        assert detector.inspect({
            "type": "synthetic", "data": {"requests": value}
        }) is None
    result = detector.inspect({
        "type": "synthetic", "data": {"requests": 100}
    })
    assert result is not None
    assert result["metric"] == "requests"
    assert result["z_score"] >= 3


def test_correlated_rule_occurrences_escalate_with_explanation():
    detector = AnomalyEngine(request_threshold=1, correlation_threshold=2)
    sample = {"type": "repeated_request_anomaly", "data": {"requests": 5}}
    detector.inspect(sample)
    alert = detector.inspect(sample)
    assert alert["severity"] == "CRITICAL"
    assert "Correlated with 2 recent occurrences" in alert["explanation"]
    fresh = detector.new_session().inspect(sample)
    assert "Correlated with" not in fresh["explanation"]
