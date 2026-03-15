# Vendor Production Access Policy

## Policy Summary

This policy governs how third-party vendors and contractors obtain temporary
access to production systems used by Northstar Commerce. The objective is to
allow tightly controlled operational support without normalizing standing access
to sensitive systems.

Production access for vendors is exceptional, time-bound, approved per task,
and recorded end to end. Requests that do not follow this policy must be denied.

## Scope

This policy applies to:

- managed service providers operating observability or incident-response tools
- contractors performing approved maintenance
- external specialists supporting migrations or severe incidents
- vendors troubleshooting licensed systems that directly impact production

This policy does not apply to:

- internal employees covered by the employee privileged-access standard
- sandbox, staging, or demo environments without production data
- customer support tooling that does not expose privileged administration paths

## Required Controls

Every vendor production-access session must include all of the following:

1. Just-in-time approval tied to a ticket or incident record.
2. Multi-factor authentication.
3. Session recording through the approved bastion or privileged session manager.
4. Named user identity. Shared vendor accounts are prohibited.
5. Explicit start and end times. The default maximum session duration is 8
   hours.
6. A clearly named sponsor from the owning internal team.

If any of the required controls cannot be satisfied, the access request must be
deferred until an approved control path is available.

## Approval Model

Approval requires two people:

- an approver from Security Operations
- the internal service owner or incident commander for the affected system

For routine maintenance, the service owner must approve during a planned change
window before Security Operations grants the session. For high-severity
incidents, Security Operations may provision the session first, but the incident
commander must confirm the vendor scope in the incident channel within 15
minutes.

No single individual may request, approve, and execute the same vendor access
session.

## Access Provisioning Steps

1. Open or reference the change ticket, incident, or maintenance task.
2. Record the vendor name, named engineer, affected systems, and expected
   duration.
3. Confirm the vendor uses the approved identity provider and MFA.
4. Provision access only through the privileged access broker.
5. Scope permissions to the minimum required systems and commands.
6. Announce session start in the operating channel for the affected system.
7. Monitor the session until the work is complete or the session expires.

## Prohibited Patterns

The following are not allowed:

- standing production credentials for vendors
- SSH keys placed directly on production hosts
- direct database superuser access without Security Operations approval
- access from unmanaged personal devices
- reusing a previous ticket for unrelated work
- extending access by editing the expiration timestamp without a new approval

## Logging and Review

Security Operations owns the monthly review of vendor production sessions.

The review must verify:

- the stated ticket or incident matched the work performed
- the session duration stayed within the approved window
- the vendor used the named account approved for the work
- the service owner confirmed work completion
- any unusual commands were reviewed and documented

Retain session recordings and broker audit logs for at least 12 months.

## Emergency Access

Emergency vendor access is allowed only for Sev 1 or significant Sev 2
incidents where internal teams cannot restore service without vendor support in
the required recovery window.

Even in emergencies, the following remain mandatory:

- MFA
- named user identity
- session recording
- an incident reference

The only control that may be shortened is the ordering of approvals, not the
approvals themselves.

## Examples

Approved example:
A database vendor joins a live incident to help analyze replication lag through
the bastion host. Security Operations provisions a 2-hour recorded session after
the incident commander confirms the scope.

Rejected example:
A contractor asks for a shared admin password because the privileged broker is
slow and the change window is about to start.

Rejected example:
A vendor that assisted last week requests the same access again "just in case"
for follow-up observation.

## Frequently Asked Questions

### Who owns this policy?

Security Operations is the policy owner. Internal service owners remain
responsible for approving access to their systems.

### How long can a vendor stay connected?

The default maximum session duration is 8 hours. Longer windows require explicit
approval from Security Operations leadership and the relevant service owner.

### Is VPN access alone sufficient?

No. VPN access is not a substitute for just-in-time approval, MFA, session
recording, or named-user identity.

### Can a vendor access production during a maintenance window without an
incident?

Yes, if the change is planned, approved, time-bound, and provisioned through the
privileged access broker with all mandatory controls in place.
