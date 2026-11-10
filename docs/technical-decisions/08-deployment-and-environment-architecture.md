# Phase 7.8 — Deployment & Environment Architecture

## 1. Purpose

This document defines Raven's deployment and environment architecture.

It establishes:

- Environment separation.
- Application deployment structure.
- Docker-based containerization.
- Configuration management.
- Secrets management.
- Database and infrastructure deployment.
- Release and upgrade strategy.
- Migration safety.
- Backup and disaster recovery.
- Deployment monitoring.
- Production security and reliability.

The objective is to establish a deployment architecture that supports reliable development, testing, and production operation without compromising data integrity, privacy, or security.

---

## 2. Architectural Principles

Raven follows these principles:

1. Development, testing, staging, and production environments must be isolated.
2. Configuration must be environment-specific.
3. Secrets must never be committed to source control.
4. Application services should be containerized.
5. Database migrations must be controlled and reversible where possible.
6. Deployments must not silently corrupt existing data.
7. Production deployments must be observable.
8. Backups must be tested through restoration.
9. Background workers must support controlled startup and shutdown.
10. Deployment failures must have a defined recovery strategy.
11. Infrastructure complexity should grow with actual workload requirements.
12. Security, correctness, and recoverability take priority over deployment convenience.

---

## 3. Deployment Architecture

Raven will initially follow a modular monolith architecture with independently executable background workers.

The application may be deployed as multiple containers while retaining a shared codebase and clear internal module boundaries.

### 3.1 Logical deployment structure

```text
                    Client
                      |
                      v
                 FastAPI API
                      |
                      v
               Agent Orchestrator
                      |
             +--------+--------+
             |                 |
             v                 v
        Memory Engine     Research Engine
             |                 |
             +--------+--------+
                      |
                      v
               PostgreSQL
                      |
          +-----------+-----------+
          |                       |
          v                       v
      RabbitMQ              Object Storage
          |
          v
     Celery Workers
          |
          +------> Memory Jobs
          |
          +------> Research Jobs
          |
          +------> Embedding Jobs
          |
          +------> Maintenance Jobs

          Observability:
          OpenTelemetry + Prometheus + Grafana
```

This is a logical deployment view. It does not require every logical component to be a separately deployed service.

### 3.2 Initial deployment units

The initial deployment should support these logical units:

| Deployment unit | Responsibility |
|---|---|
| API application | FastAPI request handling |
| Background workers | Celery task execution |
| Scheduler | Scheduled background operations |
| PostgreSQL | Primary relational database |
| RabbitMQ | Message broker |
| Object storage | Original documents and large content |
| Monitoring | Metrics, dashboards, and tracing |

Some components may be combined during local development.

Production separation should be based on workload, resource isolation, and operational needs.

---

## 4. Environment Architecture

Raven should maintain four logical environments.

### 4.1 Development

Purpose:

- Feature development.
- Local debugging.
- Rapid experimentation.
- Unit testing.
- Local integration testing.

Characteristics:

- Local Docker Compose setup.
- Synthetic or explicitly approved development data.
- Debug logging where appropriate.
- Development-only credentials.
- No production secrets.
- No production database access by default.

### 4.2 Testing

Purpose:

- Automated testing.
- Integration testing.
- Regression testing.
- Reliability testing.
- Security testing.

Characteristics:

- Isolated test database.
- Test RabbitMQ instance.
- Controlled test storage.
- Deterministic fixtures.
- Repeatable test setup.
- Automatic cleanup where safe.

Testing must not modify production data.

### 4.3 Staging

Purpose:

- Validate release candidates.
- Test deployment procedures.
- Verify migrations.
- Evaluate performance.
- Validate integration between components.

Characteristics:

- Production-like configuration.
- Isolated staging data.
- Similar service topology to production.
- Controlled access.
- Release candidate deployment.
- Deployment and recovery rehearsal.

Staging should not automatically receive real user data.

### 4.4 Production

Purpose:

- Serve actual users.
- Execute authorized workflows.
- Persist authoritative data.
- Run background processing.

Characteristics:

- Restricted access.
- Production secrets.
- Secure network configuration.
- Monitoring and alerting.
- Backup and recovery.
- Controlled releases.
- Auditable privileged operations.

### 4.5 Environment isolation

Each environment must have separate:

- Database instances or isolated database deployments.
- Broker configuration.
- Object storage locations.
- Credentials and secrets.
- Application configuration.
- Monitoring access policies.
- Data retention settings where appropriate.

Environment separation must not rely only on naming conventions.

---

## 5. Containerization

Docker is the initial containerization technology.

Docker Compose is the initial local multi-container orchestration tool.

### 5.1 Application containers

Potential containers include:

- FastAPI application.
- Celery worker.
- Celery scheduler.
- PostgreSQL.
- RabbitMQ.
- Monitoring services.

### 5.2 Container design principles

- Use reproducible build configurations.
- Pin application dependencies.
- Avoid unnecessary packages.
- Run processes with least privilege.
- Avoid running as root where practical.
- Keep secrets outside images.
- Use health checks.
- Handle termination signals correctly.
- Keep application state outside disposable containers.
- Use explicit resource limits in environments that support them.

### 5.3 Image management

Application images should be:

- Built from reviewed source.
- Versioned.
- Traceable to a source revision.
- Scanned where suitable tooling is available.
- Promoted between environments rather than rebuilt differently for each environment.

Production must not depend on an untracked development image.

---

## 6. Configuration Management

Application configuration must be externalized from application code.

### 6.1 Configuration categories

Configuration includes:

- Environment name.
- Database connection settings.
- Broker connection settings.
- Object storage configuration.
- API settings.
- Worker concurrency.
- Retry policies.
- Model configuration.
- Logging levels.
- Feature flags.
- Timeout settings.
- Retention policies.

### 6.2 Configuration rules

- Use validated configuration models.
- Keep environment-specific values separate.
- Provide safe defaults only where appropriate.
- Fail startup when mandatory configuration is invalid.
- Do not silently ignore unknown critical configuration.
- Avoid embedding environment-specific URLs in business logic.
- Version configuration changes where useful.

### 6.3 Configuration and secrets separation

Ordinary configuration and sensitive credentials must be handled separately.

Examples of secrets:

- Database passwords.
- Broker credentials.
- API keys.
- Object storage credentials.
- Identity-provider client secrets.
- Signing keys.

Secrets must not be stored in ordinary configuration files committed to Git.

---

## 7. Secrets Management

Raven must use a controlled secrets-management approach.

### 7.1 Requirements

- No secrets in source code.
- No secrets in Git history.
- No secrets in Docker images.
- No secrets in logs.
- Restrict access by environment and component.
- Rotate credentials.
- Revoke compromised credentials.
- Use separate credentials across environments.
- Avoid sharing one privileged credential across all components.

### 7.2 Local development

Local development may use an ignored environment file or another protected local secrets mechanism.

Example filename:

`.env`

It must:

- Be excluded from Git.
- Never contain production secrets.
- Be protected by local file permissions.
- Have a documented example template containing placeholders only.

### 7.3 Production

Production secrets should be supplied through an appropriate secret-management mechanism provided by the deployment platform or infrastructure.

The exact provider is deferred.

---

## 8. Database Deployment and Migration

PostgreSQL is Raven's primary relational database.

### 8.1 Database deployment

The initial database architecture follows Phase 7.2:

- One initial PostgreSQL deployment.
- Logical separation for Memory, Research, Orchestrator, and Shared Infrastructure.
- Engine-specific ownership.
- Restricted database roles.
- Controlled migrations.

### 8.2 Migration management

Alembic is the initial migration technology.

Every database change must:

1. Be represented by a reviewed migration.
2. Have a clear schema version.
3. Be tested against representative data.
4. Preserve existing records where required.
5. Validate indexes and constraints.
6. Be deployed in a controlled sequence.
7. Be monitored after application.

### 8.3 Migration safety

Prefer backward-compatible migrations.

For changes that affect active application versions:

1. Introduce compatible schema changes.
2. Deploy application code that supports the new schema.
3. Migrate or backfill data.
4. Validate the resulting state.
5. Remove obsolete schema elements only after compatibility is established.

Do not assume that every database migration can be safely reversed.

For destructive changes, recovery may require restoring from a backup or applying a forward corrective migration.

### 8.4 Migration safeguards

- Back up before high-risk migrations.
- Validate migration behavior in staging.
- Avoid long-running production locks where possible.
- Monitor migration progress.
- Define recovery procedures.
- Never run unreviewed destructive migrations automatically.

---

## 9. Object Storage Deployment

Large original documents and content should be stored outside PostgreSQL using the selected S3-compatible object storage architecture.

### 9.1 Storage responsibilities

Object storage may contain:

- Original uploaded documents.
- Large source content.
- Archived processing artifacts.
- Other large binary objects.

### 9.2 Deployment requirements

- Use environment-specific storage locations.
- Restrict access by component and user scope.
- Use opaque object identifiers.
- Validate object ownership.
- Store checksums where appropriate.
- Apply retention policies.
- Support deletion propagation.
- Protect credentials.
- Avoid public object access by default.

### 9.3 Consistency

PostgreSQL and object storage do not share one ACID transaction.

Raven must use controlled operation records and reconciliation to handle partial failures.

For example, an upload may succeed in object storage while its metadata transaction fails.

Such cases must be detectable and recoverable.

---

## 10. RabbitMQ and Celery Deployment

RabbitMQ and Celery provide asynchronous processing infrastructure.

### 10.1 RabbitMQ

Production configuration should consider:

- Durable queues where required.
- Message persistence.
- Authentication.
- Network restrictions.
- Resource limits.
- Monitoring.
- Backup and recovery requirements.
- Dead-letter routing.

### 10.2 Celery workers

Workers should be deployed according to workload characteristics.

Logical worker categories include:

- Memory processing.
- Research processing.
- Embedding generation.
- Maintenance and reconciliation.

The initial deployment may combine categories.

### 10.3 Worker lifecycle

Workers must:

- Start with validated configuration.
- Connect to required infrastructure.
- Report health.
- Process authorized tasks.
- Respect cancellation.
- Handle shutdown signals.
- Release resources.
- Avoid losing committed business results during termination.

### 10.4 Scheduler

Scheduled work may include:

- Memory maintenance.
- Research refresh.
- Reconciliation.
- Retention processing.
- Periodic operational checks.

Scheduling must be idempotent and must not create duplicate logical operations.

---

## 11. Deployment Strategy

Raven should use controlled, staged deployments.

### 11.1 Release workflow

1. Complete development changes.
2. Run automated checks.
3. Run relevant integration and regression tests.
4. Build a versioned container image.
5. Deploy to staging.
6. Run migration checks.
7. Validate service health.
8. Run critical workflow tests.
9. Approve production release.
10. Deploy production.
11. Monitor application and infrastructure health.
12. Complete release verification.

### 11.2 Release identity

Each release should record:

- Source revision.
- Application version.
- Container image version.
- Database schema version.
- Configuration version where applicable.
- Deployment timestamp.
- Deployment environment.

### 11.3 Deployment order

Deployment order must respect compatibility and dependencies.

A typical sequence may include:

1. Infrastructure changes.
2. Backward-compatible database migrations.
3. Application deployment.
4. Worker deployment.
5. Background processing verification.
6. Final schema cleanup in a later compatible release, if needed.

The exact sequence depends on the change.

---

## 12. Deployment Safety and Rollback

### 12.1 Deployment safeguards

- Health checks.
- Readiness checks.
- Migration validation.
- Controlled worker shutdown.
- Release version tracking.
- Error-rate monitoring.
- Database compatibility checks.
- Post-deployment verification.

### 12.2 Application rollback

If a release causes failures:

- Stop further rollout.
- Evaluate the affected components.
- Roll back application images where compatible.
- Preserve database integrity.
- Reconcile background tasks.
- Verify worker and broker state.
- Record the incident.

### 12.3 Database rollback

Database rollback is more complicated than application rollback.

Do not automatically reverse a migration after application data has been written using the new schema.

Use a forward corrective migration or a controlled restoration strategy where appropriate.

### 12.4 Background task safety

During deployment:

- Stop accepting new work where necessary.
- Allow safe tasks to complete.
- Preserve unacknowledged messages.
- Ensure tasks can be redelivered safely.
- Reconcile tasks interrupted during shutdown.
- Avoid duplicate authoritative effects.

---

## 13. Backup Architecture

Raven must maintain backups for authoritative data and critical infrastructure configuration.

### 13.1 PostgreSQL backup

The backup strategy should support:

- Scheduled backups.
- Point-in-time recovery where supported.
- Transaction log or WAL retention.
- Backup integrity checks.
- Restore testing.
- Restricted backup access.

### 13.2 Object storage backup

Object storage protection should include:

- Versioning where appropriate.
- Replication or backup where justified.
- Integrity checks.
- Retention policies.
- Recovery of deleted or corrupted objects where policy permits.

### 13.3 Infrastructure configuration

Protect critical configuration such as:

- Deployment definitions.
- Migration history.
- Broker configuration.
- Monitoring configuration.
- Infrastructure definitions.
- Recovery documentation.

Secrets must be backed up only through an approved secure process.

---

## 14. Disaster Recovery

Disaster recovery must restore a consistent system rather than simply restart containers.

### 14.1 Recovery priorities

1. Restore secure infrastructure access.
2. Restore PostgreSQL.
3. Restore object storage access and required content.
4. Restore RabbitMQ and relevant queue configuration.
5. Deploy compatible application versions.
6. Reconcile task and execution states.
7. Reapply applicable deletion records.
8. Rebuild or reconcile derived data and vector indexes.
9. Validate user isolation and data integrity.
10. Restore normal processing.

### 14.2 Derived data recovery

Embeddings, search indexes, and caches are derived data.

Where feasible, they should be reconstructable from authoritative records and recorded model configurations.

They must not be treated as the only copy of important information.

### 14.3 Deletion safety

Restoring an old backup must not resurrect data that was explicitly deleted after that backup.

Raven must preserve and reapply applicable deletion records or tombstones during recovery.

### 14.4 Recovery objectives

Recovery Point Objective (RPO) and Recovery Time Objective (RTO) must be defined according to operational requirements.

Exact numerical targets are deferred until infrastructure, cost, and workload requirements are established.

---

## 15. Health Checks

Raven must distinguish liveness from readiness.

### 15.1 Liveness

Liveness answers:

"Is this process running and capable of continuing?"

It should not fail merely because an optional dependency is temporarily unavailable.

### 15.2 Readiness

Readiness answers:

"Can this component safely accept its intended workload?"

Readiness may depend on required dependencies and configuration.

### 15.3 Component health

Monitor:

- FastAPI.
- Orchestrator.
- Memory Engine.
- Research Engine.
- PostgreSQL.
- RabbitMQ.
- Celery workers.
- Object storage.
- Embedding infrastructure.
- Monitoring infrastructure.

Health checks must not expose credentials or sensitive configuration.

---

## 16. Environment and Release Security

Deployment security requirements:

- Isolate production from development.
- Restrict production access.
- Use separate credentials per environment.
- Protect container images.
- Validate dependency integrity.
- Restrict database and broker network access.
- Apply least-privilege permissions.
- Secure deployment credentials.
- Protect backup access.
- Audit privileged deployment operations.
- Avoid production data in local development.
- Apply security updates through controlled releases.

Production deployment must not depend on a developer's personal credentials.

---

## 17. Infrastructure Scaling Strategy

Raven should scale according to measured bottlenecks.

### 17.1 Initial approach

Start with the modular monolith and independently executable workers.

Avoid premature microservice separation.

### 17.2 Horizontal scaling

Potential scaling options:

- Multiple API instances.
- Additional Celery workers.
- Separate resource-intensive worker pools.
- RabbitMQ capacity expansion.
- PostgreSQL read replicas.
- Dedicated vector infrastructure.
- Separate engine deployments.

### 17.3 Scaling decision criteria

Consider separation or expansion when measurements show:

- Resource contention.
- Sustained queue backlog.
- Database bottlenecks.
- Unacceptable latency.
- Different availability requirements.
- Independent scaling requirements.
- Security or isolation requirements.

A new service or database should solve a demonstrated problem rather than add complexity without measurable benefit.

---

## 18. Deployment Monitoring

Every deployment must be observable.

Monitor:

- Application startup failures.
- Readiness failures.
- Migration errors.
- Worker availability.
- Queue backlog.
- Database connectivity.
- Object storage access.
- API latency.
- Error rates.
- Resource utilization.
- Execution recovery.
- Data integrity checks.

Deployments must include post-release verification.

A successful container startup alone does not prove that Raven is operating correctly.

---

## 19. Testing Requirements

Deployment architecture must eventually be tested for:

### Environment separation

- Development cannot access production data by default.
- Testing uses isolated dependencies.
- Staging uses isolated data.
- Production secrets are not exposed.

### Containerization

- Reproducible image builds.
- Startup and shutdown behavior.
- Health checks.
- Configuration validation.
- Non-root execution where practical.

### Migration safety

- Fresh database migration.
- Upgrade from previous schema.
- Backward compatibility.
- Failed migration recovery.
- Data integrity after migration.

### Deployment safety

- Application rollback.
- Worker shutdown.
- Message redelivery.
- Interrupted task recovery.
- Post-deployment health validation.

### Backup and recovery

- PostgreSQL restore.
- Object storage recovery.
- Queue recovery where required.
- Derived index reconstruction.
- Deletion tombstone reapplication.
- Full system consistency validation.

---

## 20. Finalized Decisions

The following architectural decisions are established:

1. Raven uses separate development, testing, staging, and production environments.
2. Docker is the initial containerization technology.
3. Docker Compose is the initial local orchestration tool.
4. The initial deployment follows a modular monolith architecture with independently executable workers.
5. Configuration is externalized from application code.
6. Secrets are separated from ordinary configuration.
7. PostgreSQL remains the primary relational database.
8. Alembic manages database migrations.
9. S3-compatible object storage stores large original content.
10. RabbitMQ and Celery provide asynchronous processing infrastructure.
11. Deployments use controlled release and verification procedures.
12. Database migrations must preserve compatibility and integrity.
13. Backups and restoration testing are required.
14. Recovery must reconcile execution state and derived data.
15. Explicit deletions must remain effective after backup restoration.
16. Liveness and readiness are separate health concepts.
17. Scaling decisions are based on measured bottlenecks.
18. Production access and deployment credentials follow least privilege.

---

## 21. Deferred Decisions

The following decisions require implementation or infrastructure evaluation:

- Cloud provider.
- Container hosting platform.
- Production orchestration platform.
- Identity and secrets-management providers.
- PostgreSQL hosting configuration.
- RabbitMQ hosting configuration.
- Object storage provider.
- Deployment automation tooling.
- CI/CD provider.
- Domain and network configuration.
- Production monitoring deployment.
- Backup frequency.
- Backup retention.
- RPO and RTO targets.
- High availability and replication configuration.
- Production scaling thresholds.
- Disaster recovery location.

These decisions must remain consistent with the security, reliability, and ownership principles defined throughout Phase 7.

---

## 22. Completion Criteria

Phase 7.8 is architecturally specified when:

- Deployment units are documented.
- Environment isolation is defined.
- Containerization requirements are established.
- Configuration and secrets management are defined.
- Database and object storage deployment are addressed.
- Background worker deployment is specified.
- Release and rollback strategies are documented.
- Backup and disaster recovery are covered.
- Health checks and deployment monitoring are established.
- Scaling and infrastructure security principles are defined.

**Status:** Architecture specification complete.

**Important:** This document does not claim that Docker images, cloud infrastructure, deployment pipelines, backups, or production environments have been implemented or deployed.

---

## 23. Phase 7 Completion

Phase 7 — Technology & Infrastructure Selection is now architecturally documented across eight subphases:

1. Baseline Technology Stack.
2. Database & Storage Architecture.
3. Vector Search & Embedding Infrastructure.
4. Background Processing & Messaging.
5. NLP & Machine Learning Stack.
6. API, Security & Internal Communication.
7. Observability & Testing Infrastructure.
8. Deployment & Environment Architecture.

The selected technologies establish Raven's initial implementation direction. Deferred decisions remain open until implementation evidence, workload measurements, and operational requirements justify final selection.

---

## 24. Next Phase

**Phase 8 — Memory Engine Implementation**

The next phase transitions from architecture specifications to implementation.

Implementation should follow the documented Memory Engine architecture, data models, algorithms, and technology decisions. Code must be validated against those documents rather than used to silently redefine them.
