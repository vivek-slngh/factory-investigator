"""End-to-end experiment with held-out ground truth used only for metrics."""
import json
from pathlib import Path

from .data import write_csv
from .investigation import investigate
from .simulation import generate
from .twin import Twin


def run_demo(output: Path, seed: int = 42, engine: str = "local") -> dict:
    rows = generate(seed)
    train, calibration, evaluation = rows[:360], rows[360:504], rows[504:]
    twin = Twin.fit(train, calibration)
    scored = twin.score(evaluation)
    report = investigate(scored, engine)
    healthy = [(r, s) for r, s in zip(evaluation, scored) if r.fault == "healthy"]
    faulty = [(r, s) for r, s in zip(evaluation, scored) if r.fault != "healthy"]
    report["experiment"] = {
        "seed": seed, "engine": engine,
        "training_samples": len(train), "calibration_samples": len(calibration),
        "evaluation_samples": len(evaluation), "threshold": twin.threshold,
        "false_positive_rate": sum(s["anomaly"] for _, s in healthy) / len(healthy),
        "fault_recall": sum(s["anomaly"] for _, s in faulty) / len(faulty),
        "training_end": train[-1].timestamp.isoformat(),
        "calibration_end": calibration[-1].timestamp.isoformat(),
        "evaluation_start": evaluation[0].timestamp.isoformat(),
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "telemetry.csv", rows)
    (output / "scores.json").write_text(json.dumps(scored, indent=2, allow_nan=False) + "\n")
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    lines = ["# Pump investigation", "", report["hypothesis"], "", "## Observations", "",
             f"Flagged readings: {report['observations']['anomaly_count']}",
             f"False-positive rate: {report['experiment']['false_positive_rate']:.2%}",
             f"Fault recall: {report['experiment']['fault_recall']:.2%}", "", "## Evidence", ""]
    lines.extend(f"- [{e['citation']}] {e['text']}" for e in report["evidence"])
    lines.extend(["", "## Suggested checks", ""] + [f"- {c}" for c in report["suggested_checks"]])
    lines.extend(["", "## Limitations", ""] + [f"- {c}" for c in report["limitations"]])
    (output / "report.md").write_text("\n".join(lines) + "\n")
    return report
