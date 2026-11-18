"""Evidence specialists, runnable sequentially or as a LangGraph fan-out.

These are deterministic specialist nodes, not autonomous LLM agents. This is
an inspectable baseline for later model-backed investigation policies.
"""
from typing import TypedDict

from .retrieval import Retriever


class State(TypedDict, total=False):
    readings: list[dict]
    telemetry: dict
    operating: dict
    evidence: list[dict]
    report: dict


def telemetry_specialist(state: State) -> dict:
    anomalies = [r for r in state["readings"] if r["anomaly"]]
    elevated = []
    if anomalies:
        for sensor in ("temperature", "vibration", "pressure"):
            if sum(r["residual_z"][sensor] > 3 for r in anomalies) / len(anomalies) >= 0.5:
                elevated.append(sensor)
    return {"telemetry": {"anomaly_count": len(anomalies), "elevated_sensors": elevated,
                          "first_anomaly": anomalies[0]["timestamp"] if anomalies else None}}


def operating_specialist(state: State) -> dict:
    count = sum(r["outside_training_range"] for r in state["readings"])
    return {"operating": {"out_of_range_count": count,
                          "note": "Predictions outside the training envelope require review." if count else
                          "All evaluated operating conditions are within the training envelope."}}


def evidence_specialist(state: State) -> dict:
    anomalies = [r for r in state["readings"] if r["anomaly"]]
    if not anomalies:
        return {"evidence": []}
    terms = {sensor for row in anomalies for sensor, z in row["residual_z"].items() if abs(z) > 3}
    return {"evidence": Retriever().search(" ".join(sorted(terms)) + " bearing maintenance", limit=4)}


def reviewer(state: State) -> dict:
    telemetry = state["telemetry"]
    sources = state["evidence"]
    if not telemetry["anomaly_count"]:
        hypothesis = "No anomaly detected in this window."
        checks = []
    elif {"temperature", "vibration"}.issubset(telemetry["elevated_sensors"]):
        hypothesis = "Bearing wear or lubrication deterioration is a candidate explanation, not a confirmed diagnosis."
        checks = ["Inspect lubrication condition and bearing condition.",
                  "Check alignment and suction conditions to distinguish alternative causes."]
    else:
        hypothesis = "Sensor deviations require investigation; the available evidence does not identify a cause."
        checks = ["Validate sensor readings and inspect operating conditions."]
    return {"report": {"asset_id": state["readings"][0]["asset_id"],
                       "observations": telemetry, "operating_conditions": state["operating"],
                       "hypothesis": hypothesis, "suggested_checks": checks,
                       "evidence": sources,
                       "limitations": ["Synthetic telemetry and synthetic reference documents.",
                                       "Linear sensor surrogate, not a physics simulation.",
                                       "Deterministic extractive investigation; no LLM is used.",
                                       "No maintenance actions are executed."]}}


def investigate(readings: list[dict], engine: str = "local") -> dict:
    if not readings:
        raise ValueError("Investigation requires scored readings")
    state: State = {"readings": readings}
    if engine == "local":
        for node in (telemetry_specialist, operating_specialist, evidence_specialist, reviewer):
            state.update(node(state))
    elif engine == "langgraph":
        from langgraph.graph import END, START, StateGraph
        graph = StateGraph(State)
        for name, node in (("telemetry_node", telemetry_specialist),
                           ("operating_node", operating_specialist),
                           ("evidence_node", evidence_specialist), ("reviewer", reviewer)):
            graph.add_node(name, node)
        specialists = ["telemetry_node", "operating_node", "evidence_node"]
        for name in specialists:
            graph.add_edge(START, name)
        graph.add_edge(specialists, "reviewer")
        graph.add_edge("reviewer", END)
        state = graph.compile().invoke(state)
    else:
        raise ValueError("engine must be local or langgraph")
    return state["report"]
