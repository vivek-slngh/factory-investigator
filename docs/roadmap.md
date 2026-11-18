# Focused roadmap

The local demonstration is the current deliverable. See [status](status.md) for
what is implemented and verified, and [architecture](architecture.md) for behavior.
This is a prioritized backlog, not a commitment to build every item.

## Next: finish validating what exists

1. Install the optional LangGraph and MCP extras when package access is available.
   Pass their existing tests and run the LangGraph demo. Add one stdio client/server
   smoke check before claiming the gateway works end to end.
2. Connect the existing CSV reader to a CLI command with explicit training,
   calibration, and evaluation windows. Accept it when a saved demo dataset yields
   equivalent results and overlapping windows are rejected.
3. Group consecutive anomalous readings into events. Test healthy gaps, isolated
   spikes, and sustained faults; report sample metrics separately from event metrics.

Do one item at a time. Each should leave the default demo working.

## Then: expand only for a concrete use case

| Addition | Reason to start | Acceptance check |
| --- | --- | --- |
| User-provided maintenance documents | Built-in passages cannot answer the chosen investigation | Retrieved excerpts retain source/section references; unrelated queries can return no evidence |
| Snowflake CLI input | An actual warehouse dataset is available | Match the local reader on an equivalent fixture, then record an opt-in live read |
| One optional LLM investigator | Rule-based findings cannot express the required competing explanations | Structured output, valid citations, clear missing evidence, and bounded failure/retry behavior |
| More fault scenarios | Evaluating beyond the initial bearing demo | Held-out seeds/regimes, false alarms, and detection delay measured separately |

The long-term direction remains RAG-assisted, multi-agent investigation. Add one
model provider and one useful workflow before creating a provider framework or
multiple agent roles with overlapping responsibilities.

## Defer until needed

- Embeddings/vector storage: first show lexical retrieval misses relevant evidence.
- Model persistence: add when repeated training becomes a real workflow cost.
- Graph checkpoints: add when investigations must resume after interruption.
- HTTP API/dashboard: add when a concrete consumer needs them.
- Queues, microservices, Kubernetes, and distributed infrastructure: no current
  workload requires them; keep one package and a local process.

Before serving remote users or sensitive data, define access boundaries and test
them. Until then, keep the supported workflow local and explicit.

## Turning work into repository tasks

Pick a concrete behavior from this backlog, fix a base commit, write focused
acceptance tests, and implement a reference solution. A task should stand on its
own without requiring the whole roadmap. Keep a correct baseline; do not insert
artificial defects or pad code size to make the repository appear mature.
