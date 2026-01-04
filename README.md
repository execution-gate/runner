# Fail-Closed Execution Runner

A minimal, fail-closed execution pattern for services, workers, and agents.

This repository provides a **neutral execution runner** that enforces *explicit authorization* before work is allowed to proceed. It is designed for environments where **unauthorized execution must stop immediately**, without retries, fallbacks, or silent degradation.

This is infrastructure code, not a framework.

---

## What this is

- A **drop-in execution guard** for Python runtimes
- Enforces **fail-closed execution** at critical boundaries
- Suitable for:
  - background workers
  - job processors
  - AI agents
  - scheduled tasks
  - cost-incurring pipelines

If authorization cannot be confirmed, execution halts.

---

## Core principles

1. **Fail-closed**
   - Any failure to authorize = execution stops
   - Network errors, timeouts, invalid responses all deny

2. **Explicit boundaries**
   - Authorization is checked at defined execution boundaries
   - Never implicit, never cached blindly

3. **Runtime-agnostic**
   - No framework coupling
   - Works with queues, cron, agents, scripts

4. **Authority-driven**
   - Authorization is decided by an external authority
   - This repo does not define *who* authorizes, only *how* enforcement works

---

## The 5 execution boundaries

These boundaries are where authorization checks **must** occur.

| Boundary | When | Why |
|--------|------|-----|
| Startup | Process boot | Prevents unauthorized instances from running |
| Before job | Each work unit | Stops execution if revoked mid-run |
| Before cost | External APIs, LLMs | Prevents runaway cost |
| Before side effects | Writes, emails, payments | Prevents irreversible actions |
| Before fan-out | Loops, batches | Prevents expensive parallel execution |

You may enforce more often, but never less.

---

## Repository structure

```
runner/
├─ execution_gate/
│  ├─ guard.py          # authorization + fail-closed enforcement
│  └─ runner.py         # example execution loop
├─ examples/
│  ├─ worker.py         # queue / job worker example
│  └─ agent_loop.py     # agent-style loop example
└─ README.md
```

---

## Basic usage pattern

At every boundary:

```bash
authorize()
if not authorized:
    stop execution immediately
```

There are **no retries** on deny.

---

## Authority provider (default)

This repository uses **MachineID** as the default execution authority provider.

- Device-level authorization
- Org-level kill switch
- Fail-closed semantics

The authority provider can be swapped, but the enforcement model must remain fail-closed.

---

## Environment configuration

```bash
export MACHINEID_ORG_KEY="org_xxx"
export SERVICE_NAME="worker"
export ENVIRONMENT="prod"
export INSTANCE_ID="i-abc123"
```

Recommended device ID format:

```
{service}:{env}:{role}:{instance}
```

Example:

```
worker:prod:processor:i-abc123
```

---

## Enforcement rules (non-negotiable)

- **Timeouts:** short (≤ 3 seconds)
- **On deny:** stop immediately
- **On network failure:** deny
- **On malformed response:** deny
- **On uncertainty:** deny

Fail-closed means fail-closed.

---

## Testing the system

1. Start the service
2. Verify execution proceeds
3. Revoke authorization in the authority system
4. Wait for next boundary
5. Execution must stop immediately
6. Restore authorization
7. Execution resumes on restart or next loop

---

## What this repo is not

- Not a framework
- Not a scheduler
- Not an agent platform
- Not a retry system
- Not a best-effort guard

It is **hard enforcement**.

---

## Why this exists

As autonomous systems, agents, and background workers proliferate, **unauthorized execution becomes a systemic risk**.

Fail-open execution leads to:
- runaway costs
- security exposure
- irreversible side effects
- loss of operator control

This runner exists to make *hard stops* the default.

---

## License

MIT

Use it. Modify it. Embed it.

Just don’t make it fail open.
