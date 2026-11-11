"""Document Intelligence: uploaded documents, versions, extraction, chunks, embeddings.

A separate logical domain from Personal Memory (Phase 5.4 Document
Intelligence amendment). Document chunks are never personal memories, and
uploading a document never creates memories. This package must not import
``memory_engine.personal`` (Phase 7.1 section 23.1); the dependency points one way.
"""
