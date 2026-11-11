"""Personal Memory: facts, preferences, decisions and history about the user.

Kept separate from Document Intelligence (``memory_engine.documents``): document
chunks are never personal memories, and this package must not import document
internals (Phase 7.1 section 23.1).
"""
