# Payments Service Runbook

## Document Control

- Service: Payments API
- Service tier: Tier 1
- Primary owner: Platform Reliability
- Secondary owner: Checkout Experience
- Slack channel: `#payments-ops`
- Pager rotation: `platform-reliability-primary`
- Last reviewed: 2026-02-28

## Purpose

The Payments API accepts checkout authorization requests, applies fraud and risk
controls, writes an immutable ledger event, and returns a final payment state to
the storefront and order-management services. The service is business critical:
if it is unavailable, customers cannot complete card payments and finance cannot
reconcile order capture against downstream settlement.

This runbook exists to help the on-call engineer restore service quickly,
communicate clearly, and gather enough context to hand off deeper remediation to
the owning team. The guidance is intentionally operational rather than
architectural; refer to the platform ADRs for design rationale.

## Service Boundaries

The Payments API is responsible for:

- card authorization orchestration
- idempotency protection for retries from the storefront
- ledger event creation for approved and declined transactions
- publishing payment state changes to downstream consumers
- exposing internal operational metrics and health endpoints

The service is not responsible for:

- direct settlement with acquiring banks
- customer refund workflows
- subscription billing schedules
- tax calculation

## Dependencies

Hard dependencies:

- `ledger-writer` for immutable payment events
- `risk-evaluator` for fraud and risk scoring
- PostgreSQL for transactional state and idempotency keys
- Redis for short-lived reservation and retry coordination
- feature flag service for incident mitigations

Soft dependencies:

- notification pipeline for decline and delay alerts
- analytics export pipeline for payment conversion dashboards

If `ledger-writer` is unavailable, treat the Payments API as degraded even if
authorization requests continue to enter the system. Success without durable
ledger capture is not acceptable.

## SLOs and Operational Targets

- Availability SLO: 99.95 percent over 30 days
- Checkout authorization p95 latency: under 900 ms
- Ledger write completion after authorization: under 2 seconds
- Recovery time objective (RTO): 30 minutes
- Recovery point objective (RPO): 5 minutes

The team uses the following incident severities:

- Sev 1: customers broadly cannot complete payments
- Sev 2: elevated latency, partial failures, or delayed downstream propagation
- Sev 3: internal-only degradation with no immediate customer impact

## Dashboards and Logs

Start with:

- `Payments / Golden Signals`
- `Payments / Dependency Health`
- `Ledger Writer / Publish Lag`
- `Risk Evaluator / Redis and Decision Latency`

Primary log filters:

- `service=payments-api`
- `route=/v1/authorize`
- `error_type=dependency_timeout`
- `dependency=ledger-writer`
- `dependency=risk-evaluator`

If requests are failing and the root cause is not immediately obvious, compare
the volume of `authorize.requested`, `authorize.approved`, `authorize.declined`,
and `ledger.write.succeeded`. Divergence between authorization and ledger events
usually narrows the search to either `ledger-writer` or PostgreSQL saturation.

## Common Alerts

### `PaymentsHighLatency`

Meaning:
Checkout authorization p95 latency is above 900 ms for 10 minutes.

Likely causes:

- slow risk decisions
- Redis saturation
- downstream ledger write retry storms
- pool exhaustion in the PostgreSQL connection layer

Immediate actions:

1. Confirm whether latency is isolated to one region or global.
2. Check `risk-evaluator` decision latency and Redis connection usage.
3. If ledger publish lag is also increasing, evaluate whether `ledger-writer`
   is timing out and toggle `payments.async_ledger_write_protection` if the
   incident commander approves it.

### `PaymentsAuthorizationFailures`

Meaning:
The percentage of 5xx responses exceeds 2 percent for 5 minutes.

Immediate actions:

1. Sample logs for `dependency_timeout`, `idempotency_store_error`, and
   `ledger_write_failed`.
2. Check whether recent configuration changes were applied.
3. Confirm whether the storefront is sending retry storms without idempotency
   keys.

### `PaymentsLedgerGap`

Meaning:
Approved authorizations are not reaching the ledger within 2 seconds.

Immediate actions:

1. Inspect `ledger-writer` queue depth and consumer lag.
2. Validate that event publishing credentials are still valid.
3. If backlog is growing, stop any nonessential replays before customer-facing
   traffic is affected.

## Standard Incident Workflow

1. Acknowledge the page and open an incident channel if customer impact is
   confirmed.
2. State the current customer symptom, known blast radius, and the suspected
   failing dependency.
3. Assign roles. Platform Reliability owns incident command for Sev 1 and Sev 2
   events involving the Payments API. Checkout Experience supports storefront
   reproduction and customer-facing timing estimates.
4. Stabilize first. Prefer known feature flags and dependency isolations before
   deeper code or schema changes.
5. Capture exact timestamps for the first symptom, mitigation, and recovery so
   they can be reused in the postmortem.

## Safe Mitigations

The following actions are pre-approved if incident command judges the customer
impact high enough:

- enable `payments.defer_analytics_emission` to reduce noncritical async work
- reduce authorization request concurrency by 20 percent using the API gateway
  policy
- disable low-value secondary fraud checks with `risk.shadow_rules_only`
- pause bulk replay jobs that compete for database or Redis capacity

The following actions require explicit approval from the service owner or
incident commander:

- disabling hard fraud controls
- bypassing ledger writes
- changing settlement or capture sequencing
- modifying PostgreSQL connection pool limits in production

## Ownership and Escalation

Primary operational owner: Platform Reliability.

Escalate to Checkout Experience when:

- storefront retries are amplifying the incident
- cart and checkout experiences need temporary feature degradation
- customer messaging needs estimated recovery windows

Escalate to Data Platform when:

- ledger or analytics backlogs exceed 30 minutes
- export jobs are starved because of shared database load

Escalate to Security Operations when:

- the incident may involve credential misuse
- unusual admin sessions or vendor access overlap with the failure window

## Recovery Verification Checklist

Do not close the incident until all of the following are true:

- error rate is below 0.5 percent for 15 consecutive minutes
- p95 latency is below 900 ms
- ledger lag is back under 2 seconds
- no stuck idempotency reservations remain older than 10 minutes
- dashboard annotations and incident notes reflect the final mitigation state

## Frequently Used Queries

- "Who owns the payments service?" Answer: Platform Reliability.
- "Who backs up the primary team?" Answer: Checkout Experience.
- "What are the hard dependencies?" Answer: `ledger-writer`,
  `risk-evaluator`, PostgreSQL, Redis, and the feature flag service.
- "What is the recovery target?" Answer: RTO 30 minutes, RPO 5 minutes.

## Handoff Notes

When handing off between regions or shifts, include:

- current customer impact statement
- current mitigation flags and whether they should remain enabled
- active hypotheses that were ruled out
- dashboards or log views worth keeping open
- follow-up owners for any debt introduced during mitigation

The minimum acceptable handoff is a concise incident summary, the current
service health state, and whether Platform Reliability still retains incident
command. If the incident is still live, never assume the next engineer knows the
blast radius from the page alone.
