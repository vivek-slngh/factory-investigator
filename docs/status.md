# Implementation and validation record

Baseline recorded on 2026-11-18, developed on `vivek/update`. This is a newly built
prototype. It has no claimed production history or real-equipment validation.

## Completed work

| Area | Implemented | Verification / boundary |
| --- | --- | --- |
| Data | Typed readings, UTC normalization, CSV reader/writer, chronological validation | CSV round trip, window boundaries, invalid input tests |
| Simulation | Seeded pump data and abrupt bearing symptoms | Repeatability and multiple-seed checks |
| Learned twin | Linear expected readings, separate calibration, residual alerts | Temporal leakage, rank deficiency, label independence, detection checks |
| Retrieval | Four synthetic passages, lexical ranking, stable citation IDs | Citation fields, empty results, result limit checks |
| Investigation | Deterministic specialists and rule-based report | Healthy-window and operating-envelope checks; end-to-end demo |
| LangGraph | Optional parallel specialist graph and reviewer join | Equivalence test written; skipped locally because dependency unavailable |
| MCP | `search_maintenance` and `investigate_demo` over stdio | Registration/tool-call test written; skipped locally because dependency unavailable; stdio transport not tested |
| Snowflake | Parameterized reader with validated table name | Mocked query/mapping test only; no warehouse connection tested |
| Packaging / CI | Installable CLI, optional extras, Python 3.11/3.12 workflow | Editable install and CLI verified locally on Python 3.12; remote CI result not verified |

## Local validation

Commands used from the repository root:

```bash
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/factory-investigator demo
.venv/bin/python -m pytest -q
```

The install command above reused dependencies/build tools already available in
the development environment. For a fresh environment, use the README quick start.

Result: **15 passed, 2 skipped**. LangGraph and MCP installation was attempted but
failed because the environment could not resolve the package host. These skips
are not passing integration results. The configured CI installs both extras and
runs the LangGraph demo, but its outcome must be checked after a push.

## Default synthetic experiment

| Split | Zero-based sample indices | Purpose |
| --- | --- | --- |
| Training | 0–359 | Fit expected readings and residual scales |
| Calibration | 360–503 | Select alert threshold |
| Evaluation, healthy | 504–575 | Measure false positives |
| Evaluation, injected fault | 576–719 | Measure fault recall |

With seed 42, the observed local run flagged all 144 injected-fault readings and
1 of 72 healthy evaluation readings: **100% sample-level recall** and **1.39%
false-positive rate**. It flagged 145 readings total and warned about 2 evaluation
readings outside the training envelope.

The first flagged reading is a false positive before the injected fault begins;
`first_anomaly` is not an estimate of the true fault onset. There is no event-level
detection-delay metric yet. These results use simple synthetic linear data and a
large abrupt fault, so they do not demonstrate real-world diagnostic accuracy.

## What remains unbuilt

There is no LLM provider, embedding service, external-document ingestion, live-data
CLI, saved-model format, event grouping, HTTP API, or dashboard. There is no
checkpoint/resume implementation or remote-service authentication. The Snowflake
reader and optional integration code do not make this a production deployment.

## Updating this record

When behavior changes, update the relevant architecture section and its acceptance
check. Record test outcomes actually observed and keep skipped, mocked, and live
verification distinct. Refresh metrics only after running the documented experiment.
Keep new ideas in the roadmap until their implementation and checks exist.
