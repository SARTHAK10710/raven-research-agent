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
- PostgreSQL driver and sync vs async database access (Phase 8.2). The Python version, type checker, project layout, test location and configuration approach are approved, not deferred ([TECHNOLOGY_DECISIONS.md](TECHNOLOGY_DECISIONS.md#approved-phase-81-project-setup-decisions)).
- Parser adoption (pypdf, python-docx), OCR, advanced layout and table extraction.
- Identity and secrets providers, cloud and hosting, CI provider, coverage thresholds.
- Retention periods, backup frequency and retention, RPO/RTO, rate and file-size limits, retry counts, resource budgets.

## Known technical limitations

- **Nothing is implemented.** No code, dependencies, database, broker, storage or tests exist.
- OCR is not supported; scanned PDFs cannot be assumed processable.
- Advanced PDF layout and table extraction are not covered by the baseline.
- No CI pipeline exists.

## Open documentation issues

Reported, not resolved.

1. **Algorithm numbering:** `docs/algorithms/memory/05-document-processing-and-rag.md` declares no subphase number; the old index used 6.11, which `orchestrator/01` now uses.
2. **Filenames:** `docs/algorithms/orchestrator/02-result-validation-response-assembly` has no `.md` extension, and `research/05-retrival-…` misspells "retrieval". References match the actual names; renaming is undecided.
3. **Historical phase docs:** `docs/architecture/phase-01`…`04` keep their original "Deferred" sections (database choices deferred). They are superseded by Phases 5–7, as noted in the indexes.
4. **Overlap:** the 7.3 and 7.5 amendments both describe document embeddings and hybrid retrieval.
5. **Storage placement:** the 7.2 amendment places document records in the `memory` schema "subject to reconciliation with Phase 5". Not yet reconciled.
6. **Phase 8.1 plan:** the proposed module tree (plan 8.1 §4) has no Document Intelligence area; where Personal Memory and Document Intelligence code lives inside the package is undecided. (The earlier conflicts over test location, standalone vs workspace layout, and 8.1 dependency timing were resolved by the 2026-11-11 approved decisions, and plan 8.1 was updated to match.)
7. **No `docs/technical-decisions.md`:** some instructions refer to it. Decisions are recorded in the relevant file under `docs/technical-decisions/`.
