# Phase 7.6 — API, Security & Internal Communication

## 1. Purpose

This document defines Raven's API architecture, security model, and internal communication standards.

It establishes:

- External API boundaries.
- FastAPI application architecture.
- Authentication and authorization.
- Engine access boundaries.
- Internal service communication.
- Request and response contracts.
- API versioning.
- Rate limiting and abuse prevention.
- Data protection and security controls.
- Error handling and audit requirements.

The objective is to provide a secure and maintainable interface between users, the Orchestrator, engines, and shared infrastructure.

---

## 2. Architectural Principles

Raven follows these principles:

1. All external requests must pass through authenticated and authorized interfaces.
2. The API layer must not own engine business logic.
3. The Orchestrator coordinates workflows.
4. Memory and Research own their respective business capabilities.
5. Every operation must respect user ownership and access boundaries.
6. Internal communication must be authenticated and validated.
7. API contracts must be versioned and documented.
8. Sensitive information must be protected in transit and at rest.
9. Errors must not expose secrets or internal implementation details.
10. Security checks must not depend on frontend behavior.
11. Privileged operations must have explicit authorization.
12. Security, correctness, and data integrity take priority over convenience.

---

## 3. API Technology Stack

The initial API stack is:

| Responsibility | Technology |
|---|---|
| API framework | FastAPI |
| Language | Python |
| Request validation | Pydantic |
| API specification | OpenAPI |
| Authentication standard | OAuth 2.0 / OpenID Connect |
| Database access | SQLAlchemy |
| Database migrations | Alembic |
| API testing | HTTPX and pytest |
| Observability | OpenTelemetry |

The identity provider is not finalized. Raven should use an OIDC-compatible provider rather than coupling authentication to a specific vendor.

---

## 4. API Architecture

Raven uses an API entry layer that communicates with the Agent Orchestrator.

```text
                  Client
                    |
                    v
              API Gateway/
              FastAPI Layer
                    |
          +---------+---------+
          |                   |
          v                   v
     Authentication     Request Validation
          |                   |
          +---------+---------+
                    |
                    v
             Agent Orchestrator
                    |
          +---------+---------+
          |                   |
          v                   v
     Memory Engine       Research Engine
          |                   |
          +---------+---------+
                    |
                    v
             Shared Infrastructure
```

This is a logical architecture. It does not require a separately deployed API gateway in the initial implementation.

### 4.1 API layer responsibilities

The API layer owns:

- Receiving HTTP requests.
- Authentication token validation.
- Request schema validation.
- Basic input constraints.
- Rate limiting.
- Request correlation.
- Passing authorized user context.
- Calling the Orchestrator.
- Returning structured responses.
- Exposing API documentation.

### 4.2 API layer exclusions

The API layer must not:

- Implement memory extraction.
- Implement research discovery.
- Perform cross-engine workflow planning.
- Directly update engine-owned business records.
- Decide whether a memory is valid.
- Verify external research claims.
- Bypass Orchestrator execution management.

Business operations belong to their respective owners.

---

## 5. API Endpoint Organization

Raven should use versioned REST endpoints.

The initial public API namespace is:

`/api/v1/`

Potential endpoint groups:

| Endpoint group | Responsibility |
|---|---|
| `/api/v1/auth` | Authentication-related integration endpoints, if needed |
| `/api/v1/requests` | Submit user requests |
| `/api/v1/executions` | Retrieve execution status |
| `/api/v1/memory` | Memory-related user operations through authorized engine interfaces |
| `/api/v1/research` | Research-related user operations through authorized engine interfaces |
| `/api/v1/health` | Service health |
| `/api/v1/ready` | Service readiness |

These are logical endpoint groups. Exact routes and request methods will be finalized during implementation.

### 5.1 Request submission

A request submission endpoint should:

1. Receive the request.
2. Authenticate the user.
3. Validate the request.
4. Create or initiate an Orchestrator execution.
5. Return a structured execution reference or completed result, depending on execution mode.

### 5.2 Execution status

Execution status endpoints should return only information the authenticated user is authorized to access.

Possible information:

- Execution ID.
- Execution status.
- Task progress.
- Creation timestamp.
- Last update timestamp.
- Completion timestamp, where applicable.
- Safe error information.
- Partial completion information.

Internal worker details and sensitive processing data must not be exposed.

### 5.3 Memory and Research endpoints

These endpoints provide controlled user-facing access to engine capabilities.

The API layer must route operations through the appropriate ownership boundary.

The existence of an endpoint does not grant the API layer direct ownership of the underlying data.

---

## 6. Authentication Architecture

Authentication establishes who is making a request.

Raven should use an OIDC-compatible identity provider.

### 6.1 Authentication flow

1. User authenticates through the configured identity provider.
2. The identity provider issues an appropriate token.
3. The client sends the token with API requests.
4. FastAPI validates the token.
5. Raven establishes the authenticated principal.
6. The API layer passes the trusted identity context to the Orchestrator.

### 6.2 Token validation

Validate:

- Token signature.
- Issuer.
- Audience.
- Expiration.
- Not-before time, where applicable.
- Required claims.
- Signing key validity.

Token validation must use trusted provider configuration.

### 6.3 Identity boundaries

Authentication identity and Raven's internal user identity must be distinguishable.

The internal identity mapping must be stable and must not rely on an untrusted user-supplied identifier.

A user must not be able to access another user's data by changing a request parameter.

### 6.4 Token handling

- Do not log access tokens.
- Do not expose refresh tokens in ordinary application responses.
- Protect token storage on the client.
- Use secure transport.
- Validate tokens on protected operations.
- Apply appropriate token expiration and revocation policies.

---

## 7. Authorization Architecture

Authorization determines what an authenticated user is allowed to do.

Authentication alone is insufficient.

### 7.1 Authorization model

Use a hybrid authorization model:

- Role-based access control for broad permissions.
- Resource-level checks for individual records.
- Ownership-based checks for private user data.
- Explicit policy checks for sensitive operations.

### 7.2 User-scoped data

Private memory and research data must be scoped to the authenticated user.

Every data-access operation must verify:

- Authenticated principal.
- Internal user identity.
- Resource ownership.
- Requested operation.
- Applicable authorization policy.

### 7.3 Engine authorization

The Memory Engine and Research Engine remain responsible for validating access to their authoritative records.

The Orchestrator may pass authorized context, but the receiving engine must enforce its own data access rules.

### 7.4 Privileged operations

Operations such as:

- Bulk deletion.
- Account-level data export.
- Sensitive configuration changes.
- Administrative access.
- Security policy changes.

Require appropriate privileges and additional validation where warranted.

### 7.5 Authorization failures

Unauthorized operations must be rejected without revealing whether inaccessible private records exist.

---

## 8. Internal Communication Architecture

Raven uses hybrid internal communication:

- Direct request-response communication for short operations.
- Asynchronous messaging for long-running operations and events.

### 8.1 Communication patterns

| Pattern | Use |
|---|---|
| Synchronous request-response | Short internal operations |
| Asynchronous command | Background work |
| Event notification | State changes and completed work |
| Query interface | Controlled read operations |
| Execution reference | Tracking long-running operations |

### 8.2 Communication ownership

- The Orchestrator coordinates cross-engine workflows.
- Memory owns Memory Engine operations.
- Research owns Research Engine operations.
- Shared Infrastructure owns infrastructure-level capabilities.

The Orchestrator should not bypass an engine's interface to manipulate its internal database records.

### 8.3 Internal contracts

Internal messages must include appropriate:

- Message identifiers.
- Execution identifiers.
- Task identifiers.
- Source and destination.
- User scope, where applicable.
- Operation type.
- Correlation and causation identifiers.
- Schema version.
- Payload references.
- Authorization context.

Use the standard message envelope defined in Phase 7.4.

---

## 9. API and Internal Data Contracts

Use Pydantic models for API request and response validation.

### 9.1 Contract requirements

Every contract should define:

- Field names.
- Data types.
- Required and optional fields.
- Validation constraints.
- Default behavior.
- Allowed values.
- Error behavior.
- Schema version where required.

### 9.2 Request validation

Validate:

- Input type.
- Field lengths.
- Required values.
- Enum values.
- Timestamp formats.
- Identifier formats.
- Payload size.
- Nested object structure.

Reject invalid input before business processing begins.

### 9.3 Response validation

Responses must:

- Follow the declared response schema.
- Avoid exposing internal implementation details.
- Preserve execution and task references where relevant.
- Distinguish successful, partial, failed, and pending outcomes.
- Preserve uncertainty and evidence information when applicable.

### 9.4 Contract evolution

Changes to contracts must be reviewed for backward compatibility.

Avoid silently changing the meaning of existing fields.

---

## 10. API Versioning

Raven will initially use URL-based major versioning.

Example:

`/api/v1/`

### 10.1 Versioning rules

- Breaking changes require a new major API version.
- Backward-compatible optional additions may remain within the current version.
- Deprecated fields must be documented.
- Deprecation must include a migration path.
- Old versions should remain supported for a defined transition period where practical.

### 10.2 Internal schema versioning

Internal messages and persisted records may have independent schema versions.

API versioning must not be confused with database schema versioning or message-envelope versioning.

Each versioning mechanism has a distinct purpose.

---

## 11. Rate Limiting and Abuse Prevention

Raven must protect its APIs and processing resources against excessive or abusive requests.

### 11.1 Rate limiting dimensions

Rate limits may apply by:

- User.
- API key or client identity, where applicable.
- IP address.
- Endpoint category.
- Resource-intensive operation.
- Concurrent execution count.

### 11.2 Resource controls

Apply controls to:

- Request body size.
- Document upload size.
- Concurrent research operations.
- Background task submission.
- Expensive processing operations.
- External research requests.

### 11.3 Abuse prevention

- Reject malformed requests.
- Apply request timeouts.
- Limit excessive retries.
- Validate file types and content.
- Prevent unauthorized bulk operations.
- Monitor abnormal traffic patterns.
- Protect expensive endpoints with stricter limits.

### 11.4 User experience

When a request is rate-limited, return a structured error.

Where appropriate, include retry guidance without exposing internal resource information.

---

## 12. File and Document API Security

Raven may receive documents such as PDF, DOCX, and TXT for processing.

Document handling must be treated as a security-sensitive workflow.

Requirements:

- Validate actual file format, not only filename extension.
- Apply file-size limits.
- Restrict supported formats.
- Store uploaded files in controlled object storage.
- Use opaque storage identifiers.
- Scan files where suitable security tooling is available.
- Prevent path traversal.
- Prevent unauthorized file retrieval.
- Avoid executing document contents.
- Treat extracted text as untrusted input.
- Apply retention and deletion rules.
- Keep temporary processing artifacts isolated.

Scanned-document OCR is a separate capability and must not be assumed to exist merely because PDF uploads are supported.

---

## 13. API Error Handling

All API errors must follow a consistent response structure.

Conceptual example:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request could not be validated.",
    "request_id": "request-reference",
    "details": []
  }
}
```

This is an illustrative contract, not a finalized response schema.

### 13.1 Error categories

Potential categories:

- `INVALID_REQUEST`
- `UNAUTHENTICATED`
- `FORBIDDEN`
- `RESOURCE_NOT_FOUND`
- `RATE_LIMITED`
- `CONFLICT`
- `REQUEST_TIMEOUT`
- `SERVICE_UNAVAILABLE`
- `INTERNAL_ERROR`

### 13.2 Error handling rules

- Do not expose stack traces to clients.
- Do not expose database credentials or internal secrets.
- Avoid revealing private resource existence.
- Preserve a request or correlation identifier.
- Log technical details securely.
- Distinguish validation errors from processing failures.
- Distinguish accepted asynchronous work from completed work.

---

## 14. Security Controls

### 14.1 Transport security

- Use HTTPS for external API traffic.
- Use secure transport for internal communication where appropriate.
- Validate certificates.
- Protect broker and database connections.

### 14.2 Secrets management

- Keep secrets outside source code.
- Use environment-specific secret configuration.
- Restrict secret access.
- Rotate credentials.
- Never log credentials or tokens.

### 14.3 Input security

- Validate all external inputs.
- Treat uploaded documents as untrusted.
- Apply safe parsing.
- Prevent injection vulnerabilities.
- Validate payload references.
- Enforce request size limits.

### 14.4 Database security

- Use least-privilege database roles.
- Separate engine permissions.
- Restrict administrative access.
- Use parameterized database operations.
- Enforce ownership at the data-access layer.

### 14.5 External content security

Research content must be treated as untrusted.

The Research Engine must not execute scripts, commands, or instructions extracted from external sources.

External content must not override Raven's internal policies or authorization controls.

---

## 15. Audit and Security Logging

Security-relevant events must be recorded.

Potential events:

- Authentication success and failure.
- Authorization denial.
- Privileged operation.
- Account or permission change.
- Sensitive data export.
- Deletion request.
- Configuration change.
- Suspicious access attempt.
- Internal service authentication failure.

### 15.1 Logging requirements

- Use structured logs.
- Include correlation identifiers.
- Record event timestamps.
- Identify the responsible component.
- Avoid logging secrets.
- Avoid unnecessary personal content.
- Restrict access to security logs.
- Apply retention policies.

Engine-specific business audit events remain owned by their respective engines.

Infrastructure authentication and security events remain owned by Shared Infrastructure.

---

## 16. Testing Requirements

The API and security architecture must eventually be tested for:

### Authentication

- Valid token.
- Expired token.
- Invalid signature.
- Wrong audience.
- Unknown issuer.
- Missing token.

### Authorization

- User accessing own records.
- User attempting to access another user's records.
- Unauthorized deletion.
- Privileged operation without permission.
- Engine-level ownership validation.

### API contracts

- Invalid payload.
- Missing fields.
- Incorrect types.
- Oversized requests.
- Unknown enum values.
- Backward compatibility.

### Internal communication

- Invalid message envelope.
- Unauthorized publisher.
- Unauthorized consumer.
- Duplicate messages.
- Incorrect user scope.
- Unsupported schema version.

### Security

- Injection attempts.
- File upload abuse.
- Path traversal.
- Secret exposure.
- Sensitive logging.
- Rate-limit bypass.
- Unauthorized replay.

### Reliability

- API timeout.
- Engine unavailability.
- Broker unavailability.
- Database unavailability.
- Partial asynchronous execution.
- Request cancellation.

---

## 17. Finalized Decisions

The following architectural decisions are established:

1. FastAPI is the initial API framework.
2. Pydantic is the request and response validation baseline.
3. OpenAPI provides API contract documentation.
4. External API routes use `/api/v1/` initially.
5. Authentication uses an OIDC-compatible identity provider.
6. Authentication and authorization are separate responsibilities.
7. Authorization combines role, resource, and ownership checks.
8. The API layer does not own engine business logic.
9. The Orchestrator coordinates cross-engine workflows.
10. Memory and Research enforce their own data ownership boundaries.
11. Internal communication uses synchronous and asynchronous patterns.
12. Internal contracts must be structured and versioned.
13. Rate limiting and resource controls protect expensive operations.
14. File processing must enforce strict validation and access controls.
15. Security events must be auditable.
16. External content is untrusted input.
17. Secrets must not be stored in source code or exposed in logs.
18. Security and data integrity take priority over convenience.

---

## 18. Deferred Decisions

The following decisions require implementation or operational evaluation:

- Identity provider selection.
- Exact authentication flow for each client type.
- Token lifetime and refresh policy.
- Role definitions and permission catalogue.
- Exact API endpoint paths and methods.
- Internal synchronous transport choice.
- Internal service authentication mechanism.
- Rate-limit values.
- File-size limits.
- Upload scanning implementation.
- Security monitoring integration.
- API deprecation policy.
- Production network architecture.
- Secret-management provider.

These decisions must remain consistent with the security and ownership boundaries established here.

---

## 19. Completion Criteria

Phase 7.6 is architecturally specified when:

- External API responsibilities are documented.
- Authentication and authorization are separated.
- Engine ownership boundaries are enforced.
- Internal communication contracts are defined.
- API validation and versioning are documented.
- Rate limiting and abuse prevention are specified.
- File processing security is addressed.
- Error handling and audit requirements are established.
- Security testing requirements are documented.

**Status:** Architecture specification complete.

**Important:** This document does not claim that FastAPI routes, identity-provider integration, authorization policies, security middleware, or security tests have been implemented or deployed.

---

## 20. Next Phase

**Phase 7.7 — Observability & Testing Infrastructure**

This will define logging, metrics, distributed tracing, monitoring, alerting, testing layers, quality gates, and reliability evaluation across Raven.
