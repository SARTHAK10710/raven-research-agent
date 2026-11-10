# Rule: Security and Privacy

Non-negotiable. Sources: [7.6 API security](../../docs/technical-decisions/06-api-security-and-internal-communication.md), [7.2 storage §12–13, §17](../../docs/technical-decisions/02-database-and-storage-architecture.md), [7.5 amendment §17](../../docs/technical-decisions/05-NLP-and-machine-learning-stack.md), [7.7 §18](../../docs/technical-decisions/07-observability-and-testing-infrastructure.md), [7.8 §6–7](../../docs/technical-decisions/08-deployment-and-environment-architecture.md). If a task seems to require breaking one of these rules, stop and report it.

## User ownership and isolation

- Every private record has a user owner. Check ownership and authorization on every private data operation: reads, writes, retrieval, deletion and background jobs.
- **No cross-user retrieval or access**, including through vector search, keyword search, caches, logs, metrics, traces or derived artifacts. Enforce isolation before or during retrieval, not merely after results are returned (Decision 5.8.6). Retrieval also respects visibility, permissions, and deletion and retention state.
- Private data and explicitly shared data are separate classifications; nothing becomes shared implicitly. A record without a user identifier is never automatically public.
- Do not reveal whether another user's private resource exists.

## Authentication and authorization

- Authentication uses an OIDC-compatible identity provider (provider pending). Raven does not build its own authentication.
- Authentication and authorization are separate. Authorization combines role, resource and ownership checks.
- Engines enforce their own data-ownership boundaries; the API layer and Orchestrator do not bypass them.
- Least privilege: use separate database roles per component where practical, and keep a dedicated migration role.

## Data privacy

- Do not train models automatically on user data (Phase 8 Readme §5.5; 7.5 Decision 15).
- Do not tune models on user data automatically either. *(Raven engineering convention, not a source-document requirement; it extends the source rule above.)*
- Encrypt data in transit and sensitive stored content at rest.
- Keep operational metadata separate from business content. Observability must never become a route to private data.
- Prefer synthetic data in tests and development. Never use production data there.

## Untrusted input and document processing

- Treat uploaded files, extracted text and all external content as untrusted.
- Validate the actual file format, not only the extension or user-supplied MIME type. Restrict formats to PDF, DOCX and TXT. Enforce file-size and resource limits.
- **Never execute embedded scripts, macros or active content** during document processing.
- Run parsers safely, handle malformed files securely, and isolate and clean up temporary artifacts.
- Store uploads in controlled object storage with opaque identifiers. Prevent path traversal. Never expose raw storage locations.
- OCR is not supported. Scanned documents are not assumed to be processable.

## Secret management

- No secrets in source code, Git history, Docker images, logs or committed config. `.env` stays git-ignored, never holds production secrets, and has a placeholder-only `.env.example`.
- Use separate credentials per environment and per component where practical. Do not share one privileged credential across components.
- Never enter real credentials on the user's behalf. Never echo secret values in chat or reports. *(Raven engineering convention, not a source-document requirement.)*

## Secure logging

- Never log passwords, tokens, API keys, database credentials, full request bodies, raw personal-memory content or document text.
- Redact sensitive values; keep sensitive text out of metric labels; restrict access to traces and dashboards.
- Exception messages from lower layers may contain user data. Log the error code and type by default, not raw messages. *(Raven engineering convention, not a source-document requirement.)*

## Deletion propagation

- Explicit forgetting and deletion must reach every applicable derived artifact: embeddings, indexes, caches, profiles, extracted representations, chunks and stored objects.
- Affected information must not be returned while deletion propagation is pending.
- Deletion is idempotent, tracked and verified. Partial deletion is visible and recoverable, never reported as complete.
- Deleting a document accounts for its versions, chunks, embeddings and any provenance links into personal memory.

## Backup and recovery

- Backups are protected and access-controlled.
- Deletion state must survive restoration. Use tombstones or deletion records, and reapply deletions before restored data becomes accessible, so forgotten data cannot reappear.
- Recovery reconciles derived data against authoritative records.
