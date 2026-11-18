# Factory Investigator

A local industrial pump monitoring prototype: learn expected sensor
behavior, detect deviations, and investigate them against cited maintenance evidence.

The first milestone runs locally without Snowflake credentials or a model API key.
It generates 720 synthetic readings, fits a linear sensor surrogate on the first
360, calibrates residual thresholds on the next 144, and evaluates on the final
216. Bearing-wear symptoms begin at sample 576, leaving healthy held-out readings
for false-alarm measurement. Ground-truth labels are used only for evaluation.

## Quick start

Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
factory-investigator demo
pytest
```

The demo writes `artifacts/demo/telemetry.csv`, `scores.json`, `report.json`, and
`report.md`. Use `--output PATH` or `--seed INTEGER` to customize an experiment.
Files with these names in the output directory are replaced on each run.

For a source checkout with NumPy already installed, no installation is necessary:

```bash
PYTHONPATH=src python3 -m factory_investigator.cli demo
python3 -m pytest
```

## What exists today

- Validated telemetry with timezone-aware UTC timestamps and local CSV ingestion.
- Reproducible healthy and bearing-fault simulation.
- Learned linear twin, chronological calibration, residual anomaly scoring, and
  warnings when operating conditions fall outside the training envelope.
- BM25-style lexical retrieval with stable document/section citations.
- Deterministic telemetry, operating-condition, and evidence specialists, followed
  by a reviewer that produces a report. Optional LangGraph runs specialists in
  parallel and joins their outputs before review.
- Optional stdio MCP gateway exposing two bounded demo tools.
- Snowflake reader with validated table identifiers and bound query parameters.
- Automated tests and CI for both the local pipeline and optional integrations.

The local report uses extractive evidence and deterministic rules. It is a baseline
for RAG and multi-agent investigation, **not yet LLM-generated reasoning**. The twin
is a sensor surrogate, not a physics simulation. All included documents and data
are synthetic; demo metrics do not establish real-world diagnostic performance.

## LangGraph

```bash
python -m pip install -e '.[agents]'
factory-investigator demo --engine langgraph
```

Both engines use the same specialist functions and should return equivalent
findings. LangGraph is optional so a local demo does not depend on cloud packages.

## MCP gateway

```bash
python -m pip install -e '.[mcp]'
factory-investigator-mcp
```

Configure your MCP client to launch the installed `factory-investigator-mcp`
executable using stdio. Available tools:

- `search_maintenance(query, limit=3)`: synthetic document passages with citations.
- `investigate_demo(seed=42)`: a synthetic experiment returned in memory.

The gateway does not execute arbitrary SQL, expose credentials, or control equipment.
It is a tool facade for this application, not a general-purpose MCP proxy.

## Snowflake

Install `.[snowflake]`. Create a connector connection using your own environment or
external authentication, then pass it to `SnowflakeSource(connection, table)` from
`factory_investigator.data`. The caller owns and closes the connection. Use the
connector's default `pyformat` binding mode and a read-only warehouse role.

The table needs `TIMESTAMP` (TIMESTAMP_TZ), `ASSET_ID` (VARCHAR), and numeric
`SPEED`, `LOAD`, `AMBIENT`, `TEMPERATURE`, `VIBRATION`, `PRESSURE` columns. Load is
normalized to 0–1. Use consistent units: rpm, degrees Celsius, mm/s RMS, and bar.
Readers use half-open `[start, end)` windows. Missing/nonfinite values, duplicate
timestamps, and mixed-asset training are rejected rather than silently repaired.
Training data must be curated as healthy; the model cannot certify that itself.
The CLI currently generates demo data; live Snowflake CLI ingestion is a next task.

## Documentation and status

- [Architecture](docs/architecture.md): data flow, module responsibilities, model
  and investigation behavior, output contracts, and design boundaries.
- [Implementation record](docs/status.md): completed work, observed test results,
  synthetic metrics, and verification gaps.
- [Focused roadmap](docs/roadmap.md): the next small steps and when larger features
  would become justified.

The local baseline has 15 passing tests. Two optional LangGraph/MCP tests were
skipped because dependency downloads were blocked; their runtime behavior has not
been verified locally. Snowflake is tested with a mock connection only. CI is
configured to install the optional extras; a remote CI run has not been verified.

Keep this as one Python package with a CLI. The next work is validating the existing
integrations and making local data useful, rather than adding infrastructure.
