# Ops Agent project log

This records why the system changed and evidence that it works.
It contains no secrets and no copied production data.

## Current baseline

- Date:
- Author:
- Git commit and branch:
- API / agent / frontend image digests:
- Compose project:
- Seed version and fixed random seed:
- Prompt version or commit:
- Model provider and exact model:
- LangGraph / LangChain versions:
- LangSmith project:
- Trace retention/deletion date:

## Architecture decisions

### ADR-001 — Read-only domain boundary

- Status: accepted
- Context:
- Decision: only six typed HTTP tools; no domain DB credential or mutation tool.
- Consequences:
- Evidence: before/after fingerprint and tests.

### ADR-002 — Persistent conversation state

- Status: accepted
- Context:
- Decision: caller thread_id keys checkpoints in the checkpoint schema; the
  async pool lives for FastAPI lifespan.
- Consequences:
- Evidence: multi-turn restart test and trace.

### ADR-003 — Bounded tool loop

- Status: accepted
- Context:
- Decision: reset tool_rounds per request, use a soft-limit finalizer, and keep
  recursion_limit as a hard backstop.
- Consequences:
- Evidence: mocked routing tests and soft-limit trace.

## Evaluation run: YYYY-MM-DD / short-name

### Purpose

- Question:
- Change under evaluation:
- Expected risk:

### Reproduction

- Clean clone/start/test commands:
- `.env.example` plus locally supplied secret names only:
- Git commit and image digests:
- Seed/fingerprint before:

### Query contract

- Scenario: flagship | multi-turn | restart | API outage | soft limit | other
- Thread ID: synthetic UUID only
- User message: REDACTED or synthetic
- Expected tool sequence and bounded arguments:
- Expected answer properties:
- Expected handled-failure behavior:

### LangSmith trace

- Trace URL: private URL; never commit a share token
- Root run ID / request ID:
- Project / model / prompt version:
- Start time / duration:
- Input/output visibility: hidden | synthetic-visible
- Redaction verified by:

### Observed execution

- Actual tool sequence:
- Tool rounds / soft limit / retries:
- Final keys: answer, thread_id, tool_rounds, soft_limit_reached
- Answer summary: no sensitive raw output
- Seed/fingerprint after:
- Domain unchanged: yes | no

### Rubric

- Read-only selection: 0 | 1
- Schema validity: 0 | 1
- Flagship efficiency: 0 | 1
- No invented mutation: 0 | 1
- Loop discipline: 0 | 1
- Total: N / 5
- Mandatory criteria passed: yes | no
- Reviewer notes:

### Failure analysis

- Class: none | model | tool | API | checkpoint | timeout | contract
- User-visible behavior:
- Root cause:
- Handled without fabricated data:
- Safe retry and stop condition:

### Decision

- Result: pass | pass with follow-up | fail
- Follow-up issue / owner / due date:

## Release checklist

- [ ] API deterministic tests pass.
- [ ] Agent tests pass with `-m "not live"`.
- [ ] Frontend typecheck, tests, and build pass.
- [ ] Empty-volume clean-clone Compose startup passes.
- [ ] Smoke passes without provider secrets.
- [ ] Flagship live trace reviewed.
- [ ] Same-thread follow-up survives agent restart.
- [ ] API outage returns handled prose, not 500 or invented data.
- [ ] Fingerprint matches before and after chat.
- [ ] Trace redaction and retention reviewed.
- [ ] Published digests match this commit; rollback SHA tags recorded.
