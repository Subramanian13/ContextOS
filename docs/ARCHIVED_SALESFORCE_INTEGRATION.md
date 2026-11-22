# Archived Salesforce Developer Edition Integration

Status: removed from the active ContextOS application on 2026-11-19.

This document describes a previous prototype integration for historical reference. ContextOS no longer registers Salesforce routes, loads Salesforce settings, reads stored OAuth tokens, performs Salesforce requests, or presents CRM Account/Contact information in the frontend.

## What was implemented

The prototype connected one locked Salesforce Developer Edition organization and provided a read-only Account context panel for the synthetic Acme CRM project. It supported:

- OAuth 2.0 Authorization Code Flow with S256 PKCE.
- One-time state validation bound to an HttpOnly, SameSite cookie.
- Encrypted server-side access and refresh-token storage.
- Refresh after an API `401`, with one retry.
- Organization and Account/Contact permission validation.
- Fixed read-only SOQL queries for Organization, Account, and Contact.
- A persistent mapping from a ContextOS project ID to an organization-specific Account ID.
- Sanitized cached Account and Contact snapshots and on-demand refresh.
- Connect, validate, disconnect, Account, Contact, mapping, and CRM-context endpoints.

No client secret, access token, refresh token, encryption key, authorization code, or real credential value is included in this document.

## Former architecture

The backend generated high-entropy OAuth state and PKCE verifier values. It stored the state hash and encrypted verifier with a short expiry, consumed state only once, and exchanged the authorization code server-side. Tokens were encrypted before PostgreSQL persistence. Instance URLs were restricted to Salesforce HTTPS domains. The browser received only sanitized connection and CRM projections.

The Account mapping stored the Salesforce organization ID alongside the Account ID. Activation required a successful authenticated Account lookup, and refresh rechecked organization ownership before replacing the last successful snapshot. This connector never resolved the Acme customer credential blocker.

## Why it was removed

The connector contributed a read-only CRM information panel but did not materially participate in ContextOS's core workflow:

`Detect → Retrieve → Reason → Simulate → Approve → Execute → Verify`

Keeping it active added OAuth configuration, token lifecycle, deployment secrets, external availability, UI surface area, and a runtime cryptography dependency without improving deterministic recovery planning. The product now focuses on scheduler-owned forecasts, historical retrieval, AI-supported recovery reasoning, human approval, controlled execution, and audit history.

## Data retention

Migrations `0006_salesforce_integration` through `0009_seed_project_mapping` and their tables remain in the schema. No cleanup migration was run and no OAuth connection, encrypted token, Account mapping, or cached CRM record was deleted. Current application startup does not query these tables.

An optional future cleanup migration could drop the following only after an explicit backup and deletion decision:

- `salesforce_oauth_states`
- `salesforce_connections`
- `salesforce_project_mappings`

That cleanup is intentionally outside the archival change.

## Possible restoration

Restoration should be treated as a new reviewed feature, not a route re-enable. Recover the prior implementation from version control, then:

1. Reassess whether live CRM data materially supports recovery decisions.
2. Add real user authentication, authorization, and tenant isolation.
3. Use managed secret and encryption-key storage with rotation.
4. Review retained schemas and migrate them forward without exposing old tokens.
5. Restore OAuth and read endpoints behind explicit access controls.
6. Restore frontend context only when it supports a defined product workflow.
7. Add mocked regression tests and a separately authorized live smoke test.
8. Redact callback query parameters from gateway and application access logs.

The fictional Salesforce-related tasks and OAuth credential blocker in the Acme delivery scenario are not this external connector. They remain synthetic project-domain data and continue to exercise ContextOS recovery planning.
