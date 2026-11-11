# Known Constraints

## Permanent constraints

Changing any of these requires an approved architectural decision, recorded in the source documents first.

1. **No generative LLM APIs** in Raven processing.
2. **No locally hosted generative LLMs** in Raven processing. Use deterministic rules, conventional NLP, statistical methods, embeddings, non-generative ML, extractive processing and deterministic answer templates.
3. **Correctness before performance.** Performance never weakens correctness, deletion, identity or evidence obligations. Optimize only measured bottlenecks.
4. **Privacy and security are non-negotiable.** User ownership, isolation and authorization apply everywhere; no cross-user access; secrets never in code, Git or logs. See [security-and-privacy](../../.claude/rules/security-and-privacy.md).
5. **Personal Memory and Document Intelligence are separate logical domains** with separate ownership, models, retrieval and lifecycle.
6. **Document chunks are not personal memories.** Uploads never auto-create memories. Document facts enter memory only via the authorized candidate → resolution workflow.
7. **Similarity is not proof.** It generates candidates; it never alone justifies a merge or an answer.
8. **Evidence and provenance are preserved.** Document answers cite document, version, chunk and location. Verified, inferred, low-confidence, conflicting and missing information stay distinguishable.
9. **Deletion propagates to derived artifacts** (embeddings, indexes, caches, profiles, chunks, objects) and survives backup restoration.
10. **No unnecessary infrastructure.** No dedicated vector database, document database, search engine or service split without measured justification and approval.
11. **Architectural changes require documented justification** and user approval, never a silent change.
12. ML outputs are signals; deterministic validation protects authoritative state changes. User data is not used for automatic training.
13. Current observations never silently overwrite history. Explicit forgetting overrides expiry and archival.
14. Engine ownership: each engine is the only writer of its data. Memory and Research never orchestrate each other.

## Deferred decisions

Not decided. Do not guess them or treat them as approved. Full list in [TECHNOLOGY_DECISIONS.md](TECHNOLOGY_DECISIONS.md#deferred).

- Embedding model, dimensions, index type and parameters, chunk size and overlap, reranker, retrieval thresholds and weights.
- The embedding model, dimension, metric and index type (Decision 3), needed before Phase 8.7. Vector storage is deferred to 8.7, and 8.2 creates embedding metadata only (approved 2026-11-11). The PostgreSQL driver and access pattern, package layout, vocabularies, document record placement and owner identity were approved on 2026-11-11 ([TECHNOLOGY_DECISIONS.md](TECHNOLOGY_DECISIONS.md#approved-phase-82-decisions)). The Python version, type checker, project layout, test location and configuration approach are approved, not deferred ([TECHNOLOGY_DECISIONS.md](TECHNOLOGY_DECISIONS.md#approved-phase-81-project-setup-decisions)).
- Parser adoption (pypdf, python-docx), OCR, advanced layout and table extraction.
- Identity and secrets providers, cloud and hosting, CI provider, coverage thresholds.
- Retention periods, backup frequency and retention, RPO/RTO, rate and file-size limits, retry counts, resource budgets.

## Known technical limitations

- **Implemented:** the Phase 8.1 foundation and Phase 8.2 steps 1–5. That is PostgreSQL persistence for Memory Source, Candidate, Atomic Memory with revisions, and Provenance; for documents, versions, extracted representations, chunks with locations, embedding metadata, processing operations and document evidence; and for entities, aliases, mentions, resolution history, entity and memory relationships, and memory–entity associations; and for episodes with membership and events, profiles with revisions, supporting memories and refresh history, memory categories, and memory embedding metadata (no vectors before 8.7); and for source processing events, candidate evaluations, correction requests, and deletion operations with their ledger. No consolidation-result table exists until 8.9 defines one, and nothing performs a deletion until 8.10.
- Entities are private only (Decision 11). Shared entities need an approved curation process and a migration before they can exist. It is persistence only: no ingestion, parsing, chunking, embedding generation, resolution, retrieval ranking or deletion workflow exists, and there is no broker or object storage.
- Document keyword search uses the language-neutral `simple` text-search configuration until the language requirement (G6) is decided.
- Integration tests skip, rather than fail, when the Docker PostgreSQL service is not running. A green test run without Docker does not cover persistence; check that the integration tests were not skipped.
- Memory Source `content_ref` is optional until object storage exists (Phase 8.3).
- **Accepted deferrals from the 8.2 acceptance review (owner, 2026-11-11):**
  - Object-storage failure tests (object storage unavailable, partial upload; plan 8.2 §13) move to Phase 8.3, which introduces object storage.
  - Least-privilege database roles (7.2 §3 and §17; 7.1 §23.3) move to the first deployment environment (7.8). Until then the migrations create no roles or grants, and tests use a single database user.
- On Windows, a repository at a very long path cannot load mypy's compiled DLLs from `.venv` ("filename or extension is too long"), even with long paths enabled, because the DLL loader does not honour that setting. Verified 2026-11-11: it fails at a 180-character repository root (extension paths 256–263 characters) and passes from a 109-character root. Keep the repository root short (under about 100 characters), especially before adding deep ML dependencies such as PyTorch; otherwise point `UV_PROJECT_ENVIRONMENT` at a shorter path.
- Docker for PostgreSQL integration tests (Phase 8.2): Verified 2026-11-11: Docker Engine 29.9.3 (linux/amd64), Compose v5.5.1; a throwaway `pgvector/pgvector:pg17` container started, accepted connections (PostgreSQL 17.11), loaded `vector` 0.8.7 and ran a distance query, then was removed. Docker Desktop must be running.
- OCR is not supported; scanned PDFs cannot be assumed processable.
- Advanced PDF layout and table extraction are not covered by the baseline.
- No CI pipeline exists, so the quality gates run only by hand.
- On Windows, a default `git clone` fails checkout on over-long doc paths under `docs/implementation-plans/Phase-08-memory-engine/`. Use `git config --global core.longpaths true` or a short clone path.

## Open documentation issues

Reported, not resolved.

1. **Algorithm numbering:** `docs/algorithms/memory/05-document-processing-and-rag.md` declares no subphase number; the old index used 6.11, which `orchestrator/01` now uses.
2. **Filenames:** `docs/algorithms/orchestrator/02-result-validation-response-assembly` has no `.md` extension, and `research/05-retrival-…` misspells "retrieval". References match the actual names; renaming is undecided.
3. **Historical phase docs:** `docs/architecture/phase-01`…`04` keep their original "Deferred" sections (database choices deferred). They are superseded by Phases 5–7, as noted in the indexes.
4. **Overlap:** the 7.3 and 7.5 amendments both describe document embeddings and hybrid retrieval.
5. ~~**Storage placement**~~ — resolved 2026-11-11 by Decision 5: `memory` schema with `pm_`/`doc_`/`me_` prefixes ([7.1 §23.3](../technical-decisions/01-baseline-technology-stack.md)).
6. ~~**Phase 8.1 plan module tree**~~ — resolved 2026-11-11 by Decision 1: domain-first layout ([7.1 §23.1](../technical-decisions/01-baseline-technology-stack.md)), which supersedes plan 8.1 §4. (The earlier conflicts over test location, standalone vs workspace layout, and 8.1 dependency timing were resolved by the 2026-11-11 approved decisions, and plan 8.1 was updated to match.)
7. **Specification gaps for Phase 8.2** (see the [decision review](PHASE-8-2-ARCHITECTURE-DECISION-REVIEW.md) §5.6):
   - *Resolved 2026-11-11:* Atomic Memory lifecycle states (G1) and the conflicting relationship vocabularies (G2–G4) are defined by the approved Phase 8.2 amendment of [5.4](../data-models/phase-05-memory-engine-models.md).
   - Still open: no language requirement is stated, although embedding-model selection depends on it (G6). Parsing ownership (G5) and profile ownership (G7) are Decisions 13 and 12.
8. **No `docs/technical-decisions.md`:** some instructions refer to it. Decisions are recorded in the relevant file under `docs/technical-decisions/`.
9. **Ratio label wording:** `PROJECT_ARCHITECTURE.md`, `README.md`, phase-02/03 and this directory label the 70:30 / 55:45 / 45:55 ratios "Optimization : Performance". The phase-02 purpose text ("favors memory quality, provenance … over raw throughput") reads them as *correctness/quality : optimization/performance*. The meaning is consistent; the label is ambiguous. Relabeling is undecided.
