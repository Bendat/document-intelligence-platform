# Postmortem: Checkout Latency Incident on 2026-02-18

## Summary

On 2026-02-18, Northstar Commerce experienced elevated checkout latency and
intermittent payment failures between 14:07 UTC and 14:49 UTC. The customer
impact was concentrated in card authorization flows. At peak, checkout p95
latency rose above 6 seconds and approximately 7.4 percent of authorization
requests returned a 5xx response.

The main contributor was Redis connection pool exhaustion in the `risk-evaluator`
service after a timeout configuration change caused worker threads to hold
connections longer than expected. The Payments API depended on `risk-evaluator`
for synchronous risk decisions, so latency cascaded directly into checkout.

## Customer Impact

- increased checkout latency for card payments
- elevated payment retries from the storefront
- visible customer-facing failures in the EU primary region
- delayed order confirmation for a subset of successful payments

No payment data was lost. Ledger writes caught up after service recovery and
there was no evidence of duplicate customer charges.

## Timeline

- 13:56 UTC: a configuration change reduced the Redis socket timeout margin in
  `risk-evaluator`
- 14:07 UTC: alert `PaymentsHighLatency` fired
- 14:10 UTC: Platform Reliability acknowledged the page and opened the incident
  channel
- 14:14 UTC: dashboard review showed `risk-evaluator` latency and Redis
  connection usage spiking together
- 14:19 UTC: Checkout Experience confirmed broad customer symptoms in the EU
  region
- 14:24 UTC: incident commander approved a temporary reduction in fraud shadow
  checks
- 14:31 UTC: config rollback for `risk-evaluator` began
- 14:37 UTC: Redis pool utilization dropped below the saturation threshold
- 14:43 UTC: checkout latency returned below 1 second p95
- 14:49 UTC: incident moved to monitoring

## Detection

The first alert came from the Payments API because its p95 latency breached the
 customer-facing threshold before the `risk-evaluator` service exhausted all
 available connections. A dependency-specific alert for Redis saturation existed,
but it was configured only on absolute failure rate and not on prolonged pool
occupancy. That delayed root-cause clarity by several minutes.

## Root Cause

The root cause was a mis-tuned Redis timeout configuration in `risk-evaluator`.
When backend calls slowed under normal lunchtime traffic, worker threads held
onto Redis connections for too long and the connection pool reached saturation.
Once the pool was exhausted, request handling serialized around scarce
connections, driving latency sharply upward.

This issue propagated because the Payments API waited for synchronous fraud and
risk decisions before finalizing authorization. As `risk-evaluator` slowed,
authorization latency increased and storefront retries amplified load further.

## Contributing Factors

- the timeout change was considered low risk and did not require paired review
- no alert existed for sustained Redis pool occupancy above 85 percent
- the storefront retry policy accelerated after two seconds, which increased
  pressure during the event
- the fraud shadow rules still consumed additional Redis work even after latency
  was visible

## What Went Well

- Platform Reliability assembled the right responders quickly
- rollback was well understood and executed in under 10 minutes after root cause
  identification
- the payment ledger preserved ordering and catch-up once latency recovered
- customer support received clear guidance from Checkout Experience

## What Went Poorly

- initial suspicion focused on PostgreSQL because the first dashboard view
  emphasized payment-side latency rather than dependency saturation
- the `risk-evaluator` alerting model was too coarse to highlight pool
  exhaustion early
- retry amplification from the storefront was recognized later than it should
  have been

## Corrective Actions

### Completed

- rolled back the `risk-evaluator` timeout change
- documented the approved fraud-degradation flag sequence in the payments
  runbook
- added a dashboard panel for Redis connection pool occupancy and wait time

### In Progress

- add alerting for sustained pool occupancy above 85 percent for 5 minutes
- cap storefront retries during active payment incidents
- require paired review for Redis and connection-pool tuning changes
- add backpressure in `risk-evaluator` before worker starvation becomes visible

### Follow-up Owners

- Platform Reliability: incident review and runbook updates
- Risk Platform: connection pool instrumentation and safer defaults
- Checkout Experience: retry policy adjustments and customer messaging templates

## Lessons

The incident reinforced that dependency saturation often surfaces first in the
customer-facing service, not the failing dependency itself. Operationally, that
means responders need a dashboard path that immediately pivots from payment
latency to risk and cache health. It also confirmed that retry behavior must be
treated as part of the failure mode, not as neutral background behavior.

## FAQ

### What was the main contributor to the incident?

Redis connection pool exhaustion in `risk-evaluator`.

### Was the Payments API itself broken?

Not primarily. It was healthy enough to process requests, but its dependency on
synchronous risk decisions made it sensitive to downstream latency.

### Did we lose payment records?

No. Ledger write lag increased temporarily but caught up after the rollback.
