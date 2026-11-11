# Phase 8.2 Architecture Decision Review

**Date:** 2026-11-11 · **Basis:** `main` @ `6efd72d` (PR #3 merge of Phase 8.1 commit `5a0d6e5`) · **Status:** On 2026-11-11 the user **approved Decisions 1, 2, 4, 5 and 10** as recommended here. They are recorded in [7.1 §23](../technical-decisions/01-baseline-technology-stack.md) and the Phase 8.2 amendment of [5.4](../data-models/phase-05-memory-engine-models.md). The user also **approved deferring vector storage to 8.7** (8.2 creates embedding metadata only; 7.1 §23.5). All other recommendations, including the embedding model itself, are **not yet approved**. Phase 8.2 has **not** started.

This review verifies Phase 8.1, records the actual repository state, analyses all 15 open decisions from [NEXT_STEPS.md](NEXT_STEPS.md), and examines in depth the five decisions that block Phase 8.2. Every factual statement was checked against the repository on the date above. Statements about external libraries and models reflect knowledge at the time of writing and must be re-verified (licence, version, revision) when the decision is executed.

---

## 1. Executive summary

- **Phase 8.1 is verified, committed, pushed and merged.** Commit `5a0d6e5` (31 files) was pushed and merged into `main` through [PR #3](https://github.com/SARTHAK10710/raven-research-agent/pull/3) as merge commit `6efd72d`. All checks pass: 71 tests, Ruff lint and format, mypy strict, `uv sync --locked`. The earlier "uncommitted / no upstream / not merged" status lines were out of date and are corrected in this change.
- **The Windows mypy failure is environmental, not a project defect.** It reproduces only when the repository root is very long (180 characters here). A fresh checkout at a 109-character root with an ordinary in-tree `.venv` passes mypy strict and pytest.
- **Of the 15 open decisions, four genuinely block Phase 8.2:**
  - package layout (1)
  - database driver and access pattern (2)
  - relationship vocabulary, together with the undefined Atomic Memory lifecycle states (4)
  - document record placement (5)

  Decision 3 (embedding model) blocks 8.2 only if 8.2 creates vector columns. This review recommends that 8.2 create embedding *metadata* only and that vector storage move to 8.7, after a Raven-specific evaluation.
- **Recommended choices:**

  | # | Recommendation |
  |---|---|
  | 1 | Domain-first packages (`personal/`, `documents/`), each split into `domain` and `application`. Shared kernel in the existing `domain/`; adapters in `infrastructure/`; public contracts in `interfaces/` |
  | 2 | psycopg 3 with synchronous SQLAlchemy 2.0, one engine per process, and short owner-scoped units of work |
  | 3 | An evaluation-led choice from a shortlist of sentence-transformers models; the dimension follows the chosen model |
  | 4 | Four separate vocabularies (entity relationships, memory relationships, revision change types, memory lifecycle states) with directional, active-voice naming. Temporal meaning lives in bitemporal attributes, not relationship names |
  | 5 | All Document Intelligence records in the existing `memory` schema as separate `doc_`-prefixed tables, owned by the Memory Engine role, with a deliberate, non-cascading cross-domain evidence reference |

- **Seven specification gaps or contradictions** were found (section 5.6). None is resolved silently. Each needs a user decision.

---

## 2. Phase 8.1 verification evidence

### 2.1 Repository state (verified 2026-11-11)

| Check | Result |
|---|---|
| Current branch | `feat/phase-8-1-foundation` |
| Commit `5a0d6e5` exists | Yes: `feat(memory-engine): Phase 8.1 foundation and project setup` |
| Files in commit | **31** (24 added, 7 modified, 0 deleted), matching the expected list |
| Working tree before this review | Clean (0 uncommitted or untracked files) |
| Upstream configured | **Yes:** `origin/feat/phase-8-1-foundation`, identical to local `5a0d6e5`. The earlier "no upstream" report is out of date: the branch was pushed when the user requested a pull request |
| Pull request | [PR #3](https://github.com/SARTHAK10710/raven-research-agent/pull/3), **merged** 2026-11-10 21:19 UTC by SARTHAK10710, merge commit `6efd72d` |
| `main` content | `origin/main` @ `6efd72d`; its tree is identical to `5a0d6e5` |
| Forbidden artifacts in any branch commit | None (`.env`, `.venv/`, `__pycache__`, caches, `.coverage`, `htmlcov`, `.pyc` all absent) |
| Auto-fix monitor | On for PR #3 (no CI checks are configured in the repository) |

### 2.2 Checks run in the repository checkout

| Command | Result |
|---|---|
| `uv sync --locked` | Succeeded. 22 packages checked; the lockfile matches `pyproject.toml` |
| `uv run pytest --cov` | **71 passed**, 0 failed; 98% line and branch coverage |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 79 files already formatted |
| `uv run mypy` (repo `.venv`) | **Fails to start:** `ImportError: DLL load failed while importing 6ec57f84c680d3a3778b__mypyc: The filename or extension is too long.` (reproduced) |
| `uv run mypy` (fresh clone, see 2.3) | **Success: no issues found in 16 source files** |

### 2.3 Windows long-path investigation

- **Reproduction:** the failure reproduces in this checkout, whose root path is **180 characters**. `LongPathsEnabled` is set to `1` on this machine.
- **Measurement:** the mypy shared runtime DLL sits at 252 characters. Eleven mypyc extension modules sit at 256–263 characters, for example `.venv/Lib/site-packages/mypyc/transform/borrow_generator_attrs.cp312-win_amd64.pyd` at 263. Windows' DLL loader does not honour the long-path setting, so extension modules at or near the classic 260-character limit fail to load.
- **Control test:** a fresh clone of `5a0d6e5` at a **109-character** root, with an ordinary in-tree `.venv`, ran `uv sync --locked`, then **mypy strict with no issues in 16 files** and **pytest with 71 passed**. Its longest extension path was 192 characters.
- **Conclusion:** this is not a project defect. It comes from the long scratch-workspace path this session runs in. Any normal clone location, such as `C:\Users\<name>\raven-research-agent` or `C:\dev\raven`, avoids it.
- **Forward risk:** later phases add much deeper package trees, such as PyTorch for sentence-transformers. Keep the repository root short; under about 100 characters leaves a safe margin. `UV_PROJECT_ENVIRONMENT` pointing at a shorter path remains a workaround.

### 2.4 Phase 8.1 acceptance criteria (plan 8.1 §15)

All criteria are met.

| Area | Criterion | Evidence |
|---|---|---|
| Foundation | Python 3.12, uv workspace, member, single `uv.lock`, install works, only approved dependencies, imports | `uv sync --locked`; `uv tree` shows only `pydantic`, `pydantic-settings` (runtime) and `pytest`, `pytest-cov`, `ruff`, `mypy` (dev) as direct dependencies; `test_package.py` |
| Configuration | Pydantic Settings; valid configuration loads; missing configuration fails clearly; invalid values rejected; secrets not committed | `test_config.py` (21 tests); repository scan finds only the synthetic test password |
| Architecture | Domain/infrastructure boundary; ownership; no Orchestrator or Research logic; no unnecessary infrastructure | `test_domain_boundary.py` (source-scanning import rules); code inspection |
| Quality | Logging; consistent errors; pytest from the root; tests pass; Ruff; mypy strict | Section 2.2 |
| Documentation | Memory Engine README with setup and test commands; existing docs preserved | `memory-engine/README.md` |

---

## 3. Updated implementation status

| Item | Status |
|---|---|
| Phase 8.1 | `VERIFIED`. Committed `5a0d6e5`, pushed, merged into `main` via PR #3 (`6efd72d`) |
| Phase 8.2 | `NOT_STARTED`. Not approved |
| Phases 8.3–8.12 | `NOT_STARTED` |
| Installed dependencies | Phase 8.1 set only. No SQLAlchemy, Alembic, driver, pgvector client, Celery, sentence-transformers or spaCy |
| Infrastructure | None provisioned (no PostgreSQL, RabbitMQ or object storage) |
| This review's documentation edits | Uncommitted in the working tree of `feat/phase-8-1-foundation`. That branch is already merged, so landing these edits needs a commit and a new pull request |

---

## 4. All 15 open decisions

⚑ means explicit user approval is required. Blockers 1–5 are summarized here and analysed in depth in section 5.

### Decision 1 — Code organization for Personal Memory vs Document Intelligence inside the package ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Determines where every 8.2+ module lives, and whether the Personal Memory / Document Intelligence separation can be enforced mechanically |
| Constraints | Two separate logical domains (Phase 8 Readme §4; 5.4 amendment); domain layer free of infrastructure (plan 8.1 §7); plan 8.1 §4 proposes a feature-first tree with no Document Intelligence area; no fourth engine; no microservices |
| Options | A: keep plan 8.1's feature-first tree. B: domain-first (`personal/`, `documents/`), layered inside. C: layer-first (`domain/personal`, `application/personal`, …) |
| Depends on | None. Decision 5 should mirror it in persistence naming |
| If delayed | 8.2 cannot place persistence models; a later restructure would touch every module and import |
| Recommendation | **B** (section 5.1) |
| Approval | **Yes**. It changes plan 8.1 §4's proposed tree |

### Decision 2 — PostgreSQL driver; sync vs async database access ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Fixes the session model, transaction handling, test fixtures and worker integration for the whole engine |
| Constraints | PostgreSQL + SQLAlchemy + Alembic approved (7.1/7.2); SQLAlchemy pooling initially (7.2 §9); Celery workers (7.4); FastAPI (7.6); short transactions (plan 8.2 §8) |
| Options | psycopg 3 sync; psycopg 3 async; asyncpg (async only); psycopg2; pg8000 |
| Depends on | Decision 1 (where the persistence code goes) |
| If delayed | 8.2 cannot start |
| Recommendation | **psycopg 3 + synchronous SQLAlchemy 2.0** (section 5.2) |
| Approval | **Yes**. It is a new runtime dependency and a lasting access-pattern decision |

### Decision 3 — Embedding model, dimension, similarity metric, index type ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Vector column dimensions, index type, retrieval quality, hardware cost and future migration effort all follow from it |
| Constraints | sentence-transformers ecosystem (7.1); selection must use Raven-specific evaluation, not benchmark rankings alone (7.3 §5); model and version recorded per vector (5.4.19, 7.3 §5.2); a shared model is allowed initially if evaluation supports it (7.3 amendment §4) |
| Options | Shortlist in section 5.3; or defer by keeping 8.2 free of vector columns |
| Depends on | Decision 14 (evaluation datasets); the language requirement (gap G6) |
| If delayed | Blocks 8.7, not 8.2, provided vector columns move to 8.7 |
| Recommendation | Run a bounded evaluation before 8.7; 8.2 stores embedding metadata only (section 5.3) |
| Approval | **Yes**, for the evaluation spike, the new dependency and the final model |

### Decision 4 — Canonical vocabularies ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | These become database enums and constraints in 8.2. Ambiguous or duplicated types corrupt resolution, retrieval expansion and deletion |
| Constraints | 5.4.15 (typed, directed entity relationships; symmetric meaning explicit); 5.4.27 (memory relationship examples); 6.3.7 (supersession types); 6.3.8 (relationship types incl. `DEPENDS_ON`, `ABOUT_ENTITY`); 6.3 resolution outcomes; plan 8.5 §7 (adds "corrects"); bitemporal model (5.3.4) |
| Options | Adopt one list verbatim; merge everything into one enum; or separate vocabularies by kind (section 5.4) |
| Depends on | Gap G1 (Atomic Memory lifecycle states) |
| If delayed | 8.2 schema enums and check constraints cannot be written |
| Recommendation | Four vocabularies plus attribute-based temporal meaning (section 5.4) |
| Approval | **Yes**. It extends and clarifies approved Phase 5 and 6 vocabularies |

### Decision 5 — Placement of Document Intelligence records ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Ownership, isolation, deletion and migrations for the seven document entities |
| Constraints | Single PostgreSQL deployment with domain schemas (7.2); Document Intelligence records "initially" in the `memory` schema, "subject to reconciliation with Phase 5" (7.2 amendment §3); no separate document database (7.2 amendment §11) |
| Options | A: `memory` schema with prefixed tables. B: a second Memory-Engine-owned schema. C: separate database. D: object storage only |
| Depends on | Decisions 1 and 2 |
| If delayed | 8.2 cannot create document tables |
| Recommendation | **A**, with a controlled cross-domain evidence reference (section 5.5) |
| Approval | **Yes**. It settles the amendment's open reconciliation |

### Decision 6 — Document-to-memory authorization model ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Document text must never become personal memory without explicit user intent. This is the only bridge between the two domains |
| Constraints | Explicit authorization required (5.4 amendment §5; plan 8.4 §11; memory/05 §17); document content is untrusted (plan 8.4 §11; 7.6 §12) |
| Options | A: implicit (user can read, so extraction is allowed). Rejected: violates the explicit-authorization rule. B: per-request authorization record (user, document version, scope, purpose, expiry). C: standing per-document consent flag |
| Pros and cons | B is auditable, precise and revocable, but costs one record per request. C is convenient, but broad and easy to over-apply to new versions |
| Depends on | Decision 10 (owner identity); Decision 5 (evidence references) |
| If delayed | Blocks only the document-derived path of 8.4/8.12. Safe to delay as long as that path stays disabled |
| Recommendation | **B**. Store `doc_memory_extraction_authorization` (owner, document_version, scope, requested_by, created_at, expires_at, status). Require it on every extraction run; revocation stops future runs but does not delete promoted memories |
| Approval | **Yes** (privacy) |

### Decision 7 — Sequence: run 8.12 before 8.11; 8.4's document-derived path after 8.12 ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Plan 8.11 tests Document Intelligence end to end before plan 8.12 builds it, and plan 8.4 consumes 8.12's outputs |
| Constraints | Phase 8 Readme §6 order; "iterative integration" allowed |
| Options | Keep the order and stub 8.12 outputs (wasted work and false confidence); reorder |
| Depends on | None |
| If delayed | No effect until 8.4 |
| Recommendation | **Reorder**: … 8.10 (personal) → 8.12 → complete the 8.4 document path and 8.10 document deletion → 8.11 last |
| Approval | **Yes**. It changes the documented plan order |
| **Outcome (2026-11-12)** | **Approved as recommended** when 8.4 was approved: 8.4 builds the personal path now; its document path and the 8.10 document deletion follow 8.12; 8.11 runs last. Recorded in [7.1 §25.1](../technical-decisions/01-baseline-technology-stack.md) and the Phase 8 Readme §6 |

### Decision 8 — Local S3-compatible object storage for development and tests ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Memory Source content (5.4.1) and document originals need object storage. Tests need an isolated instance |
| Constraints | S3-compatible approach approved, provider deferred (7.1/7.8); Docker Compose for local dependencies (7.8); no new infrastructure without justification |
| Options | A: S3-compatible container in Docker Compose (development and tests only). B: filesystem adapter behind the storage port. C: cloud bucket for development |
| Pros and cons | A matches production semantics (checksums, multipart, keys) but adds a container. B is simplest but hides S3 behaviour. C costs money and risks data leaving the machine |
| Depends on | Decision 1 (port placement) |
| If delayed | Blocks 8.3 (content storage). 8.2 needs only object-key columns |
| Recommendation | Define a storage port in 8.2. Use **B for unit tests and A for integration tests**, with the container image chosen and licence-checked at 8.3 |
| Approval | **Yes** (new local infrastructure) |
| **Outcome (2026-11-11)** | **Approved:** a storage port; an in-memory fake for unit tests; **SeaweedFS** (Apache-2.0) in Docker Compose for integration tests and local development; **boto3** as the client. All are implemented in 8.3, and no port was added in 8.2. MinIO (community images stopped in 2025, repository archived in 2026) and LocalStack (account and auth token required since 2026) were ruled out. Recorded in [7.1 §24.1](../technical-decisions/01-baseline-technology-stack.md) |

### Decision 9 — When to introduce Celery/RabbitMQ and the transactional outbox

| Aspect | Analysis |
|---|---|
| Why it matters | Long-running work must not hold transactions (plan 8.2 §8). Reliable publishing needs the outbox (7.4 §9) |
| Constraints | Outbox recommended (7.4); queue topology deferred |
| Options | Outbox table in 8.2 with Celery in 8.3; or both in 8.3 |
| Pros and cons | Outbox in 8.2 puts all schema foundations in one migration series, at the cost of an unused table for one subphase. Both in 8.3 keeps 8.2 smaller but adds a schema change to 8.3 |
| Depends on | Decision 2 |
| If delayed | 8.3 would need a schema change for the outbox |
| Recommendation | **Outbox and operation tables in 8.2** (schema only, no broker); Celery and RabbitMQ in 8.3 |
| Approval | No. Low-risk sequencing within approved technology |
| **Outcome (2026-11-11)** | The owner chose **both in 8.3**: no outbox table in 8.2 (operation tables stay in 8.2). Recorded in [7.1 §23.6](../technical-decisions/01-baseline-technology-stack.md). The recommendation above is kept as the original analysis |

### Decision 10 — Owner identity before an identity provider is chosen ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Every row, query and job is owner-scoped. Owner identity is needed from 8.2 onward, but the identity provider is deferred (7.6) |
| Constraints | Authentication belongs to the Entry layer and Shared Infrastructure; engines enforce ownership (7.6 §7.3); identity records are owned by Shared Infrastructure (5.7) |
| Options | A: Memory Engine accepts a validated `OwnerScope` (opaque user id) from its caller. B: Memory Engine validates tokens itself. C: Memory Engine keeps its own user table |
| Pros and cons | A keeps the boundary clean and testable, and assumes callers are trusted. B breaks the ownership boundary. C duplicates Shared Infrastructure ownership |
| Depends on | None |
| If delayed | Blocks 8.2 column types and repository signatures |
| Recommendation | **A**: `owner_id` as an opaque identifier (UUID) on every owned row, with no foreign key to a Memory Engine user table. Repository methods require `OwnerScope` |
| Approval | **Yes** (security boundary) |

### Decision 11 — Shared public entities (5.4.13): population and privacy ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | Shared entities are the only data visible across users, so they are the main cross-user leakage risk |
| Constraints | Shared entities carry no private context; private-to-shared promotion requires explicit validation (5.4.13) |
| Options | A: private entities only at first. B: shared entities populated by user activity. C: curated shared catalogue |
| Pros and cons | A has zero leakage risk but duplicates public entities per user. B leaks risk through inference from what users mention. C is safe but needs a curation process |
| Depends on | Decision 4 (entity vocabulary) |
| If delayed | None for 8.2; the schema can carry a `scope` column |
| Recommendation | **A** in 8.5, with `scope` (`private` / `shared`) in the schema from 8.2 and shared rows prohibited by a check until a curation process is approved |
| Approval | **Yes** (privacy) |

### Decision 12 — Derived-profile ownership

| Aspect | Analysis |
|---|---|
| Why it matters | Phase 2 places derived profiles in component 3 (Entity & Relationship Management); Phase 6 (6.5.6) and plan 8.9 place them in consolidation |
| Constraints | Profiles are derived views and never authoritative (phase-02 core rules; 5.4.17); the Memory Engine owns them either way |
| Options | Component 3; or consolidation (component 7) |
| Pros and cons | Component 3 matches the Phase 2 wording, but splits profile refresh from the consolidation scheduler that triggers it. Consolidation matches the detailed algorithm (6.5.6) and plan 8.9, and keeps all derived-data refresh in one place |
| Depends on | None |
| If delayed | None until 8.9 |
| Recommendation | Consolidation (8.9). Record the Phase 2 wording difference in `KNOWN_CONSTRAINTS.md`. Approval is needed only to edit the Phase 2 document itself |
| Approval | Only for an architecture-document edit |

### Decision 13 — Document parsing ownership (6.2.1 vs the document pipeline)

| Aspect | Analysis |
|---|---|
| Why it matters | Algorithm 6.2.1 lists PDF/DOCX/TXT as memory-ingestion inputs, which overlaps the Document Intelligence pipeline. Two parsers would diverge |
| Constraints | Uploads never create memories automatically (Phase 8 Readme §4.2); document content is untrusted (7.6 §12); one source of truth per artifact |
| Options | Parse in both places; or the document pipeline owns parsing and memory ingestion handles messages and conversations only |
| Pros and cons | Parsing in both places duplicates code, doubles the attack surface for malformed files, and lets the two outputs diverge. Single ownership gives one hardened parser and one extracted representation per version that both domains can cite, but makes memory ingestion of documents depend on the document pipeline (which the authorization path already requires) |
| Depends on | Decision 6 |
| If delayed | Must be settled before 8.3 |
| Recommendation | Document pipeline owns parsing. Memory ingestion reaches document text only through the authorized document-to-memory path (Decision 6) |
| Approval | **Yes**. It reinterprets an approved Phase 6 algorithm |
| **Outcome (2026-11-11)** | **Approved as recommended:** the document pipeline (8.12) owns parsing; ingestion (8.3) validates, stores, registers and hands off; the document-to-memory path stays disabled until Decision 6 is approved. Recorded in [7.1 §24.2](../technical-decisions/01-baseline-technology-stack.md) and an amendment to [6.2](../algorithms/memory/01-memory-ingestion-extraction.md). Gap G5 closed |

### Decision 14 — spaCy pipeline; scoring thresholds and weights; evaluation datasets

| Aspect | Analysis |
|---|---|
| Why it matters | Extraction quality, resolution precision and ranking cannot be judged without labelled data. Thresholds are deferred everywhere in Phase 6 |
| Constraints | Synthetic data, versioned and reproducible (7.7 §12) |
| Options | Build datasets per subphase; build one large dataset up front |
| Pros and cons | Per-subphase datasets stay small and relevant, and are ready when needed, but risk inconsistent conventions without a shared schema. One upfront dataset is consistent, but costs a lot of time before any code needs it and goes stale as specifications are refined |
| Depends on | Decision 3 (shares the retrieval datasets) |
| If delayed | Blocks 8.4 and later quality gates |
| Recommendation | Versioned synthetic datasets under `tests/memory_engine/quality/data/`, one per capability, created with the subphase that first needs them. The retrieval set comes first, because Decision 3 needs it. spaCy model choice at 8.4 |
| Approval | spaCy model: **yes**, at 8.4. Datasets: no |
| **Outcome (2026-11-12)** | **spaCy 3.8 with `en_core_web_sm` 3.8.0**, English first (gap G6). Datasets per capability under `tests/memory_engine/quality/data/`. Recorded in [7.1 §25.2–§25.3](../technical-decisions/01-baseline-technology-stack.md) |

### Decision 15 — Approve pypdf and python-docx ⚑

| Aspect | Analysis |
|---|---|
| Why it matters | These are the proposed PDF and DOCX parsers (7.5 amendment §18). Their parsing robustness and safety on untrusted files matter |
| Constraints | "Proposed libraries must be evaluated and approved before becoming mandatory" (7.5 amendment §18); validate the real file format, enforce size and resource limits, never execute embedded content (7.6 §12; 7.5 amendment §17) |
| Options | Approve as proposed; evaluate alternatives at 8.12 |
| Pros and cons | Approving now saves time later, but commits before parser robustness on Raven's inputs is known. Evaluating at 8.12 costs a short evaluation task, but bases the choice on malformed and adversarial file results and current maintenance status |
| Depends on | Decision 13 |
| If delayed | None until 8.12 |
| Recommendation | Evaluate at the start of 8.12 against a malformed and adversarial file corpus. Check licences and maintenance |
| Approval | **Yes** |

---

## 5. Detailed analysis of the five Phase 8.2 blockers

### 5.1 Decision 1 — Package layout

**Goal:** enforce, through package boundaries and tests, that Personal Memory and Document Intelligence are separate domains, that the domain layer is infrastructure-free, and that other components reach the engine only through defined interfaces. No fourth engine and no microservices.

**Options considered**

| Option | Shape | Advantages | Disadvantages |
|---|---|---|---|
| A. Plan 8.1 tree (feature-first) | `ingestion/`, `extraction/`, … plus `domain/`, `services/`, `infrastructure/`, `interfaces/` | Matches the plan text | No Document Intelligence home; mixes feature and layer axes; Personal Memory / Document Intelligence separation unenforceable |
| **B. Domain-first, then layer** | `personal/{domain,application}`, `documents/{domain,application}`; shared kernel; `infrastructure/`; `interfaces/` | Separation enforceable by import rules; feature modules preserved inside each layer; matches the two-domain architecture | Deeper paths; one-time deviation from plan 8.1 §4 |
| C. Layer-first | `domain/{personal,documents}`, `application/{personal,documents}` | Clear layering | Separation spread across trees, harder to own and review |

**Recommended structure (B)**

```text
memory-engine/
├── migrations/                      # Alembic environment and versions (8.2), outside src/
└── src/memory_engine/
    ├── config/  exceptions/  observability/   # existing (8.1), engine-wide
    ├── domain/                       # SHARED KERNEL (existing package): domain errors, plus from 8.2
    │                                 #   identifiers, OwnerScope, temporal value objects,
    │                                 #   typed references, shared enums (Decision 4)
    ├── personal/                     # PERSONAL MEMORY
    │   ├── domain/                   #   source, candidate, atomic memory and revisions, entity,
    │   │                             #   relationships, episode, profile: dataclasses and invariants
    │   ├── application/              #   use cases per feature (ingestion, extraction, entities,
    │   │                             #   resolution, storage, retrieval, consolidation, deletion)
    │   │                             #   and their ports (repository protocols)
    │   └── api.py                    #   public facade used by interfaces/
    ├── documents/                    # DOCUMENT INTELLIGENCE
    │   ├── domain/                   #   document, version, extracted representation, chunk,
    │   │                             #   location, embedding metadata, processing operation
    │   ├── application/              #   registration, parsing, chunking, indexing, retrieval,
    │   │                             #   evidence, lifecycle, and their ports
    │   └── api.py                    #   public facade, including the read-only evidence reader
    │                                 #   used by authorized document-to-memory extraction
    ├── infrastructure/               # ADAPTERS (created as needed)
    │   ├── persistence/              #   engine/session/unit of work, outbox, operations (8.2);
    │   │   ├── personal/  documents/ #   SQLAlchemy models + repository implementations per domain
    │   ├── object_storage/  embeddings/  tasks/   # 8.3 / 8.7 / 8.3
    └── interfaces/                   # Memory Engine contracts for the Orchestrator:
                                      #   commands, queries, results (Pydantic models)
```

How plan 8.1 §4 maps onto it:
- **Feature modules:** `ingestion`, `extraction`, `entities`, `resolution`, `storage`, `retrieval`, `consolidation` and `deletion` become modules under `personal/application/`.
- **`services/`:** becomes the per-domain `application/` layer.
- **`config/`, `exceptions/`, `observability/`, `infrastructure/`, `interfaces/`:** keep their plan names.

Nothing is created until it has content.

**Import rules**

These extend the existing `test_domain_boundary.py`:

| Package | May import | Must not import |
|---|---|---|
| `*/domain`, shared `domain` | stdlib, shared kernel, `exceptions` | `application`, `infrastructure`, `interfaces`, SQLAlchemy, drivers, Celery, storage SDKs, FastAPI; the *other* domain |
| `*/application` | own `domain`, shared kernel, own ports, `exceptions`, `observability`; `documents.api` (from `personal.application.extraction` only) | `infrastructure`; the other domain's internals |
| `documents/**` | anything in `documents` and the shared kernel | **anything in `personal`**. Document Intelligence stays independent; the dependency points one way |
| `infrastructure/**` | domains and application ports (to implement them) | `interfaces` |
| `interfaces/**` | `personal.api`, `documents.api`, shared kernel | internals of either domain; `infrastructure` |

**Further choices**

- **Domain model representation:** stdlib `@dataclass(frozen=True, slots=True)` plus enums keep the domain layer dependency-light. Pydantic is used for configuration and interface contracts. This is a Raven engineering convention, not a source requirement.
- **Document deletion and personal-memory provenance:** document deletion is announced as a domain event that `personal.application` handles (wired in a composition root). That preserves the one-way dependency.

### 5.2 Decision 2 — Database driver and access pattern

**Drivers**

| Driver | Sync | Async | SQLAlchemy 2.0 | Licence (verify) | Notes |
|---|---|---|---|---|---|
| **psycopg 3** | Yes | Yes | `postgresql+psycopg` | LGPL-3.0 | Actively developed; one driver for sync and async; server-side binding; good pgvector Python support |
| psycopg2 | Yes | No | Yes | LGPL-3.0 | Mature, but maintenance-focused; no path to async |
| asyncpg | No | Yes | `postgresql+asyncpg` | Apache-2.0 | Fast, but async only; forces async everywhere, including in Celery tasks |
| pg8000 | Yes | Partial | Yes | BSD-3 | Pure Python; slower; smaller ecosystem |

**Synchronous vs asynchronous SQLAlchemy**

| Concern | Sync (recommended) | Async |
|---|---|---|
| Celery workers | Natural: Celery tasks are synchronous; prefork processes each own an engine | Needs an event loop per task or async bridging; error-prone |
| FastAPI | Supported: plain `def` endpoints run in a thread pool | Native fit for `async def` |
| Transactions | Explicit `Session` per unit of work; `version_id_col` for optimistic concurrency (5.9.4) | Same features, plus `AsyncSession` lazy-loading pitfalls (implicit IO is disallowed) |
| Testing | pytest only; transactional rollback fixtures | Needs an async test plugin (a new dependency) and async fixtures |
| Throughput | Bounded by the thread pool and connection pool. Adequate for Memory Engine work, which is dominated by NLP and embedding computation in workers | Higher concurrency for IO-bound endpoints; no measured need yet |
| Reversibility | psycopg 3 also supports async, so switching later keeps the driver | Hard to reverse once spread through the code |

**Recommendation:** psycopg 3 with **synchronous SQLAlchemy 2.0 ORM**.

- **Dependencies:** `SQLAlchemy` 2.x, `alembic` and `psycopg[binary]` are added in 8.2. The `pgvector` Python package follows in 8.7. Whether production should use the C build is checked at deployment, and the LGPL licence is reviewed then too (dynamic linking).
- **Engine and pooling:** one engine per process, with SQLAlchemy `QueuePool` and `pool_pre_ping=True`. Pool size, overflow and recycle values are configurable, with defaults set at 8.2 and tuned by measurement (7.2 §9). Celery prefork children create their engine after fork (`worker_process_init`) and never inherit a parent's connections.
- **Transactions:**
  - one `Session` per unit of work
  - `READ COMMITTED` by default
  - optimistic concurrency through a version column on mutable authoritative rows (Atomic Memory current record, entities)
  - immutable revision rows
  - outbox rows written in the same transaction as the business change
  - no transaction held across embedding, parsing or network calls (plan 8.2 §8)
- **Ownership:** every repository method takes an `OwnerScope`, and every owned table has an `owner_id` column filtered in SQL, so isolation is enforced before or during retrieval (5.8.6).
- **Testing:**
  - unit tests use in-memory fakes of the repository ports
  - integration tests use a real PostgreSQL with pgvector, started by Docker Compose (7.7 §11)
  - each test runs inside a transaction that is rolled back
  - migrations are tested upgrade → downgrade → upgrade
  - a dedicated test database, never shared with development
- **Operational reliability:** connection loss surfaces as a `PersistenceError`; retries happen only at idempotent operation boundaries, never inside a half-done unit of work.

**Prerequisite:** Docker must be available locally for integration tests. This has not been verified on this machine.

### 5.3 Decision 3 — Embedding model and dimensions

**Principle:** the dimension is a property of the chosen model and is never picked on its own. Public benchmark scores are only a reason to shortlist a model; they say nothing about retrieval quality on Raven's data (7.3 §5.1).

**Shortlist for evaluation**

Verify each entry at evaluation time: licence, current revision, and whether newer releases exist. Pin the exact Hugging Face revision hash.

| Model | Dim | Max tokens | Params (approx.) | Licence (verify) | Role |
|---|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | 256 (longer input truncated) | 22M | Apache-2.0 | Reference baseline; likely too short for document chunks |
| `BAAI/bge-small-en-v1.5` | 384 | 512 | 33M | MIT | CPU-efficient candidate |
| `BAAI/bge-base-en-v1.5` | 768 | 512 | 110M | MIT | Quality candidate |
| `intfloat/e5-base-v2` | 768 | 512 | 110M | MIT | Quality candidate; requires `query:`/`passage:` prefixes |
| `intfloat/multilingual-e5-base` | 768 | 512 | 278M | MIT | Only if multilingual support is required (gap G6) |
| `BAAI/bge-m3` | 1024 | 8192 | 568M | MIT | Upper bound: long context and multilingual; heavy on CPU |

**Excluded categories:**
- **Models requiring `trust_remote_code`:** loading them executes repository code, a supply-chain risk.
- **Non-commercial or unclear licences.**
- **Hosted embedding APIs:** they send user data off-machine, and core processing is self-hosted (7.3 §5.1).

**Evaluation process (a bounded spike before 8.7)**

1. **Datasets.** Synthetic and versioned (Decision 14):
   - **Personal Memory:** about 300 atomic memories across the 8 categories, with about 150 queries graded for relevance. Include paraphrase, negation, temporal and technical-term cases.
   - **Document Intelligence:** about 20 synthetic or public-domain documents, chunked by the planned chunker, with about 100 questions labelled with evidence chunks.
2. **Isolate model quality.** Exact (non-ANN) cosine search per model, so indexing doesn't confound the comparison.
3. **Metrics:**
   - quality: Recall@5/10, nDCG@10 and MRR, per domain
   - cost: CPU latency p50/p95 for single and batch encoding; peak memory; model load time; disk size
   - storage: vector size at the model's dimension
4. **Hybrid check.** Repeat with PostgreSQL full-text search fused in, to measure what semantic search adds on top of keyword search.
5. **Decision rule** (user to confirm the margin): choose the smallest model whose nDCG@10 is within an agreed margin of the best on **both** domains. Use one shared model unless a domain shows a material gap (7.3 amendment §4).
6. **Record the configuration:**
   - model id and revision hash
   - sentence-transformers version
   - max sequence length, truncation and prefix rules
   - normalization (`normalize_embeddings=True` makes cosine and inner product equivalent)
   - metric (cosine, `vector_cosine_ops`)
   - dimension
7. **Index.** HNSW is the initial candidate (7.3 §10.2), validated against exact search for recall. pgvector indexes the `vector` type up to 2,000 dimensions, so every shortlisted model fits.

**Practical constraints:**
- **Size:** sentence-transformers pulls in PyTorch, a large install with deep paths (see 2.3).
- **Model weights:** downloaded once and cached; production must not download at runtime.
- **CPU-only:** inference must be viable on CPU, since no GPU is assumed.

**Migration:** every vector row records model and revision (5.4.19). A model change is a controlled re-embedding with side-by-side evaluation before activation (7.3 §13). Vectors from different models are never compared.

**Effect on 8.2:** 8.2 creates embedding *metadata* tables, with model, revision, dimension, status and source references, but no vector columns. Vector tables and indexes are created in 8.7, once the model is chosen.

### 5.4 Decision 4 — Relationship vocabulary

**Problems in the current specifications**
- **Overlapping memory-relationship lists:**
  - 5.4.27: 7 lowercase examples
  - 6.3.8: 9 uppercase types, adding `DEPENDS_ON` and `ABOUT_ENTITY`
  - 6.4.5 retrieval: repeats 6.3.8
  - plan 8.5 §7: adds "corrects"
- **Wrong endpoints:** `ABOUT_ENTITY` links a memory to an *entity*, but 5.4.27 says memory relationships connect two Atomic Memories.
- **Passive-voice supersession types:** 6.3.7 names them `UPDATED_BY`, `SUPERSEDED_BY`, `CORRECTED_BY`, which are inverses of 6.3.8's active `UPDATES`/`SUPERSEDES`. Stored both ways, the direction becomes ambiguous.
- **States listed as relationships:** 6.3.7's `EXPIRED` and `RETRACTED` describe a memory's state, not a link to another memory.
- **No entity-relationship catalogue:** only examples exist (`works_at`, `uses`).
- **No Atomic Memory lifecycle states** (gap G1).

**Naming conventions (applied to every vocabulary)**
- Values are lowercase `snake_case` strings, stored as PostgreSQL text with check constraints. Python `StrEnum` members are upper case.
- A relationship row reads **"source ‹type› target"** in active voice. Passive inverses are never stored; they're derived at query time.
- Symmetric types are flagged explicitly and stored once, with a canonical ordering (lower id as source), per 5.4.15.

**A. Entity relationships (entity → entity, directed unless marked symmetric)**

Each row carries `valid_from`/`valid_to` (valid time), `recorded_at` (transaction time), confidence, provenance and scope. Rows are never overwritten; they're closed with `valid_to` and replaced.

| Type | Meaning (source → target) | Symmetric |
|---|---|---|
| `works_at` | person → organization | No |
| `member_of` | person or organization → group or organization | No |
| `reports_to` | person → person | No |
| `knows` | person ↔ person | **Yes** |
| `part_of` | entity → containing entity (team → org, module → project) | No |
| `located_in` | entity → location | No |
| `uses` | project, person or organization → technology or product | No |
| `acquired_by` | organization → organization (identity event, 5.4.14) | No |
| `merged_into` | organization → organization (identity event) | No |
| `renamed_to` | entity → successor identity, when identity changes rather than an alias (5.4.14) | No |
| `related_to` | weak, unspecified association (last resort) | **Yes** |

The catalogue is extensible only by approval. Private relationships may point at shared entities, never the reverse (5.4.13).

**B. Memory relationships (Atomic Memory → Atomic Memory, 5.4.27)**

| Type | Meaning (source → target) | Effect on target | Symmetric |
|---|---|---|---|
| `supports` | source is independent evidence for target | none (may raise confidence via evaluation) | No |
| `contradicts` | source and target cannot both hold in the same context and time | both kept; may trigger `needs_review` | **Yes** |
| `supersedes` | source replaces target as the current representation | target → `historical`, `valid_to` set | No |
| `updates` | source refines target, which **remains current** (additive context) | none | No |
| `part_of` | source is a component of target (subtask → goal) | none | No |
| `derived_from` | source (an inferred memory) was derived from target (evidence) | none | No |
| `depends_on` | source's validity is conditional on target (6.3.8 addition) | re-evaluate source if target changes | No |
| `related_to` | weak association (last resort) | none | **Yes** |

A `supersedes` row carries a `reason`: `temporal_change` (a progression such as moving city), `replacement`, or `correction` (when the erroneous fact was a *separate* memory).

**Removed from memory relationships:**
- **`ABOUT_ENTITY`** becomes **Memory–Entity associations** (`memory_entity_link`), with a `role` of `subject`, `object`, `mentioned` or `context`. This is the "entity-to-memory association" of plan 8.5 §7.
- **"corrects"** (plan 8.5) is not a relationship. A correction of the *same* fact is a new **revision** of that memory (5.4.26). A correction by a *different* memory is `supersedes` with reason `correction`.

**C. Revision change types (on immutable revision rows, 5.4.7, mapping 6.3.7)**

| Value | Replaces 6.3.7 | Meaning |
|---|---|---|
| `created` | — | first revision |
| `updated` | `UPDATED_BY` | attribute or context change (6.3.6) |
| `corrected` | `CORRECTED_BY` | the prior content was wrong (5.4.26) |
| `evidence_added` | — | merge or duplicate evidence attached (`MERGE` / `NO_CHANGE` with evidence) |
| `superseded` | `SUPERSEDED_BY` | this memory stopped being current because another memory `supersedes` it |
| `expired` | `EXPIRED` | time-limited validity ended |
| `retracted` | `RETRACTED` | the user withdrew the assertion |
| `reclassified` | — | category or origin change (5.4.9) |

**D. Atomic Memory lifecycle status (fills gap G1; separate from candidate states, retention classes and deletion states)**

`active` → `historical` (superseded or expired, still retrievable for historical queries) · `needs_review` · `retracted` · `deletion_pending` (tombstoned, invisible) · `deleted`.

Retention classes (6.5.3) remain a separate attribute.

**E. Temporal meaning: attributes, not relationship names**
- `valid_from` / `valid_to`: when it was true in the world.
- `recorded_at` / `superseded_at`: when Raven learned it or replaced it.
- `observed_at`: when the source said it.

These follow the bitemporal model (5.3.4, 6.3.7 §9.3). "Progression" is `supersedes(reason=temporal_change)` plus valid-time continuity.

**F. Evidence and derived knowledge: provenance records, not memory relationships**
- **Evidence:** Provenance Record links (memory → source, candidate or document chunk) carry a `role` of `origin`, `supporting`, `contradicting` or `correcting`. This is distinct from memory-to-memory `supports`.
- **Derived records:** episodes, semantic consolidation results and profiles link to the atomic memories they came from through their own association records (Episode Membership, Profile–Memory Association, Consolidation Result sources). Derived records never become atomic memories.

**G. Resolution outcomes (6.3, unchanged)**

`create_new`, `merge`, `update_existing`, `link_existing`, `supersede`, `needs_review`, `reject`, `no_change`. These are processing decisions recorded in resolution audit, not stored relationships.

**Mapping the categories in the user's brief**

| Brief category | Representation |
|---|---|
| Duplicate | outcome `no_change` or `merge`; revision `evidence_added`; no relationship |
| Related | `related_to` |
| Contradictory | `contradicts` (+ `needs_review` if unresolved) |
| Corrective | revision `corrected`, or `supersedes(reason=correction)` across memories |
| Updated | revision `updated`, or `updates` across memories |
| Progression | `supersedes(reason=temporal_change)` + valid time |
| Supersession | `supersedes` |
| Supporting | `supports` (memory–memory), or provenance role `supporting` (source evidence) |
| Derived | `derived_from` (inferred memories); association records (derived knowledge) |

### 5.5 Decision 5 — Document record placement and ownership

**Options**

| Option | Advantages | Disadvantages |
|---|---|---|
| **A. `memory` schema, `doc_`-prefixed tables** | Follows 7.2 and its amendment; one owner role (`raven_memory_role`); one Alembic history; simple transactions where needed | Separation relies on naming, packages and tests rather than a schema boundary |
| B. Second Memory-Engine schema (e.g. `memory_documents`) | Schema-level grants; easy to audit | Deviates from the amendment's "memory schema"; more migration and `search_path` complexity; needs an architecture change |
| C. Separate database | Strongest isolation | Rejected by 7.2 amendment §11; breaks the shared deployment, transactions and backups |
| D. Object storage only | Cheap | Rejected: no SQL ownership filtering, full-text search, versions or deletion tracking |

**Recommendation: A.**
- **Prefixes:** `pm_` for Personal Memory, `doc_` for Document Intelligence, `me_` for shared engine plumbing (outbox, operations, idempotency).
- **Ownership:** all tables owned and written only by the Memory Engine role.

**Logical records → tables (named at 8.2)**

| Logical record (5.4 amendment §3) | Table | Key rules |
|---|---|---|
| Document | `doc_document` | `owner_id`, `current_version_id`, lifecycle and deletion state; the filename is not an identity (plan 8.2 §4.1) |
| Document Version | `doc_document_version` | immutable; checksum, media type, size, object key of the original; extraction status |
| Extracted Document Representation | `doc_extracted_representation` | per version; method and version; large text in object storage; structural metadata in PostgreSQL |
| Document Chunk | `doc_chunk` | per representation; ordinal; chunk text **in PostgreSQL** (needed for the full-text `tsvector`); checksum; chunker version; `owner_id` copied onto the row for filter-first queries |
| Chunk Location and Provenance | `doc_chunk_location` | one-to-many per chunk (chunks can span pages or sections) |
| Document Embedding Metadata | `doc_embedding` | model, revision, dimension, status, chunk reference. The vector payload table `doc_embedding_vector` arrives in 8.7 (Decision 3) |
| Document Processing Operation | `doc_processing_operation` | stage, status, attempts, idempotency key, timestamps, safe error code |

**Rules that come with this placement:**
- **Isolation:** every `doc_` row carries `owner_id` and is filtered in SQL before ranking. No database view or query joins `pm_` and `doc_` tables except the evidence path below.
- **Versioning:** versions, representations, chunks and embeddings are immutable per version. Retrieval defaults to the current version and must label older-version evidence (plan 8.2 §4.2).
- **Deletion and foreign keys:** no implicit `ON DELETE CASCADE` on user data, in either domain. Deletion runs as explicit, verifiable steps in the deletion workflow (6.5.9; plan 8.10), so every removal is counted and checked. Foreign keys use `RESTRICT`.
- **Cross-domain evidence:**
  - personal-memory provenance references document evidence through `pm_document_evidence_ref`, holding `document_id`, `version_id`, a nullable `chunk_id`, and location
  - its foreign keys to `doc_` tables use `RESTRICT`
  - before deleting a document, the deletion workflow evaluates dependent memories separately (memory/05 §18; plan 8.10 §8), sets these references to `source_deleted`, and nulls the chunk reference while keeping the opaque identifiers
  - the database therefore stops silent dangling references, and independent memories are never deleted automatically
- **Indexes:**
  - B-tree on `(owner_id, …)` for every access path
  - GIN on `doc_chunk.tsv`
  - vector index on `doc_embedding_vector` (8.7)
  - kept separate from the `pm_` indexes (plan 8.7 §6)
- **Object storage keys:** opaque, owner-partitioned: `documents/{owner_id}/{document_id}/{version_id}/original` and `memory-sources/{owner_id}/{source_id}`. Raw filenames never appear in keys.

### 5.6 Architectural consistency findings

| ID | Finding | Sources | Proposed handling |
|---|---|---|---|
| G1 | Atomic Memory lifecycle states are not defined anywhere | 6.2 §8.6 says candidate states "are not the final Atomic Memory lifecycle states"; 5.3.6 delegates states to engines | Decision 4, part D (approval) |
| G2 | Memory relationship lists disagree (5.4.27 / 6.3.8 / 6.4.5 / plan 8.5 "corrects") | as cited | Decision 4, part B (approval) |
| G3 | `ABOUT_ENTITY` modelled as a memory relationship, but it targets an entity | 6.3.8 vs 5.4.27 rule 2 | Memory–Entity association (approval) |
| G4 | Passive and state-like supersession types | 6.3.7 vs 6.3.8 | Decision 4, part C (approval) |
| G5 | Document parsing appears in memory ingestion and in the document pipeline | 6.2.1 §3.2 vs memory/05 | Decision 13 (approval). **Closed 2026-11-11**: document pipeline owns parsing (7.1 §24.2) |
| G6 | No language requirement, while model selection depends on it | 7.3 §5.1 "where required"; 7.5 | **User to state** whether non-English content is in scope |
| G7 | Derived-profile ownership differs between Phase 2 and Phase 6/8 | phase-02 vs 6.5.6, plan 8.9 | Decision 12 |

No approved decision is changed by this document. Where a recommendation would change or extend one (Decisions 1, 4, 5, 7, 13), it is marked for approval.

---

## 6. Recommended architectural choices (summary)

| # | Recommendation |
|---|---|
| 1 | Domain-first `personal/` and `documents/` with `domain`/`application` layers; shared kernel `domain/`; `infrastructure/`; `interfaces/`; one-way `personal → documents.api` dependency; import rules enforced by tests |
| 2 | psycopg 3 + synchronous SQLAlchemy 2.0; one engine per process; `QueuePool` + pre-ping; `READ COMMITTED` + optimistic versions; outbox in the same transaction; Docker Compose PostgreSQL for integration tests |
| 3 | Shortlist plus a Raven-specific evaluation spike before 8.7; dimension follows the model; 8.2 stores embedding metadata only |
| 4 | Four vocabularies (entity relationships, memory relationships, revision change types, memory lifecycle status) + Memory–Entity associations + provenance roles; active-voice, directional, bitemporal attributes |
| 5 | `memory` schema with `pm_`/`doc_`/`me_` prefixes; no implicit cascades; RESTRICT-guarded cross-domain evidence references; owner id on every row |
| 6 | Per-request document-to-memory authorization record |
| 7 | Reorder: 8.12 before 8.11; 8.4 document path after 8.12 |
| 8 | Storage port; filesystem fake for unit tests; S3-compatible container for integration tests |
| 9 | Outbox and operation tables in 8.2; Celery and RabbitMQ in 8.3 |
| 10 | Caller-supplied `OwnerScope`; opaque `owner_id`; no Memory Engine user table |
| 11 | Private entities only until a curated shared catalogue is approved |
| 12 | Profiles in consolidation (8.9) |
| 13 | Document pipeline owns parsing |
| 14 | Versioned synthetic datasets per capability, retrieval set first |
| 15 | Evaluate pypdf and python-docx at 8.12 start |

---

## 7. Decision dependencies

```text
10 OwnerScope ─┐
1 Layout ──────┼──► 2 Driver ──► 9 Outbox timing ──► (8.3) Celery, 8 Object storage
4 Vocabulary ──┤                                         │
5 Placement ───┘                                         ▼
     │                                         13 Parsing ownership ──► 15 Parsers (8.12)
     ▼                                                   │
   8.2 can start (vector columns deferred)               ▼
                                              6 Authorization ──► 7 Sequence (8.4 doc path after 8.12)
14 Datasets ──► 3 Embedding model (before 8.7)
G6 Language ──► 3
4 ──► 11 Shared entities (8.5)        12 Profiles (8.9)
```

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Vocabulary drift between code and specs | One enum module in the shared kernel, mirrored by database check constraints; the specs updated in the same approved change |
| Cross-user leakage via joins, shared entities or vector search | `owner_id` on every row (including chunks and embeddings); repositories require `OwnerScope`; shared entities disabled; isolation tests per repository |
| Document content entering personal memory | One-way package dependency; authorization records; `doc_` and `pm_` never joined except through evidence references; boundary tests |
| Silent cascade deletion, or dangling evidence | No implicit cascades; RESTRICT foreign keys; explicit deletion steps with verification |
| Embedding lock-in or a poor model | Metadata-first schema; evaluation before 8.7; revision pinning; controlled re-embedding |
| Async needs discovered later | psycopg 3 supports async without a driver change; keep IO behind ports |
| Windows path-length failures with ML dependencies | Short repository root (under 100 characters); `UV_PROJECT_ENVIRONMENT` fallback; documented in `KNOWN_CONSTRAINTS.md` |
| Integration tests unavailable without Docker | Verify Docker before 8.2. Unit tests use port fakes so they never depend on Docker |
| LGPL driver licence | Review before production; dynamic linking via pip/uv is the normal use |
| Deadline (2026-11-15) | Approve Decisions 1, 2, 4, 5 and 10 first; 8.2 can then start, and the rest are decided just in time |

---

## 9. Approval requirements

| Needs explicit approval now (to start 8.2) | Needs approval later | No approval needed |
|---|---|---|
1, 2, 4 (incl. G1, G3), 5, 10 and the vector-storage deferral to 8.7: **all approved 2026-11-11** | 3 Model + evaluation spike (before 8.7) · 6 Authorization (before the 8.4 document path) · 7 Sequence · 8 Object storage (8.3) · 11 Shared entities (8.5) · 13 Parsing (8.3) · 14 spaCy model (8.4) · 15 Parsers (8.12) · G6 language scope | 9 Outbox timing · 12 Profiles (unless editing Phase 2) · 14 dataset approach |

---

## 10. Recommended order for resolving decisions

1. **Now (before 8.2):** 10 → 1 → 4 (with G1, G3) → 5 → 2, and confirm vector columns move to 8.7. Confirm Docker availability.
2. **During 8.2:** 9 (schema only).
3. **Before 8.3:** 8, 13.
4. **Before 8.4:** 6, 7, 14 (spaCy).
5. **Before 8.5:** 11.
6. **Before 8.7:** G6, then 3 (evaluation spike using the Decision 14 retrieval dataset).
7. **Before 8.9:** 12. **Before 8.12:** 15.

---

## 11. Exact next implementation step

After the user approves Decisions 1, 2, 4, 5 and 10 and the vector-column deferral, and Docker is confirmed:

**Phase 8.2, step 1. Persistence foundation and core Personal Memory tables.** In a new branch from `main`:

1. Add `SQLAlchemy` 2.x, `alembic` and `psycopg[binary]` to `memory-engine`; lock.
2. Add the shared kernel types: identifiers, `OwnerScope`, temporal value objects, and the approved vocabulary enums.
3. Add `infrastructure/persistence/`: engine and session factory, unit of work, and the `me_operation` table. *(Updated 2026-11-11: `me_outbox` moved to 8.3 per Decision 9, 7.1 §23.6.)*
4. Add `memory-engine/migrations/`: an Alembic environment targeting the `memory` schema.
5. Create the first migration: `pm_memory_source`, `pm_memory_candidate`, `pm_atomic_memory` + `pm_atomic_memory_revision`, `pm_provenance`, with `owner_id`, version columns and check constraints.
6. Write repositories with ownership enforcement, plus unit tests (fakes) and integration tests (PostgreSQL via Docker Compose; upgrade/downgrade/upgrade migration test).

Document tables (`doc_*`) follow as 8.2 step 2. Entity, relationship, episode and profile tables follow in later 8.2 steps, per plan 8.2.

**Phase 8.2 has not started. This step must not begin until the user approves it.**
