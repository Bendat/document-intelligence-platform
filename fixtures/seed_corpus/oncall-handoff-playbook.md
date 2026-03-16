# On-Call Handoff Playbook

## Purpose

This playbook defines the minimum standard for handing off active operational
work between on-call engineers. The goal is to reduce repeated triage, prevent
context loss, and make ownership explicit when incidents cross time zones or
shift boundaries.

## Handoff Triggers

Create a formal handoff when any of the following are true:

- an incident remains open across a shift change
- a risky mitigation remains active
- a dashboard or alert indicates elevated likelihood of recurrence
- a pending vendor access session overlaps the next shift

## Required Handoff Fields

Every handoff note must include:

- customer impact statement
- current severity
- suspected root cause or current working theory
- actions already taken
- actions explicitly ruled out
- dashboards or queries worth keeping open
- next check-in time
- named owner for the next shift

## Communication Rules

- Write handoffs in complete sentences, not fragments.
- Link the incident ticket or change record directly.
- State whether Platform Reliability still owns incident command.
- If Security Operations or a vendor is involved, state the current access
  window and approver.

## Common Failure Modes

- assuming the incoming engineer can infer customer impact from raw metrics
- failing to state which mitigation flags remain enabled
- forgetting to mention that a vendor session is still live
- carrying forward an untested theory as if it were confirmed

## Example Handoff

"Payments API remains Sev 2 in the EU region. Customer checkout is functional
but p95 latency is still elevated at 1.4 seconds. Platform Reliability retains
incident command. We rolled back the `risk-evaluator` timeout change, disabled
shadow fraud checks, and confirmed ledger lag is normal. Current working theory
is residual retry amplification from the storefront. Do not raise PostgreSQL
pool limits without incident commander approval. Next review at 22:30 UTC."

## FAQ

### Who normally owns incident command for payment incidents?

Platform Reliability.

### When should Security Operations be called out explicitly?

Whenever vendor access, suspicious admin activity, or privileged-session review
is part of the ongoing work.
