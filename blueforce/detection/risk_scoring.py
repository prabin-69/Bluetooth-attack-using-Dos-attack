"""Evidence-based posture assessment for virtual devices."""

from __future__ import annotations

from typing import Any


def device_risk(pairing: str, discoverable: bool, encrypted: bool) -> str:
    score = 20 if pairing == "legacy" else 8 if pairing == "unknown" else 0
    score += 10 if discoverable else 0
    score += 25 if not encrypted else 0
    if score >= 50:
        return "CRITICAL"
    if score >= 35:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"


def assess(devices: list[Any]) -> dict[str, Any]:
    score, findings, recommendations = 0, [], []
    for device in devices:
        name = device["name"]
        if device["pairing"] == "legacy":
            score += 20
            findings.append(f"{name}: legacy pairing is configured.")
            recommendations.append(f"Use modern authenticated pairing for {name}.")
        elif device["pairing"] == "unknown":
            score += 8
            findings.append(f"{name}: pairing mode is unknown; this is not proof of weakness.")
        if device["discoverable"]:
            score += 10
            findings.append(f"{name}: device is configured as discoverable.")
            recommendations.append(f"Disable discoverability for {name} when not needed.")
        if not device["encrypted"]:
            score += 25
            findings.append(f"{name}: encryption is disabled in the virtual configuration.")
            recommendations.append(f"Require encryption for {name}.")
    score = min(100, score)
    category = "LOW" if score < 25 else "MEDIUM" if score < 50 else "HIGH" if score < 75 else "CRITICAL"
    if not findings:
        findings.append("No configured risk indicators were found in the virtual lab.")
    if not recommendations:
        recommendations.append("Maintain least exposure and review pairing policy periodically.")
    return {"score": score, "category": category, "findings": findings,
            "evidence": "Assessment reflects configured virtual-device properties only.",
            "recommendations": sorted(set(recommendations))}
